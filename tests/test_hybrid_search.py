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

from tools import index_store, search_shared


class HybridSearchTests(unittest.TestCase):
    def test_hybrid_reranks_by_weighted_semantic_full_text_and_graph_signals(self):
        original_semantic = search_shared.semantic_search
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            index_root = root / "index"
            chroma_path = root / "chroma"
            index_store.rebuild_sqlite_index(index_root, [
                {
                    "id": "projects/nova/seed.md#0",
                    "path": "projects/nova/seed.md",
                    "section": "Seed",
                    "line_start": 1,
                    "line_end": 3,
                    "memory_type": "question",
                    "chunk_index": 0,
                    "text": "Exact ticket lookup needs [[SQLite FTS]] support.",
                    "embedding": [0.1],
                },
                {
                    "id": "projects/nova/graph.md#0",
                    "path": "projects/nova/graph.md",
                    "section": "SQLite FTS",
                    "line_start": 5,
                    "line_end": 9,
                    "memory_type": "decision",
                    "chunk_index": 0,
                    "text": "# SQLite FTS\nUse full-text search for exact commands and ticket IDs.",
                    "embedding": [0.2],
                },
                {
                    "id": "projects/nova/semantic.md#0",
                    "path": "projects/nova/semantic.md",
                    "section": "Semantic Only",
                    "line_start": 11,
                    "line_end": 14,
                    "memory_type": "fact",
                    "chunk_index": 0,
                    "text": "Embeddings help fuzzy recall when exact words differ.",
                    "embedding": [0.3],
                },
            ])

            def fake_semantic(chroma_path_arg, query, top_k, log=None):
                self.assertEqual(str(chroma_path), chroma_path_arg)
                return [
                    {
                        "id": "projects/nova/semantic.md#0",
                        "path": "projects/nova/semantic.md",
                        "doc": "Embeddings help fuzzy recall when exact words differ.",
                        "distance": 0.05,
                        "meta": {
                            "id": "projects/nova/semantic.md#0",
                            "path": "projects/nova/semantic.md",
                            "section": "Semantic Only",
                            "line_start": 11,
                            "line_end": 14,
                            "memory_type": "fact",
                            "chunk_index": 0,
                        },
                    },
                    {
                        "id": "projects/nova/seed.md#0",
                        "path": "projects/nova/seed.md",
                        "doc": "Exact ticket lookup needs [[SQLite FTS]] support.",
                        "distance": 0.45,
                        "meta": {
                            "id": "projects/nova/seed.md#0",
                            "path": "projects/nova/seed.md",
                            "section": "Seed",
                            "line_start": 1,
                            "line_end": 3,
                            "memory_type": "question",
                            "chunk_index": 0,
                        },
                    },
                ]

            try:
                search_shared.semantic_search = fake_semantic
                results = search_shared.hybrid_search(
                    str(chroma_path),
                    str(index_root),
                    "exact ticket lookup",
                    top_k=3,
                )
            finally:
                search_shared.semantic_search = original_semantic

        result_ids = [item["id"] for item in results]
        self.assertEqual(result_ids, [
            "projects/nova/seed.md#0",
            "projects/nova/semantic.md#0",
            "projects/nova/graph.md#0",
        ])
        self.assertGreater(results[0]["score"], results[1]["score"])
        self.assertGreater(results[1]["score"], results[2]["score"])
        self.assertLess(results[0]["distance"], results[1]["distance"])
        self.assertEqual(results[0]["why_relevant"], "hybrid_semantic_and_full_text")
        self.assertEqual(results[1]["why_relevant"], "hybrid_semantic")
        self.assertEqual(results[2]["why_relevant"], "hybrid_graph_neighbor")
        self.assertEqual(results[2]["meta"]["graph_via"], ["concept:sqlite-fts"])
        for item in results:
            self.assertIn("hybrid_signals", item)
            self.assertIn("semantic", item["hybrid_signals"])
            self.assertIn("full_text", item["hybrid_signals"])
            self.assertIn("graph", item["hybrid_signals"])


if __name__ == "__main__":
    unittest.main()
