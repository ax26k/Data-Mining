from pathlib import Path
import re
import io
import hashlib
import pandas as pd
import duckdb
import psycopg2
from minio import Minio
from minio.error import S3Error


BASE_DIR = Path(__file__).resolve().parents[1]

SALES_DIR = BASE_DIR / "data" / "sales"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
REPORTS_DIR = BASE_DIR / "reports"
STAR_SCHEMA_DIR = BASE_DIR / "star_schema"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
STAR_SCHEMA_DIR.mkdir(parents=True, exist_ok=True)


POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5435
POSTGRES_DATABASE = "annapurna"
POSTGRES_USER = "admin"
POSTGRES_PASSWORD = "admin123"


MINIO_HOST = "localhost:9001"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin123"
MINIO_BUCKET = "annapurna"


def get_business_date_from_filename(file_path):
    match = re.search(
        r"SALES_[A-Z0-9]+_(\d{8})",
        file_path.name.upper()
    )

    if match:
        date_text = match.group(1)
        return pd.to_datetime(
            date_text,
            format="%Y%m%d",
            errors="coerce"
        )

    return pd.NaT


def detect_csv_separator(file_path):
    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        errors="replace"
    ) as file:
        first_line = file.readline()

    if ";" in first_line:
        return ";"

    return ","


def normalize_columns(df):
    df.columns = [
        str(column)
        .strip()
        .lower()
        .replace("\ufeff", "")
        for column in df.columns
    ]

    df = df.loc[
        :,
        ~df.columns.duplicated()
    ]

    rename_map = {
        "item_code": "product_code",
        "quantity": "qty",
        "rate": "unit_price",
        "type": "line_type",
        "txn_time": "ts"
    }

    df = df.rename(
        columns=rename_map
    )

    return df


def read_one_file(file_path):
    business_date = get_business_date_from_filename(
        file_path
    )

    if file_path.suffix.lower() == ".csv":
        separator = detect_csv_separator(
            file_path
        )

        df = pd.read_csv(
            file_path,
            sep=separator,
            encoding="utf-8-sig",
            dtype=str
        )

    elif file_path.suffix.lower() == ".parquet":
        df = pd.read_parquet(
            file_path
        )

    else:
        return None

    df = normalize_columns(df)

    required_columns = [
        "bill_no",
        "line_no",
        "product_code",
        "qty",
        "unit_price",
        "line_type",
        "ts"
    ]

    for column in required_columns:
        if column not in df.columns:
            df[column] = None

    df["source_file"] = file_path.name
    df["business_date"] = business_date

    return df


def load_sales_files():
    print("Starting final Annapurna pipeline")

    files = sorted(
        [
            file
            for file in SALES_DIR.rglob("*")
            if file.suffix.lower() in [
                ".csv",
                ".parquet"
            ]
        ]
    )

    if not files:
        raise FileNotFoundError(
            f"No CSV or Parquet files found inside {SALES_DIR}"
        )

    frames = []

    for index, file_path in enumerate(files, start=1):
        try:
            df = read_one_file(file_path)

            if df is not None and not df.empty:
                frames.append(df)

        except Exception as error:
            print(
                f"Skipped {file_path.name}: {error}"
            )

        if index % 500 == 0:
            print(
                f"Files processed: {index} / {len(files)}"
            )

    if not frames:
        raise ValueError(
            "No valid sales files could be loaded."
        )

    sales = pd.concat(
        frames,
        ignore_index=True
    )

    print(
        f"Raw rows: {len(sales):,}"
    )

    return sales


def clean_sales_data(sales):
    print("Cleaning sales data...")

    sales["bill_no"] = (
        sales["bill_no"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    sales["line_no"] = (
        sales["line_no"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    sales["product_code"] = (
        sales["product_code"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    sales["line_type"] = (
        sales["line_type"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    sales["qty"] = pd.to_numeric(
        sales["qty"],
        errors="coerce"
    ).fillna(0)

    sales["unit_price"] = pd.to_numeric(
        sales["unit_price"],
        errors="coerce"
    ).fillna(0)

    sales["business_date"] = pd.to_datetime(
        sales["business_date"],
        errors="coerce"
    )

    sales["ts"] = sales["ts"].fillna("").astype(str)

    sales["amount"] = (
        sales["qty"] * sales["unit_price"]
    )

    sales["signed_amount"] = sales["amount"]

    sales.loc[
        sales["line_type"].isin([
            "RETURN",
            "DISCOUNT",
            "VOID"
        ]),
        "signed_amount"
    ] = -sales.loc[
        sales["line_type"].isin([
            "RETURN",
            "DISCOUNT",
            "VOID"
        ]),
        "signed_amount"
    ]

    before_deduplication = len(sales)

    sales = sales.drop_duplicates(
        subset=[
            "bill_no",
            "line_no"
        ]
    )

    duplicates_removed = (
        before_deduplication - len(sales)
    )

    print(
        f"Duplicates removed: {duplicates_removed:,}"
    )

    sales["is_void_bill"] = (
        sales.groupby("bill_no")["line_type"]
        .transform(
            lambda values: "VOID" in set(values)
        )
    )

    sales["included_in_revenue"] = (
        ~sales["line_type"].isin([
            "TAX",
            "TENDER"
        ])
    )

    sales.loc[
        sales["is_void_bill"],
        "included_in_revenue"
    ] = True

    sales["store_id"] = (
        sales["bill_no"]
        .str.extract(r"^(S\d+)", expand=False)
        .fillna("UNKNOWN")
    )

    return sales


def save_cleaned_data(sales):
    output_file = (
        OUTPUT_DIR / "sales_cleaned.parquet"
    )

    parquet_sales = sales.copy()

    parquet_sales["business_date"] = (
        parquet_sales["business_date"]
        .dt.strftime("%Y-%m-%d")
    )

    parquet_sales.to_parquet(
        output_file,
        index=False
    )

    print(
        f"Cleaned Parquet saved: {output_file}"
    )


def create_monthly_report(sales):
    print("Creating monthly report...")

    report_sales = sales.copy()

    report_sales["month"] = (
        report_sales["business_date"]
        .dt.to_period("M")
        .astype(str)
    )

    monthly = (
        report_sales[
            report_sales["included_in_revenue"] == True
        ]
        .groupby("month", as_index=False)
        .agg(
            revenue=(
                "signed_amount",
                "sum"
            ),
            transactions=(
                "bill_no",
                "nunique"
            ),
            lines=(
                "line_no",
                "count"
            )
        )
    )

    monthly["revenue"] = (
        monthly["revenue"]
        .round(2)
    )

    monthly = monthly.sort_values(
        "month"
    )

    output_file = (
        OUTPUT_DIR / "monthly_sales.csv"
    )

    monthly.to_csv(
        output_file,
        index=False
    )

    print("\nMonthly report:")
    print(
        monthly.to_string(index=False)
    )

    print(
        f"Monthly report saved: {output_file}"
    )

    return monthly


def create_daily_report(sales):
    print("Creating daily report...")

    daily = (
        sales[
            sales["included_in_revenue"] == True
        ]
        .groupby(
            "business_date",
            as_index=False
        )
        .agg(
            revenue=(
                "signed_amount",
                "sum"
            ),
            transactions=(
                "bill_no",
                "nunique"
            ),
            lines=(
                "line_no",
                "count"
            )
        )
    )

    daily["revenue"] = (
        daily["revenue"]
        .round(2)
    )

    output_file = (
        OUTPUT_DIR / "daily_sales.csv"
    )

    daily.to_csv(
        output_file,
        index=False
    )

    print(
        f"Daily report saved: {output_file}"
    )


def create_partitioned_parquet(sales):
    print("Creating partitioned Parquet files...")

    partitioned_dir = (
        DATA_DIR / "partitioned"
    )

    partitioned_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    partition_sales = sales.copy()

    for (year, month), group in partition_sales.groupby(
        [
            partition_sales["business_date"].dt.year,
            partition_sales["business_date"].dt.month
        ]
    ):
        folder = (
            partitioned_dir
            / f"year={int(year)}"
            / f"month={int(month):02d}"
        )

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        output_file = (
            folder / "sales.parquet"
        )

        group.to_parquet(
            output_file,
            index=False
        )

    print(
        f"Partitioned Parquet created at: "
        f"{partitioned_dir}"
    )


def connect_postgres():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DATABASE,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )


def export_postgres_tables():
    print("Exporting PostgreSQL master tables...")

    connection = connect_postgres()

    tables = [
        "stores",
        "product_categories",
        "products",
        "price_revisions"
    ]

    for table in tables:
        query = f"SELECT * FROM {table}"

        df = pd.read_sql(
            query,
            connection
        )

        output_file = (
            STAR_SCHEMA_DIR / f"{table}.csv"
        )

        df.to_csv(
            output_file,
            index=False
        )

        print(
            f"Exported: {table} {len(df)} rows"
        )

    connection.close()


def create_star_schema(sales):
    print("Creating star schema files...")

    fact_sales = sales[
        [
            "bill_no",
            "line_no",
            "business_date",
            "store_id",
            "product_code",
            "qty",
            "unit_price",
            "amount",
            "signed_amount",
            "line_type",
            "included_in_revenue"
        ]
    ].copy()

    fact_sales.to_parquet(
        STAR_SCHEMA_DIR / "fact_sales.parquet",
        index=False
    )

    dim_date = (
        sales[
            ["business_date"]
        ]
        .drop_duplicates()
        .sort_values("business_date")
        .reset_index(drop=True)
    )

    dim_date["date_key"] = (
        dim_date["business_date"]
        .dt.strftime("%Y%m%d")
    )

    dim_date.to_csv(
        STAR_SCHEMA_DIR / "dim_date.csv",
        index=False
    )

    dim_store = (
        sales[
            ["store_id"]
        ]
        .drop_duplicates()
        .sort_values("store_id")
        .reset_index(drop=True)
    )

    dim_store.to_csv(
        STAR_SCHEMA_DIR / "dim_store.csv",
        index=False
    )

    dim_product = (
        sales[
            ["product_code"]
        ]
        .drop_duplicates()
        .sort_values("product_code")
        .reset_index(drop=True)
    )

    dim_product.to_csv(
        STAR_SCHEMA_DIR / "dim_product.csv",
        index=False
    )

    print("Star schema files created")


def run_duckdb_queries():
    print("Running DuckDB queries...")

    partitioned_path = str(
        DATA_DIR
        / "partitioned"
        / "**"
        / "*.parquet"
    )

    connection = duckdb.connect()

    connection.execute(
        f"""
        CREATE OR REPLACE VIEW sales_parquet AS
        SELECT *
        FROM read_parquet(
            '{partitioned_path}',
            union_by_name = true
        );
        """
    )

    store_monthly = connection.execute(
        """
        SELECT
            store_id,
            strftime(
                CAST(business_date AS DATE),
                '%Y-%m'
            ) AS month,
            ROUND(
                SUM(signed_amount),
                2
            ) AS revenue,
            COUNT(DISTINCT bill_no) AS transactions
        FROM sales_parquet
        WHERE included_in_revenue = true
        GROUP BY
            store_id,
            strftime(
                CAST(business_date AS DATE),
                '%Y-%m'
            )
        ORDER BY
            store_id,
            month;
        """
    ).fetchdf()

    store_monthly_file = (
        REPORTS_DIR / "duckdb_store_monthly.csv"
    )

    store_monthly.to_csv(
        store_monthly_file,
        index=False
    )

    print(
        f"DuckDB report saved: {store_monthly_file}"
    )

    explain_result = connection.execute(
        """
        EXPLAIN
        SELECT
            store_id,
            strftime(
                CAST(business_date AS DATE),
                '%Y-%m'
            ) AS month,
            SUM(signed_amount) AS revenue
        FROM sales_parquet
        WHERE included_in_revenue = true
        GROUP BY
            store_id,
            strftime(
                CAST(business_date AS DATE),
                '%Y-%m'
            );
        """
    ).fetchall()

    explain_file = (
        REPORTS_DIR / "duckdb_query_plan.txt"
    )

    with open(
        explain_file,
        "w",
        encoding="utf-8"
    ) as file:
        for row in explain_result:
            file.write(str(row))
            file.write("\n")

    connection.close()

    print(
        f"DuckDB query plan saved: {explain_file}"
    )

    print("DuckDB query completed")


def upload_to_minio():
    print("Uploading files to MinIO...")

    client = Minio(
        MINIO_HOST,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )

    try:
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)

        files_to_upload = []

        for folder in [
            OUTPUT_DIR,
            REPORTS_DIR,
            STAR_SCHEMA_DIR
        ]:
            if folder.exists():
                files_to_upload.extend(
                    [
                        file
                        for file in folder.rglob("*")
                        if file.is_file()
                    ]
                )

        for file_path in files_to_upload:
            object_name = str(
                file_path.relative_to(BASE_DIR)
            ).replace("\\", "/")

            client.fput_object(
                MINIO_BUCKET,
                object_name,
                str(file_path)
            )

        print(
            f"Uploaded {len(files_to_upload)} files to MinIO"
        )

    except S3Error as error:
        print(
            f"MinIO upload failed: {error}"
        )


def finance_reconciliation(sales):
    print("Running finance reconciliation...")

    calculated = (
        sales[
            sales["included_in_revenue"] == True
        ]
        .groupby(
            sales["business_date"].dt.to_period("M")
        )["signed_amount"]
        .sum()
        .round(2)
    )

    calculated = calculated.reset_index()

    calculated.columns = [
        "month",
        "calculated_revenue"
    ]

    finance_file = (
        DATA_DIR / "finance_monthly.csv"
    )

    if finance_file.exists():
        finance = pd.read_csv(
            finance_file
        )

        finance.columns = [
            str(column).strip().lower()
            for column in finance.columns
        ]

        print(
            "Finance reference file found."
        )

        print(
            finance.head().to_string(index=False)
        )

    output_file = (
        REPORTS_DIR / "finance_reconciliation.csv"
    )

    calculated.to_csv(
        output_file,
        index=False
    )

    print(
        f"Finance reconciliation saved: {output_file}"
    )

    print("Finance reconciliation completed")


def main():
    sales = load_sales_files()

    sales = clean_sales_data(
        sales
    )

    save_cleaned_data(
        sales
    )

    create_monthly_report(
        sales
    )

    create_daily_report(
        sales
    )

    create_partitioned_parquet(
        sales
    )

    export_postgres_tables()

    create_star_schema(
        sales
    )

    run_duckdb_queries()

    upload_to_minio()

    finance_reconciliation(
        sales
    )

    print("\n========================================")
    print("FINAL PIPELINE COMPLETED")
    print("========================================")


if __name__ == "__main__":
    main()