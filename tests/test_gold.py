"""The gold set is well-formed and every RAG target additive exists in the store."""
from __future__ import annotations

from label_lens.db import connect
from label_lens.eval.gold import load_gold


def test_gold_rows_have_required_fields():
    for g in load_gold():
        assert g["id"] and g["question"] and g["reference"]
        assert g["lane"] in {"rag", "store", "safety", "live", "memory"}
        assert isinstance(g["additives"], list)


def test_rag_targets_are_real_additives():
    con = connect()
    known = {e for (e,) in con.execute("SELECT e_number FROM additives").fetchall()}
    for g in load_gold("rag"):
        for e in g["additives"]:
            assert e in known, f"{g['id']} targets unknown additive {e}"


def test_gold_has_enough_rag_questions_to_measure():
    assert len(load_gold("rag")) >= 15  # headroom for hit@k / MRR deltas
