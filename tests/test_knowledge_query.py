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

from tools import knowledge_query


class KnowledgeQueryTests(unittest.TestCase):
    def test_knowledge_query_dedupe_none_keeps_multiple_chunks_from_same_path(self):
        original_search = knowledge_query.semantic_search
        original_env = dict(os.environ)
        tempdir = tempfile.TemporaryDirectory()
        try:
            root = Path(tempdir.name)
            knowledge = root / "knowledge"
            knowledge.mkdir()
            os.environ["NOVA_KNOWLEDGE_ROOT"] = str(knowledge)
            os.environ["NOVA_SEARCH_ENABLED"] = "true"

            def fake_search(chroma_path, query, top_k, log=None):
                return [
                    {
                        "id": "projects/nova/architecture.md#1",
                        "path": "projects/nova/architecture.md",
                        "doc": "## Decision\nKeep four tools.",
                        "distance": 0.1,
                        "meta": {"id": "projects/nova/architecture.md#1", "path": "projects/nova/architecture.md", "section": "Decision", "chunk_index": 1},
                    },
                    {
                        "id": "projects/nova/architecture.md#2",
                        "path": "projects/nova/architecture.md",
                        "doc": "## Constraints\nNo runtime behavior.",
                        "distance": 0.2,
                        "meta": {"id": "projects/nova/architecture.md#2", "path": "projects/nova/architecture.md", "section": "Constraints", "chunk_index": 2},
                    },
                ]

            knowledge_query.semantic_search = fake_search
            result = asyncio.run(knowledge_query.execute({"query": "nova", "dedupe": "none", "limit": 5}, root))
            payload = json.loads(result[0].text)
        finally:
            knowledge_query.semantic_search = original_search
            os.environ.clear()
            os.environ.update(original_env)
            tempdir.cleanup()

        self.assertEqual(payload["dedupe"], "none")
        self.assertEqual([match["id"] for match in payload["matches"]], [
            "projects/nova/architecture.md#1",
            "projects/nova/architecture.md#2",
        ])

    def test_knowledge_query_dedupe_path_collapses_same_file(self):
        original_search = knowledge_query.semantic_search
        original_env = dict(os.environ)
        tempdir = tempfile.TemporaryDirectory()
        try:
            root = Path(tempdir.name)
            knowledge = root / "knowledge"
            knowledge.mkdir()
            os.environ["NOVA_KNOWLEDGE_ROOT"] = str(knowledge)
            os.environ["NOVA_SEARCH_ENABLED"] = "true"

            def fake_search(chroma_path, query, top_k, log=None):
                return [
                    {"id": "p.md#1", "path": "p.md", "doc": "one", "distance": 0.1, "meta": {"id": "p.md#1", "path": "p.md", "section": "A", "chunk_index": 1}},
                    {"id": "p.md#2", "path": "p.md", "doc": "two", "distance": 0.2, "meta": {"id": "p.md#2", "path": "p.md", "section": "B", "chunk_index": 2}},
                ]

            knowledge_query.semantic_search = fake_search
            result = asyncio.run(knowledge_query.execute({"query": "nova", "dedupe": "path", "limit": 5}, root))
            payload = json.loads(result[0].text)
        finally:
            knowledge_query.semantic_search = original_search
            os.environ.clear()
            os.environ.update(original_env)
            tempdir.cleanup()

        self.assertEqual(payload["dedupe"], "path")
        self.assertEqual([match["id"] for match in payload["matches"]], ["p.md#1"])

    def test_knowledge_query_returns_full_chunk_citations(self):
        original_search = knowledge_query.semantic_search
        original_env = dict(os.environ)
        tempdir = tempfile.TemporaryDirectory()
        try:
            root = Path(tempdir.name)
            knowledge = root / "knowledge"
            knowledge.mkdir()
            os.environ["NOVA_KNOWLEDGE_ROOT"] = str(knowledge)
            os.environ["NOVA_SEARCH_ENABLED"] = "true"

            def fake_search(chroma_path, query, top_k, log=None):
                return [
                    {
                        "id": "projects/nova/decisions.md#2",
                        "path": "projects/nova/decisions.md",
                        "doc": "## Decision\nNOVA stays memory-only.",
                        "distance": 0.2,
                        "meta": {
                            "id": "projects/nova/decisions.md#2",
                            "path": "projects/nova/decisions.md",
                            "section": "Decision",
                            "line_start": 10,
                            "line_end": 12,
                            "memory_type": "decision",
                            "chunk_index": 2,
                        },
                    }
                ]

            knowledge_query.semantic_search = fake_search
            result = asyncio.run(knowledge_query.execute({"query": "memory boundary"}, root))
            payload = json.loads(result[0].text)
        finally:
            knowledge_query.semantic_search = original_search
            os.environ.clear()
            os.environ.update(original_env)
            tempdir.cleanup()

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(len(payload["matches"]), 1)
        match = payload["matches"][0]
        self.assertEqual(match["id"], "projects/nova/decisions.md#2")
        self.assertEqual(match["path"], "projects/nova/decisions.md")
        self.assertEqual(match["section"], "Decision")
        self.assertEqual(match["line_start"], 10)
        self.assertEqual(match["line_end"], 12)
        self.assertEqual(match["memory_type"], "decision")
        self.assertEqual(match["chunk_index"], 2)
        self.assertEqual(match["citation"]["line_start"], 10)
        self.assertEqual(match["citation"]["line_end"], 12)


if __name__ == "__main__":
    unittest.main()
