"""SIH26042 backend (online version): Hindi -> Punjabi translation, TTS, worksheets.

Flow for /translate:  verified phrase bank  ->  cached machine result  ->  translation engine.
The browser handles Hindi speech-to-text (Web Speech API); this API does the rest.
"""
import csv
import hashlib
import io
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import (Depends, FastAPI, File, Header, HTTPException, Query,
                     UploadFile)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from . import db, engines

SUPPORTED_TTS = {"pa", "hi", "en"}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="SIH26042 Vernacular Pedagogy API (Hindi -> Punjabi)", version="0.2.0",
              lifespan=lifespan)

# Dev default allows any origin. In production set CORS_ORIGINS=https://your-frontend.app
_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["*"],
                   allow_headers=["*"])

# ---------- helpers ----------
_PUNCT = re.compile(r"[।॥\.\,\?\!\-\"'’‘“”;:()]+")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", _PUNCT.sub(" ", text or "")).strip().lower()


def require_admin(x_api_key: str = Header(default="")) -> None:
    expected = os.environ.get("ADMIN_API_KEY", "dev-key")
    if not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(401, "Invalid or missing X-API-Key")


def row_to_dict(r) -> dict:
    return {"id": r["id"], "hindi": r["hindi"], "target_text": r["target_text"],
            "lang": r["lang"], "category": r["category"], "grade": r["grade"],
            "outcome_code": r["outcome_code"], "verified": bool(r["verified"]),
            "source": r["source"]}


def upsert_phrase(conn, p: dict) -> int:
    hn = normalize(p["hindi"])
    if not hn:
        raise HTTPException(400, "Hindi text is empty")
    lang = p.get("lang") or "pa"
    conn.execute(
        """INSERT INTO phrases(hindi, hindi_norm, lang, target_text, category, grade,
               outcome_code, verified, source, updated_at)
           VALUES (?,?,?,?,?,?,?,?,'human',?)
           ON CONFLICT(hindi_norm, lang) DO UPDATE SET
               hindi=excluded.hindi, target_text=excluded.target_text,
               category=excluded.category, grade=excluded.grade,
               outcome_code=excluded.outcome_code, verified=excluded.verified,
               source='human', updated_at=excluded.updated_at""",
        (p["hindi"].strip(), hn, lang, (p.get("target_text") or "").strip(),
         p.get("category") or "general", p.get("grade"), p.get("outcome_code") or "",
         1 if p.get("verified") else 0, db.now()))
    return conn.execute("SELECT id FROM phrases WHERE hindi_norm=? AND lang=?",
                        (hn, lang)).fetchone()["id"]


def cache_machine_translation(conn, hindi: str, lang: str, text: str) -> None:
    hn = normalize(hindi)
    row = conn.execute("SELECT id, target_text FROM phrases WHERE hindi_norm=? AND lang=?",
                       (hn, lang)).fetchone()
    if row:
        if row["target_text"] == "":
            conn.execute("UPDATE phrases SET target_text=?, source='machine', updated_at=? WHERE id=?",
                         (text, db.now(), row["id"]))
    else:
        conn.execute(
            """INSERT INTO phrases(hindi, hindi_norm, lang, target_text, category, verified,
                   source, updated_at) VALUES (?,?,?,?,'cached',0,'machine',?)""",
            (hindi.strip(), hn, lang, text, db.now()))
    conn.commit()


def do_translate(conn, text: str, source: str, target: str, min_score: float) -> dict:
    start = time.perf_counter()
    result = None
    # 1) phrase bank / cache (only Hindi source is stored)
    if source == "hi":
        rows = {r["id"]: r for r in conn.execute(
            "SELECT * FROM phrases WHERE lang=? AND target_text<>''", (target,)).fetchall()}
        choices = {i: r["hindi_norm"] for i, r in rows.items()}
        best = process.extractOne(normalize(text), choices, scorer=fuzz.ratio,
                                  score_cutoff=min_score) if choices else None
        if best:
            _, score, pid = best
            r = rows[pid]
            result = {"text": r["target_text"], "origin": "verified_bank" if r["verified"] else "cache",
                      "confidence": round(score, 1), "matched_hindi": r["hindi"]}
    # 2) translation engine
    if result is None:
        try:
            out = engines.translate(text, source, target)
        except engines.EngineError as e:
            raise HTTPException(502, str(e))
        if source == "hi" and len(text) <= 300:
            cache_machine_translation(conn, text, target, out)
        result = {"text": out, "origin": "machine", "confidence": None, "matched_hindi": None}
    result.update({"query": text, "source": source, "target": target,
                   "latency_ms": round((time.perf_counter() - start) * 1000, 1)})
    return result


# ---------- request models ----------
class PhraseIn(BaseModel):
    hindi: str
    target_text: str = ""
    lang: str = "pa"
    category: str = "general"
    grade: Optional[int] = None
    outcome_code: str = ""
    verified: bool = False


class BatchIn(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=50)
    source: str = "hi"
    target: str = "pa"


# ---------- public endpoints ----------
@app.get("/health")
def health():
    return {"status": "ok", "translation_engine": os.environ.get("TRANSLATION_ENGINE", "google_free")}


@app.get("/api/v1/stats")
def stats(conn=Depends(db.get_conn)):
    q = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
    return {"phrases": q("SELECT COUNT(*) FROM phrases"),
            "with_translation": q("SELECT COUNT(*) FROM phrases WHERE target_text<>''"),
            "verified": q("SELECT COUNT(*) FROM phrases WHERE verified=1"),
            "machine_cached": q("SELECT COUNT(*) FROM phrases WHERE source='machine'")}


@app.get("/api/v1/translate")
def translate(q: str = Query(..., min_length=1, max_length=500), source: str = "hi",
              target: str = "pa", min_score: float = Query(80, ge=0, le=100),
              conn=Depends(db.get_conn)):
    """Translate one sentence. Response includes latency_ms for the 3-second timer."""
    return do_translate(conn, q, source, target, min_score)


@app.post("/api/v1/translate-batch")
def translate_batch(body: BatchIn, conn=Depends(db.get_conn)):
    """Translate many words/sentences at once (flashcards, custom worksheets)."""
    return {"results": [do_translate(conn, t, body.source, body.target, 80)
                        for t in body.texts if t.strip()]}


@app.get("/api/v1/phrases")
def list_phrases(lang: str = "pa", category: Optional[str] = None, grade: Optional[int] = None,
                 verified_only: bool = False, limit: int = Query(100, ge=1, le=500),
                 offset: int = Query(0, ge=0), conn=Depends(db.get_conn)):
    sql, args = "SELECT * FROM phrases WHERE lang=? AND target_text<>''", [lang]
    if category:
        sql += " AND category=?"; args.append(category)
    if grade is not None:
        sql += " AND grade=?"; args.append(grade)
    if verified_only:
        sql += " AND verified=1"
    sql += " ORDER BY verified DESC, id LIMIT ? OFFSET ?"
    args += [limit, offset]
    return {"phrases": [row_to_dict(r) for r in conn.execute(sql, args).fetchall()]}


@app.get("/api/v1/tts")
def tts(text: str = Query(..., min_length=1, max_length=300), lang: str = "pa"):
    """Text -> mp3 audio (cached on disk by text hash)."""
    if lang not in SUPPORTED_TTS:
        raise HTTPException(400, f"lang must be one of {sorted(SUPPORTED_TTS)}")
    os.makedirs(db.TTS_DIR, exist_ok=True)
    path = os.path.join(db.TTS_DIR, hashlib.sha1(f"{lang}|{text}".encode()).hexdigest() + ".mp3")
    if not os.path.isfile(path):
        try:
            engines.synthesize(text, lang, path)
        except engines.EngineError as e:
            raise HTTPException(502, str(e))
    return FileResponse(path, media_type="audio/mpeg")


@app.get("/api/v1/worksheet")
def worksheet(grade: Optional[int] = None, category: Optional[str] = None,
              count: int = Query(10, ge=1, le=30), lang: str = "pa",
              conn=Depends(db.get_conn)):
    """Bilingual worksheet content (JSON). The frontend lays it out and prints to PDF,
    so the browser handles Hindi/Gurmukhi fonts correctly."""
    sql, args = "SELECT * FROM phrases WHERE lang=? AND target_text<>''", [lang]
    if grade is not None:
        sql += " AND grade=?"; args.append(grade)
    if category:
        sql += " AND category=?"; args.append(category)
    sql += " ORDER BY verified DESC, id LIMIT ?"
    args.append(count)
    rows = conn.execute(sql, args).fetchall()
    items = [{"n": i + 1, "hindi": r["hindi"], "target_text": r["target_text"],
              "verified": bool(r["verified"]), "outcome_code": r["outcome_code"]}
             for i, r in enumerate(rows)]
    return {"title": "Bilingual Worksheet", "grade": grade, "category": category,
            "lang": lang, "items": items}


# ---------- admin endpoints ----------
@app.post("/api/v1/admin/phrases", dependencies=[Depends(require_admin)])
def add_or_update_phrase(p: PhraseIn, conn=Depends(db.get_conn)):
    pid = upsert_phrase(conn, p.model_dump())
    conn.commit()
    return {"id": pid}


@app.delete("/api/v1/admin/phrases/{phrase_id}", dependencies=[Depends(require_admin)])
def delete_phrase(phrase_id: int, conn=Depends(db.get_conn)):
    cur = conn.execute("DELETE FROM phrases WHERE id=?", (phrase_id,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "Phrase not found")
    return {"deleted": phrase_id}


@app.post("/api/v1/admin/import-csv", dependencies=[Depends(require_admin)])
async def import_csv(file: UploadFile = File(...), conn=Depends(db.get_conn)):
    """Columns: hindi, target_text, category, grade, outcome_code, verified (lang defaults to pa)."""
    text = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "hindi" not in reader.fieldnames:
        raise HTTPException(400, "CSV must have a 'hindi' column")
    count = 0
    for row in reader:
        if not (row.get("hindi") or "").strip():
            continue
        grade = (row.get("grade") or "").strip()
        upsert_phrase(conn, {
            "hindi": row["hindi"], "target_text": (row.get("target_text") or "").strip(),
            "lang": (row.get("lang") or "pa").strip(),
            "category": (row.get("category") or "general").strip(),
            "grade": int(grade) if grade.isdigit() else None,
            "outcome_code": (row.get("outcome_code") or "").strip(),
            "verified": (row.get("verified") or "").strip().lower() in {"1", "true", "yes"}})
        count += 1
    conn.commit()
    return {"imported": count}
