"""Text embeddings for semantic search and zero-shot classification.

Backends, in order of preference:

1. ``sentence-transformers`` (a real neural model, best quality, fully local).
2. A deterministic **hashing vectorizer** fallback (pure python, no deps): maps
   token n-grams into a fixed-dimensional L2-normalised vector. This is not as
   smart as a transformer but provides meaningful lexical similarity so semantic
   search and dedup-by-meaning keep working on a minimal install.

Both backends expose the same :meth:`encode` / :meth:`cosine` interface so the
rest of the app is backend-agnostic.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence

from ..utils.logging import get_logger

log = get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-zA-ZäöüÄÖÜß0-9]+")


class EmbeddingEngine:
    """Encodes text into fixed-length vectors, with cosine similarity."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", fallback_dim: int = 256) -> None:
        self.model_name = model_name
        self.fallback_dim = fallback_dim
        self._model = None
        self.is_ml_backend = False
        self._dim = fallback_dim
        self._try_load_model()

    # ------------------------------------------------------------------ setup
    def _try_load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self._dim = int(self._model.get_sentence_embedding_dimension())
            self.is_ml_backend = True
            log.info("Embedding backend: sentence-transformers/%s (dim=%d)", self.model_name, self._dim)
        except Exception:
            self._model = None
            self.is_ml_backend = False
            self._dim = self.fallback_dim
            log.info("Embedding backend: hashing fallback (dim=%d)", self._dim)

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def backend_name(self) -> str:
        return f"st:{self.model_name}" if self.is_ml_backend else "hash-fallback"

    # ----------------------------------------------------------------- encode
    def encode(self, text: str) -> list[float]:
        text = (text or "").strip()
        if not text:
            return [0.0] * self._dim
        if self.is_ml_backend and self._model is not None:
            try:
                vec = self._model.encode(text, normalize_embeddings=True)
                return [float(x) for x in vec]
            except Exception:  # pragma: no cover
                log.warning("ML encode failed; using fallback", exc_info=True)
        return self._hash_encode(text)

    def encode_batch(self, texts: Sequence[str]) -> list[list[float]]:
        if self.is_ml_backend and self._model is not None:
            try:
                vectors = self._model.encode(
                    list(texts), normalize_embeddings=True, batch_size=32
                )
                return [[float(x) for x in v] for v in vectors]
            except Exception:  # pragma: no cover
                log.warning("ML batch encode failed; using fallback", exc_info=True)
        return [self._hash_encode(t) for t in texts]

    # --------------------------------------------------------------- fallback
    def _hash_encode(self, text: str) -> list[float]:
        """Hashing vectorizer over unigrams + bigrams, L2-normalised."""
        vec = [0.0] * self._dim
        tokens = _TOKEN_RE.findall(text.lower())
        if not tokens:
            return vec
        grams = list(tokens)
        grams += [f"{a}_{b}" for a, b in zip(tokens, tokens[1:], strict=False)]
        for gram in grams:
            digest = hashlib.md5(gram.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % self._dim
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    # ------------------------------------------------------------- similarity
    @staticmethod
    def cosine(a: Sequence[float], b: Sequence[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)
