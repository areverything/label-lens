"""Turn one agent run into a plain-English, step-by-step activity trace.

The chat UI shows this so anyone (no background in AI, food additives, or
regulation needed) can see what the app did to answer: which official source it
checked, HOW it retrieved the information (which tool, and the method behind it),
what it found, and why that step matters. Every line is derived from the real
messages the agent produced, not narrated after the fact.

Each step is a dict: {icon, title, tool, query, how, lines, note, final}.
`title` is the plain action; `tool`/`query`/`how` are the mechanism (the tool the
agent called and how it retrieved the data); `lines` are the plain results;
`note` is an optional "why it matters".
"""
from __future__ import annotations

# Em dash (U+2014) as an escape so the source carries no literal em dash. The
# tool outputs use it as a field separator; we split on it to parse them.
_EMDASH = " — "

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
          tool: str = "", query: str = "", how: str = "", final: bool = False) -> dict:
    return {"icon": icon, "title": title, "tool": tool, "query": query, "how": how,
            "lines": lines, "note": note, "final": final}


def summarize_run(messages: list, reply: str) -> list[dict]:
    """Build the ordered, plain-English steps for one agent run.

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
    how = "Database lookup in the additive rulings table (DuckDB)"
    kw = {"tool": "additive_status", "query": term, "how": how}
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
    how = ("AI semantic search (RAG): turned the query into a vector and matched "
           "the closest brief passages in the vector index (Chroma + bge-small)")
    kw = {"tool": "search_briefs", "query": term, "how": how}
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
    how = "Live web API call to openFDA (api.fda.gov)"
    kw = {"tool": "check_recalls", "query": term, "how": how}
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
    how = "Live web API call to the US Federal Register (federalregister.gov)"
    kw = {"tool": "recent_regulatory_actions", "query": term, "how": how}
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
    how = ("The AI wrote the answer from the results above"
           if tool_calls else
           "The AI answered directly, without calling any tool")
    return _step("✅", "Wrote the answer", lines, how=how, final=True)
