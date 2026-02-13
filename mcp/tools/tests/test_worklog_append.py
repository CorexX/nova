"""
Tests für worklog/append.py
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
from mcp.types import Tool, TextContent

from tools.worklog.append import get_tool_definition, execute


# =============================================================================
# TESTS: get_tool_definition
# =============================================================================

class TestToolDefinition:
    """Tests für die Tool-Definition."""
    
    def test_returns_tool_instance(self, tmp_path: Path):
        """Tool-Definition gibt Tool-Instanz zurück."""
        tool = get_tool_definition(tmp_path)
        assert isinstance(tool, Tool)
    
    def test_has_correct_name(self, tmp_path: Path):
        """Tool hat korrekten Namen."""
        tool = get_tool_definition(tmp_path)
        assert tool.name == "nova_worklog_append"
    
    def test_has_description(self, tmp_path: Path):
        """Tool hat Beschreibung."""
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert len(tool.description) > 10
    
    def test_has_input_schema(self, tmp_path: Path):
        """Tool hat Input-Schema."""
        tool = get_tool_definition(tmp_path)
        assert tool.inputSchema
        assert "properties" in tool.inputSchema
    
    def test_entry_is_required(self, tmp_path: Path):
        """Entry-Parameter ist required."""
        tool = get_tool_definition(tmp_path)
        assert "entry" in tool.inputSchema.get("required", [])


# =============================================================================
# TESTS: execute
# =============================================================================

class TestExecute:
    """Tests für die Tool-Ausführung."""
    
    @pytest.fixture
    def workspace_with_worklog(self, tmp_path: Path) -> Path:
        """Erstellt temporäres Workspace mit WORKLOG.md."""
        knowledge_dir = tmp_path / "nova-knowledge"
        knowledge_dir.mkdir(parents=True)
        worklog = knowledge_dir / "WORKLOG.md"
        worklog.write_text("# WORKLOG\n\n## 2026-02-08\n", encoding="utf-8")
        return tmp_path
    
    @pytest.mark.asyncio
    async def test_appends_entry(self, workspace_with_worklog: Path):
        """Fügt Eintrag zum WORKLOG hinzu."""
        args = {"entry": "Test-Eintrag"}
        
        result = await execute(args, workspace_with_worklog)
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Appended" in result[0].text
        
        worklog = workspace_with_worklog / "nova-knowledge" / "WORKLOG.md"
        content = worklog.read_text(encoding="utf-8")
        assert "Test-Eintrag" in content
    
    @pytest.mark.asyncio
    async def test_adds_time_prefix(self, workspace_with_worklog: Path):
        """Fügt Zeitstempel hinzu."""
        args = {"entry": "Meeting", "time": "10:30"}
        
        await execute(args, workspace_with_worklog)
        
        worklog = workspace_with_worklog / "nova-knowledge" / "WORKLOG.md"
        content = worklog.read_text(encoding="utf-8")
        assert "- 10:30" in content
    
    @pytest.mark.asyncio
    async def test_adds_ticket_suffix(self, workspace_with_worklog: Path):
        """Fügt Ticket-ID hinzu."""
        args = {"entry": "Bug fix", "ticket": "PROJ-123"}
        
        await execute(args, workspace_with_worklog)
        
        worklog = workspace_with_worklog / "nova-knowledge" / "WORKLOG.md"
        content = worklog.read_text(encoding="utf-8")
        assert "(PROJ-123)" in content
    
    @pytest.mark.asyncio
    async def test_formats_entry_with_dash(self, workspace_with_worklog: Path):
        """Entry wird mit Dash formatiert."""
        args = {"entry": "Entry ohne Dash"}
        
        await execute(args, workspace_with_worklog)
        
        worklog = workspace_with_worklog / "nova-knowledge" / "WORKLOG.md"
        content = worklog.read_text(encoding="utf-8")
        assert "- " in content.split("Entry ohne Dash")[0]
