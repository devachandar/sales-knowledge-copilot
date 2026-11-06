# copilot/ingest/load_tables.py
"""
Day 3, Lesson 5: load the InvoicePilot CSVs into Postgres (schema "ip") with real types.

Run from the project root with your Postgres container running:
    python -m copilot.ingest.load_tables

Drops and recreates the tables each run, so it is safe to re-run.
"""

import csv
import os

import psycopg
from dotenv import load_dotenv

from copilot.config import DATA_PACKAGE_DIR, SCHEMA_SQL

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
TABLES_DIR = DATA_PACKAGE_DIR
SCHEMA_FILE = SCHEMA_SQL

# Load order matters: a table must load after the tables it points to.
TABLES = [
    ("product_versions", "product_versions.csv"),
    ("customers", "customers.csv"),
    ("bugs", "bugs.csv"),
    ("sales_records", "sales_records.csv"),
    ("usage_logs", "usage_logs.csv"),
    ("support_tickets", "support_tickets.csv"),
]


def clean(table, row):
    """Empty strings become NULL; reshape the two columns that need it."""
    row = {k: (v if v != "" else None) for k, v in row.items()}
    if table == "usage_logs":
        row["month"] = row["month"] + "-01"                      # '2026-09' -> '2026-09-01'
        row["features_used"] = row["features_used"].split(";") if row["features_used"] else []
    return row


def load_table(cur, table, csv_name):
    with open(TABLES_DIR / csv_name, newline="", encoding="utf-8") as f:
        rows = [clean(table, r) for r in csv.DictReader(f)]
    cols = list(rows[0].keys())
    sql = (f"INSERT INTO ip.{table} ({', '.join(cols)}) "
           f"VALUES ({', '.join(['%s'] * len(cols))})")
    cur.executemany(sql, [[r[c] for c in cols] for r in rows])
    return len(rows)


def main():
    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL is not set in .env")
    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(SCHEMA_FILE.read_text())
        for table, csv_name in TABLES:
            print(f"  ip.{table:18s} {load_table(cur, table, csv_name):4d} rows")
        conn.commit()

        # Smoke test: the README's Oracle story should take one join to answer
        cur.execute("""
            SELECT s.product_version, s.order_date, s.license_status, s.license_expiry_date
            FROM ip.sales_records s JOIN ip.customers c USING (customer_id)
            WHERE c.company_name = 'Oracle'
            ORDER BY s.order_date DESC LIMIT 1
        """)
        print("\nOracle's latest order:", cur.fetchone())


if __name__ == "__main__":
    main()