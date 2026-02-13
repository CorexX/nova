"""
Tool: Get Collections
Liefert Top-Level-Collections der Vault mit schnellen Kennzahlen.
"""

from pathlib import Path

from mcp.types import Tool, TextContent

from ..paths import resolve_paths


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_get_collections",
        description="Liefert Top-Level-Collections der Vault inkl. Note-Anzahl und Pfad.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    knowledge_root = resolve_paths(workspace_root).knowledge_root

    lines = ["# Collections\n"]

    if not knowledge_root.exists():
        lines.append(f"*Knowledge root nicht gefunden: `{knowledge_root}`*")
        return [TextContent(type="text", text="\n".join(lines))]

    collections = [
        d for d in sorted(knowledge_root.iterdir())
        if d.is_dir() and not d.name.startswith((".", "_"))
    ]

    if not collections:
        lines.append("*Keine Collections gefunden*")
        return [TextContent(type="text", text="\n".join(lines))]

    lines.append("| Collection | Notes (.md) | Subdirs | Path |")
    lines.append("|------------|-------------|---------|------|")
    for col in collections:
        note_count = len(list(col.rglob("*.md")))
        subdir_count = len(
            [d for d in col.rglob("*") if d.is_dir() and not d.name.startswith((".", "_"))]
        )
        rel = col.relative_to(knowledge_root).as_posix()
        lines.append(f"| `{col.name}` | {note_count} | {subdir_count} | `{rel}/` |")

    return [TextContent(type="text", text="\n".join(lines))]

