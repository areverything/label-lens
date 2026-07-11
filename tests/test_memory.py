"""User memory: a diet/allergy profile and a product log, round-tripped in DuckDB."""
from __future__ import annotations

import duckdb
import pytest

from label_lens.agent.memory import (
    ensure_memory_tables, get_log, get_log_with_additives, get_profile,
    log_product, remove_product, set_profile,
)


@pytest.fixture()
def con():
    c = duckdb.connect(":memory:")
    ensure_memory_tables(c)
    yield c
    c.close()


def test_profile_round_trips(con):
    set_profile(con, "u1", diet="vegetarian", allergies="peanuts")
    p = get_profile(con, "u1")
    assert p["diet"] == "vegetarian"
    assert p["allergies"] == "peanuts"


def test_set_profile_upserts(con):
    set_profile(con, "u1", diet="vegan", allergies="")
    set_profile(con, "u1", diet="vegan", allergies="soy")
    p = get_profile(con, "u1")
    assert p["allergies"] == "soy"  # updated, not duplicated


def test_missing_profile_is_none(con):
    assert get_profile(con, "nobody") is None


def test_product_log_accumulates_in_order(con):
    log_product(con, "u1", barcode="111", name="Gummy Bears")
    log_product(con, "u1", barcode="222", name="Red Licorice")
    names = [r["name"] for r in get_log(con, "u1")]
    assert names == ["Gummy Bears", "Red Licorice"]


def test_log_is_per_user(con):
    log_product(con, "u1", barcode="111", name="Gummy Bears")
    assert get_log(con, "u2") == []


def test_remove_product_takes_it_out_of_the_pantry(con):
    log_product(con, "u1", barcode="111", name="Gummy Bears")
    log_product(con, "u1", barcode="222", name="Red Licorice")
    remove_product(con, "u1", "111")
    names = [r["name"] for r in get_log(con, "u1")]
    assert names == ["Red Licorice"]


def test_log_with_additives_joins_real_product_tags(con):
    con.execute("CREATE TABLE product (barcode TEXT, name TEXT, additives_tags TEXT)")
    con.execute("INSERT INTO product VALUES ('999', 'Skittles', 'en:e102,en:e171')")
    log_product(con, "u1", barcode="999", name="Skittles")
    log_product(con, "u1", barcode="000", name="Unknown Bar")  # not in product table
    rows = get_log_with_additives(con, "u1")
    assert rows[0]["additives"] == "en:e102,en:e171"
    assert rows[1]["additives"] == ""  # unmatched barcode -> empty, not fabricated
