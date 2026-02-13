"""
Tool: Git Push Repos
Pushed alle Git-Repos in einem Workspace.
"""

from pathlib import Path
from mcp.types import Tool, TextContent
from tools.utils.subprocess_utils import run_async
from ..paths import resolve_paths


# =============================================================================
# TOOL DEFINITION
# =============================================================================

def get_tool_definition(workspace_root: Path) -> Tool:
    """Gibt die Tool-Definition zurück."""
    return Tool(
        name="nova_git_push_repos",
        description="Pushed alle Git-Repos in einem Workspace. Staged, committed (falls nötig) und pushed.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Workspace-Pfad (default: NOVA workspace root)",
                    "default": str(workspace_root)
                },
                "message": {
                    "type": "string",
                    "description": "Commit-Message für uncommitted changes (optional)"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Zeige was gepusht würde ohne zu pushen",
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
    Führt git_push_repos.py aus.
    
    Args:
        args: Tool-Argumente (path, message, dry_run)
        workspace_root: NOVA Workspace Root
        
    Returns:
        TextContent mit Ergebnis
    """
    script_path = resolve_paths(workspace_root).core_root / "skills" / "git_push_repos.py"
    path = args.get("path", str(workspace_root))
    message = args.get("message")
    dry_run = args.get("dry_run", False)
    
    cmd = ["python", str(script_path), path]
    if message:
        cmd.extend(["-m", message])
    if dry_run:
        cmd.append("--dry-run")
    
    result = await run_async(cmd, timeout=120)
    
    if result.timed_out:
        return [TextContent(type="text", text=f"❌ TIMEOUT: Git push abgebrochen nach 120s")]
    
    if result.error:
        return [TextContent(type="text", text=f"❌ ERROR: {result.error}")]
    
    output = result.output
    
    return [TextContent(type="text", text=output or "No output")]
