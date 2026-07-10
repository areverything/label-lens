"""Local bge-small embeddings, on Apple Silicon (MPS) when available.

Small corpus, so a tiny local model is free, fast, and needs no external API.
Normalised vectors so cosine similarity is a plain dot product.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

MODEL_NAME = "BAAI/bge-small-en-v1.5"


def _device() -> str:
    try:
        import torch

        if torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={"device": _device()},
        encode_kwargs={"normalize_embeddings": True},
    )
