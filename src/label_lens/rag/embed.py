"""Local bge-small embeddings via fastembed (ONNX runtime).

Same model as before (BAAI/bge-small-en-v1.5), run through ONNX rather than
torch: no torch/CUDA dependency, a small install, and fast CPU inference. Small
corpus, so this is free, offline-capable, and light enough for a memory-limited
deploy host. fastembed L2-normalises its output, so cosine similarity is a plain
dot product.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_community.embeddings import FastEmbedEmbeddings

MODEL_NAME = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=1)
def get_embeddings() -> FastEmbedEmbeddings:
    return FastEmbedEmbeddings(model_name=MODEL_NAME)
