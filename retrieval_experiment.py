from pathlib import Path
import re
import time
import json
import pandas as pd
import numpy as np
from datasketch import MinHash, MinHashLSH

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "data_2"
NOTICE_DIR = DATA_DIR / "notices"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

NUM_PERM = 128
THRESHOLD = 0.50
NGRAM_SIZE = 5

def normalize_text(title, body):
    text = f"{title} {body}".lower()

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\b\d{1,4}[-/]\d{1,2}[-/]\d{2,4}\b", " DATE ", text)
    text = re.sub(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b", " MONEY ", text)
    text = re.sub(r"\b\d+(?:\.\d+)?\b", " NUMBER ", text)

    return text.strip()

def shingles(text, n=NGRAM_SIZE):
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

print("Notices loaded:", len(notices))

print("Creating MinHash signatures...")
start = time.time()

signatures = {}

for i, row in notices.iterrows():
    signatures[row["notice_id"]] = create_minhash(row["text"])

print("Signature creation time:", round(time.time() - start, 2), "seconds")

print("Building LSH index...")

lsh = MinHashLSH(
    threshold=THRESHOLD,
    num_perm=NUM_PERM
)

for notice_id, signature in signatures.items():
    lsh.insert(str(notice_id), signature)

print("LSH index built.")

print("Evaluating labelled pairs...")

pairs = pd.read_csv(DATA_DIR / "labelled_pairs.csv")

results = []
candidate_counts = []

for _, pair in pairs.iterrows():
    a = str(pair["notice_id_a"])
    b = str(pair["notice_id_b"])

    candidates = set(lsh.query(signatures[pair["notice_id_a"]]))

    survives = str(pair["notice_id_b"]) in candidates

    estimated_similarity = signatures[pair["notice_id_a"]].jaccard(
        signatures[pair["notice_id_b"]]
    )

    results.append({
        "notice_id_a": a,
        "notice_id_b": b,
        "label": pair["label"],
        "estimated_similarity": estimated_similarity,
        "survives_candidate_stage": survives,
        "candidate_count": len(candidates)
    })

results_df = pd.DataFrame(results)

print("\nLabelled-pair retrieval results:")
print(
    results_df.groupby("label")["survives_candidate_stage"]
    .agg(["count", "sum", "mean"])
)

print("\nCandidate count statistics:")
print(results_df["candidate_count"].describe())

print("\nSimilarity by label:")
print(
    results_df.groupby("label")["estimated_similarity"]
    .describe()
)

results_df.to_csv(
    OUTPUT_DIR / "labelled_pair_results.csv",
    index=False
)

summary = {
    "num_notices": len(notices),
    "num_permutations": NUM_PERM,
    "ngram_size": NGRAM_SIZE,
    "lsh_threshold": THRESHOLD,
    "same_recall": float(
        results_df.loc[
            results_df["label"] == "same",
            "survives_candidate_stage"
        ].mean()
    ),
    "different_survival_rate": float(
        results_df.loc[
            results_df["label"] == "different",
            "survives_candidate_stage"
        ].mean()
    ),
    "mean_candidate_count": float(
        results_df["candidate_count"].mean()
    )
}

with open(OUTPUT_DIR / "retrieval_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print("\nSaved:")
print("outputs/labelled_pair_results.csv")
print("outputs/retrieval_summary.json")