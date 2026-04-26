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

from tools import context_resolve, memory_maintain


class ChunkMetadataTests(unittest.TestCase):
    def test_split_by_headers_adds_lines_and_memory_type(self):
        content = """# Project Alpha
Intro text.

## Decision
We will keep Markdown as source of truth.

## Open Questions
- Which index backend should be default?

## Constraints
- Local-first only.
"""

        chunks = memory_maintain._split_by_headers(content)

        decision = next(chunk for chunk in chunks if chunk["section"] == "Decision")
        question = next(chunk for chunk in chunks if chunk["section"] == "Open Questions")
        constraint = next(chunk for chunk in chunks if chunk["section"] == "Constraints")

        self.assertEqual(decision["memory_type"], "decision")
        self.assertEqual(question["memory_type"], "question")
        self.assertEqual(constraint["memory_type"], "constraint")
        self.assertEqual(decision["line_start"], 4)
        self.assertEqual(decision["line_end"], 5)
        self.assertIn("source of truth", decision["text"])

    def test_split_by_headers_extracts_lifecycle_status_and_supersedes(self):
        content = """# Knowledge Update - lifecycle

## 12:00:00 - Newer Decision

- entry_id: mem_new
- status: active
- supersedes: mem_old, mem_older

Status: Accepted

### Insight
Use lifecycle metadata in retrieval.
"""

        chunks = memory_maintain._split_by_headers(content)

        entry = next(chunk for chunk in chunks if chunk["section"] == "12:00:00 - Newer Decision")
        self.assertEqual(entry["lifecycle_status"], "active")
        self.assertEqual(entry["supersedes"], ["mem_old", "mem_older"])


class ContextPackTests(unittest.TestCase):
    def test_context_resolve_dedupe_none_keeps_multiple_chunks_from_same_path(self):
        original_search = context_resolve.semantic_search
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
                        "meta": {
                            "id": "projects/nova/architecture.md#1",
                            "path": "projects/nova/architecture.md",
                            "section": "Decision",
                            "memory_type": "decision",
                            "chunk_index": 1,
                            "lifecycle_status": "superseded",
                            "supersedes": ["mem_old"],
                        },
                    },
                    {
                        "id": "projects/nova/architecture.md#2",
                        "path": "projects/nova/architecture.md",
                        "doc": "## Constraints\nNo runtime behavior.",
                        "distance": 0.2,
                        "meta": {"id": "projects/nova/architecture.md#2", "path": "projects/nova/architecture.md", "section": "Constraints", "memory_type": "constraint", "chunk_index": 2},
                    },
                ]

            context_resolve.semantic_search = fake_search
            result = asyncio.run(context_resolve.execute({"query": "nova", "dedupe": "none", "token_budget": 900}, root))
            payload = json.loads(result[0].text)
        finally:
            context_resolve.semantic_search = original_search
            os.environ.clear()
            os.environ.update(original_env)
            tempdir.cleanup()

        self.assertEqual(payload["dedupe"], "none")
        self.assertEqual(len(payload["context_items"]), 2)
        self.assertEqual(payload["context_items"][0]["citation"]["id"], "projects/nova/architecture.md#1")
        self.assertEqual(payload["context_items"][0]["lifecycle_status"], "superseded")
        self.assertEqual(payload["context_items"][0]["supersedes"], ["mem_old"])
        self.assertEqual(payload["context_items"][0]["citation"]["lifecycle_status"], "superseded")
        self.assertEqual(payload["context_items"][1]["citation"]["id"], "projects/nova/architecture.md#2")

    def test_context_resolve_dedupe_path_collapses_same_file(self):
        original_search = context_resolve.semantic_search
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

            context_resolve.semantic_search = fake_search
            result = asyncio.run(context_resolve.execute({"query": "nova", "dedupe": "path", "token_budget": 900}, root))
            payload = json.loads(result[0].text)
        finally:
            context_resolve.semantic_search = original_search
            os.environ.clear()
            os.environ.update(original_env)
            tempdir.cleanup()

        self.assertEqual(payload["dedupe"], "path")
        self.assertEqual(len(payload["context_items"]), 1)
        self.assertEqual(payload["context_items"][0]["citation"]["id"], "p.md#1")

    def test_context_resolve_enforces_approximate_response_budget(self):
        original_search = context_resolve.semantic_search
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
                        "id": f"projects/nova/long.md#{idx}",
                        "path": f"projects/nova/long-{idx}.md",
                        "doc": "## Fact\n" + ("very long context " * 80),
                        "distance": 0.1 + (idx * 0.01),
                        "meta": {"id": f"projects/nova/long.md#{idx}", "path": f"projects/nova/long-{idx}.md", "section": "Fact", "memory_type": "fact", "chunk_index": idx},
                    }
                    for idx in range(8)
                ]

            context_resolve.semantic_search = fake_search
            result = asyncio.run(context_resolve.execute({"query": "nova", "token_budget": 300, "dedupe": "none"}, root))
            payload = json.loads(result[0].text)
        finally:
            context_resolve.semantic_search = original_search
            os.environ.clear()
            os.environ.update(original_env)
            tempdir.cleanup()

        self.assertTrue(payload["budget"]["applied"])
        self.assertLessEqual(payload["budget"]["estimated_tokens"], payload["token_budget"])
        self.assertLess(len(payload["context_items"]), 8)

    def test_context_resolve_returns_structured_context_pack(self):
        original_search = context_resolve.semantic_search
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
                        "path": "projects/nova/decisions.md",
                        "doc": "## Decision\nNOVA stays a memory/context system.",
                        "distance": 0.1,
                        "meta": {
                            "path": "projects/nova/decisions.md",
                            "section": "Decision",
                            "line_start": 10,
                            "line_end": 12,
                            "memory_type": "decision",
                        },
                    },
                    {
                        "path": "projects/nova/questions.md",
                        "doc": "## Open Questions\nWhich FTS backend should be default?",
                        "distance": 0.2,
                        "meta": {
                            "path": "projects/nova/questions.md",
                            "section": "Open Questions",
                            "line_start": 4,
                            "line_end": 5,
                            "memory_type": "question",
                        },
                    },
                    {
                        "path": "projects/nova/constraints.md",
                        "doc": "## Constraints\nIndexes are rebuildable artifacts.",
                        "distance": 0.25,
                        "meta": {
                            "path": "projects/nova/constraints.md",
                            "section": "Constraints",
                            "line_start": 1,
                            "line_end": 2,
                            "memory_type": "constraint",
                        },
                    },
                ]

            context_resolve.semantic_search = fake_search
            result = asyncio.run(context_resolve.execute({"query": "nova architecture", "project_hint": "nova"}, root))
            payload = json.loads(result[0].text)

            self.assertEqual(payload["status"], "ok")
            self.assertIn("context_pack", payload)
            pack = payload["context_pack"]
            self.assertIn("NOVA stays", pack["summary"])
            self.assertEqual(pack["relevant_decisions"][0]["path"], "projects/nova/decisions.md")
            self.assertEqual(pack["open_questions"][0]["section"], "Open Questions")
            self.assertEqual(pack["constraints"][0]["line_start"], 1)
            self.assertTrue(pack["source_files"])
            self.assertTrue(pack["suggested_next_actions"])

            first_item = payload["context_items"][0]
            self.assertEqual(first_item["memory_type"], "decision")
            self.assertEqual(first_item["citation"]["line_start"], 10)
        finally:
            context_resolve.semantic_search = original_search
            os.environ.clear()
            os.environ.update(original_env)
            tempdir.cleanup()


if __name__ == "__main__":
    unittest.main()
