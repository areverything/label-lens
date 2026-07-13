"""Regression tests for the DuckDB concurrency bug.

LangGraph runs the agent's tool calls in a thread pool. The cumulative question
("across the candy I've logged, is anything banned?") makes the agent issue many
additive_status lookups at once, which ran concurrently on one shared DuckDB
connection. DuckDB connections are not safe for concurrent queries, so a
5-column status fetch could pick up another thread's 4-column resolve_additive
rows, raising "not enough values to unpack (expected 5, got 4)". The fix hands
each thread its own connection (a cursor over one shared instance).
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from label_lens.agent.tools import _con, additive_status


def test_con_is_thread_local():
    """Each thread must get its own connection, distinct from every other thread.

    This is the property that prevents cross-thread result contamination. If
    `_con()` reverts to one shared singleton, all ids collapse to one and this
    fails.
    """
    conns = {"main": _con()}  # hold the objects so ids can't be reused by GC
    lock = threading.Lock()

    def grab(name: str) -> None:
        c = _con()
        with lock:
            conns[name] = c

    threads = [threading.Thread(target=grab, args=(f"t{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    ids = {id(c) for c in conns.values()}
    assert len(ids) == len(conns)  # main + 4 workers all distinct


def test_concurrent_additive_status_has_no_crosstalk():
    """Many additive_status calls in parallel each return their own additive's
    data, with no unpack error and no bleed-through from another lookup."""
    checks = {
        "E171": "Titanium dioxide",
        "E102": "Tartrazine",
        "E951": "Aspartame",
        "E110": "Sunset Yellow",
        "E129": "Allura Red",
    }
    terms = list(checks) * 6

    def call(term: str) -> tuple[str, str]:
        return term, additive_status.invoke({"term": term})

    for _ in range(8):
        with ThreadPoolExecutor(max_workers=10) as ex:
            for term, out in ex.map(call, terms):
                # The result names the additive that was asked for, not another's.
                assert checks[term] in out, f"{term} returned: {out[:120]}"
