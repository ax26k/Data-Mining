import pandas as pd
from pathlib import Path

folder = Path("data/sales")
out = Path("output")
out.mkdir(exist_ok=True)

frames = []

for f in folder.rglob("*"):
    try:
        if f.suffix.lower() == ".csv":
            df = pd.read_csv(
                f,
                sep=None,
                engine="python",
                encoding="utf-8-sig"
            )
        elif f.suffix.lower() == ".parquet":
            df = pd.read_parquet(f)
        else:
            continue

        df.columns = [str(c).strip().lower() for c in df.columns]
        df = df.loc[:, ~df.columns.duplicated()]
        frames.append(df)

    except Exception as e:
        print("Skipped:", f.name, e)

sales = pd.concat(frames, ignore_index=True)

sales = sales.rename(columns={
    "item_code": "product_code",
    "quantity": "qty",
    "rate": "unit_price",
    "type": "line_type",
    "txn_time": "ts"
})

sales = sales.loc[:, ~sales.columns.duplicated()]

for col in ["bill_no", "line_no", "product_code", "qty", "unit_price", "line_type", "ts"]:
    if col not in sales.columns:
        sales[col] = ""

sales["bill_no"] = sales["bill_no"].astype(str)
sales["line_no"] = sales["line_no"].astype(str)
sales["product_code"] = sales["product_code"].astype(str)
sales["line_type"] = sales["line_type"].astype(str).str.upper().str.strip()
sales["ts"] = sales["ts"].astype(str)

sales["qty"] = pd.to_numeric(sales["qty"], errors="coerce").fillna(0)
sales["unit_price"] = pd.to_numeric(sales["unit_price"], errors="coerce").fillna(0)
sales["amount"] = sales["qty"] * sales["unit_price"]
sales["signed_amount"] = sales["amount"]

sales.loc[
    sales["line_type"].isin(["RETURN", "DISCOUNT", "VOID"]),
    "signed_amount"
] = -sales.loc[
    sales["line_type"].isin(["RETURN", "DISCOUNT", "VOID"]),
    "signed_amount"
]

sales = sales.drop_duplicates(subset=["bill_no", "line_no"])

sales.to_parquet(
    out / "sales_cleaned.parquet",
    index=False
)

daily = sales.groupby("ts", as_index=False)["signed_amount"].sum()
daily.to_csv(out / "daily_sales.csv", index=False)

print("DONE")
print("Rows:", len(sales))
