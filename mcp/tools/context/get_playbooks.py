"""
Tool: Get Playbooks
Liefert verfügbare Playbooks mit Triggern live aus playbooks/.
"""

from pathlib import Path
from mcp.types import Tool, TextContent
import re
from ..paths import resolve_paths


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_get_playbooks",
        description="Liefert alle verfügbaren Playbooks mit Triggern.",
        inputSchema={"type": "object", "properties": {}, "required": []}
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    playbooks_path = resolve_paths(workspace_root).core_root / "playbooks"
    
    lines = ["# Playbooks\n"]
    lines.append("| Playbook | Trigger |")
    lines.append("|----------|---------|")
    
    if playbooks_path.exists():
        for pb in sorted(playbooks_path.glob("*.md")):
            content = pb.read_text(encoding="utf-8")
            
            # Versuche Trigger aus ## Trigger Sektion zu extrahieren
            trigger = "—"
            trigger_match = re.search(r"## Trigger\s*\n([\s\S]*?)(?=\n##|\Z)", content)
            if trigger_match:
                trigger_text = trigger_match.group(1).strip()
                # Extrahiere erste Zeile oder Bullet Points
                trigger_lines = [l.strip("- ").strip() for l in trigger_text.split("\n") if l.strip()]
                if trigger_lines:
                    trigger = ", ".join(trigger_lines[:2])  # Max 2 Trigger
            
            lines.append(f"| `{pb.name}` | {trigger} |")
    else:
        lines.append("| — | *Keine Playbooks gefunden* |")
    
    lines.append("\nPfad: `nova-core/playbooks/`")
    
    return [TextContent(type="text", text="\n".join(lines))]
