"""
Tool: Get Guides
Liefert verfügbare Guides live aus guides/.
"""

from pathlib import Path
from mcp.types import Tool, TextContent
from ..paths import resolve_paths


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_get_guides",
        description="Liefert alle verfügbaren Guides (How-Tos).",
        inputSchema={"type": "object", "properties": {}, "required": []}
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    guides_path = resolve_paths(workspace_root).core_root / "guides"
    
    lines = ["# Guides\n"]
    lines.append("| Guide | Beschreibung |")
    lines.append("|-------|--------------|")
    
    if guides_path.exists():
        for guide in sorted(guides_path.glob("*.md")):
            # Lese erste Zeile nach # für Beschreibung
            content = guide.read_text(encoding="utf-8")
            desc = "—"
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith(">"):
                    desc = line.lstrip("> ").strip()
                    break
            
            lines.append(f"| `{guide.name}` | {desc[:50]} |")
    else:
        lines.append("| — | *Keine Guides gefunden* |")
    
    lines.append("\nPfad: `nova-core/guides/`")
    
    return [TextContent(type="text", text="\n".join(lines))]
