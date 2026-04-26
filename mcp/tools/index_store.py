"""SQLite metadata and full-text index for NOVA knowledge chunks."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any


INDEX_DB_NAME = "nova_index.sqlite"
SCHEMA_VERSION = 1


def sqlite_index_path(index_root: str | Path) -> Path:
    return Path(index_root) / INDEX_DB_NAME


def _connect(index_root: str | Path) -> sqlite3.Connection:
    db_path = sqlite_index_path(index_root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db


def _init_schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        create table if not exists meta (
            key text primary key,
            value text not null
        );
        create table if not exists chunks (
            id text primary key,
            path text not null,
            section text not null default '',
            line_start integer,
            line_end integer,
            memory_type text not null default 'fact',
            chunk_index integer,
            text text not null,
            embedding_json text
        );
        create virtual table if not exists chunks_fts using fts5(
            id unindexed,
            path unindexed,
            section,
            text
        );
        create table if not exists nodes (
            id text primary key,
            type text not null,
            label text not null,
            path text,
            metadata_json text
        );
        create table if not exists edges (
            source_id text not null,
            relation text not null,
            target_id text not null,
            confidence real not null default 1.0,
            evidence_path text not null default '',
            evidence_line_start integer not null default 0,
            evidence_line_end integer,
            primary key (source_id, relation, target_id, evidence_path, evidence_line_start)
        );
        create index if not exists idx_edges_source on edges(source_id);
        create index if not exists idx_edges_target on edges(target_id);
        """
    )


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "unknown"


def _node(node_id: str, node_type: str, label: str, path: str | None = None, metadata: dict[str, Any] | None = None) -> tuple:
    return (node_id, node_type, label, path, json.dumps(metadata or {}, ensure_ascii=False))


def _edge(source_id: str, relation: str, target_id: str, item: dict[str, Any], confidence: float = 1.0) -> tuple:
    return (
        source_id,
        relation,
        target_id,
        confidence,
        str(item.get("path") or ""),
        item.get("line_start") or 0,
        item.get("line_end"),
    )


def _extract_graph_rows(items: list[dict[str, Any]]) -> tuple[list[tuple], list[tuple]]:
    nodes: dict[str, tuple] = {}
    edges: set[tuple] = set()
    chunk_concepts: dict[str, set[str]] = {}

    def add_node(row: tuple) -> None:
        nodes[row[0]] = row

    for item in items:
        item_id = str(item.get("id") or "")
        path = str(item.get("path") or "")
        text = str(item.get("text") or item.get("doc") or "")
        if not item_id or not path or not text:
            continue
        section = str(item.get("section") or "")
        memory_type = str(item.get("memory_type") or "fact")
        file_id = f"file:{path}"
        chunk_id = f"chunk:{item_id}"
        type_id = f"memory_type:{_slug(memory_type)}"
        add_node(_node(file_id, "file", path, path))
        add_node(_node(chunk_id, "chunk", section or item_id, path, {
            "chunk_id": item_id,
            "section": section,
            "memory_type": memory_type,
        }))
        add_node(_node(type_id, "memory_type", memory_type))
        edges.add(_edge(file_id, "contains", chunk_id, item))
        edges.add(_edge(chunk_id, "has_type", type_id, item))

        concepts: set[str] = {type_id}
        for link in re.findall(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]", text):
            label = link.strip()
            if not label:
                continue
            concept_id = f"concept:{_slug(label)}"
            add_node(_node(concept_id, "concept", label))
            edges.add(_edge(chunk_id, "mentions", concept_id, item))
            concepts.add(concept_id)
        for tag in re.findall(r"(?<!\w)#([A-Za-z0-9_/-]+)", text):
            label = tag.strip("/")
            if not label:
                continue
            tag_id = f"tag:{_slug(label)}"
            add_node(_node(tag_id, "tag", label))
            edges.add(_edge(chunk_id, "tagged", tag_id, item))
            concepts.add(tag_id)
        heading = section or re.sub(r"^#+\s*", "", text.splitlines()[0]).strip() if text.splitlines() else ""
        if heading:
            concept_id = f"concept:{_slug(heading)}"
            add_node(_node(concept_id, "concept", heading))
            edges.add(_edge(chunk_id, "describes", concept_id, item))
            concepts.add(concept_id)
        chunk_concepts[chunk_id] = concepts

    concept_to_chunks: dict[str, set[str]] = {}
    for chunk_id, concepts in chunk_concepts.items():
        for concept_id in concepts:
            concept_to_chunks.setdefault(concept_id, set()).add(chunk_id)
    for concept_id, chunk_ids in concept_to_chunks.items():
        for chunk_id in chunk_ids:
            edges.add((concept_id, "described_by", chunk_id, 1.0, "", 0, None))

    return list(nodes.values()), list(edges)


def rebuild_sqlite_index(index_root: str | Path, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Rebuild the SQLite metadata and FTS index from semantic index items."""
    with _connect(index_root) as db:
        _init_schema(db)
        db.execute("delete from chunks_fts")
        db.execute("delete from edges")
        db.execute("delete from nodes")
        db.execute("delete from chunks")
        db.execute(
            "insert or replace into meta(key, value) values (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )
        rows = []
        fts_rows = []
        for item in items:
            item_id = str(item.get("id") or "")
            path = str(item.get("path") or "")
            text = str(item.get("text") or item.get("doc") or "")
            if not item_id or not path or not text:
                continue
            section = str(item.get("section") or "")
            line_start = item.get("line_start")
            line_end = item.get("line_end")
            memory_type = str(item.get("memory_type") or "fact")
            chunk_index = item.get("chunk_index")
            embedding = item.get("embedding")
            embedding_json = json.dumps(embedding, ensure_ascii=False) if embedding is not None else None
            rows.append((
                item_id,
                path,
                section,
                line_start,
                line_end,
                memory_type,
                chunk_index,
                text,
                embedding_json,
            ))
            fts_rows.append((item_id, path, section, text))

        db.executemany(
            """
            insert into chunks(
                id, path, section, line_start, line_end, memory_type,
                chunk_index, text, embedding_json
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        db.executemany(
            "insert into chunks_fts(id, path, section, text) values (?, ?, ?, ?)",
            fts_rows,
        )
        node_rows, edge_rows = _extract_graph_rows(items)
        db.executemany(
            "insert or replace into nodes(id, type, label, path, metadata_json) values (?, ?, ?, ?, ?)",
            node_rows,
        )
        db.executemany(
            """
            insert or replace into edges(
                source_id, relation, target_id, confidence,
                evidence_path, evidence_line_start, evidence_line_end
            ) values (?, ?, ?, ?, ?, ?, ?)
            """,
            edge_rows,
        )
        db.commit()

    return {
        "status": "ok",
        "schema_version": SCHEMA_VERSION,
        "chunks": len(rows),
        "nodes": len(node_rows),
        "edges": len(edge_rows),
        "index_file": str(sqlite_index_path(index_root)),
    }


def _row_to_result(row: sqlite3.Row, best_rank_abs: float) -> dict[str, Any]:
    rank_abs = float(row["rank_abs"] or 0.0)
    score = rank_abs / best_rank_abs if best_rank_abs > 0.0 else 1.0
    distance = 1.0 - score
    meta = {
        "id": row["id"],
        "path": row["path"],
        "section": row["section"] or "",
        "line_start": row["line_start"],
        "line_end": row["line_end"],
        "memory_type": row["memory_type"] or "fact",
        "chunk_index": row["chunk_index"],
    }
    return {
        "id": row["id"],
        "path": row["path"],
        "doc": row["text"],
        "text": row["text"],
        "meta": meta,
        "distance": distance,
        "score": score,
        "why_relevant": "full_text_match",
    }


def _chunk_row_to_result(row: sqlite3.Row, why_relevant: str, score: float, distance: float, graph_via: list[str] | None = None) -> dict[str, Any]:
    meta = {
        "id": row["id"],
        "path": row["path"],
        "section": row["section"] or "",
        "line_start": row["line_start"],
        "line_end": row["line_end"],
        "memory_type": row["memory_type"] or "fact",
        "chunk_index": row["chunk_index"],
    }
    if graph_via is not None:
        meta["graph_via"] = graph_via
    return {
        "id": row["id"],
        "path": row["path"],
        "doc": row["text"],
        "text": row["text"],
        "meta": meta,
        "distance": distance,
        "score": score,
        "why_relevant": why_relevant,
    }


def full_text_search(index_root: str | Path, query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search the SQLite FTS index and return chunk-shaped results."""
    db_path = sqlite_index_path(index_root)
    if not db_path.exists() or not query.strip():
        return []
    safe_limit = max(1, min(50, int(limit)))
    with _connect(index_root) as db:
        _init_schema(db)
        try:
            rows = db.execute(
                """
                select
                    c.id, c.path, c.section, c.line_start, c.line_end,
                    c.memory_type, c.chunk_index, c.text,
                    abs(bm25(chunks_fts)) as rank_abs
                from chunks_fts
                join chunks c on c.id = chunks_fts.id
                where chunks_fts match ?
                order by bm25(chunks_fts)
                limit ?
                """,
                (query, safe_limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # FTS query syntax is picky; quote terms for user-facing plain text search.
            terms = [term.replace('"', '""') for term in query.split()]
            quoted_query = " OR ".join(f'"{term}"' for term in terms if term)
            if not quoted_query:
                return []
            rows = db.execute(
                """
                select
                    c.id, c.path, c.section, c.line_start, c.line_end,
                    c.memory_type, c.chunk_index, c.text,
                    abs(bm25(chunks_fts)) as rank_abs
                from chunks_fts
                join chunks c on c.id = chunks_fts.id
                where chunks_fts match ?
                order by bm25(chunks_fts)
                limit ?
                """,
                (quoted_query, safe_limit),
            ).fetchall()
    best_rank_abs = max((float(row["rank_abs"] or 0.0) for row in rows), default=0.0)
    return [_row_to_result(row, best_rank_abs) for row in rows]


def graph_search(index_root: str | Path, query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search seed chunks with FTS, then expand one hop through graph relations."""
    db_path = sqlite_index_path(index_root)
    if not db_path.exists() or not query.strip():
        return []
    safe_limit = max(1, min(50, int(limit)))
    seed_limit = min(50, max(safe_limit * 3, safe_limit + 5))
    seeds = full_text_search(index_root, query, seed_limit)
    if not seeds:
        return []
    max_seed_results = safe_limit if safe_limit == 1 else max(1, safe_limit - 1)
    results: list[dict[str, Any]] = []
    neighbor_results: list[dict[str, Any]] = []
    seen_chunk_ids: set[str] = set()
    with _connect(index_root) as db:
        _init_schema(db)
        for seed in seeds:
            seed_id = str(seed.get("id") or "")
            if not seed_id:
                continue
            if seed_id not in seen_chunk_ids and len(results) < max_seed_results:
                seed_copy = dict(seed)
                seed_copy["why_relevant"] = "graph_seed_full_text"
                results.append(seed_copy)
                seen_chunk_ids.add(seed_id)

            seed_node = f"chunk:{seed_id}"
            neighbor_rows = db.execute(
                """
                select distinct c.*, e.target_id as via
                from edges e
                join edges back on back.source_id = e.target_id
                join chunks c on ('chunk:' || c.id) = back.target_id
                where e.source_id = ?
                  and e.relation in ('mentions', 'tagged', 'describes', 'has_type')
                  and back.relation = 'described_by'
                  and c.id != ?
                order by c.path, c.chunk_index
                """,
                (seed_node, seed_id),
            ).fetchall()
            for row in neighbor_rows:
                neighbor_id = str(row["id"])
                if neighbor_id in seen_chunk_ids:
                    continue
                via = str(row["via"])
                neighbor_results.append(_chunk_row_to_result(
                    row,
                    why_relevant="graph_neighbor",
                    score=max(0.0, float(seed.get("score", 1.0)) - 0.1),
                    distance=min(1.0, float(seed.get("distance", 0.0)) + 0.1),
                    graph_via=[via],
                ))
                seen_chunk_ids.add(neighbor_id)
                if len(results) + len(neighbor_results) >= safe_limit:
                    break
            if len(results) + len(neighbor_results) >= safe_limit:
                break
    return (results + neighbor_results)[:safe_limit]
