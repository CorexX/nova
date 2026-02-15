"""Tests for system/restart_server.py."""

from pathlib import Path

import pytest
from mcp.types import TextContent, Tool

from tools.system import restart_server


class TestToolDefinition:
    def test_returns_tool_instance(self, tmp_path: Path):
        tool = restart_server.get_tool_definition(tmp_path)
        assert isinstance(tool, Tool)

    def test_has_correct_name(self, tmp_path: Path):
        tool = restart_server.get_tool_definition(tmp_path)
        assert tool.name == "nova_restart_server"


class TestExecute:
    @pytest.mark.asyncio
    async def test_rejects_non_integer_delay(self, tmp_path: Path):
        result = await restart_server.execute({"delay_seconds": "x"}, tmp_path)
        assert isinstance(result[0], TextContent)
        assert "must be an integer" in result[0].text

    @pytest.mark.asyncio
    async def test_rejects_out_of_range_delay(self, tmp_path: Path):
        result = await restart_server.execute({"delay_seconds": 99}, tmp_path)
        assert isinstance(result[0], TextContent)
        assert "between 1 and 30" in result[0].text

    @pytest.mark.asyncio
    async def test_schedules_timer(self, monkeypatch, tmp_path: Path):
        called = {}

        class FakeTimer:
            def __init__(self, delay, func):
                called["delay"] = delay
                called["func"] = func
                self.daemon = False

            def start(self):
                called["started"] = True

        monkeypatch.setattr(restart_server.threading, "Timer", FakeTimer)

        result = await restart_server.execute({"delay_seconds": 3}, tmp_path)
        assert isinstance(result[0], TextContent)
        assert "scheduled in 3s" in result[0].text
        assert called["delay"] == 3
        assert callable(called["func"])
        assert called["started"] is True
