"""SIH26042 content-sync backend.

The tablet app does the real work offline. This server only:
  1. stores the verified Hindi -> Santali phrase bank + audio,
  2. lets tablets sync (full package once, then deltas),
  3. gives admins a way to add / correct content,
  4. offers a /translate endpoint for testing the matching logic.
"""
import csv
import io
import json
import os
import re
import secrets
import zipfile
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import (Depends, FastAPI, File, Header, HTTPException, Query,
                     UploadFile)
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from rapidfuzz import fuzz, process

from . import db

@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="SIH26042 Vernacular Pedagogy - Sync Backend", version="0.1.0",
              lifespan=lifespan)
ALLOWED_AUDIO = {".mp3", ".wav", ".ogg", ".m4a"}


# ---------- helpers ----------
_PUNCT = re.compile(r"[।॥\.\,\?\!\-\"'’‘“”;:()]+")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", _PUNCT.sub(" ", text or "")).strip().lower()


def require_admin(x_api_key: str = Header(default="")) -> None:
    expected = os.environ.get("ADMIN_API_KEY", "dev-key")
    if not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


def row_to_dict(r) -> dict:
    return {
        "id": r["id"],
        "hindi": r["hindi"],
        "santali": r["santali"],
        "santali_latin": r["santali_latin"],
        "category": r["category"],
        "grade": r["grade"],
        "outcome_code": r["outcome_code"],
        "audio_url": f"/api/v1/audio/{r['audio_file']}" if r["audio_file"] else None,
        "verified": bool(r["verified"]),
        "deleted": bool(r["deleted"]),
        "version": r["version"],
    }


def upsert_phrase(conn, p: dict, version: int) -> int:
    hn = normalize(p["hindi"])
    if not hn:
        raise HTTPException(400, "Hindi text is empty")
    vals = (
        p["hindi"].strip(), p.get("santali", ""), p.get("santali_latin", ""),
        p.get("category", "general") or "general", p.get("grade"),
        p.get("outcome_code", ""), 1 if p.get("verified") else 0, version, db.now(),
    )
    row = conn.execute("SELECT id FROM phrases WHERE hindi_norm=?", (hn,)).fetchone()
    if row:
        conn.execute(
            """UPDATE phrases SET hindi=?, santali=?, santali_latin=?, category=?, grade=?,
               outcome_code=?, verified=?, deleted=0, version=?, updated_at=? WHERE id=?""",
            vals + (row["id"],),
        )
        return row["id"]
    cur = conn.execute(
        """INSERT INTO phrases(hindi, santali, santali_latin, category, grade,
           outcome_code, verified, version, updated_at, hindi_norm)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        vals + (hn,),
    )
    return cur.lastrowid


class PhraseIn(BaseModel):
    hindi: str
    santali: str = ""
    santali_latin: str = ""
    category: str = "general"
    grade: Optional[int] = None
    outcome_code: str = ""
    verified: bool = False


# ---------- public endpoints (used by the tablet) ----------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/manifest")
def manifest(conn=Depends(db.get_conn)):
    total = conn.execute("SELECT COUNT(*) FROM phrases WHERE deleted=0").fetchone()[0]
    verified = conn.execute(
        "SELECT COUNT(*) FROM phrases WHERE deleted=0 AND verified=1").fetchone()[0]
    with_audio = conn.execute(
        "SELECT COUNT(*) FROM phrases WHERE deleted=0 AND audio_file<>''").fetchone()[0]
    return {"version": db.current_version(conn), "phrases": total,
            "verified": verified, "with_audio": with_audio}


@app.get("/api/v1/sync")
def sync(since: int = Query(0, ge=0), conn=Depends(db.get_conn)):
    """Delta sync: everything changed after `since` (deleted rows come as tombstones)."""
    rows = conn.execute(
        "SELECT * FROM phrases WHERE version>? ORDER BY id", (since,)).fetchall()
    return {"version": db.current_version(conn), "phrases": [row_to_dict(r) for r in rows]}


@app.get("/api/v1/package")
def package(conn=Depends(db.get_conn)):
    """First-time sync: one zip with phrases.json + all audio files."""
    rows = conn.execute("SELECT * FROM phrases WHERE deleted=0 ORDER BY id").fetchall()
    data = {"version": db.current_version(conn), "phrases": [row_to_dict(r) for r in rows]}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("phrases.json", json.dumps(data, ensure_ascii=False))
        for r in rows:
            path = os.path.join(db.AUDIO_DIR, r["audio_file"]) if r["audio_file"] else ""
            if path and os.path.isfile(path):
                z.write(path, f"audio/{r['audio_file']}")
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": "attachment; filename=content_package.zip"})


@app.get("/api/v1/audio/{filename}")
def get_audio(filename: str):
    safe = os.path.basename(filename)
    path = os.path.join(db.AUDIO_DIR, safe)
    if not os.path.isfile(path):
        raise HTTPException(404, "Audio not found")
    return FileResponse(path)


@app.get("/api/v1/translate")
def translate(q: str = Query(..., min_length=1), min_score: float = Query(70, ge=0, le=100),
              verified_only: bool = True, conn=Depends(db.get_conn)):
    """Fuzzy-match Hindi text to the phrase bank. Same logic the tablet will use offline."""
    sql = "SELECT * FROM phrases WHERE deleted=0 AND santali<>''"
    if verified_only:
        sql += " AND verified=1"
    rows = {r["id"]: r for r in conn.execute(sql).fetchall()}
    choices = {i: r["hindi_norm"] for i, r in rows.items()}
    best = process.extractOne(normalize(q), choices, scorer=fuzz.WRatio, score_cutoff=min_score) \
        if choices else None
    if not best:
        return {"matched": False, "query": q, "message": "No confident match; send to NMT fallback"}
    _, score, pid = best
    d = row_to_dict(rows[pid])
    return {"matched": True, "query": q, "confidence": round(score, 1), "phrase": d}


# ---------- admin endpoints ----------
@app.post("/api/v1/admin/phrases", dependencies=[Depends(require_admin)])
def add_or_update_phrase(p: PhraseIn, conn=Depends(db.get_conn)):
    v = db.bump_version(conn)
    pid = upsert_phrase(conn, p.model_dump(), v)
    conn.commit()
    return {"id": pid, "version": v}


@app.delete("/api/v1/admin/phrases/{phrase_id}", dependencies=[Depends(require_admin)])
def delete_phrase(phrase_id: int, conn=Depends(db.get_conn)):
    if not conn.execute("SELECT 1 FROM phrases WHERE id=?", (phrase_id,)).fetchone():
        raise HTTPException(404, "Phrase not found")
    v = db.bump_version(conn)
    conn.execute("UPDATE phrases SET deleted=1, version=?, updated_at=? WHERE id=?",
                 (v, db.now(), phrase_id))
    conn.commit()
    return {"deleted": phrase_id, "version": v}


@app.post("/api/v1/admin/import-csv", dependencies=[Depends(require_admin)])
async def import_csv(file: UploadFile = File(...), conn=Depends(db.get_conn)):
    """Columns: hindi, santali, santali_latin, category, grade, outcome_code, verified."""
    text = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "hindi" not in reader.fieldnames:
        raise HTTPException(400, "CSV must have a 'hindi' column")
    v = db.bump_version(conn)
    count = 0
    for row in reader:
        if not (row.get("hindi") or "").strip():
            continue
        grade = (row.get("grade") or "").strip()
        upsert_phrase(conn, {
            "hindi": row["hindi"], "santali": (row.get("santali") or "").strip(),
            "santali_latin": (row.get("santali_latin") or "").strip(),
            "category": (row.get("category") or "general").strip(),
            "grade": int(grade) if grade.isdigit() else None,
            "outcome_code": (row.get("outcome_code") or "").strip(),
            "verified": (row.get("verified") or "").strip().lower() in {"1", "true", "yes"},
        }, v)
        count += 1
    conn.commit()
    return {"imported": count, "version": v}


@app.post("/api/v1/admin/audio/{phrase_id}", dependencies=[Depends(require_admin)])
async def upload_audio(phrase_id: int, file: UploadFile = File(...), conn=Depends(db.get_conn)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_AUDIO:
        raise HTTPException(400, f"Audio must be one of {sorted(ALLOWED_AUDIO)}")
    if not conn.execute("SELECT 1 FROM phrases WHERE id=?", (phrase_id,)).fetchone():
        raise HTTPException(404, "Phrase not found")
    name = f"{phrase_id}{ext}"
    with open(os.path.join(db.AUDIO_DIR, name), "wb") as f:
        f.write(await file.read())
    v = db.bump_version(conn)
    conn.execute("UPDATE phrases SET audio_file=?, version=?, updated_at=? WHERE id=?",
                 (name, v, db.now(), phrase_id))
    conn.commit()
    return {"id": phrase_id, "audio_file": name, "version": v}
