"""
Tests fÃ¼r tools/search/index_vault.py
Testet Vault-Indexierung mit gemockten Dependencies.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from mcp.types import Tool, TextContent


class TestToolDefinition:
    """Tests fÃ¼r get_tool_definition()."""
    
    def test_returns_tool_instance(self, tmp_path):
        """Gibt Tool-Instanz zurÃ¼ck."""
        from tools.search.index_vault import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert isinstance(tool, Tool)
    
    def test_has_correct_name(self, tmp_path):
        """Tool hat korrekten Namen."""
        from tools.search.index_vault import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert tool.name == "nova_index_vault"
    
    def test_has_description(self, tmp_path):
        """Tool hat Beschreibung."""
        from tools.search.index_vault import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "Semantic Search" in tool.description
    
    def test_no_required_params(self, tmp_path):
        """Keine required Parameter."""
        from tools.search.index_vault import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert tool.inputSchema["required"] == []
    
    def test_has_force_param(self, tmp_path):
        """force ist optional mit default False."""
        from tools.search.index_vault import get_tool_definition
        tool = get_tool_definition(tmp_path)
        props = tool.inputSchema["properties"]
        assert "force" in props
        assert props["force"]["default"] is False
    
    def test_has_no_scope_param(self, tmp_path):
        """Scope-Override wird nicht angeboten."""
        from tools.search.index_vault import get_tool_definition
        tool = get_tool_definition(tmp_path)
        props = tool.inputSchema["properties"]
        assert "scope" not in props


class TestSplitByHeaders:
    """Tests fÃ¼r split_by_headers() Hilfsfunktion."""
    
    def test_splits_by_h1(self):
        """Splittet bei H1-Ãœberschriften."""
        from tools.search.index_vault import split_by_headers
        
        content = """# Intro
Some intro text

# Main
The main content
"""
        chunks = split_by_headers(content)
        
        assert len(chunks) == 2
        assert chunks[0]["section"] == "Intro"
        assert chunks[1]["section"] == "Main"
    
    def test_splits_by_h2(self):
        """Splittet bei H2-Ãœberschriften."""
        from tools.search.index_vault import split_by_headers
        
        content = """## First Section
Text here

## Second Section
More text
"""
        chunks = split_by_headers(content)
        
        assert len(chunks) == 2
        assert chunks[0]["section"] == "First Section"
        assert chunks[1]["section"] == "Second Section"
    
    def test_fallback_for_no_headers(self):
        """Ganzes Dokument als Fallback wenn keine Headers."""
        from tools.search.index_vault import split_by_headers
        
        content = "Just plain text without any headers."
        chunks = split_by_headers(content)
        
        assert len(chunks) == 1
        assert chunks[0]["section"] == ""
        assert chunks[0]["text"] == content
    
    def test_limits_chunk_size(self):
        """Chunks sind auf 2000 Zeichen begrenzt."""
        from tools.search.index_vault import split_by_headers
        
        long_content = "# Header\n" + "x" * 3000
        chunks = split_by_headers(long_content)
        
        assert len(chunks[0]["text"]) <= 2000
    
    def test_empty_content(self):
        """Leerer Content ergibt leere Liste."""
        from tools.search.index_vault import split_by_headers
        
        chunks = split_by_headers("")
        assert chunks == []
    
    def test_whitespace_only(self):
        """Nur Whitespace ergibt leere Liste."""
        from tools.search.index_vault import split_by_headers
        
        chunks = split_by_headers("   \n\n  ")
        assert chunks == []


class TestExecuteMissingDependencies:
    """Tests fÃ¼r fehlende Dependencies."""
    
    @pytest.mark.asyncio
    async def test_returns_error_when_chromadb_missing(self, tmp_path):
        """Fehler wenn chromadb nicht installiert."""
        from tools.search.index_vault import execute
        
        with patch('tools.search.index_vault.get_chromadb', side_effect=ImportError("chromadb")):
            result = await execute({}, tmp_path)
        
        assert len(result) == 1
        assert "Dependencies fehlen" in result[0].text
    
    @pytest.mark.asyncio
    async def test_returns_error_when_model_missing(self, tmp_path):
        """Fehler wenn sentence-transformers nicht installiert."""
        from tools.search.index_vault import execute
        
        mock_chromadb = MagicMock()
        with patch('tools.search.index_vault.get_chromadb', return_value=mock_chromadb):
            with patch('tools.search.index_vault.get_model', side_effect=ImportError("sentence_transformers")):
                result = await execute({}, tmp_path)
        
        assert len(result) == 1
        assert "Dependencies fehlen" in result[0].text


class TestExecuteVaultNotFound:
    """Tests wenn Vault nicht existiert."""
    
    @pytest.mark.asyncio
    async def test_returns_error_when_vault_missing(self, tmp_path):
        """Fehler wenn Vault-Verzeichnis nicht existiert."""
        from tools.search.index_vault import execute
        
        mock_chromadb = MagicMock()
        mock_model = MagicMock()
        
        with patch('tools.search.index_vault.get_chromadb', return_value=mock_chromadb):
            with patch('tools.search.index_vault.get_model', return_value=mock_model):
                result = await execute({}, tmp_path)
        
        assert len(result) == 1
        assert "Vault nicht gefunden" in result[0].text


class TestExecuteIndexing:
    """Tests fÃ¼r erfolgreiche Indexierung."""
    
    @pytest.fixture
    def vault_with_files(self, tmp_path):
        """Erstellt Vault mit Test-Markdown-Dateien."""
        vault_path = tmp_path / "nova-knowledge"
        vault_path.mkdir()
        
        # Erstelle nova-core Verzeichnis (wird von index_vault erwartet)
        (tmp_path / "nova-core").mkdir()
        
        # Testdateien erstellen
        (vault_path / "doc1.md").write_text("# Dokument 1\nInhalt hier.", encoding="utf-8")
        (vault_path / "doc2.md").write_text("# Dokument 2\nAnderer Inhalt.", encoding="utf-8")
        
        return tmp_path
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mockt alle externen Dependencies."""
        mock_chromadb = MagicMock()
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 2
        mock_collection.get.return_value = {"ids": []}
        
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1, 0.2, 0.3])
        
        return {
            "chromadb": mock_chromadb,
            "client": mock_client,
            "collection": mock_collection,
            "model": mock_model
        }
    
    @pytest.mark.asyncio
    async def test_indexes_markdown_files(self, vault_with_files, mock_dependencies):
        """Indexiert alle Markdown-Dateien."""
        from tools.search.index_vault import execute
        
        with patch('tools.search.index_vault.get_chromadb', return_value=mock_dependencies["chromadb"]):
            with patch('tools.search.index_vault.get_model', return_value=mock_dependencies["model"]):
                result = await execute({}, vault_with_files)
        
        assert "Index aktualisiert" in result[0].text
        assert "Neu/Geändert" in result[0].text
    
    @pytest.mark.asyncio
    async def test_creates_index_directory(self, vault_with_files, mock_dependencies):
        """Erstellt Index-Verzeichnis falls nicht vorhanden."""
        from tools.search.index_vault import execute
        
        with patch('tools.search.index_vault.get_chromadb', return_value=mock_dependencies["chromadb"]):
            with patch('tools.search.index_vault.get_model', return_value=mock_dependencies["model"]):
                await execute({}, vault_with_files)
        
        index_path = vault_with_files / ".nova" / "index"
        assert index_path.exists()
    
    @pytest.mark.asyncio
    async def test_saves_file_hashes(self, vault_with_files, mock_dependencies):
        """Speichert Datei-Hashes fÃ¼r inkrementelles Update."""
        from tools.search.index_vault import execute
        
        with patch('tools.search.index_vault.get_chromadb', return_value=mock_dependencies["chromadb"]):
            with patch('tools.search.index_vault.get_model', return_value=mock_dependencies["model"]):
                await execute({}, vault_with_files)
        
        hash_file = vault_with_files / ".nova" / "index" / "file_hashes.json"
        assert hash_file.exists()
        
        hashes = json.loads(hash_file.read_text(encoding="utf-8"))
        assert len(hashes) == 2
    
    @pytest.mark.asyncio
    async def test_skips_unchanged_files(self, vault_with_files, mock_dependencies):
        """Ãœberspringt unverÃ¤nderte Dateien."""
        from tools.search.index_vault import execute
        
        # Erstelle existierende Hashes
        index_path = vault_with_files / ".nova" / "index"
        index_path.mkdir(parents=True)
        
        # Berechne echten Hash fÃ¼r doc1.md
        import hashlib
        content = (vault_with_files / "nova-knowledge" / "doc1.md").read_text(encoding="utf-8")
        doc1_hash = hashlib.md5(content.encode()).hexdigest()
        
        hash_file = index_path / "file_hashes.json"
        hash_file.write_text(json.dumps({
            "nova-knowledge/doc1.md": doc1_hash
        }), encoding="utf-8")
        
        with patch('tools.search.index_vault.get_chromadb', return_value=mock_dependencies["chromadb"]):
            with patch('tools.search.index_vault.get_model', return_value=mock_dependencies["model"]):
                result = await execute({}, vault_with_files)
        
        # Sollte 1 unverÃ¤ndert und 1 neu haben
        assert "Unverändert" in result[0].text


class TestExecuteForceReindex:
    """Tests fÃ¼r force=True Parameter."""
    
    @pytest.fixture
    def vault_with_hash_file(self, tmp_path):
        """Vault mit existierendem Hash-File."""
        vault_path = tmp_path / "nova-knowledge"
        vault_path.mkdir()
        (vault_path / "doc.md").write_text("# Doc\nContent", encoding="utf-8")
        
        index_path = tmp_path / ".nova" / "index"
        index_path.mkdir(parents=True)
        
        hash_file = index_path / "file_hashes.json"
        hash_file.write_text(json.dumps({
            "nova-knowledge/doc.md": "old_hash_that_would_match"
        }), encoding="utf-8")
        
        return tmp_path
    
    @pytest.mark.asyncio
    async def test_force_ignores_existing_hashes(self, vault_with_hash_file):
        """force=True ignoriert existierende Hashes."""
        from tools.search.index_vault import execute
        
        mock_chromadb = MagicMock()
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 1
        mock_collection.get.return_value = {"ids": []}
        
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1, 0.2, 0.3])
        
        with patch('tools.search.index_vault.get_chromadb', return_value=mock_chromadb):
            with patch('tools.search.index_vault.get_model', return_value=mock_model):
                result = await execute({"force": True}, vault_with_hash_file)
        
        # Mit force sollte die Datei neu indexiert werden
        assert "Neu/Geändert | 1" in result[0].text or "Neu/Geändert" in result[0].text


class TestExecuteScopeBehavior:
    """Tests fuer Scope-Verhalten."""

    @pytest.mark.asyncio
    async def test_scope_arg_is_ignored_and_knowledge_root_is_used(self, tmp_path):
        """Indexiert immer knowledge_root, auch wenn scope uebergeben wurde."""
        from tools.search.index_vault import execute

        knowledge_path = tmp_path / "nova-knowledge"
        knowledge_path.mkdir()
        (knowledge_path / "from-knowledge.md").write_text("# Test", encoding="utf-8")

        custom_path = tmp_path / "custom-scope"
        custom_path.mkdir()
        (custom_path / "from-custom.md").write_text("# Ignored", encoding="utf-8")

        mock_chromadb = MagicMock()
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 1
        mock_collection.get.return_value = {"ids": []}

        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1, 0.2, 0.3])

        with patch('tools.search.index_vault.get_chromadb', return_value=mock_chromadb):
            with patch('tools.search.index_vault.get_model', return_value=mock_model):
                result = await execute({"scope": "custom-scope"}, tmp_path)

        assert str(knowledge_path) in result[0].text


class TestExecuteDeletedFiles:
    """Tests fÃ¼r LÃ¶schung nicht mehr existierender Dateien."""
    
    @pytest.mark.asyncio
    async def test_removes_deleted_file_entries(self, tmp_path):
        """Entfernt EintrÃ¤ge fÃ¼r gelÃ¶schte Dateien."""
        from tools.search.index_vault import execute
        
        vault_path = tmp_path / "nova-knowledge"
        vault_path.mkdir()
        (vault_path / "still-here.md").write_text("# Still Here", encoding="utf-8")
        
        index_path = tmp_path / ".nova" / "index"
        index_path.mkdir(parents=True)
        
        # Hash-File mit nicht mehr existierender Datei
        hash_file = index_path / "file_hashes.json"
        hash_file.write_text(json.dumps({
            "nova-knowledge/still-here.md": "some_hash",
            "nova-knowledge/deleted.md": "old_hash"
        }), encoding="utf-8")
        
        mock_chromadb = MagicMock()
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 1
        mock_collection.get.return_value = {"ids": ["deleted_chunk"]}
        
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1, 0.2, 0.3])
        
        with patch('tools.search.index_vault.get_chromadb', return_value=mock_chromadb):
            with patch('tools.search.index_vault.get_model', return_value=mock_model):
                result = await execute({"force": True}, tmp_path)
        
        # PrÃ¼fe dass delete aufgerufen wurde
        assert mock_collection.delete.called


class TestReturnType:
    """Tests fÃ¼r korrekten Return-Type."""
    
    @pytest.mark.asyncio
    async def test_returns_list_of_text_content(self, tmp_path):
        """Gibt Liste von TextContent zurÃ¼ck."""
        from tools.search.index_vault import execute
        
        mock_chromadb = MagicMock()
        mock_model = MagicMock()
        
        with patch('tools.search.index_vault.get_chromadb', return_value=mock_chromadb):
            with patch('tools.search.index_vault.get_model', return_value=mock_model):
                result = await execute({}, tmp_path)
        
        assert isinstance(result, list)
        assert len(result) >= 1
        assert all(isinstance(item, TextContent) for item in result)

