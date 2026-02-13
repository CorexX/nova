"""
Tests für context/get_guides.py
"""

import pytest
from pathlib import Path
from mcp.types import Tool, TextContent

from tools.context.get_guides import get_tool_definition, execute


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
        assert tool.name == "nova_get_guides"
    
    def test_has_description(self, tmp_path: Path):
        """Tool hat Beschreibung."""
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "Guide" in tool.description or "How-To" in tool.description
    
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
        guides = tmp_path / "nova-core" / "guides"
        guides.mkdir(parents=True)
        
        result = await execute({}, tmp_path)
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
    
    @pytest.mark.asyncio
    async def test_lists_guide_files(self, tmp_path: Path):
        """Listet Guide-Dateien auf."""
        guides = tmp_path / "nova-core" / "guides"
        guides.mkdir(parents=True)
        (guides / "setup-project.md").write_text("# Setup\n> How to set up")
        (guides / "deploy-app.md").write_text("# Deploy\n> How to deploy")
        
        result = await execute({}, tmp_path)
        
        assert "setup-project.md" in result[0].text
        assert "deploy-app.md" in result[0].text
    
    @pytest.mark.asyncio
    async def test_extracts_description_from_blockquote(self, tmp_path: Path):
        """Extrahiert Beschreibung aus Blockquote."""
        guides = tmp_path / "nova-core" / "guides"
        guides.mkdir(parents=True)
        (guides / "my-guide.md").write_text("# Title\n\n> This is the description\n\nContent")
        
        result = await execute({}, tmp_path)
        
        assert "This is the description" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handles_no_guides(self, tmp_path: Path):
        """Behandelt leeren Guides-Ordner."""
        guides = tmp_path / "nova-core" / "guides"
        guides.mkdir(parents=True)
        
        result = await execute({}, tmp_path)
        
        # Leerer Ordner = Tabelle ohne Einträge (nur Header)
        assert "Guide" in result[0].text
        assert isinstance(result[0], TextContent)
    
    @pytest.mark.asyncio
    async def test_handles_missing_guides_dir(self, tmp_path: Path):
        """Behandelt fehlenden Guides-Ordner."""
        result = await execute({}, tmp_path)
        
        assert "Keine Guides" in result[0].text
    
    @pytest.mark.asyncio
    async def test_sorted_alphabetically(self, tmp_path: Path):
        """Sortiert alphabetisch."""
        guides = tmp_path / "nova-core" / "guides"
        guides.mkdir(parents=True)
        (guides / "z-guide.md").write_text("# Z\n> Z desc")
        (guides / "a-guide.md").write_text("# A\n> A desc")
        
        result = await execute({}, tmp_path)
        
        text = result[0].text
        assert text.index("a-guide") < text.index("z-guide")
