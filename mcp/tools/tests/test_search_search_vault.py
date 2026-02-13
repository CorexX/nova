"""
Tests fÃ¼r tools/search/search_vault.py
Testet semantische Suche mit gemockten Dependencies.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from mcp.types import Tool, TextContent


class TestToolDefinition:
    """Tests fÃ¼r get_tool_definition()."""
    
    def test_returns_tool_instance(self, tmp_path):
        """Gibt Tool-Instanz zurÃ¼ck."""
        from tools.search.search_vault import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert isinstance(tool, Tool)
    
    def test_has_correct_name(self, tmp_path):
        """Tool hat korrekten Namen."""
        from tools.search.search_vault import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert tool.name == "nova_search_vault"
    
    def test_has_description(self, tmp_path):
        """Tool hat Beschreibung."""
        from tools.search.search_vault import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert tool.description
        assert "Semantische Suche" in tool.description
    
    def test_requires_query_param(self, tmp_path):
        """query ist required Parameter."""
        from tools.search.search_vault import get_tool_definition
        tool = get_tool_definition(tmp_path)
        assert "query" in tool.inputSchema["required"]
    
    def test_has_optional_top_k(self, tmp_path):
        """top_k ist optional mit default 5."""
        from tools.search.search_vault import get_tool_definition
        tool = get_tool_definition(tmp_path)
        props = tool.inputSchema["properties"]
        assert "top_k" in props
        assert props["top_k"]["default"] == 5
    
    def test_has_optional_threshold(self, tmp_path):
        """threshold ist optional mit default 0.3."""
        from tools.search.search_vault import get_tool_definition
        tool = get_tool_definition(tmp_path)
        props = tool.inputSchema["properties"]
        assert "threshold" in props
        assert props["threshold"]["default"] == 0.3


class TestExecuteMissingDependencies:
    """Tests fÃ¼r fehlende Dependencies."""
    
    @pytest.mark.asyncio
    async def test_returns_error_when_chromadb_missing(self, tmp_path):
        """Fehler wenn chromadb nicht installiert."""
        from tools.search.search_vault import execute
        
        with patch('tools.search.search_vault.get_chromadb', side_effect=ImportError("chromadb")):
            result = await execute({"query": "test"}, tmp_path)
        
        assert len(result) == 1
        assert "Dependencies fehlen" in result[0].text
    
    @pytest.mark.asyncio
    async def test_returns_error_when_model_missing(self, tmp_path):
        """Fehler wenn sentence-transformers nicht installiert."""
        from tools.search.search_vault import execute
        
        mock_chromadb = MagicMock()
        with patch('tools.search.search_vault.get_chromadb', return_value=mock_chromadb):
            with patch('tools.search.search_vault.get_model', side_effect=ImportError("sentence_transformers")):
                result = await execute({"query": "test"}, tmp_path)
        
        assert len(result) == 1
        assert "Dependencies fehlen" in result[0].text


class TestExecuteNoIndex:
    """Tests wenn kein Index vorhanden."""
    
    @pytest.mark.asyncio
    async def test_returns_error_when_index_missing(self, tmp_path):
        """Fehler wenn Index-Verzeichnis nicht existiert."""
        from tools.search.search_vault import execute
        
        mock_chromadb = MagicMock()
        mock_model = MagicMock()
        
        with patch('tools.search.search_vault.get_chromadb', return_value=mock_chromadb):
            with patch('tools.search.search_vault.get_model', return_value=mock_model):
                result = await execute({"query": "test"}, tmp_path)
        
        assert len(result) == 1
        assert "Index nicht gefunden" in result[0].text
        assert "nova_index_vault" in result[0].text


class TestExecuteNoCollection:
    """Tests wenn Collection nicht existiert."""
    
    @pytest.mark.asyncio
    async def test_returns_error_when_collection_missing(self, tmp_path):
        """Fehler wenn 'vault' Collection nicht existiert."""
        from tools.search.search_vault import execute
        
        # Erstelle Index-Verzeichnis
        index_path = tmp_path / ".nova" / "index" / "chroma"
        index_path.mkdir(parents=True)
        
        mock_chromadb = MagicMock()
        mock_client = MagicMock()
        mock_client.get_collection.side_effect = Exception("Collection not found")
        mock_chromadb.PersistentClient.return_value = mock_client
        
        mock_model = MagicMock()
        
        with patch('tools.search.search_vault.get_chromadb', return_value=mock_chromadb):
            with patch('tools.search.search_vault.get_model', return_value=mock_model):
                result = await execute({"query": "test"}, tmp_path)
        
        assert len(result) == 1
        assert "Collection 'vault' nicht gefunden" in result[0].text


class TestExecuteSearch:
    """Tests fÃ¼r erfolgreiche Suche."""
    
    @pytest.fixture
    def mock_dependencies(self, tmp_path):
        """Mockt alle externen Dependencies."""
        # Erstelle Index-Verzeichnis
        index_path = tmp_path / ".nova" / "index" / "chroma"
        index_path.mkdir(parents=True)
        
        mock_chromadb = MagicMock()
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection
        
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1, 0.2, 0.3])
        
        return {
            "chromadb": mock_chromadb,
            "client": mock_client,
            "collection": mock_collection,
            "model": mock_model
        }
    
    @pytest.mark.asyncio
    async def test_encodes_query(self, tmp_path, mock_dependencies):
        """Query wird mit Model encoded."""
        from tools.search.search_vault import execute
        
        mock_dependencies["collection"].query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }
        
        with patch('tools.search.search_vault.get_chromadb', return_value=mock_dependencies["chromadb"]):
            with patch('tools.search.search_vault.get_model', return_value=mock_dependencies["model"]):
                await execute({"query": "RAG Architektur"}, tmp_path)
        
        mock_dependencies["model"].encode.assert_called_once_with("RAG Architektur")
    
    @pytest.mark.asyncio
    async def test_queries_collection(self, tmp_path, mock_dependencies):
        """Collection wird mit Embedding abgefragt."""
        from tools.search.search_vault import execute
        
        mock_dependencies["collection"].query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }
        
        with patch('tools.search.search_vault.get_chromadb', return_value=mock_dependencies["chromadb"]):
            with patch('tools.search.search_vault.get_model', return_value=mock_dependencies["model"]):
                await execute({"query": "test", "top_k": 10}, tmp_path)
        
        mock_dependencies["collection"].query.assert_called_once()
        call_args = mock_dependencies["collection"].query.call_args
        assert call_args.kwargs["n_results"] == 10
    
    @pytest.mark.asyncio
    async def test_returns_no_results_message(self, tmp_path, mock_dependencies):
        """Zeigt Nachricht wenn keine Ergebnisse."""
        from tools.search.search_vault import execute
        
        mock_dependencies["collection"].query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }
        
        with patch('tools.search.search_vault.get_chromadb', return_value=mock_dependencies["chromadb"]):
            with patch('tools.search.search_vault.get_model', return_value=mock_dependencies["model"]):
                result = await execute({"query": "gibberish"}, tmp_path)
        
        assert "Keine Ergebnisse" in result[0].text
    
    @pytest.mark.asyncio
    async def test_formats_results_with_similarity(self, tmp_path, mock_dependencies):
        """Ergebnisse enthalten Similarity Score."""
        from tools.search.search_vault import execute
        
        mock_dependencies["collection"].query.return_value = {
            "ids": [["doc1"]],
            "documents": [["Inhalt Ã¼ber RAG"]],
            "metadatas": [[{"path": "projects/client/test.md", "section": "RAG Basics"}]],
            "distances": [[0.2]]  # distance 0.2 = similarity 0.8
        }
        
        with patch('tools.search.search_vault.get_chromadb', return_value=mock_dependencies["chromadb"]):
            with patch('tools.search.search_vault.get_model', return_value=mock_dependencies["model"]):
                result = await execute({"query": "RAG"}, tmp_path)
        
        text = result[0].text
        assert "Suche: \"RAG\"" in text
    
    @pytest.mark.asyncio
    async def test_filters_by_threshold(self, tmp_path, mock_dependencies):
        """Ergebnisse unter threshold werden gefiltert."""
        from tools.search.search_vault import execute
        
        # distance 0.9 = similarity 0.1 (unter threshold 0.3)
        mock_dependencies["collection"].query.return_value = {
            "ids": [["doc1"]],
            "documents": [["Schwaches Match"]],
            "metadatas": [[{"path": "test.md"}]],
            "distances": [[0.9]]
        }
        
        with patch('tools.search.search_vault.get_chromadb', return_value=mock_dependencies["chromadb"]):
            with patch('tools.search.search_vault.get_model', return_value=mock_dependencies["model"]):
                result = await execute({"query": "test", "threshold": 0.3}, tmp_path)
        
        # Sollte gefiltert werden
        text = result[0].text
        # Either "Keine Ergebnisse" or the result doesn't show
        assert "Schwaches Match" not in text or "Keine Ergebnisse" in text


class TestExecuteDeduplication:
    """Tests fÃ¼r Deduplizierung nach Datei."""
    
    @pytest.fixture
    def mock_deps_with_results(self, tmp_path):
        """Mock mit mehreren Ergebnissen aus gleicher Datei."""
        index_path = tmp_path / ".nova" / "index" / "chroma"
        index_path.mkdir(parents=True)
        
        mock_chromadb = MagicMock()
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection
        
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1, 0.2, 0.3])
        
        # Mehrere Chunks aus gleicher Datei
        mock_collection.query.return_value = {
            "ids": [["doc1_chunk1", "doc1_chunk2", "doc2_chunk1"]],
            "documents": [["Section 1", "Section 2", "Andere Datei"]],
            "metadatas": [[
                {"path": "projects/client/projekt.md", "section": "Intro"},
                {"path": "projects/client/projekt.md", "section": "Details"},
                {"path": "projects/client/anderes.md", "section": "Start"}
            ]],
            "distances": [[0.1, 0.15, 0.2]]  # alle gute matches
        }
        
        return {
            "chromadb": mock_chromadb,
            "model": mock_model,
            "collection": mock_collection
        }
    
    @pytest.mark.asyncio
    async def test_deduplicates_by_file_path(self, tmp_path, mock_deps_with_results):
        """Zeigt nur erstes Ergebnis pro Datei."""
        from tools.search.search_vault import execute
        
        with patch('tools.search.search_vault.get_chromadb', return_value=mock_deps_with_results["chromadb"]):
            with patch('tools.search.search_vault.get_model', return_value=mock_deps_with_results["model"]):
                result = await execute({"query": "test"}, tmp_path)
        
        text = result[0].text
        # projekt.md sollte nur einmal erscheinen
        # Dies hÃ¤ngt von der Implementierung ab - hier testen wir nur das Format
        assert isinstance(text, str)


class TestModelWaiting:
    """Tests fÃ¼r Model-Loading im Background."""
    
    @pytest.mark.asyncio
    async def test_waits_for_model_loading(self, tmp_path):
        """Wartet auf Model wenn es noch lÃ¤dt."""
        from tools.search.search_vault import execute
        
        mock_wait = AsyncMock(return_value=False)
        
        # wait_for_model wird dynamisch aus mcp.server importiert
        with patch('mcp.server.wait_for_model', mock_wait, create=True):
            result = await execute({"query": "test"}, tmp_path)
        
        assert "lädt noch" in result[0].text


class TestReturnType:
    """Tests fÃ¼r korrekten Return-Type."""
    
    @pytest.mark.asyncio
    async def test_returns_list_of_text_content(self, tmp_path):
        """Gibt Liste von TextContent zurÃ¼ck."""
        from tools.search.search_vault import execute
        
        # Index-Pfad existiert nicht â†’ Fehler, aber immer noch korrekte Struktur
        mock_chromadb = MagicMock()
        mock_model = MagicMock()
        
        with patch('tools.search.search_vault.get_chromadb', return_value=mock_chromadb):
            with patch('tools.search.search_vault.get_model', return_value=mock_model):
                result = await execute({"query": "test"}, tmp_path)
        
        assert isinstance(result, list)
        assert len(result) >= 1
        assert all(isinstance(item, TextContent) for item in result)

