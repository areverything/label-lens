"""Store lane: the direct DuckDB lookup for an additive's legal status.

Resolves a user's term (an E-number, a chemical name, or a CAS) to the canonical
additive, then reads its per-jurisdiction status rows. Legal status stays in its
own column; every row carries its citation. This is the exact-fact lane.
"""
from __future__ import annotations

import re

import duckdb

_E_NUMBER = re.compile(r"^E\d+$", re.IGNORECASE)


def resolve_additive(con: duckdb.DuckDBPyConnection, term: str) -> dict | None:
    """Find one additive by E-number, CAS, or (case-insensitive) name."""
    term = term.strip()
    if _E_NUMBER.match(term):
        row = con.execute(
            "SELECT cas, e_number, name, family FROM additives WHERE upper(e_number) = upper(?)",
            [term]).fetchone()
    else:
        row = con.execute(
            """SELECT cas, e_number, name, family FROM additives
               WHERE cas = ? OR lower(name) LIKE '%' || lower(?) || '%'
               ORDER BY length(name) LIMIT 1""",
            [term, term]).fetchone()
    if row is None:
        return None
    return {"cas": row[0], "e_number": row[1], "name": row[2], "family": row[3]}


def status_rows(con: duckdb.DuckDBPyConnection, cas: str) -> list[dict]:
    """All cited regulatory-status rows for one additive, one per jurisdiction."""
    return [
        {"jurisdiction": j, "status": s, "detail": d, "citation": c, "as_of": ao}
        for j, s, d, c, ao in con.execute(
            """SELECT jurisdiction, status, detail, citation, as_of
               FROM regulatory_status WHERE cas = ?
               ORDER BY jurisdiction""", [cas]).fetchall()
    ]
