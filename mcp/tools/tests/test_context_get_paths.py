"""
Tests for context/get_paths.py
"""

from pathlib import Path

import pytest
from mcp.types import TextContent, Tool

from tools.context.get_paths import execute, get_tool_definition


class TestToolDefinition:
    def test_returns_tool_instance(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert isinstance(tool, Tool)

    def test_has_correct_name(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert tool.name == "nova_get_paths"


class TestExecute:
    @pytest.mark.asyncio
    async def test_returns_paths_table(self, tmp_path: Path):
        (tmp_path / "nova-core" / "core").mkdir(parents=True)
        (tmp_path / "nova-knowledge").mkdir(parents=True)
        result = await execute({}, tmp_path)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text = result[0].text
        assert "knowledge_root" in text
        assert "CURRENT.md" in text
        assert "WORKLOG.md" in text

