"""Make a DRAFT Punjabi column for the classroom sentences, for a Punjabi speaker to correct.
Run from the project root (needs internet for the free engines):
    python -m scripts.draft_translations --in data/classroom_hindi.csv --out data/pairs_draft.csv
Then the speaker opens pairs_draft.csv, fixes the `punjabi` column, and puts 1 in `checked` for every row
they approve. Save as pairs.csv. The training notebook only uses rows with checked = 1.
"""
import argparse
import csv
import time

from app import engines

ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="inp", default="data/classroom_hindi.csv")
ap.add_argument("--out", default="data/pairs_draft.csv")
ap.add_argument("--delay", type=float, default=0.5)
a = ap.parse_args()

rows = list(csv.DictReader(open(a.inp, encoding="utf-8-sig")))
with open(a.out, "w", encoding="utf-8-sig", newline="") as f:       # utf-8-sig so Excel shows Gurmukhi correctly
    w = csv.writer(f)
    w.writerow(["hindi", "punjabi", "checked", "category"])
    for i, r in enumerate(rows, 1):
        try:
            text, _engine = engines.translate(r["hindi"], "hi", "pa")
        except Exception as e:
            print(f"[{i}] failed: {e}")
            text = ""
        w.writerow([r["hindi"], text, "", r.get("category", "")])
        print(f"[{i}/{len(rows)}] {r['hindi']}  ->  {text}")
        time.sleep(a.delay)
print(f"\nWrote {a.out}. Now give it to a Punjabi speaker to correct.")
