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

from .index_store import facet_counts as _sqlite_facet_counts
from .index_store import full_text_search as _sqlite_full_text_search
from .index_store import graph_search as _sqlite_graph_search

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
                "lifecycle_status": item.get("lifecycle_status", "active"),
                "supersedes": item.get("supersedes", []),
                "chunk_index": item.get("chunk_index"),
            },
            "distance": 1.0 - sim,
            "path": item.get("path", ""),
        }
        for sim, _, item in ranked
    ]


def full_text_search(
    index_root: str,
    query: str,
    top_k: int = 5,
    log: Callable[[str], None] | None = None,
    filters: dict | None = None,
) -> list[dict]:
    if log:
        log("Searching SQLite FTS index...")
    items = _sqlite_full_text_search(index_root, query, top_k, filters=filters)
    if log:
        log("Done")
    return items


def facet_counts(
    index_root: str,
    query: str,
    filters: dict | None = None,
) -> dict[str, dict[str, int]]:
    return _sqlite_facet_counts(index_root, query, filters=filters)


def graph_search(
    index_root: str,
    query: str,
    top_k: int = 5,
    log: Callable[[str], None] | None = None,
) -> list[dict]:
    if log:
        log("Searching SQLite graph index...")
    items = _sqlite_graph_search(index_root, query, top_k)
    if log:
        log("Done")
    return items


def _result_key(item: dict) -> str:
    meta = item.get("meta") or {}
    item_id = str(item.get("id") or meta.get("id") or "")
    return item_id or f"{item.get('path', '')}:{str(item.get('doc') or item.get('text') or '')[:80]}"


def _bounded_score(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _semantic_score(item: dict) -> float:
    if "score" in item:
        return _bounded_score(float(item.get("score") or 0.0))
    return _bounded_score(1.0 - float(item.get("distance", 1.0)))


def _ensure_hybrid_entry(by_id: dict[str, dict], item: dict) -> tuple[str, dict]:
    key = _result_key(item)
    if key not in by_id:
        merged = dict(item)
        meta = dict(merged.get("meta") or {})
        merged["meta"] = meta
        merged["id"] = str(merged.get("id") or meta.get("id") or key)
        merged["path"] = str(merged.get("path") or meta.get("path") or "")
        merged["doc"] = str(merged.get("doc") or merged.get("text") or "")
        for field, default in (("lifecycle_status", "active"), ("supersedes", [])):
            if field not in meta:
                meta[field] = item.get(field, default)
        merged["hybrid_signals"] = {"semantic": 0.0, "full_text": 0.0, "graph": 0.0}
        by_id[key] = merged
    return key, by_id[key]


def _hybrid_reason(signals: dict[str, float], graph_reason: str | None = None) -> str:
    semantic = signals.get("semantic", 0.0) > 0.0
    full_text = signals.get("full_text", 0.0) > 0.0
    graph = signals.get("graph", 0.0) > 0.0
    if semantic and full_text:
        return "hybrid_semantic_and_full_text"
    if semantic and graph:
        return "hybrid_semantic_and_graph"
    if full_text and graph:
        return "hybrid_full_text_and_graph"
    if semantic:
        return "hybrid_semantic"
    if full_text:
        return "hybrid_full_text"
    if graph:
        return "hybrid_graph_neighbor" if graph_reason == "graph_neighbor" else "hybrid_graph_seed"
    return "hybrid"


def hybrid_search(
    chroma_path: str,
    index_root: str,
    query: str,
    top_k: int = 5,
    log: Callable[[str], None] | None = None,
) -> list[dict]:
    """Merge semantic, FTS, and graph retrieval with weighted reranking."""
    candidate_k = max(top_k * 3, top_k)
    semantic_items = semantic_search(chroma_path, query, candidate_k, log)
    full_text_items = full_text_search(index_root, query, candidate_k, log)
    graph_items = graph_search(index_root, query, candidate_k, log)
    by_id: dict[str, dict] = {}
    graph_reasons: dict[str, str] = {}

    for item in semantic_items:
        _, merged = _ensure_hybrid_entry(by_id, item)
        merged["hybrid_signals"]["semantic"] = max(merged["hybrid_signals"]["semantic"], _semantic_score(item))

    for item in full_text_items:
        _, merged = _ensure_hybrid_entry(by_id, item)
        merged["hybrid_signals"]["full_text"] = max(
            merged["hybrid_signals"]["full_text"],
            _bounded_score(float(item.get("score", 0.0))),
        )
        if not merged.get("doc"):
            merged["doc"] = str(item.get("doc") or item.get("text") or "")

    for item in graph_items:
        key, merged = _ensure_hybrid_entry(by_id, item)
        graph_reasons[key] = str(item.get("why_relevant") or "")
        merged["hybrid_signals"]["graph"] = max(
            merged["hybrid_signals"]["graph"],
            _bounded_score(float(item.get("score", 0.0))),
        )
        graph_meta = item.get("meta") or {}
        if graph_meta.get("graph_via") is not None:
            merged.setdefault("meta", {})["graph_via"] = graph_meta.get("graph_via")
        if not merged.get("doc"):
            merged["doc"] = str(item.get("doc") or item.get("text") or "")

    weights = {"semantic": 0.45, "full_text": 0.40, "graph": 0.15}
    ranked: list[dict] = []
    for key, item in by_id.items():
        signals = item["hybrid_signals"]
        score = sum(signals[name] * weight for name, weight in weights.items())
        item["score"] = _bounded_score(score)
        item["distance"] = 1.0 - item["score"]
        item["why_relevant"] = _hybrid_reason(signals, graph_reasons.get(key))
        ranked.append(item)

    return sorted(
        ranked,
        key=lambda x: (
            float(x.get("score", 0.0)),
            x.get("hybrid_signals", {}).get("semantic", 0.0),
            x.get("hybrid_signals", {}).get("full_text", 0.0),
            x.get("hybrid_signals", {}).get("graph", 0.0),
            str(x.get("id") or ""),
        ),
        reverse=True,
    )[:top_k]


def semantic_search(
    chroma_path: str,
    query: str,
    top_k: int = 5,
    log: Callable[[str], None] | None = None,
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
