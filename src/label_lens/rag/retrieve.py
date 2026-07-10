"""Dense retrieval baseline over the brief index.

Returns the top-k brief passages for a query, each with its additive-identity
metadata so the agent can cite the section and jurisdiction it came from.
"""
from __future__ import annotations

from dataclasses import dataclass

from label_lens.rag.index import load_index


@dataclass
class Passage:
    chunk_id: str
    section: str
    e_number: str
    name: str
    text: str
    score: float           # cosine distance; lower is closer


def retrieve(query: str, k: int = 4) -> list[Passage]:
    store = load_index()
    hits = store.similarity_search_with_score(query, k=k)
    return [
        Passage(
            chunk_id=d.metadata.get("chunk_id", d.id or ""),
            section=d.metadata.get("section", ""),
            e_number=d.metadata.get("e_number", ""),
            name=d.metadata.get("name", ""),
            text=d.page_content,
            score=float(score),
        )
        for d, score in hits
    ]
