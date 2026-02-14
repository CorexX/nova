"""
Tests fÃ¼r health/health_check.py und health/checks.py
"""

import pytest
from pathlib import Path
from datetime import datetime
from mcp.types import Tool, TextContent

from tools.health.health_check import get_tool_definition, execute
from tools.health.checks import (
    CheckResult,
    CheckGroup,
    check_vault_index,
    check_worklog_today,
    check_current_freshness,
    check_core_files,
    check_n8n_optional,
)


# =============================================================================
# TESTS: get_tool_definition
# =============================================================================

class TestToolDefinition:
    """Tests fÃ¼r die Tool-Definition."""
    
    def test_returns_tool_instance(self, tmp_path: Path):
        """Tool-Definition gibt Tool-Instanz zurÃ¼ck."""
        tool = get_tool_definition(tmp_path)
        assert isinstance(tool, Tool)
    
    def test_has_correct_name(self, tmp_path: Path):
        """Tool hat korrekten Namen."""
        tool = get_tool_definition(tmp_path)
        assert tool.name == "nova_health_check"
    
    def test_has_description(self, tmp_path: Path):
        """Tool hat Beschreibung."""
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "Status" in tool.description or "Health" in tool.description
    
    def test_no_required_params(self, tmp_path: Path):
        """Keine Parameter sind required."""
        tool = get_tool_definition(tmp_path)
        required = tool.inputSchema.get("required", [])
        assert len(required) == 0


# =============================================================================
# TESTS: CheckResult und CheckGroup
# =============================================================================

class TestCheckResult:
    """Tests fÃ¼r CheckResult."""
    
    def test_creates_check_result(self):
        """Erstellt CheckResult korrekt."""
        result = CheckResult(
            name="Test",
            status="ok",
            message="All good"
        )
        assert result.name == "Test"
        assert result.status == "ok"
        assert result.message == "All good"
    
    def test_optional_fields_have_defaults(self):
        """Optionale Felder haben Defaults."""
        result = CheckResult(
            name="Test",
            status="ok",
            message="OK"
        )
        assert result.detail == ""
        assert result.action == ""
        assert result.group == ""


class TestCheckGroup:
    """Tests fÃ¼r CheckGroup."""
    
    def test_status_ok_when_all_ok(self):
        """Status ok wenn alle Checks ok."""
        group = CheckGroup(
            name="Test",
            checks=[
                CheckResult("A", "ok", "OK"),
                CheckResult("B", "ok", "OK"),
            ]
        )
        assert group.status == "ok"
    
    def test_status_warning_when_any_warning(self):
        """Status warning wenn ein Check warning."""
        group = CheckGroup(
            name="Test",
            checks=[
                CheckResult("A", "ok", "OK"),
                CheckResult("B", "warning", "Warn"),
            ]
        )
        assert group.status == "warning"
    
    def test_status_error_when_any_error(self):
        """Status error wenn ein Check error."""
        group = CheckGroup(
            name="Test",
            checks=[
                CheckResult("A", "ok", "OK"),
                CheckResult("B", "warning", "Warn"),
                CheckResult("C", "error", "Err"),
            ]
        )
        assert group.status == "error"


# =============================================================================
# TESTS: Individual Checks
# =============================================================================

class TestCheckVaultIndex:
    """Tests fÃ¼r check_vault_index."""
    
    def test_error_when_no_hash_file(self, tmp_path: Path):
        """Error wenn file_hashes.json fehlt."""
        result = check_vault_index(tmp_path)
        assert result.status == "error"
        assert "nicht" in result.message.lower() or "fehlt" in result.detail.lower()
    
    def test_ok_when_hash_file_exists(self, tmp_path: Path):
        """OK wenn file_hashes.json existiert."""
        index_dir = tmp_path / ".nova" / "index"
        index_dir.mkdir(parents=True)
        (index_dir / "file_hashes.json").write_text('{"file1.md": "hash1", "file2.md": "hash2"}')
        
        result = check_vault_index(tmp_path)
        assert result.status == "ok"
        assert "2" in result.message
    
    def test_warning_when_empty_index(self, tmp_path: Path):
        """Warning wenn Index leer."""
        index_dir = tmp_path / ".nova" / "index"
        index_dir.mkdir(parents=True)
        (index_dir / "file_hashes.json").write_text('{}')
        
        result = check_vault_index(tmp_path)
        assert result.status == "warning"


class TestCheckWorklogToday:
    """Tests fÃ¼r check_worklog_today."""
    
    def test_warning_when_no_worklog(self, tmp_path: Path):
        """Warning wenn WORKLOG.md fehlt."""
        result = check_worklog_today(tmp_path)
        assert result.status == "warning"
    
    def test_counts_today_entries(self, tmp_path: Path):
        """ZÃ¤hlt heutige EintrÃ¤ge."""
        knowledge = tmp_path / "nova-knowledge"
        knowledge.mkdir()
        today = datetime.now().strftime("%Y-%m-%d")
        content = f"""# WORKLOG

## {today}

- 09:00 Started work
- 10:30 Meeting
- 14:00 Coding
"""
        (knowledge / "WORKLOG.md").write_text(content, encoding="utf-8")
        
        result = check_worklog_today(tmp_path)
        assert result.status == "ok"
        # Sollte mindestens 1 Eintrag finden (das Datum selbst)
        assert "Heute" in result.message
    
    def test_zero_entries_today(self, tmp_path: Path):
        """OK mit 0 EintrÃ¤ge wenn kein heutiges Datum."""
        knowledge = tmp_path / "nova-knowledge"
        knowledge.mkdir()
        content = """# WORKLOG

## 2020-01-01

- 09:00 Old entry
"""
        (knowledge / "WORKLOG.md").write_text(content, encoding="utf-8")
        
        result = check_worklog_today(tmp_path)
        assert result.status == "ok"
        assert "0" in result.message


class TestCheckCurrentFreshness:
    """Tests fÃ¼r check_current_freshness."""
    
    def test_error_when_no_current(self, tmp_path: Path):
        """Error wenn CURRENT.md fehlt."""
        result = check_current_freshness(tmp_path)
        assert result.status == "error"
    
    def test_ok_when_current_is_fresh(self, tmp_path: Path):
        """OK wenn CURRENT.md aktuell ist."""
        knowledge = tmp_path / "nova-knowledge"
        knowledge.mkdir()
        today = datetime.now().strftime("%Y-%m-%d")
        content = f"""# CURRENT

Tasks for today

*Letzte Aktualisierung: {today}*
"""
        (knowledge / "CURRENT.md").write_text(content, encoding="utf-8")
        
        result = check_current_freshness(tmp_path)
        assert result.status == "ok"


class TestCheckN8nOptional:
    """Tests fuer optionalen n8n Health-Check."""

    def test_info_when_not_configured(self, tmp_path: Path):
        result = check_n8n_optional(tmp_path)
        assert result.status == "info"
        assert "optional" in result.message.lower()

    def test_warning_when_partially_configured(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("N8N_BASE_URL", "https://n8n.home")
        monkeypatch.delenv("N8N_API_KEY", raising=False)
        result = check_n8n_optional(tmp_path)
        assert result.status == "warning"

    def test_ok_when_fully_configured(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("N8N_BASE_URL", "https://n8n.home")
        monkeypatch.setenv("N8N_API_KEY", "key")
        result = check_n8n_optional(tmp_path)
        assert result.status == "ok"


class TestCheckCoreFiles:
    """Tests fuer check_core_files mit Codex/GitHub Instructions."""

    def test_ok_when_agents_md_exists(self, tmp_path: Path):
        (tmp_path / "mcp").mkdir()
        (tmp_path / "core").mkdir()
        (tmp_path / "core" / "CORE.md").write_text("# CORE", encoding="utf-8")
        (tmp_path / "meta").mkdir()
        (tmp_path / "meta" / "PRINCIPLES.md").write_text("# PRINCIPLES", encoding="utf-8")
        (tmp_path / "AGENTS.md").write_text("# AGENTS", encoding="utf-8")

        result = check_core_files(tmp_path)
        assert result.status == "ok"

    def test_ok_when_github_copilot_instructions_exists(self, tmp_path: Path):
        (tmp_path / "mcp").mkdir()
        (tmp_path / "core").mkdir()
        (tmp_path / "core" / "CORE.md").write_text("# CORE", encoding="utf-8")
        (tmp_path / "meta").mkdir()
        (tmp_path / "meta" / "PRINCIPLES.md").write_text("# PRINCIPLES", encoding="utf-8")
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "copilot-instructions.md").write_text("# CI", encoding="utf-8")

        result = check_core_files(tmp_path)
        assert result.status == "ok"


# =============================================================================
# TESTS: execute
# =============================================================================

class TestExecute:
    """Tests fÃ¼r die Tool-AusfÃ¼hrung.
    
    HINWEIS: Execute-Tests sind aufwendig weil sie das volle Health-Check
    System aufrufen inkl. ChromaDB PrÃ¼fung. Bei Bedarf mit Mock erweitern.
    """
    
    @pytest.fixture
    def minimal_workspace(self, tmp_path: Path):
        """Minimaler Workspace."""
        # nova-core mit Index
        index_dir = tmp_path / ".nova" / "index"
        index_dir.mkdir(parents=True)
        (index_dir / "file_hashes.json").write_text('{"a.md": "h1"}')
        
        # nova-knowledge
        knowledge = tmp_path / "nova-knowledge"
        knowledge.mkdir()
        (knowledge / "WORKLOG.md").write_text("# Worklog\n", encoding="utf-8")
        
        today = datetime.now().strftime("%Y-%m-%d")
        (knowledge / "CURRENT.md").write_text(f"# Current\n\n*Letzte Aktualisierung: {today}*", encoding="utf-8")
        (knowledge / "TICKETS.md").write_text("# Tickets\n", encoding="utf-8")
        
        # Collections
        (knowledge / "projects" / "test").mkdir(parents=True)
        (knowledge / "areas" / "learning").mkdir(parents=True)
        
        # Playbooks, Guides, Skills
        (tmp_path / "nova-core" / "playbooks").mkdir(parents=True)
        (tmp_path / "nova-core" / "guides").mkdir(parents=True)
        (tmp_path / "nova-core" / "skills").mkdir(parents=True)
        
        return tmp_path
    
    @pytest.mark.skip(reason="Execute tests require full health check system, too slow for unit tests")
    @pytest.mark.asyncio
    async def test_returns_text_content(self, minimal_workspace: Path):
        """Gibt TextContent zurÃ¼ck."""
        result = await execute({}, minimal_workspace)
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
    
    @pytest.mark.skip(reason="Execute tests require full health check system, too slow for unit tests")
    @pytest.mark.asyncio
    async def test_includes_status_header(self, minimal_workspace: Path):
        """EnthÃ¤lt Status-Header."""
        result = await execute({}, minimal_workspace)
        
        assert "System Status" in result[0].text
    
    @pytest.mark.skip(reason="Execute tests require full health check system, too slow for unit tests")
    @pytest.mark.asyncio
    async def test_includes_summary(self, minimal_workspace: Path):
        """EnthÃ¤lt Zusammenfassung."""
        result = await execute({}, minimal_workspace)
        
        assert "Summary" in result[0].text
    
    @pytest.mark.skip(reason="Execute tests require full health check system, too slow for unit tests")
    @pytest.mark.asyncio
    async def test_shows_grouped_results(self, minimal_workspace: Path):
        """Zeigt gruppierte Ergebnisse."""
        result = await execute({}, minimal_workspace)
        text = result[0].text
        
        # Sollte Gruppen-Header enthalten
        assert "CORE" in text or "VAULT" in text or "Component" in text
    
    @pytest.mark.skip(reason="Execute tests require full health check system, too slow for unit tests")
    @pytest.mark.asyncio
    async def test_handles_empty_workspace(self, tmp_path: Path):
        """Behandelt leeren Workspace."""
        result = await execute({}, tmp_path)
        
        # Sollte nicht crashen
        assert isinstance(result[0], TextContent)
        # Sollte Fehler/Warnungen zeigen
        assert "âŒ" in result[0].text or "âš ï¸" in result[0].text or "Error" in result[0].text

