"""
Tests für testing/run_tests.py
"""

import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from mcp.types import Tool, TextContent

from tools.testing.run_tests import get_tool_definition, execute
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
        assert tool.name == "nova_run_tests"
    
    def test_has_description(self, tmp_path: Path):
        """Tool hat Beschreibung."""
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "pytest" in tool.description.lower() or "test" in tool.description.lower()
    
    def test_has_input_schema(self, tmp_path: Path):
        """Tool hat Input-Schema."""
        tool = get_tool_definition(tmp_path)
        assert tool.inputSchema
        assert "properties" in tool.inputSchema
    
    def test_has_pattern_parameter(self, tmp_path: Path):
        """Tool hat pattern-Parameter."""
        tool = get_tool_definition(tmp_path)
        properties = tool.inputSchema.get("properties", {})
        assert "pattern" in properties
    
    def test_has_verbose_parameter(self, tmp_path: Path):
        """Tool hat verbose-Parameter."""
        tool = get_tool_definition(tmp_path)
        properties = tool.inputSchema.get("properties", {})
        assert "verbose" in properties
    
    def test_has_failfast_parameter(self, tmp_path: Path):
        """Tool hat failfast-Parameter."""
        tool = get_tool_definition(tmp_path)
        properties = tool.inputSchema.get("properties", {})
        assert "failfast" in properties
    
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
    async def test_calls_pytest(self, tmp_path: Path):
        """Ruft pytest auf."""
        mock_result = ProcessResult(returncode=0, stdout="1 passed", stderr="")
        with patch("tools.testing.run_tests.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            result = await execute({}, tmp_path)
            
            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "pytest" in call_args
    
    @pytest.mark.asyncio
    async def test_uses_quiet_mode_by_default(self, tmp_path: Path):
        """Nutzt -q Flag standardmäßig für schnelle Ausgabe."""
        mock_result = ProcessResult(returncode=0, stdout="OK", stderr="")
        with patch("tools.testing.run_tests.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            await execute({}, tmp_path)
            
            call_args = mock_run.call_args[0][0]
            assert "-q" in call_args
            assert "--tb=short" in call_args
    
    @pytest.mark.asyncio
    async def test_passes_verbose_flag(self, tmp_path: Path):
        """Übergibt -v Flag bei verbose=True (ersetzt -q)."""
        mock_result = ProcessResult(returncode=0, stdout="OK", stderr="")
        with patch("tools.testing.run_tests.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            await execute({"verbose": True}, tmp_path)
            
            call_args = mock_run.call_args[0][0]
            assert "-v" in call_args
    
    @pytest.mark.asyncio
    async def test_passes_failfast_flag(self, tmp_path: Path):
        """Übergibt -x Flag bei failfast=True."""
        mock_result = ProcessResult(returncode=0, stdout="OK", stderr="")
        with patch("tools.testing.run_tests.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            await execute({"failfast": True}, tmp_path)
            
            call_args = mock_run.call_args[0][0]
            assert "-x" in call_args
    
    @pytest.mark.asyncio
    async def test_passes_pattern_filter(self, tmp_path: Path):
        """Übergibt -k Pattern-Filter."""
        mock_result = ProcessResult(returncode=0, stdout="OK", stderr="")
        with patch("tools.testing.run_tests.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            await execute({"pattern": "test_worklog"}, tmp_path)
            
            call_args = mock_run.call_args[0][0]
            assert "-k" in call_args
            assert "test_worklog" in call_args
    
    @pytest.mark.asyncio
    async def test_returns_text_content(self, tmp_path: Path):
        """Gibt TextContent zurück."""
        mock_result = ProcessResult(returncode=0, stdout="3 passed", stderr="")
        with patch("tools.testing.run_tests.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            result = await execute({}, tmp_path)
            
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
    
    @pytest.mark.asyncio
    async def test_shows_passed_status(self, tmp_path: Path):
        """Zeigt Checkmark und Summary bei Erfolg."""
        mock_result = ProcessResult(returncode=0, stdout="3 passed", stderr="")
        with patch("tools.testing.run_tests.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            result = await execute({}, tmp_path)
            
            assert "✅" in result[0].text
            assert "passed" in result[0].text
    
    @pytest.mark.asyncio
    async def test_shows_failed_status(self, tmp_path: Path):
        """Zeigt FAILED bei returncode != 0."""
        mock_result = ProcessResult(returncode=1, stdout="1 failed", stderr="")
        with patch("tools.testing.run_tests.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            result = await execute({}, tmp_path)
            
            assert "FAILED" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handles_timeout(self, tmp_path: Path):
        """Zeigt TIMEOUT bei Timeout."""
        mock_result = ProcessResult(returncode=-1, stdout="", stderr="", timed_out=True, error="Process timed out after 60s")
        with patch("tools.testing.run_tests.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            result = await execute({}, tmp_path)
            
            assert "TIMEOUT" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handles_error(self, tmp_path: Path):
        """Zeigt ERROR bei Fehler."""
        mock_result = ProcessResult(returncode=-1, stdout="", stderr="", error="Command not found")
        with patch("tools.testing.run_tests.run_async", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            result = await execute({}, tmp_path)
            
            assert "ERROR" in result[0].text
