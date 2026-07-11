"""The activity trace turns real agent messages into UI-ready steps.

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


def test_store_step_flags_regulator_divergence_and_citation():
    msgs = [
        SimpleNamespace(type="human", content="Is E171 banned in the EU?"),
        _ai([{"name": "additive_status", "args": {"term": "E171"}, "id": "1"}]),
        _tool("1", "Titanium dioxide (E171, CAS 13463-67-7):\n"
                   "- EU: banned — no longer authorised [Reg (EU) 2022/63, as of 2022]\n"
                   "- US FDA: permitted — allowed as a color [21 CFR 73.575, as of 2024]"),
        SimpleNamespace(type="ai", tool_calls=[],
                        content="E171 is banned in the EU [Reg (EU) 2022/63]; the US permits it."),
    ]
    steps = summarize_run(msgs, msgs[-1].content)
    store = steps[0]
    assert store["lane"] == "Store"
    assert store["call"] == 'additive_status("E171")'
    assert "EU: banned" in store["result"] and "US FDA: permitted" in store["result"]
    assert "regulator divergence" in store["tags"]
    # Closing answer note is present and marks the citation.
    assert steps[-1]["kind"] == "answer"
    assert "cited" in steps[-1]["tags"]


def test_rag_step_counts_passages():
    msgs = [
        _ai([{"name": "search_briefs", "args": {"query": "titanium dioxide"}, "id": "a"}]),
        _tool("a", "[Titanium dioxide — Evidence]\nEFSA could not rule out genotoxicity.\n\n"
                   "[Titanium dioxide — Regulatory]\nBanned in the EU from 2022."),
        SimpleNamespace(type="ai", tool_calls=[], content="Because EFSA flagged genotoxicity [EFSA]."),
    ]
    steps = summarize_run(msgs, msgs[-1].content)
    assert steps[0]["lane"] == "RAG"
    assert "2 evidence passages" in steps[0]["result"]


def test_safety_refusal_is_tagged():
    reply = ("Red 40 is permitted by the FDA [21 CFR 74.340]. I can't give a "
             "medical verdict; please consult a healthcare professional.")
    steps = summarize_run([SimpleNamespace(type="ai", tool_calls=[], content=reply)], reply)
    assert any("safety refusal" in t for t in steps[-1]["tags"])


def test_missing_data_is_honest():
    msgs = [
        _ai([{"name": "additive_status", "args": {"term": "BHT"}, "id": "z"}]),
        _tool("z", "BHT (E321, CAS 128-37-0): no regulatory-status rows recorded yet."),
        SimpleNamespace(type="ai", tool_calls=[], content="No status recorded for BHT."),
    ]
    steps = summarize_run(msgs, msgs[-1].content)
    assert "honest: no data on file" in steps[0]["tags"]
