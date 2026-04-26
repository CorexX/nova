import asyncio
import hashlib
import json
import os
import subprocess
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

from tools import memory_maintain


class MemoryValidateTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.knowledge = self.root / "knowledge-root"
        self.index = self.root / ".nova" / "index"
        self.knowledge.mkdir()
        self.index.mkdir(parents=True)
        self.original_env = dict(os.environ)
        os.environ["NOVA_KNOWLEDGE_ROOT"] = str(self.knowledge)
        os.environ["NOVA_INDEX_ROOT"] = str(self.index)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)
        self.tempdir.cleanup()

    def _validate(self):
        result = asyncio.run(memory_maintain.execute({"operation": "validate"}, self.root))
        return json.loads(result[0].text)

    def _write_index(self, items):
        (self.index / "semantic_index.json").write_text(
            json.dumps({"version": 1, "updated_at": "2026-01-01T00:00:00+00:00", "model": "test", "items": items}),
            encoding="utf-8",
        )

    def _write_hashes(self, mapping):
        (self.index / "file_hashes.json").write_text(json.dumps(mapping), encoding="utf-8")

    def test_validate_ok_for_consistent_index_and_hashes(self):
        note = self.knowledge / "note.md"
        note.write_text("# Note\n\nUseful fact.\n", encoding="utf-8")
        rel = note.relative_to(self.root).as_posix()
        self._write_hashes({rel: hashlib.md5(note.read_text(encoding="utf-8").encode("utf-8")).hexdigest()})
        self._write_index([
            {
                "id": f"{rel}#0",
                "path": rel,
                "section": "Note",
                "line_start": 1,
                "line_end": 3,
                "memory_type": "fact",
                "chunk_index": 0,
                "text": "# Note\n\nUseful fact.",
                "embedding": [0.1, 0.2, 0.3],
            }
        ])

        payload = self._validate()

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["details"]["problems"], [])
        self.assertEqual(payload["details"]["stats"]["indexed_chunks"], 1)
        self.assertEqual(payload["details"]["stats"]["embedding_dimensions"], [3])

    def test_validate_reports_index_schema_hash_and_metadata_problems(self):
        note = self.knowledge / "note.md"
        note.write_text("# Note\n\nChanged content.\n", encoding="utf-8")
        rel = note.relative_to(self.root).as_posix()
        self._write_hashes({rel: "stale-hash", "missing.md": "deadbeef"})
        self._write_index([
            {
                "id": "dup-id",
                "path": rel,
                "section": "Note",
                "line_start": 1,
                "line_end": 3,
                "memory_type": "fact",
                "chunk_index": 0,
                "text": "# Note",
                "embedding": [0.1, 0.2],
            },
            {
                "id": "dup-id",
                "path": rel,
                "section": "Bad",
                "line_start": 4,
                "line_end": 5,
                "memory_type": "runtime",
                "chunk_index": 1,
                "text": "bad type",
                "embedding": [0.1, 0.2, 0.3],
            },
            {
                "id": "missing-fields",
                "path": "ghost.md",
                "memory_type": "fact",
                "embedding": [],
            },
        ])

        payload = self._validate()

        self.assertEqual(payload["status"], "warn")
        codes = {problem["code"] for problem in payload["details"]["problems"]}
        self.assertIn("duplicate_chunk_id", codes)
        self.assertIn("invalid_memory_type", codes)
        self.assertIn("missing_required_field", codes)
        self.assertIn("invalid_embedding", codes)
        self.assertIn("inconsistent_embedding_dimension", codes)
        self.assertIn("stale_file_hash", codes)
        self.assertIn("hash_for_missing_file", codes)
        self.assertIn("indexed_file_missing", codes)

    def test_validate_reports_invalid_lifecycle_status_in_index_text(self):
        note = self.knowledge / "note.md"
        note.write_text("# Note\n\n- status: maybe\n", encoding="utf-8")
        rel = note.relative_to(self.root).as_posix()
        self._write_hashes({rel: hashlib.md5(note.read_text(encoding="utf-8").encode("utf-8")).hexdigest()})
        self._write_index([
            {
                "id": f"{rel}#0",
                "path": rel,
                "section": "Note",
                "line_start": 1,
                "line_end": 3,
                "memory_type": "fact",
                "chunk_index": 0,
                "text": "# Note\n\n- status: maybe",
                "embedding": [0.1, 0.2],
            }
        ])

        payload = self._validate()

        codes = {problem["code"] for problem in payload["details"]["problems"]}
        self.assertEqual(payload["status"], "warn")
        self.assertIn("invalid_lifecycle_status", codes)

    def test_validate_warns_when_generated_index_artifacts_are_tracked_by_git(self):
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.root, check=True)
        note = self.knowledge / "note.md"
        note.write_text("# Note\n", encoding="utf-8")
        rel = note.relative_to(self.root).as_posix()
        self._write_hashes({rel: hashlib.md5(note.read_text(encoding="utf-8").encode("utf-8")).hexdigest()})
        self._write_index([
            {
                "id": f"{rel}#0",
                "path": rel,
                "section": "Note",
                "line_start": 1,
                "line_end": 1,
                "memory_type": "fact",
                "chunk_index": 0,
                "text": "# Note",
                "embedding": [0.1, 0.2],
            }
        ])
        subprocess.run(["git", "add", ".nova/index/semantic_index.json"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "track generated index"], cwd=self.root, check=True, stdout=subprocess.DEVNULL)

        payload = self._validate()

        codes = {problem["code"] for problem in payload["details"]["problems"]}
        self.assertEqual(payload["status"], "warn")
        self.assertIn("generated_artifact_tracked", codes)

    def test_index_operation_rebuilds_sqlite_fts_index(self):
        original_encoder = memory_maintain.batch_encode_texts
        try:
            note = self.knowledge / "commands.md"
            note.write_text("# Commands\n\nRun exact ticket lookup with SQLite FTS.\n", encoding="utf-8")

            def fake_encode(texts):
                return [[1.0, 0.0] for _ in texts]

            memory_maintain.batch_encode_texts = fake_encode
            result = asyncio.run(memory_maintain.execute({"operation": "index", "force": True}, self.root))
            payload = json.loads(result[0].text)
        finally:
            memory_maintain.batch_encode_texts = original_encoder

        self.assertEqual(payload["status"], "ok")
        sqlite_index_file = Path(payload["details"]["sqlite_index_file"])
        self.assertTrue(sqlite_index_file.exists())

        from tools.index_store import full_text_search

        matches = full_text_search(self.index, "exact ticket lookup", limit=3)
        self.assertEqual([match["path"] for match in matches], ["knowledge-root/commands.md"])


if __name__ == "__main__":
    unittest.main()
