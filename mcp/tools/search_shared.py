"""
Shared resources for Search Tools.
"""
import heapq
import json
import math
import os
import sys
import threading
from pathlib import Path
from typing import Callable

_chromadb = None
_model = None
_model_lock = threading.Lock()


def chromadb_runtime_supported() -> bool:
    """Known unstable combo: Windows + Python 3.13 + chromadb rust bindings."""
    return not (sys.platform == "win32" and sys.version_info >= (3, 13))


def tool_logger(name: str) -> Callable[[str], None]:
    """Returns a stderr logger for a specific tool."""
    def _log(msg: str) -> None:
        print(f"[NOVA | {name}] {msg}", file=sys.stderr, flush=True)
    return _log


def get_model(model_name: str = "all-MiniLM-L6-v2"):
    """Returns cached sentence-transformer model."""
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(model_name)
        return _model


def encode_text(text: str, log: Callable[[str], None] | None = None) -> list[float]:
    """Encode text in-process using the cached model."""
    if log:
        log("Encoding...")
    model = get_model()
    return model.encode(text).tolist()


def batch_encode_texts(texts: list[str], log: Callable[[str], None] | None = None) -> list[list[float]]:
    """Batch encode texts in-process using the cached model."""
    if log:
        log(f"Batch encoding {len(texts)} texts...")
    model = get_model()
    return model.encode(texts).tolist()


def get_chromadb():
    """Returns cached chromadb module."""
    if not chromadb_runtime_supported():
        raise RuntimeError("ChromaDB runtime disabled on Windows with Python 3.13 due to native crashes.")
    global _chromadb
    if _chromadb is None:
        import chromadb as _chromadb_module
        _chromadb = _chromadb_module
    return _chromadb


def get_search_client(chroma_path: str, log: Callable[[str], None] | None = None):
    """
    Load chromadb and open collection. 
    Returns collection or raises.
    """
    if log:
        log("Loading chromadb...")
    chromadb = get_chromadb()
    if log:
        log("Opening collection...")
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection("vault")
    if log:
        log("Ready")
    return collection


def _should_use_safe_query() -> bool:
    """
    Decide whether to avoid native chroma query path.
    Default: enabled on Windows because native query can hard-crash the process.
    """
    override = os.getenv("NOVA_CHROMA_SAFE_QUERY")
    if override is not None:
        return override.strip().lower() in {"1", "true", "yes", "on"}
    return sys.platform == "win32"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a <= 0.0 or norm_b <= 0.0:
        return -1.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def _manual_query_collection(
    collection,
    query_embedding: list[float],
    top_k: int,
    log: Callable[[str], None] | None = None,
) -> dict:
    """
    Safe query mode: fetch embeddings and rank in pure Python.
    Avoids native ANN query path that can crash on some runtimes.
    """
    if log:
        log("Searching (safe mode)...")

    total = collection.count()
    if total == 0:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    batch_size = 1000
    heap: list[tuple[float, str, str, dict]] = []
    for offset in range(0, total, batch_size):
        batch = collection.get(
            include=["documents", "metadatas", "embeddings"],
            limit=batch_size,
            offset=offset,
        )
        ids = batch.get("ids", []) or []
        docs = batch.get("documents", []) or []
        metas = batch.get("metadatas", []) or []
        embeds = batch.get("embeddings", []) or []
        for item_id, doc, meta, emb in zip(ids, docs, metas, embeds):
            sim = _cosine_similarity(query_embedding, emb)
            if sim < 0:
                continue
            # Keep fixed-size min-heap with best similarities.
            if len(heap) < top_k:
                heapq.heappush(heap, (sim, item_id, doc, meta or {}))
            elif sim > heap[0][0]:
                heapq.heapreplace(heap, (sim, item_id, doc, meta or {}))

    ranked = sorted(heap, key=lambda x: x[0], reverse=True)
    ids_out = [item_id for _, item_id, _, _ in ranked]
    docs_out = [doc for _, _, doc, _ in ranked]
    metas_out = [meta for _, _, _, meta in ranked]
    distances_out = [1.0 - sim for sim, _, _, _ in ranked]

    return {
        "ids": [ids_out],
        "documents": [docs_out],
        "metadatas": [metas_out],
        "distances": [distances_out],
    }


def _semantic_index_file(chroma_path: str) -> Path:
    return Path(chroma_path).parent / "semantic_index.json"


def _search_from_semantic_index(
    index_file: Path,
    query_embedding: list[float],
    top_k: int,
    log: Callable[[str], None] | None = None,
) -> list[dict]:
    if log:
        log(f"Searching local index: {index_file}")
    try:
        payload = json.loads(index_file.read_text(encoding="utf-8"))
    except Exception:
        return []

    raw_items = payload.get("items", []) if isinstance(payload, dict) else []
    # Keep a deterministic tie-breaker to avoid comparing dicts when similarity ties.
    heap: list[tuple[float, int, dict]] = []
    for idx, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        emb = item.get("embedding") or []
        sim = _cosine_similarity(query_embedding, emb)
        if sim < 0:
            continue
        if len(heap) < top_k:
            heapq.heappush(heap, (sim, idx, item))
        elif sim > heap[0][0]:
            heapq.heapreplace(heap, (sim, idx, item))

    ranked = sorted(heap, key=lambda x: (x[0], x[1]), reverse=True)
    return [
        {
            "id": item.get("id", ""),
            "doc": item.get("text", ""),
            "meta": {
                "id": item.get("id", ""),
                "path": item.get("path", ""),
                "section": item.get("section", ""),
                "line_start": item.get("line_start"),
                "line_end": item.get("line_end"),
                "memory_type": item.get("memory_type", "fact"),
                "chunk_index": item.get("chunk_index"),
            },
            "distance": 1.0 - sim,
            "path": item.get("path", ""),
        }
        for sim, _, item in ranked
    ]


def semantic_search(
    chroma_path: str,
    query: str,
    top_k: int = 5,
    log: Callable[[str], None] | None = None
) -> list[dict]:
    """
    Perform semantic search. Returns list of {path, doc, distance, meta}.
    """
    query_embedding = encode_text(query, log)
    index_file = _semantic_index_file(chroma_path)
    if index_file.exists():
        items = _search_from_semantic_index(index_file, query_embedding, top_k, log)
        if log:
            log("Done")
        return items

    collection = get_search_client(chroma_path, log)
    if _should_use_safe_query():
        if log:
            log("Native query disabled; using safe ranking path.")
        results = _manual_query_collection(collection, query_embedding, top_k, log)
    else:
        if log:
            log("Searching...")
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
    if log:
        log("Done")
    
    items = []
    if results["ids"][0]:
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            items.append({
                "doc": doc,
                "meta": meta,
                "distance": distance,
                "path": meta.get("path", ""),
            })
    return items
