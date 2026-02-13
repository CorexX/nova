"""
Tool: Get Architecture
Liefert eine context-sparende Zusammenfassung der NOVA-Architektur.

Liest aus nova-core/meta/ARCHITECTURE.md:
- Kompakt: Extrahiert den <!-- COMPACT_START --> bis <!-- COMPACT_END --> Bereich
- Full: Gibt die komplette Datei zurück
- Section: Sucht nach ## [Sektionsname] und gibt diesen Abschnitt zurück
"""

from pathlib import Path
from mcp.types import Tool, TextContent
from ..paths import resolve_paths

# Import des Skills
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "skills"))
from get_architecture import get_architecture


# =============================================================================
# TOOL DEFINITION
# =============================================================================

def get_tool_definition(workspace_root: Path) -> Tool:
    """Gibt die Tool-Definition zurück."""
    return Tool(
        name="nova_get_architecture",
        description=(
            "Liefert eine context-sparende Zusammenfassung der NOVA-Architektur. "
            "Liest aus ARCHITECTURE.md. Standardmäßig kompakt (~40 Zeilen). "
            "Nutze section für spezifische Themen wie 'Design-Prinzipien' oder 'Komponenten'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "description": "Nur bestimmte Sektion laden (z.B. 'Design-Prinzipien', 'Komponenten', 'Sicherheit')"
                },
                "full": {
                    "type": "boolean",
                    "description": "Komplette ARCHITECTURE.md ausgeben (mehr Context, ~800 Zeilen)"
                }
            },
            "required": []
        }
    )


# =============================================================================
# TOOL IMPLEMENTATION
# =============================================================================

async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    """
    Gibt Architektur-Zusammenfassung zurück.
    
    Args:
        args: Tool-Argumente (section, full)
        workspace_root: NOVA Workspace Root
        
    Returns:
        TextContent mit Architektur-Übersicht
    """
    section = args.get("section")
    full = args.get("full", False)
    
    # Pfad zur ARCHITECTURE.md
    architecture_path = resolve_paths(workspace_root).core_root / "meta" / "ARCHITECTURE.md"
    
    result = get_architecture(full=full, section=section, architecture_path=architecture_path)
    
    return [TextContent(type="text", text=result)]
