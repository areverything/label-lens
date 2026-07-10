"""A minimal RAG pipeline (retrieve -> answer from contexts) for RAGAS scoring.

This is the pure-RAG baseline RAGAS measures: it isolates retrieval + grounded
generation from the full agent's tool routing, so context_precision/recall and
faithfulness are attributable to the retriever and prompt, not to a tool call.
"""
from __future__ import annotations

from label_lens.eval.corpus import load_corpus
from label_lens.eval.retrievers import dense
from label_lens.llm import chat

_SYS = """Answer the question using ONLY the provided context passages. Cite the \
regulation or source named in the context. If the context does not contain the \
answer, say so. Keep legal status, hazard, and personal harm separate; do not \
give medical advice."""


def _contexts(question: str, k: int, retriever=dense) -> list[str]:
    by_id = {d.chunk_id: d for d in load_corpus()}
    return [by_id[cid].text for cid in retriever(question, k=k) if cid in by_id]


def rag_answer(question: str, k: int = 4, retriever=dense) -> tuple[str, list[str]]:
    """Return (answer, contexts) for one question."""
    contexts = _contexts(question, k, retriever)
    joined = "\n\n---\n\n".join(contexts)
    answer = chat(
        [{"role": "system", "content": _SYS},
         {"role": "user", "content": f"Context:\n{joined}\n\nQuestion: {question}"}],
        temperature=0.0, max_tokens=500)
    return answer, contexts
