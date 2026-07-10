"""Gather the facts for one additive's brief from the DuckDB store.

Pure data assembly, no LLM. Everything here is traceable to a table row, so the
deterministic parts of a brief can never hallucinate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import duckdb

# Order jurisdictions consistently; IARC last because it's a hazard note, not law.
JURISDICTION_ORDER = ["EU", "US_FDA", "US_CA", "IARC"]
JURISDICTION_LABEL = {
    "EU": "European Union",
    "US_FDA": "United States (FDA)",
    "US_CA": "California",
    "IARC": "IARC (cancer-hazard classification)",
}


@dataclass
class Facts:
    cas: str
    e_number: str
    name: str
    family: str
    colour_index: str | None
    wikidata_qid: str | None
    cas_alternates: str
    efsa_adi: str | None
    efsa_url: str | None
    status: list[dict] = field(default_factory=list)      # per-jurisdiction rows
    example_products: list[str] = field(default_factory=list)


def assemble(con: duckdb.DuckDBPyConnection, cas: str) -> Facts:
    a = con.execute(
        """SELECT cas, e_number, name, family, colour_index, wikidata_qid,
                  cas_alternates, efsa_adi, efsa_evaluation_url
           FROM additives WHERE cas = ?""", [cas]).fetchone()
    if a is None:
        raise KeyError(f"no additive with cas={cas}")

    status = [
        {"jurisdiction": j, "status": s, "detail": d, "citation": c, "as_of": ao}
        for j, s, d, c, ao in con.execute(
            """SELECT jurisdiction, status, detail, citation, as_of
               FROM regulatory_status WHERE cas = ?""", [cas]).fetchall()
    ]
    status.sort(key=lambda r: JURISDICTION_ORDER.index(r["jurisdiction"])
                if r["jurisdiction"] in JURISDICTION_ORDER else 99)

    products = [
        n for (n,) in con.execute(
            """SELECT name FROM product
               WHERE name IS NOT NULL
                 AND list_contains(string_split(additives_tags, ','), 'en:' || lower(?))
               LIMIT 3""", [a[1]]).fetchall()
    ]

    return Facts(
        cas=a[0], e_number=a[1], name=a[2], family=a[3], colour_index=a[4],
        wikidata_qid=a[5], cas_alternates=a[6], efsa_adi=a[7], efsa_url=a[8],
        status=status, example_products=products,
    )
