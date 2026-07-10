"""Baseline answer-quality harness: LLM-judge + RAGAS over the gold set.

Usage:
    uv run python scripts/eval_answers.py [--ragas-n N]

Judges the real agent's answers (correctness / groundedness / safety) on every
gold question, and runs RAGAS (context precision/recall, faithfulness, answer
relevancy) over the RAG pipeline on a sample. Writes evals/results.json and
prints a scorecard. Needs OPENROUTER_API_KEY.
"""
from __future__ import annotations

import argparse
import json

from label_lens.config import ROOT
from label_lens.eval.gold import load_gold
from label_lens.eval.run import evaluate_answers

RESULTS = ROOT / "evals" / "results.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ragas-n", type=int, default=10,
                    help="how many RAG-lane questions to score with RAGAS (cost control)")
    args = ap.parse_args()

    print("Judging the agent's answers on the gold set...")
    judged = evaluate_answers()

    print(f"Running RAGAS on {args.ragas_n} RAG questions...")
    from label_lens.eval.ragas_eval import ragas_scores
    ragas = ragas_scores(load_gold("rag")[: args.ragas_n])

    out = {"judge": {k: v for k, v in judged.items() if k != "rows"},
           "judge_rows": judged["rows"], "ragas": ragas, "ragas_n": args.ragas_n}
    RESULTS.write_text(json.dumps(out, indent=2))

    print("\n## Baseline scorecard\n")
    print(f"Agent answers (n={judged['n']}):")
    print(f"  correctness  {judged['correctness']:.3f}")
    print(f"  groundedness {judged['groundedness']:.3f}")
    print(f"  safety_ok    {judged['safety_ok']:.3f}")
    print(f"\nRAGAS / RAG pipeline (n={args.ragas_n}):")
    for k, v in ragas.items():
        print(f"  {k:18} {v:.3f}")
    print(f"\nSaved -> {RESULTS}")


if __name__ == "__main__":
    main()
