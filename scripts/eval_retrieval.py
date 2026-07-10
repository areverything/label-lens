"""Retrieval eval: baseline (dense) vs reranker vs hybrid, over the gold set.

Usage:
    uv run python scripts/eval_retrieval.py

Prints a Markdown comparison table (Hit@1 / Hit@3 / MRR). No LLM calls; the
reranker and embeddings run locally via ONNX.
"""
from __future__ import annotations

from label_lens.eval.run import evaluate_retrieval, format_table


def main() -> None:
    rows = evaluate_retrieval(fetch_k=10)
    print(format_table(rows))


if __name__ == "__main__":
    main()
