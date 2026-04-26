import sqlite3
import sys
import tempfile
import types
import unittest
from dataclasses import dataclass
from pathlib import Path


@dataclass
class _TextContent:
    type: str
    text: str


@dataclass
class _Tool:
    name: str
    description: str
    inputSchema: dict


_mcp_types = types.ModuleType("mcp.types")
_mcp_types.TextContent = _TextContent
_mcp_types.Tool = _Tool
sys.modules.setdefault("mcp.types", _mcp_types)

ROOT = Path(__file__).resolve().parents[1]
MCP_ROOT = ROOT / "mcp"
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

from tools import index_store


class IndexStoreTests(unittest.TestCase):
    def test_rebuild_sqlite_index_creates_tables_and_full_text_results(self):
        with tempfile.TemporaryDirectory() as tempdir:
            index_root = Path(tempdir) / "index"
            items = [
                {
                    "id": "projects/nova/design.md#0",
                    "path": "projects/nova/design.md",
                    "section": "Retrieval",
                    "line_start": 1,
                    "line_end": 4,
                    "memory_type": "decision",
                    "chunk_index": 0,
                    "text": "NOVA should use SQLite FTS for exact ticket and command recall.",
                    "embedding": [0.1, 0.2],
                },
                {
                    "id": "projects/nova/other.md#0",
                    "path": "projects/nova/other.md",
                    "section": "Other",
                    "line_start": 1,
                    "line_end": 2,
                    "memory_type": "fact",
                    "chunk_index": 0,
                    "text": "Unrelated note about gardening.",
                    "embedding": [0.2, 0.3],
                },
            ]

            result = index_store.rebuild_sqlite_index(index_root, items)
            matches = index_store.full_text_search(index_root, "SQLite ticket command", limit=5)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["chunks"], 2)
            self.assertTrue((index_root / "nova_index.sqlite").exists())
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["id"], "projects/nova/design.md#0")
            self.assertEqual(matches[0]["meta"]["memory_type"], "decision")
            self.assertEqual(matches[0]["why_relevant"], "full_text_match")

    def test_full_text_score_is_higher_for_better_bm25_rank(self):
        with tempfile.TemporaryDirectory() as tempdir:
            index_root = Path(tempdir) / "index"
            index_store.rebuild_sqlite_index(index_root, [
                {
                    "id": "strong.md#0",
                    "path": "strong.md",
                    "section": "Strong",
                    "line_start": 1,
                    "line_end": 1,
                    "memory_type": "fact",
                    "chunk_index": 0,
                    "text": "SQLite ticket command",
                    "embedding": [0.1],
                },
                {
                    "id": "weak.md#0",
                    "path": "weak.md",
                    "section": "Weak",
                    "line_start": 1,
                    "line_end": 1,
                    "memory_type": "fact",
                    "chunk_index": 0,
                    "text": "SQLite ticket command unrelated unrelated unrelated unrelated unrelated unrelated",
                    "embedding": [0.2],
                },
            ])

            matches = index_store.full_text_search(index_root, "SQLite ticket command", limit=2)

            self.assertEqual([match["id"] for match in matches], ["strong.md#0", "weak.md#0"])
            self.assertGreater(matches[0]["score"], matches[1]["score"])
            self.assertLess(matches[0]["distance"], matches[1]["distance"])

    def test_rebuild_sqlite_index_extracts_graph_nodes_and_edges(self):
        with tempfile.TemporaryDirectory() as tempdir:
            index_root = Path(tempdir) / "index"
            index_store.rebuild_sqlite_index(index_root, [
                {
                    "id": "projects/nova/graph.md#0",
                    "path": "projects/nova/graph.md",
                    "section": "Graph Retrieval",
                    "line_start": 1,
                    "line_end": 5,
                    "memory_type": "decision",
                    "chunk_index": 0,
                    "text": "# Graph Retrieval\nUse [[SQLite FTS]] with #memory graph expansion.",
                    "embedding": [0.1],
                }
            ])

            db = sqlite3.connect(index_root / "nova_index.sqlite")
            try:
                nodes = {row[0]: row[1] for row in db.execute("select id, type from nodes")}
                edges = {(row[0], row[1], row[2]) for row in db.execute("select source_id, relation, target_id from edges")}
            finally:
                db.close()

            self.assertEqual(nodes["file:projects/nova/graph.md"], "file")
            self.assertEqual(nodes["chunk:projects/nova/graph.md#0"], "chunk")
            self.assertEqual(nodes["concept:sqlite-fts"], "concept")
            self.assertEqual(nodes["tag:memory"], "tag")
            self.assertIn(("file:projects/nova/graph.md", "contains", "chunk:projects/nova/graph.md#0"), edges)
            self.assertIn(("chunk:projects/nova/graph.md#0", "mentions", "concept:sqlite-fts"), edges)
            self.assertIn(("chunk:projects/nova/graph.md#0", "tagged", "tag:memory"), edges)

    def test_graph_search_expands_from_seed_chunk_to_related_chunks(self):
        with tempfile.TemporaryDirectory() as tempdir:
            index_root = Path(tempdir) / "index"
            index_store.rebuild_sqlite_index(index_root, [
                {
                    "id": "projects/nova/question.md#0",
                    "path": "projects/nova/question.md",
                    "section": "Question",
                    "line_start": 1,
                    "line_end": 3,
                    "memory_type": "question",
                    "chunk_index": 0,
                    "text": "How do we improve exact lookup? See [[SQLite FTS]].",
                    "embedding": [0.1],
                },
                {
                    "id": "projects/nova/decision.md#0",
                    "path": "projects/nova/decision.md",
                    "section": "SQLite FTS",
                    "line_start": 1,
                    "line_end": 4,
                    "memory_type": "decision",
                    "chunk_index": 0,
                    "text": "# SQLite FTS\nDecision: use full-text search for exact commands and ticket IDs.",
                    "embedding": [0.2],
                },
            ])

            matches = index_store.graph_search(index_root, "exact lookup", limit=5)

            self.assertEqual([match["id"] for match in matches], [
                "projects/nova/question.md#0",
                "projects/nova/decision.md#0",
            ])
            self.assertEqual(matches[0]["why_relevant"], "graph_seed_full_text")
            self.assertEqual(matches[1]["why_relevant"], "graph_neighbor")
            self.assertIn("concept:sqlite-fts", matches[1]["meta"]["graph_via"])

    def test_graph_search_expands_through_shared_memory_type(self):
        with tempfile.TemporaryDirectory() as tempdir:
            index_root = Path(tempdir) / "index"
            index_store.rebuild_sqlite_index(index_root, [
                {
                    "id": "projects/nova/source.md#0",
                    "path": "projects/nova/source.md",
                    "section": "Decision A",
                    "line_start": 1,
                    "line_end": 2,
                    "memory_type": "decision",
                    "chunk_index": 0,
                    "text": "Decision: exact lookup needs graph expansion.",
                    "embedding": [0.1],
                },
                {
                    "id": "projects/nova/related.md#0",
                    "path": "projects/nova/related.md",
                    "section": "Decision B",
                    "line_start": 1,
                    "line_end": 2,
                    "memory_type": "decision",
                    "chunk_index": 0,
                    "text": "Decision: graph retrieval should connect related decisions.",
                    "embedding": [0.2],
                },
            ])

            matches = index_store.graph_search(index_root, "exact lookup", limit=5)

            self.assertEqual([match["id"] for match in matches], [
                "projects/nova/source.md#0",
                "projects/nova/related.md#0",
            ])
            self.assertIn("memory_type:decision", matches[1]["meta"]["graph_via"])

    def test_graph_search_reserves_budget_for_neighbors_when_many_seed_chunks_match(self):
        with tempfile.TemporaryDirectory() as tempdir:
            index_root = Path(tempdir) / "index"
            items = [
                {
                    "id": "projects/nova/seed.md#0",
                    "path": "projects/nova/seed.md",
                    "section": "Seed",
                    "line_start": 1,
                    "line_end": 2,
                    "memory_type": "question",
                    "chunk_index": 0,
                    "text": "exact lookup exact lookup exact lookup [[Shared Graph Topic]]",
                    "embedding": [0.1],
                },
                {
                    "id": "projects/nova/neighbor.md#0",
                    "path": "projects/nova/neighbor.md",
                    "section": "Shared Graph Topic",
                    "line_start": 1,
                    "line_end": 2,
                    "memory_type": "decision",
                    "chunk_index": 0,
                    "text": "# Shared Graph Topic\nThis neighbor explains graph expansion.",
                    "embedding": [0.2],
                },
            ]
            for idx in range(8):
                items.append({
                    "id": f"projects/nova/noisy-{idx}.md#0",
                    "path": f"projects/nova/noisy-{idx}.md",
                    "section": f"Noisy {idx}",
                    "line_start": 1,
                    "line_end": 2,
                    "memory_type": "fact",
                    "chunk_index": 0,
                    "text": "exact lookup filler text that also matches the seed query.",
                    "embedding": [0.3],
                })
            index_store.rebuild_sqlite_index(index_root, items)

            matches = index_store.graph_search(index_root, "exact lookup", limit=5)

            ids = [match["id"] for match in matches]
            self.assertIn("projects/nova/seed.md#0", ids)
            self.assertIn("projects/nova/neighbor.md#0", ids)
            self.assertLess(len(matches), 6)

    def test_rebuild_sqlite_index_extracts_facets_for_filtering(self):
        with tempfile.TemporaryDirectory() as tempdir:
            index_root = Path(tempdir) / "index"
            index_store.rebuild_sqlite_index(index_root, [
                {
                    "id": "projects/nova/retrieval.md#0",
                    "path": "projects/nova/retrieval.md",
                    "section": "Hybrid Retrieval",
                    "line_start": 1,
                    "line_end": 4,
                    "memory_type": "decision",
                    "chunk_index": 0,
                    "text": "Decision: use [[Hybrid Search]] for retrieval. #mcp/search",
                    "embedding": [0.1],
                },
                {
                    "id": "projects/other/retrieval.md#0",
                    "path": "projects/other/retrieval.md",
                    "section": "Hybrid Retrieval",
                    "line_start": 1,
                    "line_end": 4,
                    "memory_type": "fact",
                    "chunk_index": 0,
                    "text": "Fact: retrieval can use unrelated filters. #archive",
                    "embedding": [0.2],
                },
            ])

            db = sqlite3.connect(index_root / "nova_index.sqlite")
            try:
                facets = {(row[0], row[1], row[2]) for row in db.execute(
                    "select chunk_id, facet_type, facet_value from facets"
                )}
            finally:
                db.close()

        self.assertIn(("projects/nova/retrieval.md#0", "project", "nova"), facets)
        self.assertIn(("projects/nova/retrieval.md#0", "memory_type", "decision"), facets)
        self.assertIn(("projects/nova/retrieval.md#0", "tag", "mcp/search"), facets)
        self.assertIn(("projects/nova/retrieval.md#0", "concept", "hybrid-search"), facets)
        self.assertIn(("projects/nova/retrieval.md#0", "section", "hybrid-retrieval"), facets)

    def test_full_text_search_applies_facet_filters_and_returns_counts(self):
        with tempfile.TemporaryDirectory() as tempdir:
            index_root = Path(tempdir) / "index"
            index_store.rebuild_sqlite_index(index_root, [
                {
                    "id": "projects/nova/retrieval.md#0",
                    "path": "projects/nova/retrieval.md",
                    "section": "Hybrid Retrieval",
                    "line_start": 1,
                    "line_end": 4,
                    "memory_type": "decision",
                    "chunk_index": 0,
                    "text": "Decision: use [[Hybrid Search]] for retrieval. #mcp/search",
                    "embedding": [0.1],
                },
                {
                    "id": "projects/other/retrieval.md#0",
                    "path": "projects/other/retrieval.md",
                    "section": "Other Retrieval",
                    "line_start": 1,
                    "line_end": 4,
                    "memory_type": "fact",
                    "chunk_index": 0,
                    "text": "Fact: retrieval can use unrelated filters. #archive",
                    "embedding": [0.2],
                },
            ])

            matches = index_store.full_text_search(
                index_root,
                "retrieval",
                limit=5,
                filters={"project": "nova", "memory_type": ["decision"], "tag": "mcp/search"},
            )
            counts = index_store.facet_counts(index_root, "retrieval", filters={"project": "nova"})

        self.assertEqual([match["id"] for match in matches], ["projects/nova/retrieval.md#0"])
        self.assertEqual(matches[0]["meta"]["facets"]["project"], ["nova"])
        self.assertEqual(counts["memory_type"], {"decision": 1})
        self.assertEqual(counts["tag"], {"mcp/search": 1})
        self.assertEqual(counts["concept"], {"hybrid-search": 1})

    def test_rebuild_sqlite_index_replaces_stale_rows(self):
        with tempfile.TemporaryDirectory() as tempdir:
            index_root = Path(tempdir) / "index"
            index_store.rebuild_sqlite_index(index_root, [
                {
                    "id": "old.md#0",
                    "path": "old.md",
                    "section": "Old",
                    "line_start": 1,
                    "line_end": 1,
                    "memory_type": "fact",
                    "chunk_index": 0,
                    "text": "old content",
                    "embedding": [0.1],
                }
            ])
            index_store.rebuild_sqlite_index(index_root, [
                {
                    "id": "new.md#0",
                    "path": "new.md",
                    "section": "New",
                    "line_start": 1,
                    "line_end": 1,
                    "memory_type": "fact",
                    "chunk_index": 0,
                    "text": "new searchable content",
                    "embedding": [0.2],
                }
            ])

            db = sqlite3.connect(index_root / "nova_index.sqlite")
            try:
                ids = [row[0] for row in db.execute("select id from chunks order by id")]
            finally:
                db.close()

            self.assertEqual(ids, ["new.md#0"])


if __name__ == "__main__":
    unittest.main()
