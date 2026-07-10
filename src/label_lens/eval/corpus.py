"""Load the full brief-chunk corpus into memory for retrieval experiments.

The corpus is tiny (84 chunks), so BM25 and reranking can operate over all of it
without an index. Each item keeps its chunk_id, additive e_number, section, and
text, so a retriever's hits can be scored against the gold set by e_number.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from label_lens.config import DATA
from label_lens.rag.chunk import chunk_brief

BRIEFS_DIR = DATA / "briefs"


@dataclass(frozen=True)
class Doc:
    chunk_id: str
    e_number: str
    name: str
    section: str
    text: str


@lru_cache(maxsize=1)
def load_corpus() -> tuple[Doc, ...]:
    docs: list[Doc] = []
    for p in sorted(BRIEFS_DIR.glob("*.md")):
        for c in chunk_brief(p.read_text()):
            docs.append(Doc(c.chunk_id, c.e_number, c.name, c.section, c.text))
    return tuple(docs)


@lru_cache(maxsize=1)
def by_id() -> dict[str, Doc]:
    """Chunk_id -> Doc, for looking up a retrieved chunk's text and metadata."""
    return {d.chunk_id: d for d in load_corpus()}
