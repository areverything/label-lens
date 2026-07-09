"""Offline smoke tests for the Day-1 spine. No network (uses the cached taxonomy)."""
from __future__ import annotations

import pytest

from label_lens.etl import off_taxonomy
from label_lens.slice import BY_E_NUMBER, SLICE, e_num_digits


def test_slice_is_28_unique_additives():
    assert len(SLICE) == 28
    assert len(BY_E_NUMBER) == 28  # E-numbers are unique


def test_e_num_digits():
    assert e_num_digits("E171") == "171"
    assert e_num_digits("e102") == "102"


@pytest.mark.skipif(not off_taxonomy.TAXONOMY_PATH.exists(),
                    reason="taxonomy not downloaded")
def test_taxonomy_parses_marquee_additives():
    tax = off_taxonomy.load()
    tio2 = tax["171"]
    assert tio2.name_en and "titanium" in tio2.name_en.lower()
    assert tio2.wikidata_qid == "Q193521"      # the QID that bridges to CAS
    assert "colour" in tio2.additives_classes


def test_most_slice_additives_are_in_taxonomy():
    tax = off_taxonomy.load()
    present = [e for e in BY_E_NUMBER if e_num_digits(e) in tax]
    # We expect near-full coverage; assert a floor so a taxonomy shift is caught.
    assert len(present) >= 24
