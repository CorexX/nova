"""
Tests for context/get_collections.py
"""

from pathlib import Path

import pytest
from mcp.types import TextContent, Tool

from tools.context.get_collections import execute, get_tool_definition


class TestToolDefinition:
    def test_returns_tool_instance(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert isinstance(tool, Tool)

    def test_has_correct_name(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert tool.name == "nova_get_collections"


class TestExecute:
    @pytest.mark.asyncio
    async def test_returns_text_content(self, tmp_path: Path):
        (tmp_path / "nova-knowledge" / "projects").mkdir(parents=True)
        result = await execute({}, tmp_path)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_lists_collections(self, tmp_path: Path):
        knowledge = tmp_path / "nova-knowledge"
        (knowledge / "projects").mkdir(parents=True)
        (knowledge / "areas").mkdir(parents=True)
        result = await execute({}, tmp_path)
        assert "projects" in result[0].text
        assert "areas" in result[0].text

    @pytest.mark.asyncio
    async def test_ignores_hidden_and_underscore(self, tmp_path: Path):
        knowledge = tmp_path / "nova-knowledge"
        (knowledge / "projects").mkdir(parents=True)
        (knowledge / ".hidden").mkdir(parents=True)
        (knowledge / "_tmp").mkdir(parents=True)
        result = await execute({}, tmp_path)
        assert "projects" in result[0].text
        assert ".hidden" not in result[0].text
        assert "_tmp" not in result[0].text

