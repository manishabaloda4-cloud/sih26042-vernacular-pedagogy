import io
import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp()
os.environ["ADMIN_API_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

H = {"X-API-Key": "test-key"}


def test_flow():
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert c.get("/api/v1/manifest").json()["version"] == 0

        # admin auth
        assert c.post("/api/v1/admin/phrases", json={"hindi": "x"}).status_code == 401

        # CSV import (dummy Santali text, only for testing the pipeline)
        csv_data = ("hindi,santali,santali_latin,category,grade,outcome_code,verified\n"
                    "बैठ जाओ,TEST_SANTALI_1,t1,classroom,1,,1\n"
                    "अपनी किताब खोलो,TEST_SANTALI_2,t2,classroom,1,,1\n"
                    "शाबाश,,,praise,1,,0\n")
        r = c.post("/api/v1/admin/import-csv", headers=H,
                   files={"file": ("p.csv", io.BytesIO(csv_data.encode()), "text/csv")})
        assert r.json() == {"imported": 3, "version": 1}

        # re-import must not duplicate
        c.post("/api/v1/admin/import-csv", headers=H,
               files={"file": ("p.csv", io.BytesIO(csv_data.encode()), "text/csv")})
        m = c.get("/api/v1/manifest").json()
        assert m["phrases"] == 3 and m["verified"] == 2

        # fuzzy translate (slightly different input)
        t = c.get("/api/v1/translate", params={"q": "अपनी किताब खोलिए"}).json()
        assert t["matched"] and t["phrase"]["santali"] == "TEST_SANTALI_2"
        # unverified phrase is not returned
        assert not c.get("/api/v1/translate", params={"q": "शाबाश"}).json()["matched"]
        # garbage -> no match
        assert not c.get("/api/v1/translate", params={"q": "zzzz qqqq"}).json()["matched"]

        # audio upload + delta sync
        v_before = c.get("/api/v1/manifest").json()["version"]
        pid = t["phrase"]["id"]
        r = c.post(f"/api/v1/admin/audio/{pid}", headers=H,
                   files={"file": ("a.mp3", io.BytesIO(b"fakeaudio"), "audio/mpeg")})
        assert r.status_code == 200
        d = c.get("/api/v1/sync", params={"since": v_before}).json()
        assert len(d["phrases"]) == 1 and d["phrases"][0]["audio_url"]
        assert c.get(d["phrases"][0]["audio_url"]).content == b"fakeaudio"
        assert c.post(f"/api/v1/admin/audio/{pid}", headers=H,
                      files={"file": ("a.exe", io.BytesIO(b"x"), "x/y")}).status_code == 400

        # delete -> tombstone in sync
        v = c.get("/api/v1/manifest").json()["version"]
        c.delete(f"/api/v1/admin/phrases/{pid}", headers=H)
        d = c.get("/api/v1/sync", params={"since": v}).json()
        assert d["phrases"][0]["deleted"] is True

        # package zip
        z = c.get("/api/v1/package")
        assert z.status_code == 200 and z.content[:2] == b"PK"
