"""
Tool: Summarize Day
MCP-Adapter für das summarize_day.py Skript.

Nutzt direkten Import statt Subprocess für bessere Performance.
"""

import sys
import time
from pathlib import Path
from mcp.types import Tool, TextContent

# Add skills to path for direct import
skills_path = Path(__file__).parent.parent.parent.parent / "skills"
if str(skills_path) not in sys.path:
    sys.path.insert(0, str(skills_path))


# =============================================================================
# TOOL DEFINITION
# =============================================================================

def get_tool_definition(workspace_root: Path) -> Tool:
    """Gibt die Tool-Definition zurück."""
    return Tool(
        name="nova_summarize_day",
        description="Fasst alle Copilot Sessions des Tages zusammen für das WORKLOG. Mit LLM-Option für detaillierte Zusammenfassung.",
        inputSchema={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Datum im Format YYYY-MM-DD (default: heute)"
                },
                "llm": {
                    "type": "boolean",
                    "description": "Nutze LLM für intelligente Zusammenfassung mit Erkenntnissen und offenen Punkten",
                    "default": False
                },
                "close_day": {
                    "type": "boolean",
                    "description": "Tagesabschluss mit Ticket-Zuordnung und Zeitbuchungsvorschlag",
                    "default": False
                },
                "worklog": {
                    "type": "boolean",
                    "description": "Generiere einfaches WORKLOG-Format",
                    "default": False
                },
                "raw": {
                    "type": "boolean",
                    "description": "Zeige rohe Session-Daten als JSON",
                    "default": False
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
    Führt summarize_day direkt aus (kein Subprocess).
    
    Args:
        args: Tool-Argumente (date, worklog, raw, llm, close_day)
        workspace_root: NOVA Workspace Root
        
    Returns:
        TextContent mit Ergebnis
    """
    from datetime import datetime, date
    import json
    
    start = time.time()
    
    try:
        # Direct import from skills
        import summarize_day as sd
        
        # Parse date
        if args.get("date"):
            target_date = datetime.strptime(args["date"], "%Y-%m-%d").date()
        else:
            target_date = date.today()
        
        # Get sessions
        session_files = sd.get_session_files(target_date)
        
        if not session_files:
            output = f"Keine Sessions gefunden für {target_date}"
        else:
            sessions = [sd.parse_session_file(f) for f in session_files]
            
            if args.get("raw"):
                output = json.dumps(sessions, indent=2, default=str)
            elif args.get("worklog"):
                output = sd.generate_worklog_entry(sessions, target_date)
            elif args.get("close_day"):
                output = sd.close_day_with_llm(sessions, target_date, session_files)
            elif args.get("llm"):
                output = sd.summarize_with_llm(sessions, target_date, session_files)
            else:
                output = sd.summarize_sessions(sessions)
            
        elapsed = time.time() - start
        print(f"[MCP summarize_day] Completed in {elapsed:.2f}s", file=sys.stderr)
        
    except Exception as e:
        import traceback
        elapsed = time.time() - start
        output = f"Fehler nach {elapsed:.2f}s: {e}\n{traceback.format_exc()}"
        print(f"[MCP summarize_day] ERROR: {e}", file=sys.stderr)
    
    return [TextContent(type="text", text=output or "No output")]
