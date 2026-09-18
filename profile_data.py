from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "data_2"

notice_files = sorted((DATA_DIR / "notices").glob("*.csv"))

print("=" * 50)
print("NOTICE CORPUS")
print("=" * 50)

print("Notice files:", len(notice_files))

total_rows = 0

for file in notice_files:
    df = pd.read_csv(file)
    print(f"{file.name}: {len(df)} rows")
    total_rows += len(df)

print("Total notices:", total_rows)

pairs_file = DATA_DIR / "labelled_pairs.csv"
pairs = pd.read_csv(pairs_file)

print("\n" + "=" * 50)
print("LABELLED PAIRS")
print("=" * 50)

print("Columns:", list(pairs.columns))
print("Total pairs:", len(pairs))

print("\nLabel distribution:")
print(pairs["label"].value_counts())

print("\nLabel percentages:")
print((pairs["label"].value_counts(normalize=True) * 100).round(2))