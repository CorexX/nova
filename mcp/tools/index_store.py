"""SQLite metadata and full-text index for NOVA knowledge chunks."""

from __future__ import annotations

import json
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
        """
    )


def rebuild_sqlite_index(index_root: str | Path, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Rebuild the SQLite metadata and FTS index from semantic index items."""
    with _connect(index_root) as db:
        _init_schema(db)
        db.execute("delete from chunks_fts")
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
        db.commit()

    return {
        "status": "ok",
        "schema_version": SCHEMA_VERSION,
        "chunks": len(rows),
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
