"""
Tests für context/get_scope.py
"""

import pytest
from pathlib import Path
from mcp.types import Tool, TextContent

from tools.context.get_scope import get_tool_definition, execute


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
        assert tool.name == "nova_get_scope"
    
    def test_has_description(self, tmp_path: Path):
        """Tool hat Beschreibung."""
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "Scope" in tool.description or "schreiben" in tool.description.lower()
    
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

## Schreib-Scope

| Pfad | Erlaubt |
|------|---------|
| WORKLOG.md | Append |
| nova-core/ | Nein |

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
    async def test_extracts_scope_section(self, tmp_path: Path, principles_content: str):
        """Extrahiert Schreib-Scope-Sektion."""
        core = tmp_path / "nova-core" / "core"
        core.mkdir(parents=True)
        (core / "PRINCIPLES.md").write_text(principles_content)
        
        result = await execute({}, tmp_path)
        
        assert "Schreib-Scope" in result[0].text
        assert "WORKLOG.md" in result[0].text
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
        (core / "PRINCIPLES.md").write_text("# No scope here")
        
        result = await execute({}, tmp_path)
        
        assert "nicht gefunden" in result[0].text
