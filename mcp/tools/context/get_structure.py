"""
Tool: Get Structure
Liefert die Vault-Struktur live aus dem Filesystem.
"""

from pathlib import Path

from mcp.types import TextContent, Tool

from ..paths import resolve_paths


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_get_structure",
        description="Liefert die aktuelle Vault-Struktur (nova-core + nova-knowledge Ordner).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    lines = ["# Vault-Struktur\n"]
    paths = resolve_paths(workspace_root)

    core_path = paths.core_root
    if core_path.exists():
        lines.append("```")
        lines.append("nova-core/                    # Framework (public)")
        for entry in sorted(core_path.iterdir()):
            if entry.is_dir() and not entry.name.startswith((".", "_")):
                lines.append(f"- {entry.name}/")
        lines.append("```\n")

    knowledge_path = paths.knowledge_root
    if knowledge_path.exists():
        lines.append("```")
        lines.append("nova-knowledge/               # Arbeit (privat)")
        for entry in sorted(knowledge_path.iterdir()):
            if entry.name.startswith((".", "_")):
                continue
            if entry.is_dir():
                lines.append(f"- {entry.name}/")
            elif entry.suffix == ".md":
                lines.append(f"- {entry.name}")
        lines.append("```")

    lines.append("")
    lines.append("## Boundary")
    lines.append("- `nova-core/knowledge`: nur kritisches Framework-Wissen (stabil, selten).")
    lines.append("- `nova-knowledge/knowledge`: laufendes Fachwissen/Notizen (lebendiger Inhalt).")
    lines.append("- `nova-core/meta`: Architektur, ADRs, Changelog (System-Ebene).")
    lines.append("- `nova-knowledge/skills`: Agent-Skill-Spezifikationen (domain-nah).")
    lines.append("- `nova-core/skills`: technische Legacy-Skripte.")

    return [TextContent(type="text", text="\n".join(lines))]
