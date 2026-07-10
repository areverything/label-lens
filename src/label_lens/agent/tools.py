"""The four agent tools, one per lane, as LangChain tools.

Each returns a compact, citation-bearing string for the model to compose from.
The Store and RAG lanes answer stable "what / why" questions; the two live
government tools answer "what's happening right now". Legal status, hazard
classification, and personal harm are kept distinct in the wording so the model
cannot conflate them.
"""
from __future__ import annotations

from functools import lru_cache

import duckdb
from langchain_core.tools import tool

from label_lens.agent import live, memory, store
from label_lens.config import DB_PATH
from label_lens.rag.retrieve import retrieve


@lru_cache(maxsize=1)
def _con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(DB_PATH))
    memory.ensure_memory_tables(con)
    return con


@tool
def additive_status(term: str) -> str:
    """Look up an additive's legal regulatory status by jurisdiction.

    Use for exact-fact questions like "Is E171 banned in the EU?". `term` may be
    an E-number (E171), a chemical name (titanium dioxide), or a CAS number.
    Returns each jurisdiction's legal status with its citation. This is legal
    status only, not a hazard or safety judgement.
    """
    con = _con()
    a = store.resolve_additive(con, term)
    if a is None:
        return f"No additive found matching '{term}'."
    rows = store.status_rows(con, a["cas"])
    head = f"{a['name']} ({a['e_number']}, CAS {a['cas']}):"
    if not rows:
        return f"{head} no regulatory-status rows recorded yet."
    lines = [
        f"- {r['jurisdiction']}: {r['status']} — {r['detail']} "
        f"[{r['citation']}, as of {r['as_of']}]"
        for r in rows
    ]
    return head + "\n" + "\n".join(lines)


@tool
def search_briefs(query: str) -> str:
    """Retrieve evidence passages from the per-additive briefs (RAG).

    Use for "why" and "is it dangerous" questions that need explanation and
    scientific evidence, e.g. "Why did the EU ban titanium dioxide?". Returns the
    most relevant brief sections, each tagged with its additive and section.
    """
    passages = retrieve(query, k=4)
    if not passages:
        return "No brief passages retrieved."
    return "\n\n".join(
        f"[{p.name} — {p.section}]\n{p.text}" for p in passages
    )


@tool
def check_recalls(term: str) -> str:
    """Check openFDA for recent food recalls mentioning a product or additive.

    Use for "is this recalled?" questions. `term` is a product name, brand, or
    additive. Live call to the openFDA food-enforcement API.
    """
    res = live.openfda_recalls(term)
    if res.get("error"):
        return f"Could not reach openFDA: {res['error']}"
    recalls = res["recalls"]
    if not recalls:
        return f"No openFDA food recalls found mentioning '{term}'."
    lines = [
        f"- [{r['recall_date']}] {r['recalling_firm']}: {r['product']} "
        f"(class {r['classification']}, {r['status']}) — {r['reason']}"
        for r in recalls
    ]
    return f"openFDA recalls mentioning '{term}':\n" + "\n".join(lines)


@tool
def recent_regulatory_actions(term: str) -> str:
    """Search the Federal Register for recent FDA rules on an additive.

    Use for "any recent FDA action / new ban?" questions. Surfaces new rules,
    bans, and authorization revocations that post-date the briefs. `term` is the
    additive name (e.g. "FD&C Red No. 3"). Live call to the Federal Register API.
    """
    res = live.federal_register(term)
    if res.get("error"):
        return f"Could not reach the Federal Register: {res['error']}"
    docs = res["documents"]
    if not docs:
        return f"No recent Federal Register documents found for '{term}'."
    lines = [
        f"- [{d['published']}] {d['type']}: {d['title']} ({d['url']})"
        for d in docs
    ]
    return f"Federal Register (FDA) documents for '{term}':\n" + "\n".join(lines)


ALL_TOOLS = [additive_status, search_briefs, check_recalls, recent_regulatory_actions]
