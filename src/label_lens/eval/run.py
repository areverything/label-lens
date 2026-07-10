"""Run the retrieval comparison over the gold set: baseline vs reranker vs hybrid."""
from __future__ import annotations

from statistics import mean

from label_lens.eval.gold import load_gold
from label_lens.eval.metrics import hit_at_k, reciprocal_rank
from label_lens.eval.retrievers import RETRIEVERS


def evaluate_retrieval(retrievers: dict | None = None, fetch_k: int = 10) -> list[dict]:
    """Per-retriever hit@1, hit@3, and MRR over the RAG gold questions."""
    retrievers = retrievers or RETRIEVERS
    gold = [g for g in load_gold("rag") if g.get("additives")]
    out = []
    for name, fn in retrievers.items():
        h1, h3, rr = [], [], []
        for g in gold:
            ranked = fn(g["question"], k=fetch_k)
            correct = set(g["additives"])
            h1.append(hit_at_k(ranked, correct, 1))
            h3.append(hit_at_k(ranked, correct, 3))
            rr.append(reciprocal_rank(ranked, correct))
        out.append({
            "retriever": name,
            "n": len(gold),
            "hit@1": round(mean(h1), 3),
            "hit@3": round(mean(h3), 3),
            "mrr": round(mean(rr), 3),
        })
    return out


def format_table(rows: list[dict]) -> str:
    head = "| Retriever | Hit@1 | Hit@3 | MRR |\n|---|--:|--:|--:|"
    body = "\n".join(
        f"| {r['retriever']} | {r['hit@1']:.3f} | {r['hit@3']:.3f} | {r['mrr']:.3f} |"
        for r in rows)
    return head + "\n" + body


def evaluate_answers(gold: list[dict] | None = None) -> dict:
    """Judge the real agent's answers for correctness, groundedness, and safety.

    Runs the full agent (routing + tools + memory) on each question, then scores
    the answer with the LLM judge. Safety is reported over the safety-lane rows
    where the boundary is actually exercised.
    """
    from label_lens.agent.graph import answer as agent_answer
    from label_lens.eval.judge import judge_answer

    gold = gold or load_gold()
    rows = []
    for g in gold:
        ans = agent_answer(g["question"])
        verdict = judge_answer(g["question"], g["reference"], ans)
        rows.append({"id": g["id"], "lane": g["lane"], **verdict})
    return {
        "n": len(rows),
        "correctness": round(mean(r["correctness"] for r in rows), 3),
        "groundedness": round(mean(r["groundedness"] for r in rows), 3),
        # The safety boundary must hold on every answer, not just safety-lane ones.
        "safety_ok": round(mean(1.0 if r["safety_ok"] else 0.0 for r in rows), 3),
        "rows": rows,
    }
