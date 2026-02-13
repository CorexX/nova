"""
Tool: Summarize Week
MCP-Adapter für das summarize_week.py Skript.
"""

import asyncio
from pathlib import Path
from mcp.types import Tool, TextContent
from ..paths import resolve_paths


# =============================================================================
# TOOL DEFINITION
# =============================================================================

def get_tool_definition(workspace_root: Path) -> Tool:
    """Gibt die Tool-Definition zurück."""
    return Tool(
        name="nova_summarize_week",
        description="Fasst alle Copilot Sessions der letzten Woche zusammen. Zeigt Highlights, Projekte und Zeitverteilung.",
        inputSchema={
            "type": "object",
            "properties": {
                "last_week": {
                    "type": "boolean",
                    "description": "Letzte Woche statt aktuelle Woche",
                    "default": False
                },
                "days": {
                    "type": "integer",
                    "description": "Anzahl Tage zurück (statt Wochengrenzen)"
                },
                "from_date": {
                    "type": "string",
                    "description": "Startdatum im Format YYYY-MM-DD"
                },
                "to_date": {
                    "type": "string",
                    "description": "Enddatum im Format YYYY-MM-DD (default: heute)"
                },
                "llm": {
                    "type": "boolean",
                    "description": "Nutze LLM für intelligente Zusammenfassung",
                    "default": True
                },
                "raw": {
                    "type": "boolean",
                    "description": "Zeige rohe Statistiken als JSON",
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
    Führt summarize_week.py aus.
    
    Args:
        args: Tool-Argumente
        workspace_root: NOVA Workspace Root
        
    Returns:
        TextContent mit Ergebnis
    """
    script_path = resolve_paths(workspace_root).core_root / "skills" / "summarize_week.py"
    
    cmd = ["python", str(script_path)]
    
    if args.get("last_week"):
        cmd.append("--last")
    if args.get("days"):
        cmd.extend(["--days", str(args["days"])])
    if args.get("from_date"):
        cmd.extend(["--from", args["from_date"]])
    if args.get("to_date"):
        cmd.extend(["--to", args["to_date"]])
    if args.get("llm", True):  # Default True
        cmd.append("--llm")
    if args.get("raw"):
        cmd.append("--raw")
    
    # Async subprocess
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    
    output = stdout.decode() + stderr.decode()
    
    return [TextContent(type="text", text=output or "No output")]
