"""
Tests für context/get_tickets.py
"""

import pytest
from pathlib import Path
from mcp.types import Tool, TextContent

from tools.context.get_tickets import get_tool_definition, execute


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
        assert tool.name == "nova_get_tickets"
    
    def test_has_description(self, tmp_path: Path):
        """Tool hat Beschreibung."""
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "TICKETS" in tool.description
    
    def test_no_required_params(self, tmp_path: Path):
        """Keine Parameter sind required."""
        tool = get_tool_definition(tmp_path)
        required = tool.inputSchema.get("required", [])
        assert len(required) == 0


# =============================================================================
# TESTS: execute
# =============================================================================

class TestExecute:
    """Tests für die Tool-Ausführung."""
    
    @pytest.mark.asyncio
    async def test_returns_text_content(self, tmp_path: Path):
        """Gibt TextContent zurück."""
        knowledge = tmp_path / "nova-knowledge"
        knowledge.mkdir()
        (knowledge / "TICKETS.md").write_text("# Tickets\n| ID | Name |")
        
        result = await execute({}, tmp_path)
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
    
    @pytest.mark.asyncio
    async def test_returns_file_content(self, tmp_path: Path):
        """Gibt Dateiinhalt zurück."""
        knowledge = tmp_path / "nova-knowledge"
        knowledge.mkdir()
        content = "# TICKETS\n\n| Ticket | Budget |\n|--------|--------|\n| ABC-1 | 10h |"
        (knowledge / "TICKETS.md").write_text(content)
        
        result = await execute({}, tmp_path)
        
        assert result[0].text == content
    
    @pytest.mark.asyncio
    async def test_handles_missing_file(self, tmp_path: Path):
        """Behandelt fehlende Datei."""
        result = await execute({}, tmp_path)
        
        assert "nicht gefunden" in result[0].text
