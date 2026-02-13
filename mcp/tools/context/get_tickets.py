"""
Tool: Get Tickets
Liefert TICKETS.md - aktive Tickets mit Budgets.
"""

from pathlib import Path
from mcp.types import Tool, TextContent
from ..paths import resolve_paths


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_get_tickets",
        description="Liefert TICKETS.md - aktive Tickets mit Zeitbudgets.",
        inputSchema={"type": "object", "properties": {}, "required": []}
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    tickets_path = resolve_paths(workspace_root).tickets_md
    
    if tickets_path.exists():
        content = tickets_path.read_text(encoding="utf-8")
        return [TextContent(type="text", text=content)]
    else:
        return [TextContent(type="text", text="*TICKETS.md nicht gefunden*")]
