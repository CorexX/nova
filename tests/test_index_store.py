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
