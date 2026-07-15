"""User memory in DuckDB: an append-only product log (the pantry).

Enables cumulative questions ("across everything I logged today, is anything
restricted?"). Kept deliberately small: a log of products the user asked about.
The table is created on demand so an already-built store gains it without a full
rebuild.
"""
from __future__ import annotations

from datetime import datetime, timezone

import duckdb

_DDL = """
CREATE SEQUENCE IF NOT EXISTS product_log_seq START 1;
CREATE TABLE IF NOT EXISTS product_log (
    id        BIGINT DEFAULT nextval('product_log_seq') PRIMARY KEY,
    user_id   TEXT NOT NULL,
    barcode   TEXT,
    name      TEXT,
    logged_at TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_memory_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(_DDL)


def log_product(con: duckdb.DuckDBPyConnection, user_id: str, *,
                barcode: str = "", name: str = "") -> None:
    con.execute(
        "INSERT INTO product_log (user_id, barcode, name, logged_at) VALUES (?, ?, ?, ?)",
        [user_id, barcode, name, _now()])


def remove_product(con: duckdb.DuckDBPyConnection, user_id: str, barcode: str) -> None:
    """Remove a product from the user's pantry (all log rows for that barcode)."""
    con.execute("DELETE FROM product_log WHERE user_id = ? AND barcode = ?",
                [user_id, barcode])


def get_log(con: duckdb.DuckDBPyConnection, user_id: str) -> list[dict]:
    return [
        {"barcode": b, "name": n, "logged_at": t}
        for b, n, t in con.execute(
            """SELECT barcode, name, logged_at FROM product_log
               WHERE user_id = ? ORDER BY id""", [user_id]).fetchall()
    ]


def get_log_with_additives(con: duckdb.DuckDBPyConnection, user_id: str) -> list[dict]:
    """Logged products joined to their real additive tags from the product table.

    Grounds cumulative questions: the additive list comes from the store, not the
    model's guess. `additives` is the comma-joined en:e### tags, empty if the
    barcode is not in the product table.
    """
    return [
        {"barcode": b, "name": n, "additives": tags or ""}
        for b, n, tags in con.execute(
            """SELECT pl.barcode, COALESCE(NULLIF(pl.name, ''), p.name),
                      p.additives_tags
               FROM product_log pl
               LEFT JOIN product p ON pl.barcode = p.barcode
               WHERE pl.user_id = ? ORDER BY pl.id""", [user_id]).fetchall()
    ]
