"""Store lane: resolve an additive term and read its cited status rows."""
from __future__ import annotations

import pytest

from label_lens.db import connect
from label_lens.agent.store import resolve_additive, status_rows


@pytest.fixture(scope="module")
def con():
    c = connect()
    yield c
    c.close()


def test_resolve_by_e_number(con):
    a = resolve_additive(con, "E171")
    assert a is not None
    assert a["e_number"] == "E171"
    assert a["cas"]  # a CAS was resolved


def test_resolve_by_name_is_case_insensitive(con):
    a = resolve_additive(con, "titanium dioxide")
    assert a is not None
    assert a["e_number"] == "E171"


def test_resolve_unknown_returns_none(con):
    assert resolve_additive(con, "E99999") is None
    assert resolve_additive(con, "unobtainium") is None


def test_status_rows_carry_citation_and_jurisdiction(con):
    a = resolve_additive(con, "E171")
    rows = status_rows(con, a["cas"])
    juris = {r["jurisdiction"] for r in rows}
    assert "EU" in juris
    eu = next(r for r in rows if r["jurisdiction"] == "EU")
    assert eu["status"] == "banned"
    assert eu["citation"]  # every row is cited
