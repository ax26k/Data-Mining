from pathlib import Path
import re
import time
import pandas as pd
from datasketch import MinHash, MinHashLSH

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "data_2"
NOTICE_DIR = DATA_DIR / "notices"

NUM_PERM = 128
NGRAM_SIZE = 5

def normalize_text(title, body):
    text = f"{title} {body}".lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\b\d{1,4}[-/]\d{1,2}[-/]\d{2,4}\b", " DATE ", text)
    text = re.sub(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b", " MONEY ", text)
    text = re.sub(r"\b\d+(?:\.\d+)?\b", " NUMBER ", text)
    return text.strip()

def shingles(text, n=5):
    return set(text[i:i+n] for i in range(len(text) - n + 1))

def create_minhash(text):
    mh = MinHash(num_perm=NUM_PERM)
    for shingle in shingles(text):
        mh.update(shingle.encode("utf-8"))
    return mh

print("Loading notices...")

files = sorted(NOTICE_DIR.glob("*.csv"))
notices = pd.concat(
    [pd.read_csv(file) for file in files],
    ignore_index=True
)

notices["text"] = notices.apply(
    lambda row: normalize_text(row["title"], row["body"]),
    axis=1
)

print("Creating signatures...")
start = time.time()

signatures = {
    row["notice_id"]: create_minhash(row["text"])
    for _, row in notices.iterrows()
}

print("Signature time:", round(time.time() - start, 2), "seconds")

pairs = pd.read_csv(DATA_DIR / "labelled_pairs.csv")

thresholds = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80]

all_results = []

for threshold in thresholds:
    print(f"\nTesting threshold: {threshold}")

    lsh = MinHashLSH(
        threshold=threshold,
        num_perm=NUM_PERM
    )

    for notice_id, signature in signatures.items():
        lsh.insert(str(notice_id), signature)

    start = time.time()

    for _, pair in pairs.iterrows():
        a = pair["notice_id_a"]
        b = pair["notice_id_b"]

        candidates = set(lsh.query(signatures[a]))

        all_results.append({
            "threshold": threshold,
            "label": pair["label"],
            "survives": str(b) in candidates,
            "candidate_count": len(candidates)
        })

    elapsed = time.time() - start

    result_df = pd.DataFrame([
        r for r in all_results
        if r["threshold"] == threshold
    ])

    same = result_df[result_df["label"] == "same"]
    different = result_df[result_df["label"] == "different"]

    print("Same recall:", round(same["survives"].mean(), 4))
    print("Different survival:", round(different["survives"].mean(), 4))
    print("Mean candidates:", round(result_df["candidate_count"].mean(), 2))
    print("Median candidates:", round(result_df["candidate_count"].median(), 2))
    print("Evaluation time:", round(elapsed, 2), "seconds")

pd.DataFrame(all_results).to_csv(
    BASE_DIR / "outputs" / "threshold_sweep.csv",
    index=False
)

print("\nSaved outputs/threshold_sweep.csv")