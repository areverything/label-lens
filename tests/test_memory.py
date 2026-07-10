"""User memory: a diet/allergy profile and a product log, round-tripped in DuckDB."""
from __future__ import annotations

import duckdb
import pytest

from label_lens.agent.memory import (
    ensure_memory_tables, get_log, get_profile, log_product, set_profile,
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
