"""RAGAS retrieval + generation metrics over the RAG pipeline.

RAGAS 0.4.3 hard-imports a legacy langchain module (chat_models.vertexai) that
langchain 1.x dropped; we never use VertexAI, so a one-line sys.modules shim lets
RAGAS import and run against the current stack without downgrading everything.

Metrics (all through the OpenRouter gateway + local fastembed embeddings):
- context_precision / context_recall: is the retrieved context relevant and
  complete against the reference?
- faithfulness: are the answer's claims supported by the retrieved context?
- answer_relevancy: is the answer on-topic for the question?
"""
from __future__ import annotations

import sys
import types

# Shim before importing ragas (see module docstring).
_vertex = types.ModuleType("langchain_community.chat_models.vertexai")
_vertex.ChatVertexAI = object  # type: ignore[attr-defined]
sys.modules.setdefault("langchain_community.chat_models.vertexai", _vertex)

from langchain_core.embeddings import Embeddings  # noqa: E402
from ragas import EvaluationDataset, SingleTurnSample, evaluate  # noqa: E402
from ragas.embeddings import LangchainEmbeddingsWrapper  # noqa: E402
from ragas.llms import LangchainLLMWrapper  # noqa: E402
from ragas.metrics import (  # noqa: E402
    answer_relevancy, context_precision, context_recall, faithfulness,
)

from label_lens.agent.graph import _model  # noqa: E402
from label_lens.eval.rag_pipeline import rag_answer  # noqa: E402
from label_lens.rag.embed import MODEL_NAME, get_embeddings  # noqa: E402

METRICS = [context_precision, context_recall, faithfulness, answer_relevancy]


class _StringModelEmbeddings(Embeddings):
    """Delegates to fastembed but exposes `model` as a string.

    RAGAS's usage telemetry reads `embeddings.model` expecting a string;
    fastembed's own `.model` is the embedding object, which fails validation and
    silently NaNs answer_relevancy. This adapter fixes that without touching the
    embedding path.
    """

    model = MODEL_NAME

    def __init__(self) -> None:
        self._inner = get_embeddings()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._inner.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._inner.embed_query(text)


def ragas_scores(gold: list[dict], k: int = 4) -> dict:
    """Run the RAG pipeline on each gold row, then score with RAGAS. Mean per metric."""
    samples = []
    for g in gold:
        answer, contexts = rag_answer(g["question"], k=k)
        samples.append(SingleTurnSample(
            user_input=g["question"],
            retrieved_contexts=contexts,
            response=answer,
            reference=g["reference"],
        ))
    dataset = EvaluationDataset(samples=samples)
    result = evaluate(
        dataset,
        metrics=METRICS,
        llm=LangchainLLMWrapper(_model()),
        embeddings=LangchainEmbeddingsWrapper(_StringModelEmbeddings()),
    )
    df = result.to_pandas()
    return {m.name: round(float(df[m.name].mean()), 3) for m in METRICS}
