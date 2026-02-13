"""
Tool: Health Check
Detaillierter System-Status Report für NOVA.

Zeigt Status aller Subsysteme in 5 Gruppen:
- CORE: MCP Tools, Python, Core Files
- VAULT: Collections, Notes, WORKLOG, TICKETS
- SEARCH: Embedding Model, Vault Index
- CONTENT: Playbooks, Guides, Skills, Templates
- TODAY: Worklog Einträge, CURRENT Freshness
"""

from pathlib import Path
from mcp.types import Tool, TextContent

from .checks import (
    run_grouped_checks,
    get_actions_from_groups,
    format_grouped_simple,
)


def get_tool_definition(workspace_root: Path) -> Tool:
    """Gibt die Tool-Definition zurück."""
    return Tool(
        name="nova_health_check",
        description=(
            "Detaillierter System-Status Report. Zeigt Vault-Index, Model-Status, "
            "Worklog, CURRENT.md Freshness und Git Status."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    """Führt detaillierten Health Check aus mit gruppierter Ausgabe."""
    
    groups = await run_grouped_checks(workspace_root)
    
    # Status Icons
    icons = {"ok": "✅", "warning": "⚠️", "error": "❌"}
    
    # Header
    lines = ["# NOVA System Status", ""]
    
    # Gruppierte Tabellen
    for group in groups:
        group_icon = icons.get(group.status, "")
        lines.append(f"### {group_icon} {group.name}")
        lines.append("")
        lines.append("| Component | Status | Details |")
        lines.append("|-----------|--------|---------|")
        
        for check in group.checks:
            icon = icons.get(check.status, "❓")
            detail = check.detail if check.detail else "-"
            lines.append(f"| {check.name} | {icon} {check.message} | {detail} |")
        
        lines.append("")
    
    # Zusammenfassung
    total_checks = sum(len(g.checks) for g in groups)
    ok_count = sum(1 for g in groups for c in g.checks if c.status == "ok")
    warn_count = sum(1 for g in groups for c in g.checks if c.status == "warning")
    error_count = sum(1 for g in groups for c in g.checks if c.status == "error")
    
    lines.append("---")
    if error_count > 0:
        lines.append(f"**Summary:** ❌ {error_count} Errors, {warn_count} Warnings, {ok_count} OK ({total_checks} total)")
    elif warn_count > 0:
        lines.append(f"**Summary:** ⚠️ {warn_count} Warnings, {ok_count} OK ({total_checks} total)")
    else:
        lines.append(f"**Summary:** ✅ All {total_checks} checks passed")
    
    # Aktionen
    actions = get_actions_from_groups(groups)
    if actions:
        lines.append("")
        lines.append("**Recommended Actions:**")
        for action in actions:
            lines.append(action)
    
    return [TextContent(type="text", text="\n".join(lines))]


# Quick Check für session_init (ohne eigenes Tool)
async def quick_check(workspace_root: Path) -> str:
    """
    Schneller Health Check für session_init.
    Gibt gruppierte kompakte Statuszeilen zurück.
    """
    groups = await run_grouped_checks(workspace_root)
    
    status_lines = format_grouped_simple(groups)
    actions = get_actions_from_groups(groups)
    
    result = f"## System Status\n{status_lines}"
    
    if actions:
        result += "\n\n**Action Required:**\n" + "\n".join(actions)
    
    return result
