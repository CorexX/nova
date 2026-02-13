"""
Tool: Get Agent Skills
Listet agentische Skill-Spezifikationen und Legacy-Skripte.
"""

from pathlib import Path

from mcp.types import TextContent, Tool

from ..paths import resolve_paths


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_get_agent_skills",
        description=(
            "Listet Agent-Skills aus nova-knowledge/skills und zeigt Legacy-Python-Skripte "
            "aus nova-core/skills getrennt an."
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


def _list_skill_specs(skills_root: Path) -> list[str]:
    if not skills_root.exists():
        return []
    specs: list[str] = []
    for md in sorted(skills_root.rglob("*.md")):
        if md.name.upper() == "README.md":
            continue
        rel = md.relative_to(skills_root)
        specs.append(str(rel).replace("\\", "/"))
    return specs


def _list_legacy_scripts(core_skills_root: Path) -> list[str]:
    if not core_skills_root.exists():
        return []
    scripts: list[str] = []
    for py in sorted(core_skills_root.glob("*.py")):
        if py.name.startswith("_"):
            continue
        scripts.append(py.name)
    return scripts


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    paths = resolve_paths(workspace_root)
    specs_root = paths.knowledge_root / "skills"
    legacy_root = paths.core_root / "skills"

    specs = _list_skill_specs(specs_root)
    legacy = _list_legacy_scripts(legacy_root)

    lines = ["# Agent Skills", ""]
    lines.append("## Canonical Skill Specs (`nova-knowledge/skills`)")
    if specs:
        for item in specs:
            lines.append(f"- `{item}`")
    else:
        lines.append("- *Keine Skill-Spezifikationen gefunden*")

    lines.append("")
    lines.append("## Legacy Python Scripts (`nova-core/skills`)")
    if legacy:
        for item in legacy:
            lines.append(f"- `{item}`")
    else:
        lines.append("- *Keine Legacy-Skripte gefunden*")

    lines.append("")
    lines.append("Hinweis: Agent-Skill-Wissen gehoert nach `nova-knowledge/skills`.")
    lines.append("`nova-core/skills` bleibt fuer technische Legacy-Skripte.")

    return [TextContent(type="text", text="\n".join(lines))]
