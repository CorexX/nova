"""
Tests für context/get_conventions.py
"""

import pytest
from pathlib import Path
from mcp.types import Tool, TextContent

from tools.context.get_conventions import get_tool_definition, execute


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
        assert tool.name == "nova_get_conventions"
    
    def test_has_description(self, tmp_path: Path):
        """Tool hat Beschreibung."""
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "Konvention" in tool.description or "Naming" in tool.description
    
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

## Dateisystem-Prinzipien

| Format | Beispiel |
|--------|----------|
| kebab-case | my-file.md |
| ISO Date | 2026-01-15 |

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
    async def test_extracts_conventions_section(self, tmp_path: Path, principles_content: str):
        """Extrahiert Dateisystem-Prinzipien-Sektion."""
        core = tmp_path / "nova-core" / "core"
        core.mkdir(parents=True)
        (core / "PRINCIPLES.md").write_text(principles_content)
        
        result = await execute({}, tmp_path)
        
        assert "Dateisystem-Prinzipien" in result[0].text
        assert "kebab-case" in result[0].text
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
        (core / "PRINCIPLES.md").write_text("# No conventions here")
        
        result = await execute({}, tmp_path)
        
        assert "nicht gefunden" in result[0].text
