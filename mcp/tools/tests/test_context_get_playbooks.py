"""
Tests für context/get_playbooks.py
"""

import pytest
from pathlib import Path
from mcp.types import Tool, TextContent

from tools.context.get_playbooks import get_tool_definition, execute


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
        assert tool.name == "nova_get_playbooks"
    
    def test_has_description(self, tmp_path: Path):
        """Tool hat Beschreibung."""
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "Playbook" in tool.description
    
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
        playbooks = tmp_path / "nova-core" / "playbooks"
        playbooks.mkdir(parents=True)
        
        result = await execute({}, tmp_path)
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
    
    @pytest.mark.asyncio
    async def test_lists_playbook_files(self, tmp_path: Path):
        """Listet Playbook-Dateien auf."""
        playbooks = tmp_path / "nova-core" / "playbooks"
        playbooks.mkdir(parents=True)
        (playbooks / "close_day.md").write_text("# Close Day\n## Trigger\n- close day")
        (playbooks / "deploy.md").write_text("# Deploy\n## Trigger\n- deploy")
        
        result = await execute({}, tmp_path)
        
        assert "close_day.md" in result[0].text
        assert "deploy.md" in result[0].text
    
    @pytest.mark.asyncio
    async def test_extracts_trigger(self, tmp_path: Path):
        """Extrahiert Trigger aus Playbook."""
        playbooks = tmp_path / "nova-core" / "playbooks"
        playbooks.mkdir(parents=True)
        content = """# Close Day

## Trigger

- close day
- feierabend
"""
        (playbooks / "close_day.md").write_text(content)
        
        result = await execute({}, tmp_path)
        
        assert "close day" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handles_no_trigger_section(self, tmp_path: Path):
        """Behandelt fehlendes Trigger-Section."""
        playbooks = tmp_path / "nova-core" / "playbooks"
        playbooks.mkdir(parents=True)
        (playbooks / "no-trigger.md").write_text("# Playbook without trigger section")
        
        result = await execute({}, tmp_path)
        
        # Sollte nicht crashen
        assert "no-trigger.md" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handles_no_playbooks(self, tmp_path: Path):
        """Behandelt fehlende Playbooks."""
        playbooks = tmp_path / "nova-core" / "playbooks"
        playbooks.mkdir(parents=True)
        
        result = await execute({}, tmp_path)
        
        # Keine md-Files = leere Tabelle, kein Crash
        assert isinstance(result[0], TextContent)
    
    @pytest.mark.asyncio
    async def test_handles_missing_playbooks_dir(self, tmp_path: Path):
        """Behandelt fehlenden Playbooks-Ordner."""
        result = await execute({}, tmp_path)
        
        assert "Keine Playbooks" in result[0].text
    
    @pytest.mark.asyncio
    async def test_sorted_alphabetically(self, tmp_path: Path):
        """Sortiert alphabetisch."""
        playbooks = tmp_path / "nova-core" / "playbooks"
        playbooks.mkdir(parents=True)
        (playbooks / "z-playbook.md").write_text("# Z")
        (playbooks / "a-playbook.md").write_text("# A")
        
        result = await execute({}, tmp_path)
        
        text = result[0].text
        assert text.index("a-playbook") < text.index("z-playbook")
