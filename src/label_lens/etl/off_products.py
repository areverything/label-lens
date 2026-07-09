"""Open Food Facts product loader for the chosen category. [SCAFFOLD]

Purpose: populate the `product` table with US candy/confectionery items that
carry at least one slice additive, so the app can scan a real product and route
to its additive briefs.

Source: OFF full product dump as Parquet on Hugging Face, filtered in-place with
        DuckDB (no full download). Barcode lookups at query time use the OFF v2
        API. ODbL; send a User-Agent.
        hf://datasets/openfoodfacts/product-database/food.parquet
Transform (DuckDB over Parquet): filter
        countries_tags LIKE '%en:united-states%'
        AND categories_tags LIKE '%en:candies%'   (+ related confectionery tags)
        AND list_has_any(additives_tags, <slice e-tags>)
        project barcode, product_name, brands, categories, additives_tags,
        ingredients_text; write to the `product` table.
"""
from __future__ import annotations

from label_lens.slice import SLICE

PARQUET_URL = "hf://datasets/openfoodfacts/product-database/food.parquet"
OFF_V2_PRODUCT = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

# OFF additive tags for the slice, e.g. "en:e171", to filter the product dump.
SLICE_ADDITIVE_TAGS = tuple(f"en:{e.e_number.lower()}" for e in SLICE)


def load() -> int:
    raise NotImplementedError("OFF product loader: Day-1 continuation. See module docstring.")
