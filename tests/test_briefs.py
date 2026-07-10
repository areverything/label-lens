"""Offline tests for brief rendering (no DB, no LLM)."""
from __future__ import annotations

from label_lens.briefs.assemble import Facts
from label_lens.briefs import generate as g


def _facts():
    return Facts(
        cas="13463-67-7", e_number="E171", name="Titanium dioxide", family="colour",
        colour_index="CI 77891", wikidata_qid="Q193521", cas_alternates="1309-63-3",
        efsa_adi=None, efsa_url="http://example.org/efsa",
        status=[
            {"jurisdiction": "EU", "status": "banned", "detail": "Banned as a food additive.", "citation": "Reg (EU) 2022/63", "as_of": "2022-01-14"},
            {"jurisdiction": "US_FDA", "status": "permitted", "detail": "Permitted color additive.", "citation": "21 CFR 73.575", "as_of": "2024-01-01"},
        ],
        example_products=["Skittles"],
    )


def test_deterministic_sections_carry_facts_and_citations():
    f = _facts()
    brief = g.render_brief(f, "[narrative]")
    assert brief.startswith("# Titanium dioxide (E171, CAS 13463-67-7)")
    assert "## Identity" in brief and "## Regulatory status" in brief and "## Evidence" in brief
    # every status row's citation is rendered verbatim
    assert "Reg (EU) 2022/63" in brief and "21 CFR 73.575" in brief


def test_missing_jurisdictions_are_flagged_not_hidden():
    # only EU + FDA supplied; California and IARC should be called out as uncompiled
    brief = g.render_brief(_facts(), "[narrative]")
    assert "No regulatory status compiled yet" in brief
    assert "California" in brief and "IARC" in brief


def test_llm_facts_block_is_grounded():
    # the block handed to the LLM must include the citations so claims can be grounded
    block = g._facts_block(_facts())
    assert "(Reg (EU) 2022/63)" in block and "(21 CFR 73.575)" in block
