"""Turn one agent run into a compact, human-readable activity trace.

The chat UI shows this so a viewer can see the app "doing the right thing" in the
background: which lane each question was routed to (Store / RAG / live government
API), the query it ran, a one-line summary of what came back, and a short tag for
the requirement that step demonstrates. Everything here is derived from the real
messages the agent produced, not narrated after the fact.
"""
from __future__ import annotations

# Em dash (U+2014) as an escape so the source carries no literal em dash. The
# tool outputs use it as a field separator; we split on it to parse them.
_EMDASH = " — "

# Tool name -> the lane label a viewer sees.
_LANES = {
    "additive_status": "Store",
    "search_briefs": "RAG",
    "check_recalls": "Live · openFDA",
    "recent_regulatory_actions": "Live · Federal Register",
}


def summarize_run(messages: list, reply: str) -> list[dict]:
    """Build the ordered list of steps for one agent run.

    `messages` is the full LangGraph message list (human, ai-with-tool-calls,
    tool-result, final ai). `reply` is the final answer text. Returns a list of
    step dicts: one per tool call, then a closing "answer" note.
    """
    results = {
        getattr(m, "tool_call_id", None): str(getattr(m, "content", ""))
        for m in messages
        if getattr(m, "type", "") == "tool"
    }
    steps: list[dict] = []
    for m in messages:
        for tc in getattr(m, "tool_calls", None) or []:
            name = tc.get("name", "")
            args = tc.get("args") or {}
            arg = next(iter(args.values()), "") if args else ""
            steps.append(_tool_step(name, str(arg), results.get(tc.get("id"), "")))
    steps.append(_answer_step(reply))
    return steps


def _tool_step(name: str, arg: str, content: str) -> dict:
    result, tags = _summarize(name, content)
    return {
        "kind": "tool",
        "lane": _LANES.get(name, name),
        "call": f'{name}("{arg}")',
        "result": result,
        "tags": tags,
    }


def _summarize(name: str, content: str) -> tuple[str, list[str]]:
    """One-line result summary plus the requirement tags for a tool result."""
    c = content or ""
    low = c.lower()

    if name == "additive_status":
        if "no additive found" in low or "no regulatory-status rows" in low:
            return _oneline(c), ["honest: no data on file"]
        pairs, statuses = [], set()
        for line in c.splitlines():
            line = line.strip()
            if line.startswith("- ") and ":" in line:
                juris, rest = line[2:].split(":", 1)
                status = rest.split(_EMDASH)[0].split("[")[0].strip()
                pairs.append((juris.strip(), status))
                statuses.add(status.lower())
        shown = "; ".join(f"{j}: {s}" for j, s in pairs[:3])
        if len(pairs) > 3:
            shown += f" (+{len(pairs) - 3} more)"
        tags = ["legal status, cited"]
        if len(statuses) > 1:
            tags.append("regulator divergence")
        return shown or _oneline(c), tags

    if name == "search_briefs":
        if "no brief passages" in low:
            return "no passages retrieved", ["honest: no evidence on file"]
        names, count = [], 0
        for line in c.splitlines():
            if line.startswith("["):
                count += 1
                nm = line[1:].split(_EMDASH)[0].strip()
                if nm and nm not in names:
                    names.append(nm)
        summary = f"{count} evidence passage{'s' if count != 1 else ''}"
        if names:
            summary += " · " + ", ".join(names[:3])
        return summary, ["evidence (RAG), cited"]

    if name == "check_recalls":
        if "could not reach" in low:
            return _oneline(c), ["live call failed"]
        if "no openfda food recalls" in low:
            return "no current recalls", ["live: openFDA, current data"]
        n = sum(1 for ln in c.splitlines() if ln.strip().startswith("- "))
        return f"{n} recall{'s' if n != 1 else ''} found", ["live: openFDA, current data"]

    if name == "recent_regulatory_actions":
        if "could not reach" in low:
            return _oneline(c), ["live call failed"]
        if "no recent federal register" in low:
            return "no recent actions", ["live: Federal Register, current data"]
        n = sum(1 for ln in c.splitlines() if ln.strip().startswith("- "))
        return f"{n} FDA document{'s' if n != 1 else ''}", ["live: Federal Register, current data"]

    return _oneline(c), []


def _answer_step(reply: str) -> dict:
    """The closing note: what the composed answer demonstrates."""
    low = (reply or "").lower()
    tags: list[str] = []
    if "[" in (reply or ""):
        tags.append("cited")
    if any(k in low for k in (
        "not a doctor", "medical advice", "healthcare professional",
        "consult a", "talk to your doctor", "see a doctor", "not a substitute",
    )):
        tags.append("safety refusal: no medical verdict")
    if any(k in low for k in (
        "not the same as", "does not mean", "doesn't mean",
        "not proven harmful", "isn't the same",
    )):
        tags.append("banned ≠ harmful kept distinct")
    return {
        "kind": "answer",
        "lane": "Answer",
        "call": "",
        "result": "composed from the tool results above",
        "tags": tags or ["cited"],
    }


def _oneline(text: str) -> str:
    """First non-empty line, trimmed, for terse error/empty summaries."""
    for line in (text or "").splitlines():
        line = line.strip()
        if line:
            return line[:120]
    return "(no output)"
