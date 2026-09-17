"""
semantic_cache.py — In-memory semantic LLM response cache for SovereignForge.

How it works:
  - Every prompt is first looked up by exact SHA-256 hash (always safe).
  - Short prompts are also embedded with sentence-transformers (all-MiniLM-L6-v2)
    and matched by cosine similarity >= SIMILARITY_THRESHOLD (0.92).
  - Long prompts are exact-match only. MiniLM truncates input at ~256 tokens, so
    two long prompts that share a prefix (e.g. successive ReAct turns of one task,
    or two reports on the same letterhead) would embed identically and return the
    wrong cached answer.
  - Cache is LRU-capped at MAX_CACHE_SIZE entries to bound memory usage
  - 100% offline — uses the same embedding model already used by the knowledge base
"""
from __future__ import annotations

import time
import hashlib
from collections import OrderedDict
from typing import Optional

import numpy as np

# ── Configuration ──────────────────────────────────────────────────────────────
SIMILARITY_THRESHOLD = 0.92   # cosine similarity above which we return cache hit
MAX_CACHE_SIZE = 200          # max entries before LRU eviction
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # same model used by knowledge_base.py
# Prompts longer than this are matched exactly only (~256 MiniLM tokens).
MAX_SEMANTIC_CHARS = 1000

_embedder = None  # lazy-loaded singleton


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def _embed(text: str) -> list[float]:
    """Return embedding vector for a text string."""
    return _get_embedder().encode(text, convert_to_tensor=False).tolist()


def _cosine(a: list[float], b: list[float]) -> float:
    """NumPy cosine similarity between two equal-length vectors."""
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


def _exact_key(model_key: str, prompt: str) -> str:
    return hashlib.sha256(f"{model_key}\x00{prompt}".encode()).hexdigest()


class SemanticCache:
    """
    Semantic LRU cache for LLM responses (single event loop, no locking).
    Key = sha256(model_key + full prompt). Value = (embedding | None, response, metadata).
    """

    def __init__(
        self,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        max_size: int = MAX_CACHE_SIZE,
        max_semantic_chars: int = MAX_SEMANTIC_CHARS,
    ):
        self.threshold = similarity_threshold
        self.max_size = max_size
        self.max_semantic_chars = max_semantic_chars
        self._store: OrderedDict[str, tuple[Optional[list[float]], str, dict]] = OrderedDict()
        self.hits = 0
        self.exact_hits = 0
        self.semantic_hits = 0
        self.misses = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, model_key: str, prompt: str) -> Optional[str]:
        """
        Look up a cached response.
        Returns the cached response string on an exact or (for short prompts)
        semantic near-match, otherwise None (caller must call the LLM).
        """
        key = _exact_key(model_key, prompt)
        if key in self._store:
            self._store.move_to_end(key)
            self.hits += 1
            self.exact_hits += 1
            return self._store[key][1]

        if len(prompt) <= self.max_semantic_chars:
            best_key = self._best_semantic_match(model_key, prompt)
            if best_key is not None:
                self._store.move_to_end(best_key)
                self.hits += 1
                self.semantic_hits += 1
                return self._store[best_key][1]

        self.misses += 1
        return None

    def put(self, model_key: str, prompt: str, response: str) -> None:
        """
        Store a (prompt, response) pair in the cache.
        Evicts the least-recently-used entry when max_size is reached.
        """
        emb = None
        if len(prompt) <= self.max_semantic_chars:
            try:
                emb = _embed(prompt)
            except Exception:
                emb = None  # embedding unavailable — still usable for exact hits

        key = _exact_key(model_key, prompt)
        self._store[key] = (
            emb,
            response,
            {
                "model_key": model_key,
                "cached_at": time.time(),
                "prompt_preview": prompt[:80],
            },
        )
        self._store.move_to_end(key)

        # LRU eviction
        while len(self._store) > self.max_size:
            self._store.popitem(last=False)

    def stats(self) -> dict:
        """Return cache statistics for the /health endpoint."""
        total = self.hits + self.misses
        return {
            "entries": len(self._store),
            "max_size": self.max_size,
            "hits": self.hits,
            "exact_hits": self.exact_hits,
            "semantic_hits": self.semantic_hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 3) if total else 0.0,
            "threshold": self.threshold,
        }

    def clear(self) -> None:
        """Clear all cache entries (useful for testing or manual reset)."""
        self._store.clear()
        self.hits = 0
        self.exact_hits = 0
        self.semantic_hits = 0
        self.misses = 0

    # ── Internals ─────────────────────────────────────────────────────────────

    def _best_semantic_match(self, model_key: str, prompt: str) -> Optional[str]:
        candidates = [
            (k, emb) for k, (emb, _, meta) in self._store.items()
            if emb is not None and meta.get("model_key") == model_key
        ]
        if not candidates:
            return None
        try:
            query_emb = _embed(prompt)
        except Exception:
            return None  # embedding failed — fall through to LLM

        best_key, best_score = None, 0.0
        for k, emb in candidates:
            score = _cosine(query_emb, emb)
            if score > best_score:
                best_key, best_score = k, score
        return best_key if best_score >= self.threshold else None


# ── Module-level singleton — import this from registry.py ──
cache = SemanticCache()
