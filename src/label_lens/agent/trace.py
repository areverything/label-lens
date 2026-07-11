"""Turn one agent run into a step-by-step activity trace for two audiences.

The chat UI shows this so a shopper with no background in AI or additives can see
what the app did, AND a certification reviewer can see exactly how: the technique
used and the concrete call made (SQL query, RAG vector search, or live API
request). Every line is derived from the real messages the agent produced.

Each step is a dict: {icon, title, tool, query, lines, note, tech, final}.
- title: the plain-English action (for the shopper).
- lines: the plain results.  note: an optional "why it matters".
- tool/query + tech {technique, call}: one consolidated technical block naming
  the tool called, the technique, and the exact call (for the reviewer).
The agent framework and model are run-level, returned once by agent_info().
"""
from __future__ import annotations

import os

# Em dash (U+2014) as an escape so the source carries no literal em dash. The
# tool outputs use it as a field separator; we split on it to parse them.
_EMDASH = " — "

# The embedding model behind the RAG lane (see rag/embed.py). Shown to reviewers.
_EMBED_MODEL = "BAAI/bge-small-en-v1.5"

# Regulator codes -> names a newcomer can read.
_JURIS = {
    "EU": "European Union",
    "US_FDA": "US FDA",
    "US_CA": "California",
    "IARC": "Cancer research (IARC)",
}

# Status codes -> plain outcomes. The IARC ones are cancer-hazard ratings, not
# legal decisions; the wording keeps them distinct from "banned / allowed".
_STATUS = {
    "authorised": "Allowed",
    "permitted": "Allowed",
    "authorised_warning": "Allowed, but must carry a warning label",
    "banned": "Banned",
    "revoked": "Approval revoked (no longer allowed)",
    "not_approved": "Not approved",
    "not_authorised": "Not allowed",
    "listed": "Listed as a concern (California Prop 65)",
    "group_2b": "Rated a possible cause of cancer (IARC Group 2B)",
    "not_classified": "Not rated as a cancer hazard",
}


def _step(icon: str, title: str, lines: list[str], note: str = "", *,
          tool: str = "", query: str = "",
          tech: dict | None = None, final: bool = False) -> dict:
    return {"icon": icon, "title": title, "tool": tool, "query": query,
            "lines": lines, "note": note, "tech": tech or {}, "final": final}


def agent_info() -> dict:
    """Run-level facts for the reviewer: the agent framework and the model.

    These frame every step (the model chose the tools), so they are shown once at
    the top of the log rather than repeated on each step.
    """
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    return {
        "framework": "LangGraph ReAct agent (create_react_agent)",
        "model": f"{model} via OpenRouter",
        "note": "The model picks which tool(s) to call by function-calling.",
    }


def summarize_run(messages: list, reply: str) -> list[dict]:
    """Build the ordered steps for one agent run.

    `messages` is the full LangGraph message list; `reply` is the final answer.
    Returns one step per source the agent checked, then a closing answer step.
    """
    results = {
        getattr(m, "tool_call_id", None): str(getattr(m, "content", ""))
        for m in messages
        if getattr(m, "type", "") == "tool"
    }
    builders = {
        "additive_status": _store_step,
        "search_briefs": _rag_step,
        "check_recalls": _recalls_step,
        "recent_regulatory_actions": _actions_step,
    }
    steps: list[dict] = []
    for m in messages:
        for tc in getattr(m, "tool_calls", None) or []:
            args = tc.get("args") or {}
            arg = str(next(iter(args.values()), "")) if args else ""
            content = results.get(tc.get("id"), "")
            build = builders.get(tc.get("name", ""))
            if build:
                steps.append(build(arg, content))
    steps.append(_answer_step(reply, tool_calls=bool(steps)))
    return steps


def _store_step(term: str, content: str) -> dict:
    title = f"Looked up the official rulings on “{term}”"
    kw = {
        "tool": "additive_status", "query": term,
        "tech": {
            "technique": "Deterministic SQL lookup (no LLM)",
            "call": ("resolve_additive(term) → SELECT jurisdiction, status, detail, "
                     "citation, as_of FROM regulatory_status WHERE cas = ?  (DuckDB)"),
        },
    }
    low = content.lower()
    if "no additive found" in low:
        return _step("⚖️", title, ["We don’t have this additive in our data yet."],
                     "When data is missing, the app says so instead of guessing.", **kw)
    if "no regulatory-status rows" in low:
        return _step("⚖️", title, ["No official rulings recorded for it yet."],
                     "When data is missing, the app says so instead of guessing.", **kw)
    legal, hazard, statuses = [], [], set()
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("- ") and ":" in line:
            juris, rest = line[2:].split(":", 1)
            juris = juris.strip()
            status = rest.split(_EMDASH)[0].split("[")[0].strip()
            label = f"{_JURIS.get(juris, juris)}: {_STATUS.get(status, status.replace('_', ' ').capitalize())}"
            if juris == "IARC":
                hazard.append(label)
            else:
                legal.append(label)
                statuses.add(status.lower())
    note = ""
    if len(statuses) > 1:
        note = ("Regulators reached different decisions here. The app shows each "
                "one rather than picking a winner.")
    return _step("⚖️", title, legal + hazard, note, **kw)


def _rag_step(term: str, content: str) -> dict:
    title = f"Read the evidence notes about “{term}”"
    kw = {
        "tool": "search_briefs", "query": term,
        "tech": {
            "technique": "Dense vector retrieval (RAG)",
            "call": (f'Chroma.similarity_search_with_score("{term}", k=4) over '
                     f'collection "briefs"; embeddings {_EMBED_MODEL} '
                     "(fastembed/ONNX); cosine distance"),
        },
    }
    if "no brief passages" in content.lower():
        return _step("📚", title, ["No evidence notes matched this."],
                     "When there’s nothing to cite, the app says so instead of guessing.", **kw)
    n = sum(1 for ln in content.splitlines() if ln.startswith("["))
    return _step("📚", title,
                 [f"Pulled the {n} most relevant passage{'s' if n != 1 else ''} "
                  "to explain the “why”."],
                 "These are curated notes from regulators and studies, not a web search.", **kw)


def _recalls_step(term: str, content: str) -> dict:
    title = f"Checked for active recalls of “{term}”"
    kw = {
        "tool": "check_recalls", "query": term,
        "tech": {
            "technique": "Live REST API call (openFDA food-enforcement)",
            "call": (f'GET api.fda.gov/food/enforcement.json?search='
                     f'reason_for_recall:"{term}"&limit=5  '
                     "(falls back to product_description)"),
        },
    }
    low = content.lower()
    if "could not reach" in low:
        return _step("🚨", title, ["Couldn’t reach the FDA recall service just now."], **kw)
    note = "This is a live check with the FDA right now, not a saved answer."
    if "no openfda food recalls" in low:
        return _step("🚨", title, ["No active recalls right now."], note, **kw)
    n = sum(1 for ln in content.splitlines() if ln.strip().startswith("- "))
    return _step("🚨", title, [f"Found {n} active recall{'s' if n != 1 else ''}."], note, **kw)


def _actions_step(term: str, content: str) -> dict:
    title = f"Checked for recent government action on “{term}”"
    kw = {
        "tool": "recent_regulatory_actions", "query": term,
        "tech": {
            "technique": "Live REST API call (US Federal Register)",
            "call": (f"GET federalregister.gov/api/v1/documents.json?"
                     f"conditions[term]={term}&conditions[agencies][]="
                     "food-and-drug-administration&order=relevance&per_page=5"),
        },
    }
    low = content.lower()
    if "could not reach" in low:
        return _step("📰", title, ["Couldn’t reach the government service just now."], **kw)
    note = "This is a live check of the US Federal Register, not a saved answer."
    if "no recent federal register" in low:
        return _step("📰", title, ["No recent action found."], note, **kw)
    n = sum(1 for ln in content.splitlines() if ln.strip().startswith("- "))
    return _step("📰", title, [f"Found {n} recent official document{'s' if n != 1 else ''}."], note, **kw)


def _answer_step(reply: str, *, tool_calls: bool) -> dict:
    low = (reply or "").lower()
    lines = ["Every fact above is cited from the source that stated it."]
    if any(k in low for k in (
        "not a doctor", "medical advice", "healthcare professional",
        "consult a", "talk to your doctor", "see a doctor", "not a substitute",
    )):
        lines.append("It won’t say whether something will harm you personally. "
                     "For that, it points you to a health professional.")
    if any(k in low for k in (
        "not the same as", "does not mean", "doesn’t mean", "doesn't mean",
        "not proven harmful", "isn’t the same", "isn't the same",
    )):
        lines.append("It keeps “banned somewhere” separate from “proven harmful”.")
    # No exact call here: the framework and model are named once in agent_info().
    technique = ("LLM synthesis: the model composed the answer from the tool "
                 "results above" if tool_calls else
                 "The model answered directly, without calling any tool")
    return _step("✅", "Wrote the answer", lines, tech={"technique": technique}, final=True)
