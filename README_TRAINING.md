# Training kit: Hindi to Punjabi (fine-tune NLLB-200 with LoRA)

Copy `scripts/`, `data/classroom_hindi.csv` and `notebooks/` into your backend project folder.

## Steps
1. **Draft the classroom pairs** (needs internet):  
   `python -m scripts.draft_translations`  -> `data/pairs_draft.csv`
2. **Punjabi speaker checks it.** Open `pairs_draft.csv` in Excel/Sheets, fix the `punjabi` column, put `1` in `checked` for each approved row. Save as `pairs.csv`. Add more sentences if you can (aim for 300 or more); the more verified pairs, the more meaningful the classroom test.
3. **Open `notebooks/train_hi_pa_lora.ipynb` in Google Colab**, set the runtime to a T4 GPU, run all cells in order, upload `pairs.csv` when asked.
   The notebook downloads and cleans the public CoRil-Parallel corpus itself (cell 1a). Read the printed samples.
4. **Write down the printed numbers** (classroom and general test, baseline versus fine-tuned, trainable parameter count).
5. Download `hi-pa-lora.zip` and unzip it into `models/hi-pa-lora/` in your backend folder.

## Optional: run the same data prep on your own computer
`pip install huggingface_hub pandas` then `python -m scripts.prepare_corpus` -> `data/extra.csv`, `data/general_test.csv`.
`general_test.csv` also works with `python -m scripts.evaluate --test data/general_test.csv ...` to compare engines.

## Credit and licence
CoRil-Parallel: Bhattacharjee et al., arXiv 2509.19941, licence CC-BY-4.0. Cite it in your report.
NLLB-200 weights: non-commercial licence (CC-BY-NC).
