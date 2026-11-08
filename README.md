# SIH26042 – Backend (online): Hindi → Punjabi

FastAPI + SQLite. A browser/tablet frontend calls it over the internet.

`/translate` order: **verified phrase bank → cached machine result → translation engine**.
Hindi speech-to-text is done in the browser (Web Speech API, `hi-IN`); this API does translation,
Punjabi text-to-speech, and worksheet content.

## Run (Windows)
```
pip install -r requirements.txt
set ADMIN_API_KEY=choose-a-secret
python -m uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs

## Load starter phrases (Punjabi included; have a Punjabi speaker verify them)
```
curl -X POST http://127.0.0.1:8000/api/v1/admin/import-csv -H "X-API-Key: choose-a-secret" -F "file=@seed/phrases_seed.csv"
```

## Settings (environment variables)
| Variable | Default | Meaning |
|---|---|---|
| ADMIN_API_KEY | dev-key | secret for admin endpoints |
| TRANSLATION_ENGINE | google_free | `google_free` or `mock` (add Bhashini etc. in app/engines.py) |
| TTS_ENGINE | gtts | `gtts` or `mock` |
| CORS_ORIGINS | * | set to your frontend URL in production |
| DATA_DIR | data | where the database and audio cache live |

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | /health | server check |
| GET | /api/v1/stats | phrase counts |
| GET | /api/v1/translate?q=...&source=hi&target=pa | translate one sentence (returns latency_ms and origin) |
| POST | /api/v1/translate-batch | translate many texts |
| GET | /api/v1/phrases?category=&grade= | list phrases (flashcards) |
| GET | /api/v1/tts?text=...&lang=pa | text → mp3 |
| GET | /api/v1/worksheet?grade=1&count=10 | worksheet content (frontend prints to PDF) |
| POST | /api/v1/admin/phrases | add/update (needs X-API-Key) |
| DELETE | /api/v1/admin/phrases/{id} | delete |
| POST | /api/v1/admin/import-csv | bulk import |

## Test
```
pytest -q
```
Tests use mock engines, so they run offline. Real translation/TTS need internet.

## Engines and our own model
`TRANSLATION_ENGINE` is a comma list tried in order. Every machine answer reports which engine made it (`engine` field).
- `google_free`, `mymemory`: free online services (pretrained by others, not trained by us).
- `local_model`: **our** fine-tuned NLLB-200 (600M) with a LoRA adapter. Train it with `notebooks/train_hi_pa_lora.ipynb`
  on Google Colab, unzip the downloaded `hi-pa-lora.zip` into `models/hi-pa-lora/`, then:
```
pip install -r requirements-ml.txt
set TRANSLATION_ENGINE=local_model,google_free
python -m uvicorn app.main:app --reload
```
The first request loads the model (slow); later ones are faster. Check latency on your machine.

## Measure accuracy (for the report)
Make `data/test.csv` with columns `hindi,punjabi` (reference checked by a Punjabi speaker; never train on these rows):
```
python -m scripts.evaluate --test data/test.csv --engines google_free,mymemory,local_model
```
It prints chrF++, BLEU, failures and average seconds per engine.
