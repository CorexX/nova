"""
Tool: Get Paths
Liefert zentrale NOVA-Pfade fuer schnelle Navigation.
"""

from pathlib import Path

from mcp.types import Tool, TextContent

from ..paths import resolve_paths


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_get_paths",
        description="Liefert zentrale NOVA-Pfade (core, knowledge, index, key files).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    p = resolve_paths(workspace_root)

    lines = [
        "# NOVA Paths",
        "",
        "| Key | Path |",
        "|-----|------|",
        f"| `core_root` | `{p.core_root}` |",
        f"| `knowledge_root` | `{p.knowledge_root}` |",
        f"| `index_root` | `{p.index_root}` |",
        f"| `chroma_path` | `{p.chroma_path}` |",
        f"| `CORE.md` | `{p.core_md}` |",
        f"| `PRINCIPLES.md` | `{p.principles_md}` |",
        f"| `CURRENT.md` | `{p.current_md}` |",
        f"| `TICKETS.md` | `{p.tickets_md}` |",
        f"| `WORKLOG.md` | `{p.worklog_md}` |",
    ]

    return [TextContent(type="text", text="\n".join(lines))]

