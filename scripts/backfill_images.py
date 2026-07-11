"""Build data/product_images.json: barcode -> front-image URL from Open Food Facts.

Images are kept in a committed JSON sidecar rather than in the DuckDB, because
the app mutates the committed DB at runtime (memory tables) and a dirtied binary
can be skipped by a host's git update on redeploy, whereas a text file always
updates cleanly. OFF is intermittently flaky, so each product is retried; any
that fail are simply absent (the UI shows a placeholder).

Usage:
    uv run python scripts/backfill_images.py
"""
from __future__ import annotations

import json
import time

import httpx

from label_lens.config import DATA, USER_AGENT
from label_lens.db import connect

API = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
FIELDS = "image_front_small_url,image_small_url"
OUT = DATA / "product_images.json"


def _image_for(barcode: str) -> str | None:
    for attempt in range(3):
        try:
            r = httpx.get(API.format(barcode=barcode), params={"fields": FIELDS},
                          headers={"User-Agent": USER_AGENT}, timeout=25)
            if r.status_code == 200:
                p = r.json().get("product", {}) or {}
                return p.get("image_front_small_url") or p.get("image_small_url")
        except httpx.HTTPError:
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


def main() -> None:
    con = connect()
    barcodes = [b for (b,) in con.execute(
        "SELECT barcode FROM product WHERE additives_tags <> '' ORDER BY barcode").fetchall()]
    con.close()
    images: dict[str, str] = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [b for b in barcodes if b not in images]
    print(f"Fetching images for {len(todo)} products ({len(images)} already known)...")
    for i, bc in enumerate(todo, 1):
        url = _image_for(bc)
        if url:
            images[bc] = url
        if i % 20 == 0:
            print(f"  {i}/{len(todo)}")
        time.sleep(0.3)  # be polite to OFF
    OUT.write_text(json.dumps(images, indent=0, sort_keys=True))
    print(f"Wrote {len(images)} image URLs -> {OUT}")


if __name__ == "__main__":
    main()
