"""Build and load the Chroma index over the per-additive briefs.

One vector per brief section (identity / regulatory status / evidence). Metadata
carries the additive identity and citation-bearing section so a retrieved passage
is traceable back to its additive and jurisdiction lane.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from label_lens.config import DATA
from label_lens.rag.chunk import chunk_brief
from label_lens.rag.embed import get_embeddings

CHROMA_DIR = DATA / "chroma"
BRIEFS_DIR = DATA / "briefs"
COLLECTION = "briefs"


def _documents(briefs_dir: Path) -> list[Document]:
    docs: list[Document] = []
    for p in sorted(briefs_dir.glob("*.md")):
        for c in chunk_brief(p.read_text()):
            docs.append(Document(
                page_content=c.text,
                id=c.chunk_id,
                metadata={
                    "chunk_id": c.chunk_id,
                    "section": c.section,
                    "e_number": c.e_number,
                    "cas": c.cas,
                    "name": c.name,
                    "source": p.name,
                },
            ))
    return docs


def build_index(briefs_dir: Path = BRIEFS_DIR,
                persist_dir: Path = CHROMA_DIR) -> Chroma:
    """Rebuild from scratch: wipe the persisted store, re-embed every chunk."""
    docs = _documents(briefs_dir)
    if not docs:
        raise RuntimeError(f"no briefs found in {briefs_dir}")
    if persist_dir.exists():
        shutil.rmtree(persist_dir)
    store = Chroma(
        collection_name=COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(persist_dir),
    )
    store.add_documents(docs, ids=[d.id for d in docs])
    return store


def load_index(persist_dir: Path = CHROMA_DIR) -> Chroma:
    if not persist_dir.exists():
        raise FileNotFoundError(
            f"no Chroma index at {persist_dir}; run scripts/build_index.py first"
        )
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(persist_dir),
    )


def ensure_index(persist_dir: Path = CHROMA_DIR) -> Chroma:
    """Load the index, building it once if it does not exist yet.

    Used at app startup on a fresh host (the index is gitignored, so a deployed
    clone rebuilds it once from the committed briefs). Cheap: no LLM, just the
    embedding model that is loaded for queries anyway.
    """
    if persist_dir.exists():
        return load_index(persist_dir)
    return build_index(persist_dir=persist_dir)
