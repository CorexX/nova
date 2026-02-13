"""
Tests für context/get_structure.py
"""

import pytest
from pathlib import Path
from mcp.types import Tool, TextContent

from tools.context.get_structure import get_tool_definition, execute


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
        assert tool.name == "nova_get_structure"
    
    def test_has_description(self, tmp_path: Path):
        """Tool hat Beschreibung."""
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "Struktur" in tool.description or "structure" in tool.description.lower()
    
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
        (tmp_path / "nova-core").mkdir()
        (tmp_path / "nova-knowledge").mkdir()
        
        result = await execute({}, tmp_path)
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
    
    @pytest.mark.asyncio
    async def test_lists_nova_core_dirs(self, tmp_path: Path):
        """Listet nova-core Verzeichnisse auf."""
        core = tmp_path / "nova-core"
        (core / "mcp").mkdir(parents=True)
        (core / "guides").mkdir(parents=True)
        
        result = await execute({}, tmp_path)
        
        assert "nova-core" in result[0].text
        assert "mcp" in result[0].text
        assert "guides" in result[0].text
    
    @pytest.mark.asyncio
    async def test_lists_nova_knowledge_dirs(self, tmp_path: Path):
        """Listet nova-knowledge Verzeichnisse auf."""
        knowledge = tmp_path / "nova-knowledge"
        (knowledge / "kunden").mkdir(parents=True)
        (knowledge / "kompetenz").mkdir(parents=True)
        (knowledge / "CURRENT.md").write_text("# Current")
        
        result = await execute({}, tmp_path)
        
        assert "nova-knowledge" in result[0].text
        assert "kunden" in result[0].text
        assert "CURRENT.md" in result[0].text
    
    @pytest.mark.asyncio
    async def test_ignores_hidden_dirs(self, tmp_path: Path):
        """Ignoriert versteckte Verzeichnisse."""
        core = tmp_path / "nova-core"
        (core / "visible").mkdir(parents=True)
        (core / ".hidden").mkdir(parents=True)
        
        result = await execute({}, tmp_path)
        
        assert "visible" in result[0].text
        assert ".hidden" not in result[0].text
    
    @pytest.mark.asyncio
    async def test_ignores_underscore_dirs(self, tmp_path: Path):
        """Ignoriert _ Verzeichnisse."""
        core = tmp_path / "nova-core"
        (core / "visible").mkdir(parents=True)
        (core / "_ignored").mkdir(parents=True)
        
        result = await execute({}, tmp_path)
        
        assert "visible" in result[0].text
        assert "_ignored" not in result[0].text
    
    @pytest.mark.asyncio
    async def test_handles_missing_core(self, tmp_path: Path):
        """Funktioniert ohne nova-core."""
        (tmp_path / "nova-knowledge").mkdir()
        
        result = await execute({}, tmp_path)
        
        # Sollte nicht crashen
        assert isinstance(result[0], TextContent)
    
    @pytest.mark.asyncio
    async def test_handles_missing_knowledge(self, tmp_path: Path):
        """Funktioniert ohne nova-knowledge."""
        (tmp_path / "nova-core").mkdir()
        
        result = await execute({}, tmp_path)
        
        # Sollte nicht crashen
        assert isinstance(result[0], TextContent)
