# SIH26042 – Vernacular Pedagogy Backend (Hindi → Punjabi, online)

FastAPI + SQLite. A web frontend calls it over the internet.

`/translate` order: **verified phrase bank → cached machine result → translation engine**.
Hindi speech-to-text runs in the browser (Web Speech API, `hi-IN`); this API handles translation,
Punjabi text-to-speech, and worksheet content.

## Run (Windows)
```
pip install -r requirements.txt
set ADMIN_API_KEY=choose-a-secret
python -m uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs

## Load starter phrases
```
curl -X POST http://127.0.0.1:8000/api/v1/admin/import-csv -H "X-API-Key: choose-a-secret" -F "file=@seed/phrases_seed.csv"
```
The Punjabi text in the seed file is unverified. A native speaker should check it and set `verified` to 1.

## Settings (environment variables)
| Variable | Default | Meaning |
|---|---|---|
| ADMIN_API_KEY | dev-key | secret for admin endpoints (always set your own when deployed) |
| TRANSLATION_ENGINE | google_free,mymemory | engines tried in order; also `mock` |
| TTS_ENGINE | gtts | `gtts` or `mock` |
| CORS_ORIGINS | * | set to your frontend URL in production |
| DATA_DIR | data | database and audio cache location |

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | /health | server check |
| GET | /api/v1/stats | phrase counts |
| GET | /api/v1/translate?q=...&source=hi&target=pa | translate one sentence (returns origin and latency_ms) |
| POST | /api/v1/translate-batch | translate many texts |
| GET | /api/v1/phrases?category=&grade= | list phrases (flashcards) |
| GET | /api/v1/tts?text=...&lang=pa | text → mp3 |
| GET | /api/v1/worksheet?grade=1&count=10 | worksheet content (frontend prints to PDF) |
| POST | /api/v1/admin/phrases | add/update a phrase (needs X-API-Key) |
| DELETE | /api/v1/admin/phrases/{id} | delete a phrase |
| POST | /api/v1/admin/import-csv | bulk import |

## Test
```
python -m pytest -q
```
Tests use mock engines and run offline. Real translation and TTS need internet.
