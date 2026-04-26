"""
Database initialization and connection management.
Loads CSV data into an in-memory SQLite database using the provided schema.
"""

import sqlite3
import csv
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "database_schema.sql")

# Table name -> CSV filename mapping (respects foreign key insertion order)
TABLE_CSV_MAP = [
    ("sectors", "sectors.csv"),
    ("securities", "securities.csv"),
    ("benchmarks", "benchmarks.csv"),
    ("portfolios", "portfolios.csv"),
    ("holdings", "holdings.csv"),
    ("transactions", "transactions.csv"),
    ("historical_prices", "historical_prices.csv"),
    ("portfolio_performance", "portfolio_performance.csv"),
    ("risk_metrics", "risk_metrics.csv"),
]


def _create_schema(conn: sqlite3.Connection) -> None:
    with open(SCHEMA_FILE, "r") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    logger.debug("Schema created.")


def _load_csv(conn: sqlite3.Connection, table: str, csv_path: str) -> int:
    if not os.path.exists(csv_path):
        logger.warning("CSV not found, skipping: %s", csv_path)
        return 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return 0

    columns = rows[0].keys()
    placeholders = ", ".join(["?" for _ in columns])
    col_names = ", ".join(columns)
    sql = f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})"

    def _coerce(val: str) -> Optional[str]:
        stripped = val.strip()
        return None if stripped == "" else stripped

    data = [tuple(_coerce(row[c]) for c in columns) for row in rows]
    conn.executemany(sql, data)
    logger.debug("Loaded %d rows into %s", len(data), table)
    return len(data)


def build_database() -> sqlite3.Connection:
    """
    Build and return an in-memory SQLite connection populated with all CSV data.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    _create_schema(conn)

    total = 0
    for table, csv_filename in TABLE_CSV_MAP:
        csv_path = os.path.join(DATA_DIR, csv_filename)
        total += _load_csv(conn, table, csv_path)

    conn.commit()
    logger.info("Database ready. Total rows loaded: %d", total)
    return conn


def execute_query(conn: sqlite3.Connection, sql: str) -> list[dict]:
    """
    Execute a SELECT query and return results as a list of dicts.
    Raises ValueError on non-SELECT queries to prevent data mutation.
    """
    normalized = sql.strip().lstrip(";").strip().upper()
    if not normalized.startswith("SELECT") and not normalized.startswith("WITH"):
        raise ValueError("Only SELECT/WITH queries are permitted.")

    cursor = conn.execute(sql)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]