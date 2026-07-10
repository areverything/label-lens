"""Build the Chroma vector index over the per-additive briefs.

Usage:
    uv run python scripts/build_index.py

Rebuilds from scratch each run (wipes data/chroma), embedding every brief
section with local bge-small. Fast: the corpus is tens of additives.
"""
from __future__ import annotations

from label_lens.rag.index import CHROMA_DIR, build_index


def main() -> None:
    store = build_index()
    n = store._collection.count()
    print(f"Indexed {n} brief chunks -> {CHROMA_DIR}")


if __name__ == "__main__":
    main()
