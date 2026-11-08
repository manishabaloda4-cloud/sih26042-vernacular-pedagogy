"""Score translation engines on a test CSV with chrF++ and BLEU, and measure speed.

Test CSV columns: hindi, punjabi   (punjabi = reference translation checked by a Punjabi speaker)
Run from the project root:
    python -m scripts.evaluate --test data/test.csv --engines google_free,mymemory,local_model
Use --engines mock for a quick dry run without internet.
"""
import argparse
import csv
import statistics
import time

import sacrebleu

from app import engines


def get_fn(name):
    if name == "mock":
        return lambda text, s, t: f"[{t}] {text}"
    return engines._ENGINES[name]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", required=True)
    ap.add_argument("--engines", default="google_free,mymemory")
    ap.add_argument("--delay", type=float, default=0.4, help="seconds between calls (avoid rate limits)")
    ap.add_argument("--out", default="data/eval_results.csv")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.test, encoding="utf-8-sig")))
    src = [r["hindi"] for r in rows]
    refs = [r["punjabi"] for r in rows]
    chrf = sacrebleu.CHRF(word_order=2)  # chrF++
    summary = []
    for name in [n.strip() for n in a.engines.split(",") if n.strip()]:
        fn, hyps, times = get_fn(name), [], []
        for text in src:
            t0 = time.perf_counter()
            try:
                h = fn(text, "hi", "pa") or ""
            except Exception as e:
                print(f"  [{name}] failed on '{text[:30]}': {e}")
                h = ""
            times.append(time.perf_counter() - t0)
            hyps.append(h)
            time.sleep(a.delay)
        failed = sum(1 for h in hyps if not h)
        summary.append({"engine": name, "sentences": len(src), "failed": failed,
                        "chrF++": round(chrf.corpus_score(hyps, [refs]).score, 1),
                        "BLEU": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 1),
                        "avg_seconds": round(statistics.mean(times), 2)})
        with open(f"data/eval_outputs_{name}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["hindi", "reference", "output"])
            w.writerows(zip(src, refs, hyps))

    print(f"\n{'engine':<14}{'n':>5}{'failed':>8}{'chrF++':>9}{'BLEU':>8}{'avg s':>8}")
    for s in summary:
        print(f"{s['engine']:<14}{s['sentences']:>5}{s['failed']:>8}{s['chrF++']:>9}{s['BLEU']:>8}{s['avg_seconds']:>8}")
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)
    print(f"\nSaved {a.out} and per-engine outputs in data/")


if __name__ == "__main__":
    main()
