import asyncio
import json
import os
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

from tools import index_store, knowledge_query


class KnowledgeQueryFullTextTests(unittest.TestCase):
    def test_knowledge_query_full_text_mode_uses_sqlite_fts(self):
        original_env = dict(os.environ)
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            knowledge = root / "knowledge"
            index_root = root / ".nova" / "index"
            knowledge.mkdir()
            os.environ["NOVA_KNOWLEDGE_ROOT"] = str(knowledge)
            os.environ["NOVA_INDEX_ROOT"] = str(index_root)
            os.environ["NOVA_SEARCH_ENABLED"] = "true"
            try:
                index_store.rebuild_sqlite_index(index_root, [
                    {
                        "id": "projects/nova/commands.md#0",
                        "path": "projects/nova/commands.md",
                        "section": "Commands",
                        "line_start": 3,
                        "line_end": 6,
                        "memory_type": "procedure",
                        "chunk_index": 0,
                        "text": "Use nova_memory_maintain index --force before exact ticket lookup.",
                        "embedding": [0.1, 0.2],
                    }
                ])

                result = asyncio.run(knowledge_query.execute(
                    {"query": "exact ticket lookup", "mode": "full_text", "limit": 3},
                    root,
                ))
                payload = json.loads(result[0].text)
            finally:
                os.environ.clear()
                os.environ.update(original_env)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["mode"], "full_text")
        self.assertEqual(len(payload["matches"]), 1)
        match = payload["matches"][0]
        self.assertEqual(match["id"], "projects/nova/commands.md#0")
        self.assertEqual(match["why_relevant"], "full_text_match")
        self.assertGreater(match["score"], 0)

    def test_tool_schema_exposes_search_mode(self):
        tool = knowledge_query.get_tool_definition(Path.cwd())
        mode = tool.inputSchema["properties"]["mode"]
        self.assertEqual(mode["enum"], ["semantic", "full_text", "hybrid", "graph"])
        self.assertEqual(mode["default"], "semantic")

    def test_knowledge_query_graph_mode_uses_graph_search(self):
        original_env = dict(os.environ)
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            knowledge = root / "knowledge"
            index_root = root / ".nova" / "index"
            knowledge.mkdir()
            os.environ["NOVA_KNOWLEDGE_ROOT"] = str(knowledge)
            os.environ["NOVA_INDEX_ROOT"] = str(index_root)
            os.environ["NOVA_SEARCH_ENABLED"] = "true"
            try:
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

                result = asyncio.run(knowledge_query.execute(
                    {"query": "exact lookup", "mode": "graph", "limit": 5},
                    root,
                ))
                payload = json.loads(result[0].text)
            finally:
                os.environ.clear()
                os.environ.update(original_env)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["mode"], "graph")
        self.assertEqual([match["id"] for match in payload["matches"]], [
            "projects/nova/question.md#0",
            "projects/nova/decision.md#0",
        ])
        self.assertEqual(payload["matches"][1]["why_relevant"], "graph_neighbor")
        self.assertIn("concept:sqlite-fts", payload["matches"][1]["graph_via"])


if __name__ == "__main__":
    unittest.main()
