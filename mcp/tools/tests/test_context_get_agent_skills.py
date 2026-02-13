"""
Tests fuer context/get_agent_skills.py
"""

from pathlib import Path

import pytest
from mcp.types import TextContent, Tool

from tools.context.get_agent_skills import execute, get_tool_definition


class TestToolDefinition:
    def test_returns_tool_instance(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert isinstance(tool, Tool)

    def test_has_correct_name(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert tool.name == "nova_get_agent_skills"

    def test_has_description(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert "Skill" in tool.description


class TestExecute:
    @pytest.mark.asyncio
    async def test_returns_text_content(self, tmp_path: Path):
        result = await execute({}, tmp_path)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_lists_skill_specs_and_legacy_scripts(self, tmp_path: Path):
        knowledge_skills = tmp_path / "nova-knowledge" / "skills" / "terraform"
        knowledge_skills.mkdir(parents=True)
        (knowledge_skills / "provider-setup.md").write_text("# Spec", encoding="utf-8")

        core_skills = tmp_path / "nova-core" / "skills"
        core_skills.mkdir(parents=True)
        (core_skills / "summarize_day.py").write_text("print('x')", encoding="utf-8")

        result = await execute({}, tmp_path)
        text = result[0].text
        assert "provider-setup.md" in text
        assert "summarize_day.py" in text

    @pytest.mark.asyncio
    async def test_handles_empty_skill_sources(self, tmp_path: Path):
        result = await execute({}, tmp_path)
        text = result[0].text
        assert "Keine Skill-Spezifikationen" in text
        assert "Keine Legacy-Skripte" in text
