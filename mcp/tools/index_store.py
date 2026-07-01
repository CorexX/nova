"""SQLite metadata and full-text index for NOVA knowledge chunks."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any


INDEX_DB_NAME = "nova_index.sqlite"
SCHEMA_VERSION = 2


def _normalize_supersedes(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = value.strip()
        if not raw or raw in {"[]", "-", "none", "None"}:
            return []
        return [item.strip().strip("'\"") for item in raw.split(",") if item.strip().strip("'\"")]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _lifecycle_status(item: dict[str, Any] | sqlite3.Row) -> str:
    try:
        value = item["lifecycle_status"]
    except (KeyError, IndexError):
        value = None
    return str(value or "active").strip().lower() or "active"


def _supersedes(item: dict[str, Any] | sqlite3.Row) -> list[str]:
    try:
        value = item["supersedes_json"]
    except (KeyError, IndexError):
        try:
            value = item["supersedes"]
        except (KeyError, IndexError):
            value = None
    if isinstance(value, str) and value.strip().startswith("["):
        try:
            return _normalize_supersedes(json.loads(value))
        except json.JSONDecodeError:
            pass
    return _normalize_supersedes(value)


def sqlite_index_path(index_root: str | Path) -> Path:
    return Path(index_root) / INDEX_DB_NAME


def _connect(index_root: str | Path) -> sqlite3.Connection:
    db_path = sqlite_index_path(index_root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # timeout=30: SQLite retries for up to 30 s when the DB is locked by a
    # concurrent writer (e.g. rebuild_sqlite_index running while a search hits
    # the same file on an Azure Files volume).
    db = sqlite3.connect(db_path, timeout=30)
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
            lifecycle_status text not null default 'active',
            supersedes_json text not null default '[]',
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
        create table if not exists facets (
            chunk_id text not null,
            facet_type text not null,
            facet_value text not null,
            primary key (chunk_id, facet_type, facet_value),
            foreign key (chunk_id) references chunks(id) on delete cascade
        );
        create index if not exists idx_edges_source on edges(source_id);
        create index if not exists idx_edges_target on edges(target_id);
        create index if not exists idx_facets_type_value on facets(facet_type, facet_value);
        create index if not exists idx_facets_chunk on facets(chunk_id);
        """
    )
    existing_columns = {row["name"] for row in db.execute("pragma table_info(chunks)").fetchall()}
    if "lifecycle_status" not in existing_columns:
        db.execute("alter table chunks add column lifecycle_status text not null default 'active'")
    if "supersedes_json" not in existing_columns:
        db.execute("alter table chunks add column supersedes_json text not null default '[]'")


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
        lifecycle_status = _lifecycle_status(item)
        supersedes = _supersedes(item)
        file_id = f"file:{path}"
        chunk_id = f"chunk:{item_id}"
        type_id = f"memory_type:{_slug(memory_type)}"
        status_id = f"lifecycle_status:{_slug(lifecycle_status)}"
        add_node(_node(file_id, "file", path, path))
        add_node(_node(chunk_id, "chunk", section or item_id, path, {
            "chunk_id": item_id,
            "section": section,
            "memory_type": memory_type,
            "lifecycle_status": lifecycle_status,
            "supersedes": supersedes,
        }))
        add_node(_node(type_id, "memory_type", memory_type))
        add_node(_node(status_id, "lifecycle_status", lifecycle_status))
        edges.add(_edge(file_id, "contains", chunk_id, item))
        edges.add(_edge(chunk_id, "has_type", type_id, item))
        edges.add(_edge(chunk_id, "has_lifecycle_status", status_id, item))
        for superseded_id in supersedes:
            superseded_node_id = f"memory:{superseded_id}"
            add_node(_node(superseded_node_id, "memory", superseded_id))
            edges.add(_edge(chunk_id, "supersedes", superseded_node_id, item))

        concepts: set[str] = {type_id, status_id}
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


def _path_project(path: str) -> str:
    parts = [part for part in Path(path).parts if part]
    if len(parts) >= 2 and parts[0].lower() == "projects":
        return _slug(parts[1])
    return ""


def _extract_facet_rows(items: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    rows: set[tuple[str, str, str]] = set()
    for item in items:
        item_id = str(item.get("id") or "")
        path = str(item.get("path") or "")
        text = str(item.get("text") or item.get("doc") or "")
        if not item_id or not path:
            continue
        memory_type = str(item.get("memory_type") or "fact").strip().lower() or "fact"
        lifecycle_status = _lifecycle_status(item)
        supersedes = _supersedes(item)
        section = str(item.get("section") or "").strip()
        project = _path_project(path)
        rows.add((item_id, "memory_type", _slug(memory_type)))
        rows.add((item_id, "lifecycle_status", _slug(lifecycle_status)))
        for superseded_id in supersedes:
            rows.add((item_id, "supersedes", superseded_id))
        if project:
            rows.add((item_id, "project", project))
        if section:
            rows.add((item_id, "section", _slug(section)))
        for link in re.findall(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]", text):
            label = link.strip()
            if label:
                rows.add((item_id, "concept", _slug(label)))
        for tag in re.findall(r"(?<!\w)#([A-Za-z0-9_/-]+)", text):
            label = tag.strip("/").lower()
            if label:
                rows.add((item_id, "tag", label))
    return sorted(rows)


def _normalize_filters(filters: dict[str, Any] | None) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    if not isinstance(filters, dict):
        return normalized
    aliases = {"tags": "tag", "concepts": "concept", "projects": "project", "memory_types": "memory_type"}
    for raw_key, raw_value in filters.items():
        key = aliases.get(str(raw_key).strip().lower(), str(raw_key).strip().lower())
        if not key:
            continue
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        clean_values: list[str] = []
        for value in values:
            if value is None:
                continue
            text = str(value).strip().lower()
            if not text:
                continue
            clean_values.append(text if key in {"tag", "supersedes"} else _slug(text))
        if clean_values:
            normalized[key] = sorted(set(clean_values))
    return normalized


def _facet_map(db: sqlite3.Connection, chunk_ids: list[str]) -> dict[str, dict[str, list[str]]]:
    if not chunk_ids:
        return {}
    placeholders = ",".join("?" for _ in chunk_ids)
    rows = db.execute(
        f"select chunk_id, facet_type, facet_value from facets where chunk_id in ({placeholders}) order by facet_type, facet_value",
        chunk_ids,
    ).fetchall()
    by_chunk: dict[str, dict[str, list[str]]] = {}
    for row in rows:
        by_chunk.setdefault(row["chunk_id"], {}).setdefault(row["facet_type"], []).append(row["facet_value"])
    return by_chunk


def _filter_clause(filters: dict[str, Any] | None) -> tuple[str, list[str], dict[str, list[str]]]:
    normalized = _normalize_filters(filters)
    clauses: list[str] = []
    params: list[str] = []
    for idx, (facet_type, values) in enumerate(normalized.items()):
        placeholders = ",".join("?" for _ in values)
        clauses.append(
            f"exists (select 1 from facets f{idx} where f{idx}.chunk_id = c.id and f{idx}.facet_type = ? and f{idx}.facet_value in ({placeholders}))"
        )
        params.append(facet_type)
        params.extend(values)
    return (" and " + " and ".join(clauses) if clauses else "", params, normalized)


def rebuild_sqlite_index(index_root: str | Path, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Rebuild the SQLite metadata and FTS index from semantic index items."""
    with _connect(index_root) as db:
        _init_schema(db)
        db.execute("delete from chunks_fts")
        db.execute("delete from facets")
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
            lifecycle_status = _lifecycle_status(item)
            supersedes = _supersedes(item)
            supersedes_json = json.dumps(supersedes, ensure_ascii=False)
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
                lifecycle_status,
                supersedes_json,
                chunk_index,
                text,
                embedding_json,
            ))
            fts_rows.append((item_id, path, section, text))

        db.executemany(
            """
            insert into chunks(
                id, path, section, line_start, line_end, memory_type,
                lifecycle_status, supersedes_json, chunk_index, text, embedding_json
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        db.executemany(
            "insert into chunks_fts(id, path, section, text) values (?, ?, ?, ?)",
            fts_rows,
        )
        node_rows, edge_rows = _extract_graph_rows(items)
        facet_rows = _extract_facet_rows(items)
        db.executemany(
            "insert or replace into nodes(id, type, label, path, metadata_json) values (?, ?, ?, ?, ?)",
            node_rows,
        )
        db.executemany(
            "insert or replace into facets(chunk_id, facet_type, facet_value) values (?, ?, ?)",
            facet_rows,
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
        "facets": len(facet_rows),
        "index_file": str(sqlite_index_path(index_root)),
    }


def _row_to_result(row: sqlite3.Row, best_rank_abs: float, facets: dict[str, list[str]] | None = None) -> dict[str, Any]:
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
        "lifecycle_status": _lifecycle_status(row),
        "supersedes": _supersedes(row),
        "chunk_index": row["chunk_index"],
    }
    if facets is not None:
        meta["facets"] = facets
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
        "lifecycle_status": _lifecycle_status(row),
        "supersedes": _supersedes(row),
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


def full_text_search(index_root: str | Path, query: str, limit: int = 5, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Search the SQLite FTS index and return chunk-shaped results."""
    db_path = sqlite_index_path(index_root)
    if not db_path.exists() or not query.strip():
        return []
    safe_limit = max(1, min(50, int(limit)))
    with _connect(index_root) as db:
        _init_schema(db)
        filter_sql, filter_params, _ = _filter_clause(filters)
        try:
            rows = db.execute(
                f"""
                select
                    c.id, c.path, c.section, c.line_start, c.line_end,
                    c.memory_type, c.lifecycle_status, c.supersedes_json, c.chunk_index, c.text,
                    abs(bm25(chunks_fts)) as rank_abs
                from chunks_fts
                join chunks c on c.id = chunks_fts.id
                where chunks_fts match ?{filter_sql}
                order by bm25(chunks_fts)
                limit ?
                """,
                [query, *filter_params, safe_limit],
            ).fetchall()
        except sqlite3.OperationalError:
            # FTS query syntax is picky; quote terms for user-facing plain text search.
            terms = [term.replace('"', '""') for term in query.split()]
            quoted_query = " OR ".join(f'"{term}"' for term in terms if term)
            if not quoted_query:
                return []
            rows = db.execute(
                f"""
                select
                    c.id, c.path, c.section, c.line_start, c.line_end,
                    c.memory_type, c.lifecycle_status, c.supersedes_json, c.chunk_index, c.text,
                    abs(bm25(chunks_fts)) as rank_abs
                from chunks_fts
                join chunks c on c.id = chunks_fts.id
                where chunks_fts match ?{filter_sql}
                order by bm25(chunks_fts)
                limit ?
                """,
                [quoted_query, *filter_params, safe_limit],
            ).fetchall()
        facet_by_chunk = _facet_map(db, [str(row["id"]) for row in rows])
    best_rank_abs = max((float(row["rank_abs"] or 0.0) for row in rows), default=0.0)
    return [_row_to_result(row, best_rank_abs, facet_by_chunk.get(str(row["id"]), {})) for row in rows]


def facet_counts(index_root: str | Path, query: str, filters: dict[str, Any] | None = None) -> dict[str, dict[str, int]]:
    """Return facet value counts for chunks matching a full-text query and optional filters."""
    db_path = sqlite_index_path(index_root)
    if not db_path.exists() or not query.strip():
        return {}
    with _connect(index_root) as db:
        _init_schema(db)
        filter_sql, filter_params, _ = _filter_clause(filters)
        try:
            rows = db.execute(
                f"""
                select f.facet_type, f.facet_value, count(distinct c.id) as count
                from chunks_fts
                join chunks c on c.id = chunks_fts.id
                join facets f on f.chunk_id = c.id
                where chunks_fts match ?{filter_sql}
                group by f.facet_type, f.facet_value
                order by f.facet_type, count desc, f.facet_value
                """,
                [query, *filter_params],
            ).fetchall()
        except sqlite3.OperationalError:
            terms = [term.replace('"', '""') for term in query.split()]
            quoted_query = " OR ".join(f'"{term}"' for term in terms if term)
            if not quoted_query:
                return {}
            rows = db.execute(
                f"""
                select f.facet_type, f.facet_value, count(distinct c.id) as count
                from chunks_fts
                join chunks c on c.id = chunks_fts.id
                join facets f on f.chunk_id = c.id
                where chunks_fts match ?{filter_sql}
                group by f.facet_type, f.facet_value
                order by f.facet_type, count desc, f.facet_value
                """,
                [quoted_query, *filter_params],
            ).fetchall()
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        counts.setdefault(row["facet_type"], {})[row["facet_value"]] = int(row["count"])
    return counts


def graph_search(
    index_root: str | Path,
    query: str,
    limit: int = 5,
    semantic_seeds: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Search seed chunks, then expand one hop through graph relations.

    If *semantic_seeds* are provided they are used as primary seeds
    (embedding-based), with FTS seeds merged in as fallback.
    """
    db_path = sqlite_index_path(index_root)
    if not db_path.exists() or not query.strip():
        return []
    safe_limit = max(1, min(50, int(limit)))
    seed_limit = min(50, max(safe_limit * 3, safe_limit + 5))

    # Merge semantic + FTS seeds, semantic first (higher quality).
    fts_seeds = full_text_search(index_root, query, seed_limit)
    semantic_seed_ids = {str(s.get("id") or "") for s in semantic_seeds or []}
    if semantic_seeds:
        seen_ids = set(semantic_seed_ids)
        merged = list(semantic_seeds)
        for fs in fts_seeds:
            if str(fs.get("id") or "") not in seen_ids:
                merged.append(fs)
        seeds = merged[:seed_limit]
    else:
        seeds = fts_seeds
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
            effective_score = float(seed.get("score", 1.0))
            if "score" not in seed and "distance" in seed:
                effective_score = max(0.0, 1.0 - float(seed["distance"]))
            if seed_id not in seen_chunk_ids and len(results) < max_seed_results:
                seed_copy = dict(seed)
                seed_copy["why_relevant"] = "graph_seed_semantic" if seed_id in semantic_seed_ids else "graph_seed_full_text"
                # Ensure score exists (semantic seeds only have distance).
                if "score" not in seed_copy and "distance" in seed_copy:
                    seed_copy["score"] = effective_score
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
                    score=max(0.0, effective_score - 0.1),
                    distance=min(1.0, float(seed.get("distance", 0.0)) + 0.1),
                    graph_via=[via],
                ))
                seen_chunk_ids.add(neighbor_id)
                if len(results) + len(neighbor_results) >= safe_limit:
                    break
            if len(results) + len(neighbor_results) >= safe_limit:
                break
    return (results + neighbor_results)[:safe_limit]
