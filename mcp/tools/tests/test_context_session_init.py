"""
Tests für context/session_init.py
"""

import pytest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock
from mcp.types import Tool, TextContent

from tools.context.session_init import (
    get_tool_definition, 
    execute,
    _extract_section,
    _get_top_principles,
    _get_scope,
    _get_core_persona
)


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
        assert tool.name == "nova_session_init"
    
    def test_has_description(self, tmp_path: Path):
        """Tool hat Beschreibung."""
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "Session" in tool.description
    
    def test_no_required_params(self, tmp_path: Path):
        """Keine Parameter sind required."""
        tool = get_tool_definition(tmp_path)
        required = tool.inputSchema.get("required", [])
        assert len(required) == 0


# =============================================================================
# TESTS: Helper Functions
# =============================================================================

class TestExtractSection:
    """Tests für _extract_section."""
    
    def test_extracts_section_until_separator(self):
        """Extrahiert Sektion bis ---."""
        content = """# Doc

## Target

Content here

---

## Other
"""
        result = _extract_section(content, "Target")
        assert "Target" in result
        assert "Content here" in result
        assert "Other" not in result
    
    def test_returns_none_for_missing_section(self):
        """Gibt None für fehlende Sektion."""
        content = "# Doc\n\n## Other\n\nContent"
        result = _extract_section(content, "Missing")
        assert result is None


class TestGetTopPrinciples:
    """Tests für _get_top_principles."""
    
    def test_extracts_principles_table(self):
        """Extrahiert Prinzipien-Tabelle."""
        content = """# Doc

## Kernprinzipien

| # | Prinzip |
|---|---------|
| 1 | First |
| 2 | Second |

### Details
"""
        result = _get_top_principles(content)
        assert "Kernprinzipien" in result
        assert "First" in result
        assert "Second" in result
    
    def test_handles_missing_table(self):
        """Behandelt fehlende Tabelle."""
        content = "# No table here"
        result = _get_top_principles(content)
        assert "nicht gefunden" in result


class TestGetScope:
    """Tests für _get_scope."""
    
    def test_extracts_scope_section(self):
        """Extrahiert Schreib-Scope Sektion."""
        content = """# Doc

## Schreib-Scope

| Path | Allowed |
|------|---------|
| /a | yes |

---

## Other
"""
        result = _get_scope(content)
        assert "Schreib-Scope" in result
        assert "/a" in result
    
    def test_handles_missing_scope(self):
        """Behandelt fehlende Sektion."""
        content = "# No scope"
        result = _get_scope(content)
        assert "nicht gefunden" in result


class TestGetCorePersona:
    """Tests für _get_core_persona."""
    
    def test_extracts_persona(self):
        """Extrahiert Persona-Sektion."""
        content = """# CORE

## Wer du bist

Du bist NOVA.

# Persona Overlay: soviet

## Antwortmuster

- Struktur: `Status` -> `Lage` -> `Vorschlag` -> `Bestaetigung`

---

## Other
"""
        result = _get_core_persona(content)
        assert "Wer du bist" in result
        assert "NOVA" in result
        assert "Persona Overlay" in result
        assert "Bestaetigung" in result
    
    def test_handles_missing_persona(self):
        """Behandelt fehlende Persona."""
        content = "# No persona"
        result = _get_core_persona(content)
        assert "nicht gefunden" in result


# =============================================================================
# TESTS: execute
# =============================================================================

class TestExecute:
    """Tests für die Tool-Ausführung."""
    
    @pytest.fixture
    def minimal_workspace(self, tmp_path: Path):
        """Minimaler Workspace mit erforderlichen Dateien."""
        # nova-core/core/
        core_dir = tmp_path / "nova-core" / "core"
        core_dir.mkdir(parents=True)
        
        (core_dir / "CORE.md").write_text("""# NOVA

## Wer du bist

Du bist NOVA, ein Tech-Kommandant.

# Persona Overlay: soviet

## Antwortmuster

- Struktur: `Status` -> `Lage` -> `Vorschlag` -> `Bestaetigung`

---
""", encoding="utf-8")
        
        (core_dir / "PRINCIPLES.md").write_text("""# Principles

## Kernprinzipien

| # | Prinzip |
|---|---------|
| 1 | Persist |
| 2 | Append |

### Details

---

## Schreib-Scope

| Pfad | Erlaubt |
|------|---------|
| WORKLOG | ja |

---

## Lade-Regeln

| Wenn | Dann |
|------|------|
| Kunde erwaehnt | Lade Kunde |

""", encoding="utf-8")
        
        # nova-knowledge/
        knowledge_dir = tmp_path / "nova-knowledge"
        knowledge_dir.mkdir()
        
        (knowledge_dir / "CURRENT.md").write_text("# Current\n\n- Task 1", encoding="utf-8")
        (knowledge_dir / "TICKETS.md").write_text("""# Tickets

## Aktive Tickets

| Ticket | Bereich |
|--------|---------|
| ABC-1 | Test |

---

## Buchungsregeln

| Bereich | Ticket |
|---------|--------|
| Intern | INT-1 |

---
""", encoding="utf-8")
        
        # Kunden
        (knowledge_dir / "projects" / "alpha").mkdir(parents=True)
        (knowledge_dir / "areas" / "learning").mkdir(parents=True)
        
        return tmp_path
    
    @pytest.mark.asyncio
    async def test_returns_text_content(self, minimal_workspace: Path):
        """Gibt TextContent zurück."""
        # Mock health check um externe Abhängigkeit zu vermeiden
        with patch("tools.context.session_init._get_health_check") as mock_health:
            mock_checks = AsyncMock()
            mock_checks.run_grouped_checks = AsyncMock(return_value={})
            mock_checks.format_grouped_simple = lambda x: "✅ OK"
            mock_checks.get_actions_from_groups = lambda x: []
            mock_health.return_value = mock_checks
            
            result = await execute({}, minimal_workspace)
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
    
    @pytest.mark.asyncio
    async def test_includes_date_and_week(self, minimal_workspace: Path):
        """Enthält Datum und Kalenderwoche."""
        with patch("tools.context.session_init._get_health_check") as mock_health:
            mock_checks = AsyncMock()
            mock_checks.run_grouped_checks = AsyncMock(return_value={})
            mock_checks.format_grouped_simple = lambda x: "✅ OK"
            mock_checks.get_actions_from_groups = lambda x: []
            mock_health.return_value = mock_checks
            
            result = await execute({}, minimal_workspace)
        
        text = result[0].text
        assert "KW" in text
        assert "2026" in text or "202" in text  # Jahr
    
    @pytest.mark.asyncio
    async def test_includes_persona(self, minimal_workspace: Path):
        """Enthält Persona aus CORE.md."""
        with patch("tools.context.session_init._get_health_check") as mock_health:
            mock_checks = AsyncMock()
            mock_checks.run_grouped_checks = AsyncMock(return_value={})
            mock_checks.format_grouped_simple = lambda x: "✅ OK"
            mock_checks.get_actions_from_groups = lambda x: []
            mock_health.return_value = mock_checks
            
            result = await execute({}, minimal_workspace)
        
        assert "Wer du bist" in result[0].text
        assert "NOVA" in result[0].text
        assert "Persona Overlay" in result[0].text
        assert "Bestaetigung" in result[0].text
    
    @pytest.mark.asyncio
    async def test_includes_principles(self, minimal_workspace: Path):
        """Enthält Kernprinzipien."""
        with patch("tools.context.session_init._get_health_check") as mock_health:
            mock_checks = AsyncMock()
            mock_checks.run_grouped_checks = AsyncMock(return_value={})
            mock_checks.format_grouped_simple = lambda x: "✅ OK"
            mock_checks.get_actions_from_groups = lambda x: []
            mock_health.return_value = mock_checks
            
            result = await execute({}, minimal_workspace)
        
        assert "Kernprinzipien" in result[0].text
        assert "Persist" in result[0].text
    
    @pytest.mark.asyncio
    async def test_includes_scope(self, minimal_workspace: Path):
        """Enthält Schreib-Scope."""
        with patch("tools.context.session_init._get_health_check") as mock_health:
            mock_checks = AsyncMock()
            mock_checks.run_grouped_checks = AsyncMock(return_value={})
            mock_checks.format_grouped_simple = lambda x: "✅ OK"
            mock_checks.get_actions_from_groups = lambda x: []
            mock_health.return_value = mock_checks
            
            result = await execute({}, minimal_workspace)
        
        assert "Schreib-Scope" in result[0].text
    
    @pytest.mark.asyncio
    async def test_includes_current_focus(self, minimal_workspace: Path):
        """Enthält aktuellen Fokus aus CURRENT.md."""
        with patch("tools.context.session_init._get_health_check") as mock_health:
            mock_checks = AsyncMock()
            mock_checks.run_grouped_checks = AsyncMock(return_value={})
            mock_checks.format_grouped_simple = lambda x: "✅ OK"
            mock_checks.get_actions_from_groups = lambda x: []
            mock_health.return_value = mock_checks
            
            result = await execute({}, minimal_workspace)
        
        assert "Task 1" in result[0].text
    
    @pytest.mark.asyncio
    async def test_includes_collections_list(self, minimal_workspace: Path):
        """Enthaelt Collections-Liste."""
        with patch("tools.context.session_init._get_health_check") as mock_health:
            mock_checks = AsyncMock()
            mock_checks.run_grouped_checks = AsyncMock(return_value={})
            mock_checks.format_grouped_simple = lambda x: "??? OK"
            mock_checks.get_actions_from_groups = lambda x: []
            mock_health.return_value = mock_checks
            
            result = await execute({}, minimal_workspace)
        
        assert "Collections" in result[0].text
        assert "projects" in result[0].text
        assert "areas" in result[0].text

    @pytest.mark.asyncio
    async def test_includes_startklar(self, minimal_workspace: Path):
        """Enthält Startklar-Marker."""
        with patch("tools.context.session_init._get_health_check") as mock_health:
            mock_checks = AsyncMock()
            mock_checks.run_grouped_checks = AsyncMock(return_value={})
            mock_checks.format_grouped_simple = lambda x: "✅ OK"
            mock_checks.get_actions_from_groups = lambda x: []
            mock_health.return_value = mock_checks
            
            result = await execute({}, minimal_workspace)
        
        assert "Startklar" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handles_missing_core(self, tmp_path: Path):
        """Behandelt fehlende CORE.md."""
        (tmp_path / "nova-knowledge").mkdir()
        
        with patch("tools.context.session_init._get_health_check") as mock_health:
            mock_checks = AsyncMock()
            mock_checks.run_grouped_checks = AsyncMock(return_value={})
            mock_checks.format_grouped_simple = lambda x: "✅ OK"
            mock_checks.get_actions_from_groups = lambda x: []
            mock_health.return_value = mock_checks
            
            result = await execute({}, tmp_path)
        
        assert "CORE.md nicht gefunden" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handles_health_check_error(self, minimal_workspace: Path):
        """Behandelt Health-Check Fehler gracefully."""
        with patch("tools.context.session_init._get_health_check") as mock_health:
            mock_health.side_effect = Exception("Test error")
            
            result = await execute({}, minimal_workspace)
        
        # Sollte nicht crashen
        assert isinstance(result[0], TextContent)
        assert "fehlgeschlagen" in result[0].text or "Exception" in result[0].text

    @pytest.mark.asyncio
    async def test_auto_index_runs_when_search_enabled(self, minimal_workspace: Path):
        """Führt Auto-Indexing aus wenn Search aktiviert ist."""
        mock_index_tool = AsyncMock()
        mock_index_tool.execute = AsyncMock(
            return_value=[TextContent(type="text", text="✅ Index aktualisiert\n\n| Metrik | Wert |")]
        )

        with patch("tools.context.session_init._get_index_vault", return_value=mock_index_tool):
            with patch("tools.context.session_init._get_health_check") as mock_health:
                mock_checks = AsyncMock()
                mock_checks.run_grouped_checks = AsyncMock(return_value={})
                mock_checks.format_grouped_simple = lambda x: "✅ OK"
                mock_checks.get_actions_from_groups = lambda x: []
                mock_health.return_value = mock_checks

                result = await execute({}, minimal_workspace)

        mock_index_tool.execute.assert_awaited_once_with({"force": False}, minimal_workspace)
        assert "## Index Status" in result[0].text
        assert "✅ Auto-Index: aktualisiert (inkrementell)" in result[0].text

    @pytest.mark.asyncio
    async def test_auto_index_skipped_when_search_disabled(self, minimal_workspace: Path):
        """Überspringt Auto-Indexing wenn Search deaktiviert ist."""
        fake_paths = SimpleNamespace(
            knowledge_root=minimal_workspace / "nova-knowledge",
            core_md=minimal_workspace / "nova-core" / "core" / "CORE.md",
            principles_md=minimal_workspace / "nova-core" / "core" / "PRINCIPLES.md",
            search_enabled=False,
        )

        with patch("tools.context.session_init.resolve_paths", return_value=fake_paths):
            with patch("tools.context.session_init._get_index_vault") as mock_get_index:
                with patch("tools.context.session_init._get_health_check") as mock_health:
                    mock_checks = AsyncMock()
                    mock_checks.run_grouped_checks = AsyncMock(return_value={})
                    mock_checks.format_grouped_simple = lambda x: "✅ OK"
                    mock_checks.get_actions_from_groups = lambda x: []
                    mock_health.return_value = mock_checks

                    result = await execute({}, minimal_workspace)

        mock_get_index.assert_not_called()
        assert "## Index Status" in result[0].text
        assert "Indexing übersprungen (search.enabled=false)" in result[0].text

    @pytest.mark.asyncio
    async def test_auto_index_failure_is_non_blocking(self, minimal_workspace: Path):
        """Index-Fehler blockiert Session-Init nicht."""
        with patch("tools.context.session_init._get_index_vault", side_effect=RuntimeError("boom")):
            with patch("tools.context.session_init._get_health_check") as mock_health:
                mock_checks = AsyncMock()
                mock_checks.run_grouped_checks = AsyncMock(return_value={})
                mock_checks.format_grouped_simple = lambda x: "✅ OK"
                mock_checks.get_actions_from_groups = lambda x: []
                mock_health.return_value = mock_checks

                result = await execute({}, minimal_workspace)

        assert "## Index Status" in result[0].text
        assert "⚠️ Auto-Index fehlgeschlagen: RuntimeError" in result[0].text
        assert "Startklar" in result[0].text
        assert "## System Status" in result[0].text

    @pytest.mark.asyncio
    async def test_health_check_still_runs_after_index_failure(self, minimal_workspace: Path):
        """Health-Check läuft auch wenn Auto-Indexing fehlschlägt."""
        with patch("tools.context.session_init._get_index_vault", side_effect=Exception("index failed")):
            with patch("tools.context.session_init._get_health_check") as mock_health:
                mock_checks = AsyncMock()
                mock_checks.run_grouped_checks = AsyncMock(return_value={"SEARCH": []})
                mock_checks.format_grouped_simple = lambda x: "✅ Health läuft"
                mock_checks.get_actions_from_groups = lambda x: []
                mock_health.return_value = mock_checks

                result = await execute({}, minimal_workspace)

        mock_checks.run_grouped_checks.assert_awaited_once_with(minimal_workspace)
        assert "✅ Health läuft" in result[0].text
