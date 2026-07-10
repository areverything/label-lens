"""Three retrieval strategies over the brief chunks, for the eval comparison.

- dense: the baseline. Meaning-based similarity from the Chroma index.
- rerank: dense fetches a wider candidate set, a cross-encoder (bge-reranker,
  ONNX) re-scores each (query, passage) pair; the likeliest fix for confusing
  near-identical briefs (E210 vs E211).
- hybrid: BM25 keyword scores fused with dense via reciprocal-rank fusion; helps
  when the query carries exact tokens (E-numbers, CAS, "21 CFR 74.706") that
  meaning-based search can miss.

Each returns a ranked list of chunk_ids (best first), so metrics.py can score
hits by the additive e_number behind each chunk.
"""
from __future__ import annotations

from functools import lru_cache

from label_lens.eval.corpus import by_id, load_corpus
from label_lens.rag.index import load_index

# How many candidates the two-stage retrievers pull before re-ranking/fusing.
FETCH = 20


def dense(query: str, k: int = 5) -> list[str]:
    hits = load_index().similarity_search_with_score(query, k=k)
    return [d.metadata.get("chunk_id", d.id) for d, _ in hits]


@lru_cache(maxsize=1)
def _reranker():
    from fastembed.rerank.cross_encoder import TextCrossEncoder
    return TextCrossEncoder(model_name="BAAI/bge-reranker-base")


def rerank(query: str, k: int = 5, fetch: int = FETCH) -> list[str]:
    docs = by_id()
    ids = [cid for cid in dense(query, k=fetch) if cid in docs]
    scores = list(_reranker().rerank(query, [docs[cid].text for cid in ids]))
    ranked = sorted(zip(ids, scores), key=lambda x: x[1], reverse=True)
    return [cid for cid, _ in ranked[:k]]


@lru_cache(maxsize=1)
def _bm25():
    from rank_bm25 import BM25Okapi
    corpus = load_corpus()
    tokenized = [_tokens(d.text) for d in corpus]
    return BM25Okapi(tokenized), [d.chunk_id for d in corpus]


def _tokens(text: str) -> list[str]:
    # Lowercase word/number tokens; keeps "e211", "74.706", "cas" as units.
    import re
    return re.findall(r"[a-z0-9.]+", text.lower())


def hybrid(query: str, k: int = 5, fetch: int = FETCH, rrf_k: int = 60) -> list[str]:
    bm25, ids = _bm25()
    scores = bm25.get_scores(_tokens(query))
    bm25_ranked = [ids[i] for i in sorted(range(len(ids)), key=lambda i: scores[i], reverse=True)][:fetch]
    dense_ranked = dense(query, k=fetch)

    fused: dict[str, float] = {}
    for ranking in (bm25_ranked, dense_ranked):
        for rank, cid in enumerate(ranking):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)
    return [cid for cid, _ in sorted(fused.items(), key=lambda x: x[1], reverse=True)[:k]]


RETRIEVERS = {"dense": dense, "rerank": rerank, "hybrid": hybrid}
