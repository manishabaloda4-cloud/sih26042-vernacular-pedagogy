"""Download CoRil-Parallel (Hindi-Punjabi, CC-BY-4.0), clean it, and write:
   data/extra.csv         general training pairs (hindi,punjabi)
   data/general_test.csv  held-out general-domain test pairs (never train on these)
Run from the project root:   pip install huggingface_hub pandas
                             python -m scripts.prepare_corpus --max-train 6000 --max-test 300
Dataset: https://huggingface.co/datasets/HimangY/CoRil-Parallel  (paper: arXiv 2509.19941)
"""
import os
import random
import re

import pandas as pd

REPO = "HimangY/CoRil-Parallel"          # CC-BY-4.0, Hindi-Punjabi files are under HI-PA/
_DEV = re.compile(r"[\u0900-\u097F]")     # Devanagari
_GUR = re.compile(r"[\u0A00-\u0A7F]")     # Gurmukhi
_LAT = re.compile(r"[A-Za-z]")
_BAD = re.compile(r"xxx|[(){}\[\]]|--|\.\.|व्यवधान|मेज", re.I)
# The GOV part is state-assembly debates. Drop political / legislative lines: not suitable for a children's tool.
_POLITICS = ("श्री ", "श्रीमती", "माननीय", "अध्यक्ष", "सदन", "मंत्री", "विधेयक", "सरकार", "विधान", "भाजपा",
             "कांग्रेस", "पार्टी", "बजट", "कर्ज", "चुनाव", "विधायक", "प्रश्न", "उत्तर", "प्रतिवेदन")


def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[।॥\.\,\?\!\-\"';:()]", " ", str(s))).strip().lower()


def clean_pair(h, p, min_words=3, max_words=14):
    h, p = h.strip(), p.strip()
    if not h or not p or _BAD.search(h) or _BAD.search(p):
        return False
    if any(w in h for w in _POLITICS):
        return False
    if _LAT.search(h) or _LAT.search(p):          # skip mixed-script lines
        return False
    if not _DEV.search(h) or not _GUR.search(p):  # Hindi must be Devanagari, Punjabi Gurmukhi
        return False
    hw, pw = len(h.split()), len(p.split())
    if not (min_words <= hw <= max_words):        # short sentences only
        return False
    return 0.5 <= pw / hw <= 2.0                  # drop badly misaligned pairs


def build_corpus(max_train=6000, max_test=300, seed=42, cache_dir=None):
    """Download CoRil HI-PA, clean it, return (train_df, general_test_df) with columns hindi, punjabi, key."""
    from huggingface_hub import hf_hub_download, list_repo_files
    files = [f for f in list_repo_files(REPO, repo_type="dataset") if f.startswith("HI-PA/") and f.endswith(".txt")]
    if not files:
        raise RuntimeError("No HI-PA files found. Check https://huggingface.co/datasets/HimangY/CoRil-Parallel")
    rows = {"train": [], "test": []}
    for f in files:
        split = "test" if f.endswith("_test.txt") else "train" if f.endswith(("_train.txt", "_dev.txt")) else None
        if split is None:
            continue
        path = hf_hub_download(REPO, f, repo_type="dataset", cache_dir=cache_dir)
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")      # format: hindi <TAB> punjabi
                if len(parts) == 2 and clean_pair(*parts):
                    rows[split].append((parts[0].strip(), parts[1].strip()))

    def frame(pairs):
        df = pd.DataFrame(pairs, columns=["hindi", "punjabi"])
        df["key"] = df.hindi.map(_norm)
        return df.drop_duplicates("key").sample(frac=1, random_state=seed).reset_index(drop=True)

    test = frame(rows["test"]).head(max_test)
    train = frame(rows["train"])
    train = train[~train.key.isin(set(test.key))].head(max_train).reset_index(drop=True)
    return train, test


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-train", type=int, default=6000)
    ap.add_argument("--max-test", type=int, default=300)
    a = ap.parse_args()
    train, test = build_corpus(a.max_train, a.max_test)
    os.makedirs("data", exist_ok=True)
    train[["hindi", "punjabi"]].to_csv("data/extra.csv", index=False)
    test[["hindi", "punjabi"]].to_csv("data/general_test.csv", index=False)
    print(f"train {len(train)} pairs, test {len(test)} pairs")
    print(train.sample(min(8, len(train)), random_state=1).to_string())
    print("\nRead these samples. If many look wrong, lower --max-train or tighten clean_pair().")
