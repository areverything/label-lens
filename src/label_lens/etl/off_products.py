"""Open Food Facts product loader for the chosen category.

Purpose: populate the `product` table with US candy/confectionery items that
carry at least one slice additive, so the app can scan a real product and route
to its additive briefs.

Two paths, same output:
- `load()` (default) uses the OFF Search API: targeted, reliable, no bulk
  download, filters to US products carrying a slice additive then keeps the
  candy/confectionery ones.
- `load_via_parquet()` filters the full OFF Parquet dump with DuckDB (projection
  + predicate pushdown). Heavier and subject to Hugging Face rate limits; kept
  for bulk reloads.

Both write to the `product` table. ODbL data; send a User-Agent.
"""
from __future__ import annotations

import time

import duckdb
import httpx

from label_lens.config import DB_PATH, USER_AGENT
from label_lens.db import connect, init_schema
from label_lens.slice import SLICE

SEARCH_API = "https://world.openfoodfacts.org/api/v2/search"
PARQUET_URL = "hf://datasets/openfoodfacts/product-database/food.parquet"
OFF_V2_PRODUCT = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

# OFF additive tags for the slice, e.g. "en:e171", to filter products by.
SLICE_ADDITIVE_TAGS = tuple(f"en:{e.e_number.lower()}" for e in SLICE)

# Category-tag substrings that mark a product as candy/confectionery.
_CANDY_KEYWORDS = ("candie", "confection", "sweet-snack", "chewing-gum",
                   "marshmallow", "lollipop", "gumm")

_FIELDS = "code,product_name,brands,categories_tags,countries_tags,additives_tags,ingredients_text"


def _is_candy(categories_tags: list[str] | None) -> bool:
    return any(k in c for c in (categories_tags or []) for k in _CANDY_KEYWORDS)


def _row(p: dict) -> tuple:
    code = p.get("code")
    return (
        code,
        (p.get("product_name") or None),
        (p.get("brands") or None),
        ", ".join(p.get("categories_tags") or []),
        ", ".join(p.get("countries_tags") or []),
        ",".join(p.get("additives_tags") or []),
        (p.get("ingredients_text") or None),
        f"https://world.openfoodfacts.org/product/{code}",
    )


def _get_json(client: httpx.Client, params: dict, tries: int = 4) -> dict:
    """GET with backoff on the Search API's frequent 429/503/timeout hiccups."""
    for i in range(tries):
        try:
            r = client.get(SEARCH_API, params=params)
            if r.status_code in (429, 500, 502, 503, 504):
                raise httpx.HTTPStatusError(f"status {r.status_code}", request=r.request, response=r)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPStatusError, httpx.TransportError) as e:
            if i == tries - 1:
                raise
            time.sleep(10 * (i + 1))
    return {}


def search_candy_products(total: int = 400, per_additive: int = 60,
                          pages: int = 3, page_size: int = 50,
                          throttle_s: float = 7.0) -> list[tuple]:
    """Collect US candy products carrying a slice additive, via the Search API.

    Queries per additive (US + that additive), keeps the candy ones, dedupes by
    barcode. Throttled to respect the Search API rate limit (~10 req/min).
    """
    seen: dict[str, tuple] = {}
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60) as c:
        for tag in SLICE_ADDITIVE_TAGS:
            kept_for_tag = 0
            for page in range(1, pages + 1):
                if len(seen) >= total or kept_for_tag >= per_additive:
                    break
                products = _get_json(c, {
                    "countries_tags_en": "United States",
                    "additives_tags": tag,
                    "fields": _FIELDS,
                    "page_size": page_size,
                    "page": page,
                }).get("products", [])
                if not products:
                    break
                for p in products:
                    if not p.get("code") or not _is_candy(p.get("categories_tags")):
                        continue
                    if p["code"] not in seen:
                        seen[p["code"]] = _row(p)
                        kept_for_tag += 1
                        if len(seen) >= total or kept_for_tag >= per_additive:
                            break
                time.sleep(throttle_s)
            if len(seen) >= total:
                break
    return list(seen.values())


def load(total: int = 400, db_path=DB_PATH) -> int:
    """Load US candy products (with a slice additive) into `product` via the API."""
    rows = search_candy_products(total=total)
    con = connect(db_path)
    init_schema(con)
    con.execute("DELETE FROM product")
    con.executemany("INSERT OR REPLACE INTO product VALUES (?,?,?,?,?,?,?,?)", rows)
    n = con.execute("SELECT count(*) FROM product").fetchone()[0]
    con.close()
    return n


def _tag_array_sql(tags: tuple[str, ...]) -> str:
    return "[" + ", ".join(f"'{t}'" for t in tags) + "]"


def load_via_parquet(limit: int = 400, db_path=DB_PATH) -> int:
    """Alternative: filter the full OFF Parquet with DuckDB (subject to HF rate limits)."""
    tags = _tag_array_sql(SLICE_ADDITIVE_TAGS)
    con: duckdb.DuckDBPyConnection = connect(db_path)
    init_schema(con)
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("DELETE FROM product")
    con.execute(
        f"""
        INSERT OR REPLACE INTO product
        SELECT
            code AS barcode,
            coalesce(list_filter(product_name, x -> x.lang = 'en')[1].text,
                     product_name[1].text) AS name,
            brands,
            array_to_string(categories_tags, ', ') AS categories,
            array_to_string(countries_tags, ', ') AS countries,
            array_to_string(additives_tags, ',') AS additives_tags,
            coalesce(list_filter(ingredients_text, x -> x.lang = 'en')[1].text,
                     ingredients_text[1].text) AS ingredients_text,
            'https://world.openfoodfacts.org/product/' || code AS off_url
        FROM read_parquet('{PARQUET_URL}')
        WHERE list_contains(countries_tags, 'en:united-states')
          AND len(list_filter(categories_tags, t -> t LIKE '%candie%'
                              OR t LIKE '%confection%' OR t LIKE '%sweets%')) > 0
          AND len(list_intersect(additives_tags, {tags})) > 0
          AND code IS NOT NULL
        LIMIT {int(limit)}
        """
    )
    n = con.execute("SELECT count(*) FROM product").fetchone()[0]
    con.close()
    return n
