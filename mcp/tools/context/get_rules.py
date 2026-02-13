"""
Tool: Get Rules
Liefert die 8 Kernprinzipien des NOVA-Agents aus PRINCIPLES.md.
"""

import re
from pathlib import Path
from mcp.types import Tool, TextContent
from ..paths import resolve_paths


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_get_rules",
        description="Liefert die 8 Kernprinzipien des NOVA-Agents. Rufe am Session-Start auf.",
        inputSchema={"type": "object", "properties": {}, "required": []}
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    principles_path = resolve_paths(workspace_root).principles_md
    
    if not principles_path.exists():
        return [TextContent(type="text", text="❌ PRINCIPLES.md nicht gefunden")]
    
    content = principles_path.read_text(encoding="utf-8")
    
    # Extrahiere alles von "## Kernprinzipien" bis "---"
    match = re.search(r"(## Kernprinzipien.*?)(?=\n---)", content, re.DOTALL)
    
    if match:
        result = match.group(1).strip()
    else:
        result = "❌ Kernprinzipien-Sektion nicht gefunden"
    
    return [TextContent(type="text", text=result)]
