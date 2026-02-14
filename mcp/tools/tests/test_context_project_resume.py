"""
Tests for context/project_resume.py
"""

from pathlib import Path

import pytest
from mcp.types import TextContent, Tool

from tools.context.project_resume import execute, get_tool_definition


class TestToolDefinition:
    def test_returns_tool_instance(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert isinstance(tool, Tool)

    def test_has_correct_name(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert tool.name == "nova_project_resume"


class TestExecute:
    @pytest.fixture
    def workspace(self, tmp_path: Path) -> Path:
        (tmp_path / "nova-core" / "core").mkdir(parents=True)
        (tmp_path / "nova-knowledge" / "my-space" / "homelab" / "knowledge").mkdir(parents=True)
        (tmp_path / "nova-knowledge" / "projects" / "internal" / "homelab").mkdir(parents=True)

        (tmp_path / "nova-core" / "core" / "CORE.md").write_text("# CORE", encoding="utf-8")
        (tmp_path / "nova-knowledge" / "my-space" / "homelab" / "README.md").write_text(
            "# Homelab README", encoding="utf-8"
        )
        (tmp_path / "nova-knowledge" / "my-space" / "homelab" / "CURRENT.md").write_text(
            "# Current", encoding="utf-8"
        )
        (tmp_path / "nova-knowledge" / "my-space" / "homelab" / "knowledge" / "commands-runbook.md").write_text(
            "# Commands", encoding="utf-8"
        )
        (tmp_path / "nova-knowledge" / "projects" / "internal" / "homelab" / "README.md").write_text(
            "# Homelab README", encoding="utf-8"
        )
        (tmp_path / "nova-knowledge" / "projects" / "internal" / "homelab" / "CURRENT.md").write_text(
            "## In Progress\n- [x] done", encoding="utf-8"
        )
        (tmp_path / "nova-knowledge" / "projects" / "internal" / "homelab" / "BACKLOG.md").write_text(
            "## Now\n- [ ] todo", encoding="utf-8"
        )

        return tmp_path

    @pytest.mark.asyncio
    async def test_loads_project_docs_and_marks_missing(self, workspace: Path):
        result = await execute(
            {
                "path": "my-space/homelab",
                "include_session_init": False,
                "documents": ["README.md", "BACKLOG.md", "knowledge/commands-runbook.md"],
            },
            workspace,
        )
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text = result[0].text
        assert "Project Resume Bundle" in text
        assert "README.md" in text
        assert "Status: vorhanden" in text
        assert "BACKLOG.md" in text
        assert "Status: nicht vorhanden" in text
        assert "commands-runbook.md" in text

    @pytest.mark.asyncio
    async def test_handles_missing_path(self, workspace: Path):
        result = await execute(
            {"path": "not-there", "include_session_init": False},
            workspace,
        )
        text = result[0].text
        assert "Pfad nicht gefunden" in text
        assert "Zielpfad: nicht vorhanden" in text

    @pytest.mark.asyncio
    async def test_auto_discovers_markdown_when_documents_missing(self, workspace: Path):
        result = await execute(
            {"path": "my-space/homelab", "include_session_init": False},
            workspace,
        )
        text = result[0].text
        assert "Auto-Discovery" in text
        assert "README.md" in text
        assert "CURRENT.md" in text

    @pytest.mark.asyncio
    async def test_resolves_project_by_hint(self, workspace: Path):
        result = await execute(
            {
                "project_hint": "homlab",
                "include_session_init": False,
                "mode": "bundle",
                "documents": ["README.md"],
            },
            workspace,
        )
        text = result[0].text
        assert "Zielpfad:" in text
        assert "homelab" in text
        assert "README.md" in text

    @pytest.mark.asyncio
    async def test_continue_mode_returns_structured_report(self, workspace: Path):
        result = await execute(
            {
                "path": "my-space/homelab",
                "include_session_init": False,
                "mode": "continue",
            },
            workspace,
        )
        text = result[0].text
        assert "Continue Report" in text
        assert "Kurzuebersicht" in text
        assert "Letzte Arbeitsschritte" in text
        assert "Offene Punkte" in text
        assert "Naechster Konkreter Plan" in text
