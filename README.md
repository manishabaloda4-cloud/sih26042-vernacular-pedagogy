# SIH26042 – Sync Backend (FastAPI + SQLite)

Thin server for the offline tablet app. Stores the verified Hindi→Santali phrase bank and audio,
and lets tablets download it once (`/package`) and then sync only changes (`/sync?since=N`).

## Run
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
export ADMIN_API_KEY=choose-a-secret                  # Windows: set ADMIN_API_KEY=...
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs for the interactive API.

## Load the starter phrases
```bash
curl -X POST http://127.0.0.1:8000/api/v1/admin/import-csv \
  -H "X-API-Key: $ADMIN_API_KEY" -F "file=@seed/phrases_seed.csv"
```
The Santali columns are **intentionally empty**. A native speaker must fill and verify them
(set `verified` to 1). Only verified phrases are used by `/translate`.

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | /api/v1/manifest | current content version and counts |
| GET | /api/v1/package | first-time zip (phrases.json + audio) |
| GET | /api/v1/sync?since=N | changes after version N (deleted = tombstone) |
| GET | /api/v1/audio/{file} | one audio file |
| GET | /api/v1/translate?q=... | fuzzy Hindi→Santali match (for testing) |
| POST | /api/v1/admin/phrases | add or update one phrase |
| DELETE | /api/v1/admin/phrases/{id} | remove a phrase |
| POST | /api/v1/admin/import-csv | bulk import |
| POST | /api/v1/admin/audio/{id} | upload recorded audio |

Admin endpoints need the `X-API-Key` header.

## Test
```bash
pytest -q
```
