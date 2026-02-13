"""
Tool: Get Conventions
Liefert Datei-Konventionen (Naming, Formate).
Liest aus PRINCIPLES.md (Single Source of Truth).
"""

import re
from pathlib import Path
from mcp.types import Tool, TextContent
from ..paths import resolve_paths


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_get_conventions",
        description="Liefert Datei-Konventionen: Naming, Formate, WORKLOG-Syntax.",
        inputSchema={"type": "object", "properties": {}, "required": []}
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    principles_path = resolve_paths(workspace_root).principles_md
    
    if not principles_path.exists():
        return [TextContent(type="text", text="❌ PRINCIPLES.md nicht gefunden")]
    
    content = principles_path.read_text(encoding="utf-8")
    
    # Extrahiere "## Dateisystem-Prinzipien" bis zum nächsten "---"
    match = re.search(r"(## Dateisystem-Prinzipien.*?)(?=\n---)", content, re.DOTALL)
    
    if match:
        result = match.group(1).strip()
    else:
        result = "❌ Dateisystem-Prinzipien Sektion nicht gefunden in PRINCIPLES.md"
    
    return [TextContent(type="text", text=result)]
