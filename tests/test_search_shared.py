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

from tools import search_shared


class SemanticIndexSearchTests(unittest.TestCase):
    def test_search_from_semantic_index_preserves_chunk_metadata(self):
        with tempfile.TemporaryDirectory() as tempdir:
            index_file = Path(tempdir) / "semantic_index.json"
            index_file.write_text(
                """{
  "version": 1,
  "model": "test-model",
  "items": [
    {
      "id": "projects/nova/decisions.md#2",
      "path": "projects/nova/decisions.md",
      "section": "Decision",
      "line_start": 10,
      "line_end": 12,
      "memory_type": "decision",
      "chunk_index": 2,
      "text": "## Decision\\nNOVA stays memory-only.",
      "embedding": [1.0, 0.0]
    }
  ]
}
""",
                encoding="utf-8",
            )

            results = search_shared._search_from_semantic_index(index_file, [1.0, 0.0], 1)

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result["path"], "projects/nova/decisions.md")
        self.assertEqual(result["id"], "projects/nova/decisions.md#2")
        self.assertEqual(result["doc"], "## Decision\nNOVA stays memory-only.")
        self.assertAlmostEqual(result["distance"], 0.0)
        self.assertEqual(result["meta"]["id"], "projects/nova/decisions.md#2")
        self.assertEqual(result["meta"]["section"], "Decision")
        self.assertEqual(result["meta"]["line_start"], 10)
        self.assertEqual(result["meta"]["line_end"], 12)
        self.assertEqual(result["meta"]["memory_type"], "decision")
        self.assertEqual(result["meta"]["chunk_index"], 2)


if __name__ == "__main__":
    unittest.main()
