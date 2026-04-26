from pathlib import Path
import ast
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MemorySurfaceTests(unittest.TestCase):
    def test_server_exposes_only_memory_context_tools_by_source(self):
        source = ROOT.joinpath("mcp/nova_mcp_core_server.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        tools_assign = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "TOOLS":
                        tools_assign = node.value
                        break
        self.assertIsNotNone(tools_assign)
        self.assertIsInstance(tools_assign, ast.Dict)
        tool_names = sorted(k.value for k in tools_assign.keys if isinstance(k, ast.Constant))

        self.assertEqual(tool_names, [
            "nova_context_resolve",
            "nova_knowledge_query",
            "nova_knowledge_update",
            "nova_memory_maintain",
        ])
        self.assertIn('Server("nova-memory")', source)

    def test_repository_no_longer_contains_runtime_assets(self):
        removed_paths = [
            "launcher.py",
            "setup.py",
            "skills",
            "playbooks",
            "templates/personas",
            ".github/copilot-instructions.md",
            ".nova-index/chroma/chroma.sqlite3",
        ]

        for rel in removed_paths:
            self.assertFalse(ROOT.joinpath(rel).exists(), rel)

    def test_readme_declares_nova_2_memory_context_boundary(self):
        readme = ROOT.joinpath("README.md").read_text(encoding="utf-8")

        self.assertIn("NOVA 2.0", readme)
        self.assertIn("Memory / Context System", readme)
        self.assertIn("Operator", readme)
        self.assertIn("Knowledge Base", readme)
        self.assertIn("NOVA is not an agent runtime", readme)


if __name__ == "__main__":
    unittest.main()
