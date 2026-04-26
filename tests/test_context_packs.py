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

from mcp.tools import context_resolve, memory_maintain


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


class ContextPackTests(unittest.TestCase):
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
