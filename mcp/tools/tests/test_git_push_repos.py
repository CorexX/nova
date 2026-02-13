"""
Tests für git/push_repos.py
"""

import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from mcp.types import Tool, TextContent

from tools.git.push_repos import get_tool_definition, execute
from tools.utils.subprocess_utils import ProcessResult


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
        assert tool.name == "nova_git_push_repos"
    
    def test_has_description(self, tmp_path: Path):
        """Tool hat Beschreibung."""
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "push" in tool.description.lower() or "Push" in tool.description
    
    def test_has_input_schema(self, tmp_path: Path):
        """Tool hat Input-Schema."""
        tool = get_tool_definition(tmp_path)
        assert tool.inputSchema
        assert "properties" in tool.inputSchema
    
    def test_has_path_parameter(self, tmp_path: Path):
        """Tool hat path-Parameter."""
        tool = get_tool_definition(tmp_path)
        properties = tool.inputSchema.get("properties", {})
        assert "path" in properties
    
    def test_has_dry_run_parameter(self, tmp_path: Path):
        """Tool hat dry_run-Parameter."""
        tool = get_tool_definition(tmp_path)
        properties = tool.inputSchema.get("properties", {})
        assert "dry_run" in properties
    
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
    async def test_calls_subprocess(self, tmp_path: Path):
        """Ruft subprocess mit korrektem Skript auf."""
        # Create fake script path
        skills_dir = tmp_path / "nova-core" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "git_push_repos.py").write_text("# fake script")
        
        mock_result = ProcessResult(returncode=0, stdout="OK", stderr="")
        with patch("tools.git.push_repos.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            result = await execute({}, tmp_path)
            
            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "git_push_repos.py" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_passes_dry_run_flag(self, tmp_path: Path):
        """Übergibt --dry-run Flag."""
        skills_dir = tmp_path / "nova-core" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "git_push_repos.py").write_text("# fake script")
        
        mock_result = ProcessResult(returncode=0, stdout="OK", stderr="")
        with patch("tools.git.push_repos.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            await execute({"dry_run": True}, tmp_path)
            
            call_args = mock_run.call_args[0][0]
            assert "--dry-run" in call_args
    
    @pytest.mark.asyncio
    async def test_passes_message(self, tmp_path: Path):
        """Übergibt Commit-Message."""
        skills_dir = tmp_path / "nova-core" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "git_push_repos.py").write_text("# fake script")
        
        mock_result = ProcessResult(returncode=0, stdout="OK", stderr="")
        with patch("tools.git.push_repos.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            await execute({"message": "Test commit"}, tmp_path)
            
            call_args = mock_run.call_args[0][0]
            assert "-m" in call_args
            assert "Test commit" in call_args
    
    @pytest.mark.asyncio
    async def test_returns_text_content(self, tmp_path: Path):
        """Gibt TextContent zurück."""
        skills_dir = tmp_path / "nova-core" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "git_push_repos.py").write_text("# fake script")
        
        mock_result = ProcessResult(returncode=0, stdout="Pushed 2 repos", stderr="")
        with patch("tools.git.push_repos.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            result = await execute({}, tmp_path)
            
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Pushed 2 repos" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handles_timeout(self, tmp_path: Path):
        """Zeigt TIMEOUT bei Timeout."""
        skills_dir = tmp_path / "nova-core" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "git_push_repos.py").write_text("# fake script")
        
        mock_result = ProcessResult(returncode=-1, stdout="", stderr="", timed_out=True, error="Process timed out after 120s")
        with patch("tools.git.push_repos.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            result = await execute({}, tmp_path)
            
            assert "TIMEOUT" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handles_error(self, tmp_path: Path):
        """Zeigt ERROR bei Fehler."""
        skills_dir = tmp_path / "nova-core" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "git_push_repos.py").write_text("# fake script")
        
        mock_result = ProcessResult(returncode=-1, stdout="", stderr="", error="Command not found")
        with patch("tools.git.push_repos.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            result = await execute({}, tmp_path)
            
            assert "ERROR" in result[0].text
