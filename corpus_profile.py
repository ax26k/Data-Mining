from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "data_2"
NOTICE_DIR = DATA_DIR / "notices"

files = sorted(NOTICE_DIR.glob("*.csv"))

all_data = []

for file in files:
    df = pd.read_csv(file)
    all_data.append(df)

notices = pd.concat(all_data, ignore_index=True)

print("=" * 60)
print("FULL CORPUS PROFILE")
print("=" * 60)

print("\nTotal notices:", len(notices))
print("Total columns:", len(notices.columns))

print("\nColumns:")
print(list(notices.columns))

print("\nMissing values:")
print(notices.isna().sum())

print("\nDuplicate notice IDs:", notices["notice_id"].duplicated().sum())

print("\nUnique notice IDs:", notices["notice_id"].nunique())

print("\nUnique portals:", notices["portal_id"].nunique())

print("\nTop 20 portals by notice count:")
print(notices["portal_id"].value_counts().head(20))

print("\nNotice length statistics:")

notices["title_length"] = notices["title"].astype(str).str.len()
notices["body_length"] = notices["body"].astype(str).str.len()
notices["combined_length"] = (
    notices["title"].astype(str) + " " + notices["body"].astype(str)
).str.len()

print(
    notices[
        ["title_length", "body_length", "combined_length"]
    ].describe().round(2)
)

print("\nEstimated value statistics:")
print(notices["estimated_value"].describe().round(2))

print("\nClosing date range:")
print("Minimum:", notices["closing_date"].min())
print("Maximum:", notices["closing_date"].max())

print("\nPublished date range:")
print("Minimum:", notices["published_at"].min())
print("Maximum:", notices["published_at"].max())

print("\nLabelled pairs:")
pairs = pd.read_csv(DATA_DIR / "labelled_pairs.csv")

print("Total pairs:", len(pairs))
print(pairs["label"].value_counts())
print((pairs["label"].value_counts(normalize=True) * 100).round(2))