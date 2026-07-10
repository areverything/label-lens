"""Retrieval metrics over ranked chunk_ids, scored by additive e_number."""
from __future__ import annotations

from label_lens.eval.metrics import hit_at_k, reciprocal_rank, additive_of


def test_additive_of_reads_the_chunk_id_prefix():
    assert additive_of("E211::Evidence") == "E211"
    assert additive_of("E102::Regulatory status") == "E102"


def test_hit_at_k_true_when_correct_additive_in_top_k():
    ranked = ["E210::Evidence", "E211::Evidence", "E133::Identity"]
    assert hit_at_k(ranked, {"E211"}, k=2) == 1
    assert hit_at_k(ranked, {"E211"}, k=1) == 0  # E211 is at rank 2, not in top-1


def test_hit_at_k_false_when_absent():
    ranked = ["E210::Evidence", "E133::Identity"]
    assert hit_at_k(ranked, {"E211"}, k=5) == 0


def test_reciprocal_rank_is_one_over_first_correct_rank():
    ranked = ["E210::Evidence", "E211::Evidence", "E211::Identity"]
    assert reciprocal_rank(ranked, {"E211"}) == 0.5


def test_reciprocal_rank_zero_when_no_correct_hit():
    assert reciprocal_rank(["E210::Evidence"], {"E211"}) == 0.0


def test_hit_accepts_multiple_correct_additives():
    ranked = ["E251::Evidence", "E250::Evidence"]
    assert hit_at_k(ranked, {"E249", "E250"}, k=2) == 1
