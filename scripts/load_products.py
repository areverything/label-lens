"""Load US candy products (carrying a slice additive) from Open Food Facts.

    uv run python scripts/load_products.py [TOTAL]

Populates the `product` table via the OFF Search API, then prints how many
products link to each slice additive.
"""
from __future__ import annotations

import sys
import time

from label_lens.db import connect
from label_lens.etl import off_products


def main() -> None:
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    t0 = time.time()
    n = off_products.load(total=total)
    print(f"loaded {n} products in {time.time() - t0:.0f}s")

    con = connect()
    print("\nProducts per slice additive:")
    for e, name, cnt in con.execute("""
        SELECT a.e_number, a.name, count(*) AS n
        FROM product p, additives a
        WHERE list_contains(string_split(p.additives_tags, ','), 'en:' || lower(a.e_number))
        GROUP BY a.e_number, a.name ORDER BY n DESC""").fetchall():
        print(f"  {e:5s} {name[:28]:28s} {cnt}")
    con.close()


if __name__ == "__main__":
    main()
