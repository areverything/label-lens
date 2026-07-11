"""The activity trace turns real agent messages into plain-English steps.

These stub the LangGraph message objects (anything with .type / .tool_calls /
.tool_call_id / .content) so we test the parsing, not the LLM.
"""
from __future__ import annotations

from types import SimpleNamespace

from label_lens.agent.trace import agent_info, summarize_run


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
    # The headline is plain English (no function-call syntax, no jargon codes)...
    assert "additive_status(" not in _text(store)
    assert "European Union: Banned" in store["lines"]
    assert "US FDA: Allowed" in store["lines"]
    assert "different decisions" in store["note"]
    # ...but the mechanism is exposed separately: the tool name and how it ran.
    assert store["tool"] == "additive_status"
    assert store["query"] == "titanium dioxide"
    assert "DuckDB" in store["tech"]["call"]
    # Closing answer step is marked final, notes the citation, and says the AI
    # composed it (a tool ran upstream).
    assert steps[-1]["final"] is True
    assert any("cited" in line for line in steps[-1]["lines"])
    assert "wrote the answer from the results" in steps[-1]["how"].lower()


def test_each_lane_reports_its_tool_and_retrieval_method():
    cases = [
        ("search_briefs", "query", "titanium dioxide",
         "[Titanium dioxide — Evidence]\ntext", "search_briefs", "RAG"),
        ("check_recalls", "term", "Red 3",
         "No openFDA food recalls found mentioning 'Red 3'.", "check_recalls", "openFDA"),
        ("recent_regulatory_actions", "term", "Red 3",
         "No recent Federal Register documents found for 'Red 3'.",
         "recent_regulatory_actions", "Federal Register"),
    ]
    for tool, argname, arg, content, want_tool, want_technique in cases:
        msgs = [
            _ai([{"name": tool, "args": {argname: arg}, "id": "x"}]),
            _tool("x", content),
            _final("An answer [cite]."),
        ]
        step = summarize_run(msgs, msgs[-1].content)[0]
        assert step["tool"] == want_tool
        assert step["query"] == arg
        # The technique name (RAG / openFDA / Federal Register) is on the tech block.
        assert want_technique in step["tech"]["technique"]


def test_reviewer_technical_detail_carries_technique_and_exact_call():
    msgs = [
        _ai([{"name": "search_briefs", "args": {"query": "titanium dioxide"}, "id": "a"}]),
        _tool("a", "[Titanium dioxide — Evidence]\ntext"),
        _final("Because EFSA flagged genotoxicity [EFSA]."),
    ]
    rag = summarize_run(msgs, msgs[-1].content)[0]
    assert "RAG" in rag["tech"]["technique"]
    # The exact call names the vector store, the query term, k, and the model.
    assert "similarity_search_with_score" in rag["tech"]["call"]
    assert 'titanium dioxide' in rag["tech"]["call"]
    assert "k=4" in rag["tech"]["call"]
    assert "bge-small" in rag["tech"]["call"]

    # openFDA step exposes the real endpoint and query field.
    recall = summarize_run([
        _ai([{"name": "check_recalls", "args": {"term": "Red 3"}, "id": "b"}]),
        _tool("b", "No openFDA food recalls found mentioning 'Red 3'."),
        _final("No recalls [cite]."),
    ], "No recalls [cite].")[0]
    assert "api.fda.gov/food/enforcement.json" in recall["tech"]["call"]


def test_agent_info_names_framework_and_model():
    info = agent_info()
    assert "create_react_agent" in info["framework"]
    assert "OpenRouter" in info["model"]


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
    # The plain result/headline stays jargon-free; "RAG" only appears in the
    # separate mechanism line.
    assert "RAG" not in rag["title"] and not any("RAG" in ln for ln in rag["lines"])
    assert "RAG" in rag["how"]


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
