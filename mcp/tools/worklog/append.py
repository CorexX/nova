"""
Tool: Worklog Append
Fügt einen Eintrag zum WORKLOG.md hinzu (append-only).
"""

from datetime import datetime
from pathlib import Path
from mcp.types import Tool, TextContent
from ..paths import resolve_paths


# =============================================================================
# TOOL DEFINITION
# =============================================================================

def get_tool_definition(workspace_root: Path) -> Tool:
    """Gibt die Tool-Definition zurück."""
    return Tool(
        name="nova_worklog_append",
        description="Fügt einen Eintrag zum WORKLOG.md hinzu (append-only).",
        inputSchema={
            "type": "object",
            "properties": {
                "entry": {
                    "type": "string",
                    "description": "Der Eintrag (z.B. '- 10:30 Meeting mit Kunde X (PROJ-123)')"
                },
                "time": {
                    "type": "string",
                    "description": "Zeitstempel HH:MM (optional, default: jetzt)"
                },
                "ticket": {
                    "type": "string",
                    "description": "Ticket-ID (optional, z.B. 'PROJ-123')"
                }
            },
            "required": ["entry"]
        }
    )


# =============================================================================
# TOOL IMPLEMENTATION
# =============================================================================

async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    """
    Fügt Eintrag zum WORKLOG hinzu.
    
    Args:
        args: Tool-Argumente (entry, time, ticket)
        workspace_root: NOVA Workspace Root
        
    Returns:
        TextContent mit Bestätigung
    """
    worklog_path = resolve_paths(workspace_root).worklog_md
    
    entry = args.get("entry", "")
    time_str = args.get("time") or datetime.now().strftime("%H:%M")
    ticket = args.get("ticket", "")
    
    # Format entry
    if not entry.startswith("-"):
        entry = f"- {entry}"
    if time_str and not entry.startswith(f"- {time_str}"):
        entry = f"- {time_str} {entry.lstrip('- ')}"
    if ticket and ticket not in entry:
        entry = f"{entry} ({ticket})"
    
    # Append to file
    with open(worklog_path, "a", encoding="utf-8") as f:
        f.write(f"\n{entry}")
    
    return [TextContent(type="text", text=f"Appended to WORKLOG.md:\n{entry}")]
