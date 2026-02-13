"""
Tests für context/get_rules.py
"""

import pytest
from pathlib import Path
from mcp.types import Tool, TextContent

from tools.context.get_rules import get_tool_definition, execute


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
        assert tool.name == "nova_get_rules"
    
    def test_has_description(self, tmp_path: Path):
        """Tool hat Beschreibung."""
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "Kernprinzipien" in tool.description or "Prinzipien" in tool.description
    
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
    
    @pytest.fixture
    def principles_content(self):
        """Standard PRINCIPLES.md Inhalt."""
        return """# Principles

## Kernprinzipien

| # | Prinzip |
|---|---------|
| 1 | Persist Results |
| 2 | Append Only |

---

## Other Section
"""

    @pytest.mark.asyncio
    async def test_returns_text_content(self, tmp_path: Path, principles_content: str):
        """Gibt TextContent zurück."""
        core = tmp_path / "nova-core" / "core"
        core.mkdir(parents=True)
        (core / "PRINCIPLES.md").write_text(principles_content)
        
        result = await execute({}, tmp_path)
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
    
    @pytest.mark.asyncio
    async def test_extracts_kernprinzipien_section(self, tmp_path: Path, principles_content: str):
        """Extrahiert Kernprinzipien-Sektion."""
        core = tmp_path / "nova-core" / "core"
        core.mkdir(parents=True)
        (core / "PRINCIPLES.md").write_text(principles_content)
        
        result = await execute({}, tmp_path)
        
        assert "Kernprinzipien" in result[0].text
        assert "Persist Results" in result[0].text
        assert "Other Section" not in result[0].text
    
    @pytest.mark.asyncio
    async def test_handles_missing_file(self, tmp_path: Path):
        """Behandelt fehlende Datei."""
        result = await execute({}, tmp_path)
        
        assert "nicht gefunden" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handles_missing_section(self, tmp_path: Path):
        """Behandelt fehlende Sektion."""
        core = tmp_path / "nova-core" / "core"
        core.mkdir(parents=True)
        (core / "PRINCIPLES.md").write_text("# No rules here")
        
        result = await execute({}, tmp_path)
        
        assert "nicht gefunden" in result[0].text
