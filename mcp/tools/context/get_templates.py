"""
Tool: Get Templates
Liefert verfügbare Templates live aus _template/ Ordnern.
"""

from pathlib import Path
from mcp.types import Tool, TextContent
from ..paths import resolve_paths


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_get_templates",
        description="Liefert alle verfügbaren Templates für Kunden, Sideprojects, etc.",
        inputSchema={"type": "object", "properties": {}, "required": []}
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    knowledge_path = resolve_paths(workspace_root).knowledge_root
    
    lines = ["# Templates\n"]
    lines.append("| Template | Pfad | Inhalt |")
    lines.append("|----------|------|--------|")
    
    templates_found = False
    
    if knowledge_path.exists():
        for template_dir in knowledge_path.rglob("_template"):
            if template_dir.is_dir():
                templates_found = True
                parent = template_dir.parent.name
                rel_path = template_dir.relative_to(knowledge_path)
                
                # Liste Dateien im Template
                files = [f.name for f in template_dir.iterdir() if f.is_file()]
                content = ", ".join(files[:3]) if files else "—"
                
                lines.append(f"| {parent} | `{rel_path}/` | {content} |")
    
    if not templates_found:
        lines.append("| — | — | *Keine Templates gefunden* |")
    
    return [TextContent(type="text", text="\n".join(lines))]
