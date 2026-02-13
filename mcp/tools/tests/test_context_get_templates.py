"""
Tests für context/get_templates.py
"""

import pytest
from pathlib import Path
from mcp.types import Tool, TextContent

from tools.context.get_templates import get_tool_definition, execute


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
        assert tool.name == "nova_get_templates"
    
    def test_has_description(self, tmp_path: Path):
        """Tool hat Beschreibung."""
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "Template" in tool.description
    
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
        (tmp_path / "nova-knowledge").mkdir()
        
        result = await execute({}, tmp_path)
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
    
    @pytest.mark.asyncio
    async def test_finds_template_dirs(self, tmp_path: Path):
        """Findet _template Verzeichnisse."""
        template = tmp_path / "nova-knowledge" / "kunden" / "_template"
        template.mkdir(parents=True)
        (template / "README.md").write_text("# Template")
        
        result = await execute({}, tmp_path)
        
        assert "kunden" in result[0].text
        assert "_template" in result[0].text or "README.md" in result[0].text
    
    @pytest.mark.asyncio
    async def test_lists_template_files(self, tmp_path: Path):
        """Listet Dateien im Template."""
        template = tmp_path / "nova-knowledge" / "kunden" / "_template"
        template.mkdir(parents=True)
        (template / "README.md").write_text("# Template")
        (template / "WORKLOG.md").write_text("# Worklog")
        
        result = await execute({}, tmp_path)
        
        assert "README.md" in result[0].text
    
    @pytest.mark.asyncio
    async def test_finds_nested_templates(self, tmp_path: Path):
        """Findet verschachtelte Templates."""
        t1 = tmp_path / "nova-knowledge" / "kunden" / "_template"
        t2 = tmp_path / "nova-knowledge" / "sideprojects" / "_template"
        t1.mkdir(parents=True)
        t2.mkdir(parents=True)
        (t1 / "file1.md").write_text("# 1")
        (t2 / "file2.md").write_text("# 2")
        
        result = await execute({}, tmp_path)
        
        assert "kunden" in result[0].text
        assert "sideprojects" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handles_no_templates(self, tmp_path: Path):
        """Behandelt fehlende Templates."""
        (tmp_path / "nova-knowledge" / "kunden").mkdir(parents=True)
        
        result = await execute({}, tmp_path)
        
        assert "Keine Templates" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handles_missing_knowledge(self, tmp_path: Path):
        """Behandelt fehlendes nova-knowledge."""
        result = await execute({}, tmp_path)
        
        # Sollte nicht crashen
        assert isinstance(result[0], TextContent)
