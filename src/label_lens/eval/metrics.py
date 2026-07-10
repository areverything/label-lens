"""Retrieval metrics: was the right additive's brief retrieved, and how high?

A chunk_id is "<E-number>::<section>", so the additive behind any ranked chunk is
its prefix. A hit means a chunk from a gold-correct additive appears in the top-k.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence


def additive_of(chunk_id: str) -> str:
    return chunk_id.split("::", 1)[0]


def hit_at_k(ranked: Sequence[str], correct: Iterable[str], k: int) -> int:
    correct = set(correct)
    return int(any(additive_of(cid) in correct for cid in ranked[:k]))


def reciprocal_rank(ranked: Sequence[str], correct: Iterable[str]) -> float:
    correct = set(correct)
    for rank, cid in enumerate(ranked, start=1):
        if additive_of(cid) in correct:
            return 1.0 / rank
    return 0.0
