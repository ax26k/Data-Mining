import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

CSV_PATH = "data/data_2/notices/part-000.csv"

conn = psycopg2.connect(
    host="localhost",
    port=5434,
    database="procurement",
    user="postgres",
    password="postgres"
)

cur = conn.cursor()

import glob

files = glob.glob("data/data_2/notices/*.csv")

all_data = []

for file in files:
    df = pd.read_csv(file)
    all_data.append(df)

df = pd.concat(all_data, ignore_index=True)

df["published_at"] = pd.to_datetime(df["published_at"])
df["closing_date"] = pd.to_datetime(df["closing_date"]).dt.date

portal_rows = [
    (
        portal_id,
        f"Portal {portal_id}",
        None
    )
    for portal_id in df["portal_id"].dropna().unique()
]

execute_values(
    cur,
    """
    INSERT INTO portals
    (portal_id, portal_name, source_url)
    VALUES %s
    ON CONFLICT (portal_id) DO NOTHING
    """,
    portal_rows
)

notice_rows = [
    (
        row.notice_id,
        row.portal_id,
        row.published_at,
        row.title,
        row.body,
        row.estimated_value,
        row.closing_date
    )
    for row in df.itertuples(index=False)
]

execute_values(
    cur,
    """
    INSERT INTO notices
    (
        notice_id,
        portal_id,
        published_at,
        title,
        body,
        estimated_value,
        closing_date
    )
    VALUES %s
    ON CONFLICT (notice_id) DO NOTHING
    """,
    notice_rows,
    page_size=1000
)

conn.commit()

cur.execute("SELECT COUNT(*) FROM portals")
print("Portals loaded:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM notices")
print("Notices loaded:", cur.fetchone()[0])

cur.close()
conn.close()