"""Backfill each product's front image URL from Open Food Facts.

Adds product.image_url and fills it from the OFF product API (the small front
image, ~200px). OFF is intermittently flaky, so each product is retried; any that
still fail are left NULL and shown with a placeholder in the UI. Run once; the
result is committed with the DuckDB so the deployed app needs no live fetch.

Usage:
    uv run python scripts/backfill_images.py
"""
from __future__ import annotations

import time

import httpx

from label_lens.config import USER_AGENT
from label_lens.db import connect

API = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
FIELDS = "image_front_small_url,image_small_url"


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
    con.execute("ALTER TABLE product ADD COLUMN IF NOT EXISTS image_url TEXT")
    barcodes = [b for (b,) in con.execute(
        "SELECT barcode FROM product WHERE image_url IS NULL ORDER BY barcode").fetchall()]
    print(f"Backfilling images for {len(barcodes)} products...")
    got = 0
    for i, bc in enumerate(barcodes, 1):
        url = _image_for(bc)
        if url:
            con.execute("UPDATE product SET image_url = ? WHERE barcode = ?", [url, bc])
            got += 1
        if i % 20 == 0:
            print(f"  {i}/{len(barcodes)} ({got} with images)")
        time.sleep(0.3)  # be polite to OFF
    total = con.execute("SELECT count(*) FROM product WHERE image_url IS NOT NULL").fetchone()[0]
    con.close()
    print(f"Done. {total} products now have an image URL.")


if __name__ == "__main__":
    main()
