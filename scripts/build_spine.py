"""Day 1 entrypoint: build the canonical additive spine and load DuckDB.

    uv run python scripts/build_spine.py

Resolves the slice's E-number -> CAS spine (OFF taxonomy + Wikidata), loads the
canonical `additives` table and the curated `regulatory_status` seed into
DuckDB, then prints a coverage + resolution report you can eyeball.
"""
from __future__ import annotations

from label_lens.db import connect, init_schema
from label_lens.etl.regulatory_seed import SEED
from label_lens.etl.spine import build_spine


def main() -> None:
    records = build_spine()

    con = connect()
    init_schema(con)
    con.execute("DELETE FROM additives")
    con.execute("DELETE FROM regulatory_status")

    e_to_cas: dict[str, str] = {}
    for r in records:
        if r.cas:
            e_to_cas[r.e_number] = r.cas
        # Unresolved additives still get a row under a visible placeholder key so
        # they surface in the store and the report instead of vanishing.
        cas_key = r.cas or f"UNRESOLVED:{r.e_number}"
        con.execute(
            """INSERT OR REPLACE INTO additives VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            [cas_key, r.e_number, r.name, r.family, r.additives_classes, r.colour_index,
             r.wikidata_qid, r.efsa_evaluation_url, r.efsa_adi, r.hook,
             r.cas_alternates, r.resolution_status],
        )

    seeded, skipped = 0, []
    for e_number, jur, status, detail, citation, as_of in SEED:
        cas = e_to_cas.get(e_number)
        if not cas:
            skipped.append(f"{e_number}/{jur}")
            continue
        con.execute(
            """INSERT OR REPLACE INTO regulatory_status VALUES (?,?,?,?,?,?,?)""",
            [cas, jur, status, detail, citation, "curated-primary", as_of],
        )
        seeded += 1

    _report(records, seeded, skipped, con)
    con.close()


def _report(records, seeded, skipped, con) -> None:
    total = len(records)
    by_status: dict[str, int] = {}
    for r in records:
        by_status[r.resolution_status] = by_status.get(r.resolution_status, 0) + 1

    print("\n" + "=" * 64)
    print(f"  SPINE BUILD REPORT  ({total} additives in slice)")
    print("=" * 64)
    print("\nCAS resolution:")
    for status in ("ok", "ambiguous_cas", "no_cas", "no_qid", "not_in_taxonomy"):
        if status in by_status:
            print(f"  {by_status[status]:2d}  {status}")
    resolved = sum(1 for r in records if r.cas)
    print(f"\n  {resolved}/{total} resolved to a canonical CAS "
          f"({100 * resolved // total}%)")

    warned = [r for r in records if r.warnings]
    if warned:
        print(f"\nWarnings ({len(warned)} additives need a look):")
        for r in warned:
            for w in r.warnings:
                print(f"  [{r.e_number:5s} {r.name[:28]:28s}] {w}")

    print(f"\nRegulatory seed loaded: {seeded} status rows"
          + (f"  (skipped, no CAS: {', '.join(skipped)})" if skipped else ""))

    print("\nSample canonical rows:")
    rows = con.execute(
        "SELECT e_number, cas, name, family, resolution_status FROM additives "
        "ORDER BY e_number LIMIT 8"
    ).fetchall()
    for e, cas, name, fam, st in rows:
        print(f"  {e:5s}  {str(cas):14s}  {name[:30]:30s}  {fam:14s}  {st}")

    div = con.execute(
        "SELECT COUNT(DISTINCT cas) FROM regulatory_status"
    ).fetchone()[0]
    print(f"\nAdditives with >=1 curated regulatory status: {div}")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    main()
