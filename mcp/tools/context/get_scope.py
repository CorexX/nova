"""
Tool: Get Scope
Liefert den Schreib-Scope - was der Agent darf und was nicht.
Liest aus PRINCIPLES.md (Single Source of Truth).
"""

import re
from pathlib import Path
from mcp.types import Tool, TextContent
from ..paths import resolve_paths


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_get_scope",
        description="Liefert den Schreib-Scope: Was darfst du schreiben, was nicht?",
        inputSchema={"type": "object", "properties": {}, "required": []}
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    principles_path = resolve_paths(workspace_root).principles_md
    
    if not principles_path.exists():
        return [TextContent(type="text", text="❌ PRINCIPLES.md nicht gefunden")]
    
    content = principles_path.read_text(encoding="utf-8")
    
    # Extrahiere "## Schreib-Scope" bis zum nächsten "---"
    match = re.search(r"(## Schreib-Scope.*?)(?=\n---)", content, re.DOTALL)
    
    if match:
        result = match.group(1).strip()
    else:
        result = "❌ Schreib-Scope Sektion nicht gefunden in PRINCIPLES.md"
    
    return [TextContent(type="text", text=result)]
