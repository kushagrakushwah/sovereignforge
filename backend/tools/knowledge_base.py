"""
knowledge_base.py — Local RAG (Retrieval-Augmented Generation) for SovereignForge

Stores and searches organization documents entirely on-premise.
Uses sentence-transformers for embeddings + FAISS/numpy for similarity search.
No external API calls — fully air-gapped.
"""
import sys
import os
import json
import asyncio
import hashlib
import pickle
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import tempfile

TEMP_DIR = Path(tempfile.gettempdir())

# KB storage path
KB_DIR = os.path.join(TEMP_DIR, "sovereignforge", "knowledge_base")
KB_INDEX_FILE = os.path.join(KB_DIR, "index.pkl")
KB_DOCS_FILE  = os.path.join(KB_DIR, "documents.json")

# Embedding model (downloaded once, then 100% offline)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # 90 MB, fast, good quality

_embedder = None   # lazy-loaded singleton


def _get_embedder():
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedder = SentenceTransformer(EMBEDDING_MODEL)
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
    return _embedder


def _cosine_similarity(a, b):
    """NumPy cosine similarity between two vectors."""
    import numpy as np
    a, b = np.array(a), np.array(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _bm25_score(query_tokens: list[str], doc_tokens: list[str], avg_doc_len: float, k1: float = 1.5, b: float = 0.75) -> float:
    """
    Pure-Python BM25 score for keyword relevance.
    No external library needed — implements the standard BM25 formula.
    """
    score = 0.0
    doc_len = len(doc_tokens)
    doc_freq = {}
    for token in doc_tokens:
        doc_freq[token] = doc_freq.get(token, 0) + 1

    for token in set(query_tokens):
        if token not in doc_freq:
            continue
        tf = doc_freq[token]
        idf = 1.0  # simplified IDF (1.0 per matching term)
        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * doc_len / max(avg_doc_len, 1))
        score += idf * numerator / max(denominator, 1e-9)
    return score


def _load_state():
    """Load documents + embeddings from disk."""
    os.makedirs(KB_DIR, exist_ok=True)
    documents = []
    embeddings = []

    if os.path.exists(KB_DOCS_FILE):
        with open(KB_DOCS_FILE, "r", encoding="utf-8") as f:
            documents = json.load(f)

    if os.path.exists(KB_INDEX_FILE):
        with open(KB_INDEX_FILE, "rb") as f:
            embeddings = pickle.load(f)

    return documents, embeddings


def _save_state(documents, embeddings):
    """Persist documents + embeddings to disk."""
    os.makedirs(KB_DIR, exist_ok=True)
    with open(KB_DOCS_FILE, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)
    with open(KB_INDEX_FILE, "wb") as f:
        pickle.dump(embeddings, f)


def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> List[str]:
    """Split text into overlapping chunks for better retrieval."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return [c for c in chunks if len(c.strip()) > 30]


def ingest_text(
    text: str,
    source_name: str,
    doc_type: str = "manual",
    metadata: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Ingest a text document into the knowledge base.
    Splits into chunks and stores embeddings.
    Returns {"success": bool, "chunks_added": int, "source": str, "error": str|None}
    """
    try:
        embedder = _get_embedder()
        documents, embeddings = _load_state()

        chunks = _chunk_text(text)
        added = 0

        for i, chunk in enumerate(chunks):
            doc_id = hashlib.md5(f"{source_name}:{i}:{chunk[:50]}".encode()).hexdigest()

            # Avoid duplicates
            if any(d["id"] == doc_id for d in documents):
                continue

            embedding = embedder.encode(chunk, convert_to_tensor=False).tolist()
            documents.append({
                "id": doc_id,
                "text": chunk,
                "source": source_name,
                "doc_type": doc_type,
                "chunk_index": i,
                "ingested_at": datetime.now().isoformat(),
                "metadata": metadata or {},
            })
            embeddings.append(embedding)
            added += 1

        _save_state(documents, embeddings)
        return {
            "success": True,
            "chunks_added": added,
            "total_docs": len(documents),
            "source": source_name,
            "error": None,
        }
    except Exception as e:
        return {"success": False, "chunks_added": 0, "total_docs": 0, "source": source_name, "error": str(e)}


def search_knowledge_base(
    query: str,
    n_results: int = 5,
    doc_type_filter: str = None,
) -> Dict[str, Any]:
    """
    Search the knowledge base using semantic similarity.
    Returns top-N most relevant chunks.
    """
    try:
        embedder = _get_embedder()
        documents, embeddings = _load_state()

        if not documents:
            return {
                "success": False,
                "results": [],
                "query": query,
                "error": "Knowledge base is empty. Ingest documents first.",
            }

        query_embedding = embedder.encode(query, convert_to_tensor=False).tolist()

        # ── Hybrid BM25 + Dense scoring ──────────────────────────────────────
        query_tokens = query.lower().split()
        all_doc_tokens = [doc["text"].lower().split() for doc in documents]
        avg_doc_len = sum(len(t) for t in all_doc_tokens) / max(len(all_doc_tokens), 1)

        # Get max BM25 score for normalization
        bm25_scores_raw = [
            _bm25_score(query_tokens, tokens, avg_doc_len)
            for tokens in all_doc_tokens
        ]
        max_bm25 = max(bm25_scores_raw) if bm25_scores_raw else 1.0
        max_bm25 = max(max_bm25, 1e-9)  # avoid division by zero

        scored = []
        for i, (doc, emb) in enumerate(zip(documents, embeddings)):
            if doc_type_filter and doc.get("doc_type") != doc_type_filter:
                continue

            dense_score = _cosine_similarity(query_embedding, emb)
            # Normalized BM25 to [0, 1] range
            bm25_norm = bm25_scores_raw[i] / max_bm25

            # Hybrid score: 60% semantic + 40% keyword
            hybrid_score = 0.60 * dense_score + 0.40 * bm25_norm
            scored.append((hybrid_score, dense_score, bm25_norm, doc))

        # Sort descending by hybrid score, take top N
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:n_results]

        RELEVANCE_THRESHOLD = 0.20  # raised from 0.15 — filters out noise
        import re
        results = []
        for hybrid_score, dense_score, bm25_norm, doc in top:
            if hybrid_score > RELEVANCE_THRESHOLD:
                # Sanitize text to prevent repeating character hallucination in LLMs
                clean_text = re.sub(r'[\u2550\u2500-\u257F]{4,}', '', doc["text"]) # Strip unicode box drawing lines
                clean_text = re.sub(r'[-=_*#]{5,}', '', clean_text) # Strip long dash/equals lines
                
                results.append({
                    "score": round(hybrid_score, 4),
                    "dense_score": round(dense_score, 4),
                    "bm25_score": round(bm25_norm, 4),
                    "text": clean_text.strip(),
                    "source": doc["source"],
                    "doc_type": doc.get("doc_type", "unknown"),
                    "chunk_index": doc.get("chunk_index", 0),
                })

        # ── No-match guardrail ────────────────────────────────────────────────
        if not results:
            return {
                "success": True,
                "results": [],
                "query": query,
                "total_searched": len(scored),
                "error": None,
                "message": "No sufficiently relevant documents found. The knowledge base may not contain information about this topic.",
            }

        return {
            "success": True,
            "results": results,
            "query": query,
            "total_searched": len(scored),
            "error": None,
        }
    except Exception as e:
        return {"success": False, "results": [], "query": query, "error": str(e)}


def get_kb_stats() -> Dict[str, Any]:
    """Return knowledge base statistics."""
    try:
        documents, _ = _load_state()
        sources = {}
        for doc in documents:
            s = doc.get("source", "unknown")
            sources[s] = sources.get(s, 0) + 1
        return {
            "total_chunks": len(documents),
            "sources": sources,
            "kb_dir": KB_DIR,
            "ready": len(documents) > 0,
        }
    except Exception:
        return {"total_chunks": 0, "sources": {}, "kb_dir": KB_DIR, "ready": False}


def clear_knowledge_base() -> Dict[str, Any]:
    """Clear all documents from the knowledge base."""
    try:
        if os.path.exists(KB_DOCS_FILE):
            os.remove(KB_DOCS_FILE)
        if os.path.exists(KB_INDEX_FILE):
            os.remove(KB_INDEX_FILE)
        return {"success": True, "message": "Knowledge base cleared."}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ── Async wrappers for agent tool dispatch ───────────────────────────────────

async def run_search_kb(query: str, n_results: int = 2) -> Dict[str, Any]:
    """Agent-callable async wrapper for KB search."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, search_knowledge_base, query, n_results)


async def run_ingest_file(file_path: str, source_name: str = None, doc_type: str = "document") -> Dict[str, Any]:
    """
    Ingest a text/PDF/DOCX file into the knowledge base.
    Extracts text first, then ingests chunks.
    """
    if not os.path.exists(file_path):
        return {"success": False, "chunks_added": 0, "error": f"File not found: {file_path}"}

    ext = Path(file_path).suffix.lower()
    name = source_name or Path(file_path).name

    try:
        text = ""
        if ext in (".txt", ".md"):
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()

        elif ext == ".pdf":
            import fitz   # pymupdf
            doc = fitz.open(file_path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()

        elif ext in (".docx",):
            from docx import Document
            doc = Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

        else:
            # Try plain text read
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()

        if not text.strip():
            return {"success": False, "chunks_added": 0, "error": "File appears to be empty or unreadable."}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, ingest_text, text, name, doc_type, {"file_path": file_path})

    except Exception as e:
        return {"success": False, "chunks_added": 0, "error": str(e)}
