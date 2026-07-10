"""Chunker splits a per-additive brief into section chunks, metadata intact."""
from __future__ import annotations

from label_lens.rag.chunk import chunk_brief

BRIEF = """# Tartrazine (FD&C Yellow 5) (E102, CAS 1934-21-0)

## Identity
- **Name:** Tartrazine (FD&C Yellow 5)
- **E-number:** E102
- **CAS:** 1934-21-0
- **Family:** colour

## Regulatory status

| Jurisdiction | Status | Detail | Citation |
|---|---|---|---|
| European Union | authorised_warning | child-attention label | Reg (EC) 1333/2008 Annex V |

## Evidence

Tartrazine is regulated differently in the EU and the US. Banned somewhere does
not mean proven harmful.
"""


def test_splits_into_three_labelled_sections():
    chunks = chunk_brief(BRIEF)
    assert [c.section for c in chunks] == ["Identity", "Regulatory status", "Evidence"]


def test_every_chunk_carries_additive_identity():
    for c in chunk_brief(BRIEF):
        assert c.e_number == "E102"
        assert c.cas == "1934-21-0"
        assert c.name == "Tartrazine (FD&C Yellow 5)"


def test_chunk_text_keeps_heading_and_body():
    evidence = next(c for c in chunk_brief(BRIEF) if c.section == "Evidence")
    assert "## Evidence" in evidence.text
    assert "not mean proven harmful" in evidence.text


def test_chunk_id_is_stable_and_unique_per_section():
    ids = [c.chunk_id for c in chunk_brief(BRIEF)]
    assert ids == ["E102::Identity", "E102::Regulatory status", "E102::Evidence"]
