"""
Tool: Get Current
Liefert CURRENT.md - den aktuellen Fokus.
"""

from pathlib import Path
from mcp.types import Tool, TextContent
from ..paths import resolve_paths


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_get_current",
        description="Liefert CURRENT.md - was ist der aktuelle Fokus?",
        inputSchema={"type": "object", "properties": {}, "required": []}
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    current_path = resolve_paths(workspace_root).current_md
    
    if current_path.exists():
        content = current_path.read_text(encoding="utf-8")
        return [TextContent(type="text", text=content)]
    else:
        return [TextContent(type="text", text="*CURRENT.md nicht gefunden*")]
