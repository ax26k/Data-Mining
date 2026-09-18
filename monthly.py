import pandas as pd
from pathlib import Path

out = Path("output")

df = pd.read_parquet(out / "sales_cleaned.parquet")

df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
df["month"] = df["ts"].dt.to_period("M").astype(str)

monthly = df.groupby("month", as_index=False).agg(
    revenue=("signed_amount", "sum"),
    transactions=("bill_no", "nunique"),
    lines=("line_no", "count")
)

monthly.to_csv(out / "monthly_sales.csv", index=False)

print(monthly)
print("Monthly report created")
