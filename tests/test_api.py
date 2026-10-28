import io
import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp()
os.environ["ADMIN_API_KEY"] = "test-key"
os.environ["TRANSLATION_ENGINE"] = "mock"
os.environ["TTS_ENGINE"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

H = {"X-API-Key": "test-key"}
CSV = ("hindi,target_text,category,grade,outcome_code,verified\n"
       "बैठ जाओ,ਬੈਠ ਜਾਓ,classroom,1,,1\n"
       "अपनी किताब खोलो,ਆਪਣੀ ਕਿਤਾਬ ਖੋਲ੍ਹੋ,classroom,1,,1\n"
       "मेरे साथ गिनो,ਮੇਰੇ ਨਾਲ ਗਿਣੋ,numeracy,2,,0\n")


def upload(c):
    return c.post("/api/v1/admin/import-csv", headers=H,
                  files={"file": ("p.csv", io.BytesIO(CSV.encode()), "text/csv")})


def test_flow():
    with TestClient(app) as c:
        assert c.get("/health").json()["status"] == "ok"
        assert c.post("/api/v1/admin/phrases", json={"hindi": "x"}).status_code == 401

        assert upload(c).json() == {"imported": 3}
        upload(c)  # re-import must not duplicate
        s = c.get("/api/v1/stats").json()
        assert s["phrases"] == 3 and s["verified"] == 2

        # 1) fuzzy hit on the verified bank
        t = c.get("/api/v1/translate", params={"q": "अपनी किताब खोलिए"}).json()
        assert t["origin"] == "verified_bank" and t["text"] == "ਆਪਣੀ ਕਿਤਾਬ ਖੋਲ੍ਹੋ"
        assert "latency_ms" in t

        # a single word must NOT match a full stored sentence
        w = c.get("/api/v1/translate", params={"q": "बैठ"}).json()
        assert w["origin"] == "machine"

        # 2) unknown sentence -> engine, 3) same sentence again -> cache
        m = c.get("/api/v1/translate", params={"q": "कल छुट्टी है"}).json()
        assert m["origin"] == "machine" and m["text"].startswith("[pa]")
        m2 = c.get("/api/v1/translate", params={"q": "कल छुट्टी है"}).json()
        assert m2["origin"] == "cache"

        # batch
        b = c.post("/api/v1/translate-batch", json={"texts": ["बैठ जाओ", "आम"]}).json()
        assert [r["origin"] for r in b["results"]] == ["verified_bank", "machine"]

        # phrases list + worksheet
        assert len(c.get("/api/v1/phrases", params={"category": "classroom"}).json()["phrases"]) == 2
        w = c.get("/api/v1/worksheet", params={"grade": 1, "count": 5}).json()
        assert len(w["items"]) >= 2 and w["items"][0]["target_text"]

        # tts
        r = c.get("/api/v1/tts", params={"text": "ਬੈਠ ਜਾਓ", "lang": "pa"})
        assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
        assert c.get("/api/v1/tts", params={"text": "x", "lang": "zz"}).status_code == 400

        # CORS
        r = c.get("/health", headers={"Origin": "http://localhost:5173"})
        assert r.headers.get("access-control-allow-origin")

        # admin delete
        pid = c.get("/api/v1/phrases").json()["phrases"][0]["id"]
        assert c.delete(f"/api/v1/admin/phrases/{pid}", headers=H).status_code == 200
        assert c.delete(f"/api/v1/admin/phrases/{pid}", headers=H).status_code == 404
