"""
Tool: Run Tests
Führt pytest für die MCP Tool-Tests aus.

KEEP IT SIMPLE: Standardmäßig nur schnelle Tests (-q --tb=short).
"""

import sys
import time
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
        name="nova_run_tests",
        description="Führt pytest für MCP Tool-Tests aus. Zeigt Testergebnisse.",
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Test-Pattern (z.B. 'test_worklog' für spezifische Tests)",
                    "default": ""
                },
                "verbose": {
                    "type": "boolean",
                    "description": "Ausführliche Ausgabe (-v statt -q)",
                    "default": False
                },
                "failfast": {
                    "type": "boolean",
                    "description": "Stoppe beim ersten Fehler (-x Flag)",
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
    Führt pytest aus.
    
    Args:
        args: Tool-Argumente (pattern, verbose, failfast)
        workspace_root: NOVA Workspace Root
        
    Returns:
        TextContent mit Test-Ergebnissen
    """
    start = time.time()
    
    mcp_path = resolve_paths(workspace_root).core_root / "mcp"
    tests_path = mcp_path / "tools" / "tests"
    
    # KEEP IT SIMPLE: -q --tb=short als Standard für schnelle Ausgabe
    cmd = ["python", "-m", "pytest", str(tests_path), "-q", "--tb=short"]
    
    if args.get("verbose", False):
        # Ersetze -q durch -v für verbose
        cmd = ["python", "-m", "pytest", str(tests_path), "-v", "--tb=short"]
    
    if args.get("failfast", False):
        cmd.append("-x")
    
    pattern = args.get("pattern", "")
    if pattern:
        cmd.extend(["-k", pattern])
    
    # Progress-Log nach stderr (erscheint in VS Code MCP Output)
    print(f"[nova_run_tests] Starting pytest...", file=sys.stderr)
    print(f"[nova_run_tests] Pattern: {pattern or 'all'}", file=sys.stderr)
    
    # Run pytest with timeout
    result = await run_async(cmd, cwd=str(mcp_path), timeout=60)
    
    elapsed = time.time() - start
    print(f"[nova_run_tests] Completed in {elapsed:.1f}s", file=sys.stderr)
    
    if result.timed_out:
        return [TextContent(
            type="text",
            text=f"⏱️ **TIMEOUT** nach 60 Sekunden\n\nPattern: `{pattern or 'all'}`"
        )]
    
    if result.error:
        return [TextContent(
            type="text",
            text=f"❌ **ERROR**\n\n{result.error}"
        )]
    
    output = result.stdout.strip()
    
    # Kompakte Ausgabe: Nur letzte Zeile (Summary) + Fehler falls vorhanden
    lines = output.split('\n')
    summary_line = lines[-1] if lines else "No output"
    
    if result.success:
        return [TextContent(
            type="text", 
            text=f"✅ **{summary_line}** ({elapsed:.1f}s)"
        )]
    else:
        # Bei Fehlern: Zeige Fehlerdetails
        return [TextContent(
            type="text", 
            text=f"❌ **FAILED** ({elapsed:.1f}s)\n\n```\n{output}\n```"
        )]
