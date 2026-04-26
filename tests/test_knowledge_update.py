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

from tools import knowledge_update


class KnowledgeUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.knowledge = self.root / "knowledge-root"
        self.knowledge.mkdir()
        self.original_env = dict(os.environ)
        os.environ["NOVA_KNOWLEDGE_ROOT"] = str(self.knowledge)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)
        self.tempdir.cleanup()

    def _execute(self, args):
        result = asyncio.run(knowledge_update.execute(args, self.root))
        return json.loads(result[0].text)

    def test_dry_run_returns_proposed_write_without_touching_files(self):
        payload = self._execute({
            "content": "NOVA write API should support dry runs.",
            "source": "unit-test",
            "project": "nova",
            "topic": "write-safety",
            "title": "Dry Run",
            "confidence": 0.8,
            "memory_type": "decision",
            "scope": "project",
            "mode": "dry_run",
        })

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["mode"], "dry_run")
        self.assertEqual(payload["written_paths"], [])
        self.assertEqual(len(payload["would_write_paths"]), 1)
        proposed_path = Path(payload["would_write_paths"][0])
        self.assertEqual(proposed_path.parent, self.knowledge / "knowledge")
        self.assertTrue(proposed_path.name.endswith("-write-safety.md"))
        self.assertFalse((self.knowledge / "knowledge").exists())
        self.assertFalse(payload["index_stale"])
        self.assertEqual(payload["entry"]["memory_type"], "decision")
        self.assertEqual(payload["entry"]["scope"], "project")
        self.assertEqual(payload["entry"]["confidence"], 0.8)

    def test_append_writes_structured_metadata_and_reports_index_stale(self):
        payload = self._execute({
            "content": "Append mode writes durable memory.",
            "source": "unit-test",
            "project": "nova",
            "topic": "write-safety",
            "title": "Append Metadata",
            "confidence": 0.75,
            "memory_type": "fact",
            "scope": "project",
            "mode": "append",
        })

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["mode"], "append")
        self.assertTrue(payload["index_stale"])
        self.assertEqual(payload["recommended_maintenance"], {"operation": "index", "force": False})
        note_path = Path(payload["written_paths"][0])
        self.assertTrue(note_path.exists())
        text = note_path.read_text(encoding="utf-8")
        self.assertIn("entry_id:", text)
        self.assertIn("memory_type: fact", text)
        self.assertIn("scope: project", text)
        self.assertIn("status: active", text)
        self.assertIn("observed_at:", text)
        self.assertIn("### Insight", text)
        self.assertIn("Append mode writes durable memory.", text)

    def test_target_path_must_stay_inside_knowledge_root(self):
        payload = self._execute({
            "content": "Should not write outside vault.",
            "source": "unit-test",
            "target_path": "../escape.md",
            "mode": "append",
        })

        self.assertEqual(payload["status"], "error")
        self.assertIn("target_path", payload["message"])
        self.assertEqual(payload["written_paths"], [])

    def test_invalid_memory_type_and_scope_are_rejected(self):
        payload = self._execute({
            "content": "Bad metadata.",
            "source": "unit-test",
            "memory_type": "runtime",
            "scope": "cron",
        })

        self.assertEqual(payload["status"], "error")
        self.assertIn("memory_type", payload["validation_errors"])
        self.assertIn("scope", payload["validation_errors"])

    def test_propose_patch_creates_reviewable_patch_without_modifying_target(self):
        target = self.knowledge / "curated" / "memory.md"
        target.parent.mkdir(parents=True)
        target.write_text("# Existing\n", encoding="utf-8")

        payload = self._execute({
            "content": "Patch proposal should be reviewable.",
            "source": "unit-test",
            "target_path": "curated/memory.md",
            "topic": "curation",
            "title": "Patch Proposal",
            "memory_type": "decision",
            "scope": "project",
            "mode": "propose_patch",
        })

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["mode"], "propose_patch")
        self.assertEqual(payload["written_paths"], [])
        self.assertEqual(target.read_text(encoding="utf-8"), "# Existing\n")
        patch_path = Path(payload["proposed_patch_path"])
        self.assertTrue(patch_path.exists())
        patch_text = patch_path.read_text(encoding="utf-8")
        self.assertIn("*** Begin Patch", patch_text)
        self.assertIn("*** Update File:", patch_text)
        self.assertIn("Patch proposal should be reviewable.", patch_text)


if __name__ == "__main__":
    unittest.main()
