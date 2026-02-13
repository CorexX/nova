"""
Tests für nova_get_architecture Tool.
"""

import pytest
from pathlib import Path
from mcp.types import Tool, TextContent

from tools.architecture.get_architecture import get_tool_definition, execute


@pytest.fixture
def workspace_with_architecture(tmp_path: Path) -> Path:
    """Erstellt einen Workspace mit ARCHITECTURE.md."""
    meta_dir = tmp_path / "nova-core" / "meta"
    meta_dir.mkdir(parents=True)
    
    architecture_content = """# NOVA Architecture

<!-- COMPACT_START -->

## Quick Reference

> **Vault = Source of Truth.**

### Struktur
- nova-core/
- nova-knowledge/

### Design-Regeln
1. Vault = Truth
2. Append-only

<!-- COMPACT_END -->

## Design-Prinzipien

Detaillierte Design-Prinzipien hier...

## Komponenten

Komponenten-Details hier...
"""
    (meta_dir / "ARCHITECTURE.md").write_text(architecture_content, encoding="utf-8")
    return tmp_path


class TestToolDefinition:
    """Tests für die Tool-Definition."""
    
    def test_returns_tool_instance(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert isinstance(tool, Tool)
    
    def test_has_correct_name(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert tool.name == "nova_get_architecture"
    
    def test_has_description(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert len(tool.description) > 0
        assert "Architektur" in tool.description or "architecture" in tool.description.lower()
    
    def test_has_input_schema(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert tool.inputSchema is not None
        assert "properties" in tool.inputSchema


class TestExecute:
    """Tests für die Tool-Ausführung."""
    
    @pytest.mark.asyncio
    async def test_returns_text_content(self, workspace_with_architecture: Path):
        result = await execute({}, workspace_with_architecture)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
    
    @pytest.mark.asyncio
    async def test_compact_output_from_markers(self, workspace_with_architecture: Path):
        result = await execute({}, workspace_with_architecture)
        text = result[0].text
        
        # Sollte den COMPACT-Bereich enthalten
        assert "Quick Reference" in text
        assert "Vault = Source of Truth" in text
        
        # Sollte NICHT den vollen Inhalt enthalten
        assert "Detaillierte Design-Prinzipien" not in text
    
    @pytest.mark.asyncio
    async def test_section_parameter_works(self, workspace_with_architecture: Path):
        result = await execute({"section": "Design-Prinzipien"}, workspace_with_architecture)
        text = result[0].text
        
        assert "Design-Prinzipien" in text
        assert "Detaillierte" in text
    
    @pytest.mark.asyncio
    async def test_invalid_section_returns_available(self, workspace_with_architecture: Path):
        result = await execute({"section": "nonexistent"}, workspace_with_architecture)
        text = result[0].text
        
        assert "nicht gefunden" in text
        assert "Verfügbare Sektionen" in text
    
    @pytest.mark.asyncio
    async def test_full_parameter_gives_complete_file(self, workspace_with_architecture: Path):
        result = await execute({"full": True}, workspace_with_architecture)
        text = result[0].text
        
        # Sollte alles enthalten
        assert "NOVA Architecture" in text
        assert "Design-Prinzipien" in text
        assert "Komponenten" in text
        assert "COMPACT_START" in text  # Marker sind auch drin
    
    @pytest.mark.asyncio
    async def test_missing_file_returns_error(self, tmp_path: Path):
        result = await execute({}, tmp_path)
        text = result[0].text
        
        assert "ERROR" in text or "nicht gefunden" in text
