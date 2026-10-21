"""Embedding-model seam (domain model §4: pluggable embedding choice).

- `get_embedding_function("onnx")` — Chroma's default MiniLM (best quality);
  downloads its model on first use, so it needs the network exactly once.
- `get_embedding_function("hash")` — deterministic token-hash vectors: fully
  offline (used by all tests), weaker semantics (token-overlap only).
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict

from chromadb.api.types import Documents, EmbeddingFunction

_logger = logging.getLogger("database.vector")


class HashEmbeddings(EmbeddingFunction[Documents]):
    """Deterministic, offline embedding function (bag of hashed tokens).

    Subclasses Chroma's EmbeddingFunction protocol so collections can
    serialize/restore the model from config (name/get_config/build_from_config).
    """

    def __init__(self, dim: int = 96) -> None:
        self._dim = dim

    def __call__(self, input):
        vectors = []
        for text in input:
            vector = [0.0] * self._dim
            for token in str(text).lower().replace(",", " ").split():
                digest = int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], "big")
                vector[digest % self._dim] += 1.0
            vectors.append(vector)
        return vectors

    @staticmethod
    def name() -> str:
        return "hash_embeddings"

    def get_config(self) -> Dict[str, Any]:
        return {"dim": self._dim}

    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "HashEmbeddings":
        return HashEmbeddings(dim=config.get("dim", 96))


def get_embedding_function(mode: str):
    """Resolve the configured embedding model by name.

    'onnx' (default) → chromadb DefaultEmbeddingFunction (MiniLM); falls
    back to hash embeddings with a loud warning when the model cannot be
    initialized (e.g. offline first run) — dev demo must stay usable, but the
    degraded semantic quality is logged, never silent.
    """
    if mode == "hash":
        return HashEmbeddings()
    if mode == "onnx":
        try:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

            _logger.info("vector store embedding model: chromadb default (ONNX MiniLM)")
            return DefaultEmbeddingFunction()
        except Exception as exc:  # pragma: no cover — network-dependent path
            _logger.warning(
                "ONNX embedding model unavailable (%s: %s); falling back to "
                "deterministic hash embeddings (semantic quality reduced). "
                "First ONNX use downloads the model — retry with network, or "
                "set ADVISOR_EMBEDDING_FUNCTION=hash to silence this.",
                type(exc).__name__, exc,
            )
            return HashEmbeddings()
    raise ValueError(
        f"Unknown embedding mode {mode!r}: use 'onnx' (default) or 'hash' (offline tests)"
    )