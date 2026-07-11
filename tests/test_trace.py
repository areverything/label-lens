"""The activity trace turns real agent messages into plain-English steps.

These stub the LangGraph message objects (anything with .type / .tool_calls /
.tool_call_id / .content) so we test the parsing, not the LLM.
"""
from __future__ import annotations

from types import SimpleNamespace

from label_lens.agent.trace import summarize_run


def _ai(tool_calls):
    return SimpleNamespace(type="ai", tool_calls=tool_calls, content="")


def _tool(call_id, content):
    return SimpleNamespace(type="tool", tool_call_id=call_id, content=content)


def _final(text):
    return SimpleNamespace(type="ai", tool_calls=[], content=text)


def _text(step):
    """All human-visible text of a step, joined, for substring checks."""
    return " ".join([step["title"], *step["lines"], step["note"]])


def test_store_step_is_plain_and_flags_divergence():
    msgs = [
        SimpleNamespace(type="human", content="Is E171 banned in the EU?"),
        _ai([{"name": "additive_status", "args": {"term": "titanium dioxide"}, "id": "1"}]),
        _tool("1", "Titanium dioxide (E171, CAS 13463-67-7):\n"
                   "- EU: banned — no longer authorised [Reg (EU) 2022/63, as of 2022]\n"
                   "- US_FDA: permitted — allowed as a color [21 CFR 73.575, as of 2024]"),
        _final("E171 is banned in the EU [Reg (EU) 2022/63]; the US permits it."),
    ]
    steps = summarize_run(msgs, msgs[-1].content)
    store = steps[0]
    # No function-call syntax, no jargon codes in what the user sees.
    assert "additive_status(" not in _text(store)
    assert "European Union: Banned" in store["lines"]
    assert "US FDA: Allowed" in store["lines"]
    assert "different decisions" in store["note"]
    # Closing answer step is marked final and notes the citation.
    assert steps[-1]["final"] is True
    assert any("cited" in line for line in steps[-1]["lines"])


def test_iarc_hazard_is_worded_apart_from_legal_status():
    msgs = [
        _ai([{"name": "additive_status", "args": {"term": "aspartame"}, "id": "a"}]),
        _tool("a", "Aspartame (E951, CAS 22839-47-0):\n"
                   "- US_FDA: permitted — allowed [21 CFR, as of 2024]\n"
                   "- IARC: group_2b — possible carcinogen [IARC 2023]"),
        _final("Aspartame is permitted; IARC rates it Group 2B."),
    ]
    store = summarize_run(msgs, msgs[-1].content)[0]
    assert "Cancer research (IARC): Rated a possible cause of cancer (IARC Group 2B)" in store["lines"]


def test_rag_step_counts_passages_without_jargon():
    msgs = [
        _ai([{"name": "search_briefs", "args": {"query": "titanium dioxide"}, "id": "a"}]),
        _tool("a", "[Titanium dioxide — Evidence]\nEFSA could not rule out genotoxicity.\n\n"
                   "[Titanium dioxide — Regulatory]\nBanned in the EU from 2022."),
        _final("Because EFSA flagged genotoxicity [EFSA]."),
    ]
    rag = summarize_run(msgs, msgs[-1].content)[0]
    assert "2 most relevant passages" in _text(rag)
    assert "RAG" not in _text(rag)


def test_safety_refusal_line_is_present():
    reply = ("Red 40 is permitted by the FDA [21 CFR 74.340]. I can't give a "
             "medical verdict; please consult a healthcare professional.")
    steps = summarize_run([_final(reply)], reply)
    assert any("harm you personally" in line for line in steps[-1]["lines"])


def test_missing_data_is_honest():
    msgs = [
        _ai([{"name": "additive_status", "args": {"term": "BHT"}, "id": "z"}]),
        _tool("z", "BHT (E321, CAS 128-37-0): no regulatory-status rows recorded yet."),
        _final("No status recorded for BHT."),
    ]
    store = summarize_run(msgs, msgs[-1].content)[0]
    assert "No official rulings recorded" in _text(store)
    assert "instead of guessing" in store["note"]
