"""
Tests für tools/sessions/summarize_week.py
Testet Wochen-Zusammenfassung mit gemockten Dependencies.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from mcp.types import Tool, TextContent


class TestToolDefinition:
    """Tests für get_tool_definition()."""
    
    def test_returns_tool_instance(self, tmp_path):
        """Gibt Tool-Instanz zurück."""
        from tools.sessions.summarize_week import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert isinstance(tool, Tool)
    
    def test_has_correct_name(self, tmp_path):
        """Tool hat korrekten Namen."""
        from tools.sessions.summarize_week import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert tool.name == "nova_summarize_week"
    
    def test_has_description(self, tmp_path):
        """Tool hat Beschreibung."""
        from tools.sessions.summarize_week import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "Woche" in tool.description
    
    def test_no_required_params(self, tmp_path):
        """Keine required Parameter."""
        from tools.sessions.summarize_week import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert tool.inputSchema["required"] == []
    
    def test_has_last_week_param(self, tmp_path):
        """last_week Parameter vorhanden."""
        from tools.sessions.summarize_week import get_tool_definition
        tool = get_tool_definition(tmp_path)
        props = tool.inputSchema["properties"]
        assert "last_week" in props
        assert props["last_week"]["default"] is False
    
    def test_has_days_param(self, tmp_path):
        """days Parameter vorhanden."""
        from tools.sessions.summarize_week import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert "days" in tool.inputSchema["properties"]
    
    def test_has_from_date_param(self, tmp_path):
        """from_date Parameter vorhanden."""
        from tools.sessions.summarize_week import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert "from_date" in tool.inputSchema["properties"]
    
    def test_has_to_date_param(self, tmp_path):
        """to_date Parameter vorhanden."""
        from tools.sessions.summarize_week import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert "to_date" in tool.inputSchema["properties"]
    
    def test_has_llm_param_default_true(self, tmp_path):
        """llm Parameter mit default True."""
        from tools.sessions.summarize_week import get_tool_definition
        tool = get_tool_definition(tmp_path)
        props = tool.inputSchema["properties"]
        assert "llm" in props
        assert props["llm"]["default"] is True
    
    def test_has_raw_param(self, tmp_path):
        """raw Parameter vorhanden."""
        from tools.sessions.summarize_week import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert "raw" in tool.inputSchema["properties"]


class TestExecuteCommandBuilding:
    """Tests für Command-Aufbau."""
    
    @pytest.mark.asyncio
    async def test_builds_command_with_script_path(self, tmp_path):
        """Erstellt Befehl mit korrektem Script-Pfad."""
        import asyncio
        
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        mock_proc.returncode = 0
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc) as mock_exec:
            from tools.sessions.summarize_week import execute
            await execute({}, tmp_path)
        
        # Prüfe dass python und script path korrekt sind
        call_args = mock_exec.call_args[0]
        assert call_args[0] == "python"
        assert "summarize_week.py" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_adds_last_week_flag(self, tmp_path):
        """Fügt --last Flag hinzu wenn last_week=True."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc) as mock_exec:
            from tools.sessions.summarize_week import execute
            await execute({"last_week": True}, tmp_path)
        
        call_args = mock_exec.call_args[0]
        assert "--last" in call_args
    
    @pytest.mark.asyncio
    async def test_adds_days_argument(self, tmp_path):
        """Fügt --days N hinzu."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc) as mock_exec:
            from tools.sessions.summarize_week import execute
            await execute({"days": 14}, tmp_path)
        
        call_args = mock_exec.call_args[0]
        assert "--days" in call_args
        assert "14" in call_args
    
    @pytest.mark.asyncio
    async def test_adds_from_date_argument(self, tmp_path):
        """Fügt --from YYYY-MM-DD hinzu."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc) as mock_exec:
            from tools.sessions.summarize_week import execute
            await execute({"from_date": "2025-02-01"}, tmp_path)
        
        call_args = mock_exec.call_args[0]
        assert "--from" in call_args
        assert "2025-02-01" in call_args
    
    @pytest.mark.asyncio
    async def test_adds_to_date_argument(self, tmp_path):
        """Fügt --to YYYY-MM-DD hinzu."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc) as mock_exec:
            from tools.sessions.summarize_week import execute
            await execute({"to_date": "2025-02-10"}, tmp_path)
        
        call_args = mock_exec.call_args[0]
        assert "--to" in call_args
        assert "2025-02-10" in call_args
    
    @pytest.mark.asyncio
    async def test_adds_llm_flag_by_default(self, tmp_path):
        """Fügt --llm Flag hinzu (default True)."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc) as mock_exec:
            from tools.sessions.summarize_week import execute
            await execute({}, tmp_path)
        
        call_args = mock_exec.call_args[0]
        assert "--llm" in call_args
    
    @pytest.mark.asyncio
    async def test_adds_raw_flag(self, tmp_path):
        """Fügt --raw Flag hinzu."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc) as mock_exec:
            from tools.sessions.summarize_week import execute
            await execute({"raw": True}, tmp_path)
        
        call_args = mock_exec.call_args[0]
        assert "--raw" in call_args


class TestExecuteOutput:
    """Tests für Output-Verarbeitung."""
    
    @pytest.mark.asyncio
    async def test_returns_stdout(self, tmp_path):
        """Gibt stdout zurück."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"Week summary output", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
            from tools.sessions.summarize_week import execute
            result = await execute({}, tmp_path)
        
        assert "Week summary output" in result[0].text
    
    @pytest.mark.asyncio
    async def test_includes_stderr(self, tmp_path):
        """Inkludiert auch stderr im Output."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"stdout", b"stderr info"))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
            from tools.sessions.summarize_week import execute
            result = await execute({}, tmp_path)
        
        assert "stdout" in result[0].text
        assert "stderr info" in result[0].text
    
    @pytest.mark.asyncio
    async def test_returns_no_output_message(self, tmp_path):
        """Gibt 'No output' zurück wenn leer."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
            from tools.sessions.summarize_week import execute
            result = await execute({}, tmp_path)
        
        assert result[0].text == "No output"


class TestReturnType:
    """Tests für korrekten Return-Type."""
    
    @pytest.mark.asyncio
    async def test_returns_list_of_text_content(self, tmp_path):
        """Gibt Liste von TextContent zurück."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"test", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
            from tools.sessions.summarize_week import execute
            result = await execute({}, tmp_path)
        
        assert isinstance(result, list)
        assert len(result) >= 1
        assert all(isinstance(item, TextContent) for item in result)


class TestSubprocessCall:
    """Tests für Subprocess-Aufrufe."""
    
    @pytest.mark.asyncio
    async def test_uses_pipes_for_output(self, tmp_path):
        """Verwendet PIPE für stdout und stderr."""
        import asyncio
        
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc) as mock_exec:
            from tools.sessions.summarize_week import execute
            await execute({}, tmp_path)
        
        call_kwargs = mock_exec.call_args[1]
        assert call_kwargs["stdout"] == asyncio.subprocess.PIPE
        assert call_kwargs["stderr"] == asyncio.subprocess.PIPE
