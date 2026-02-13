"""
Tool: Index Vault
Indexiert alle Markdown-Dateien in der Vault für Semantic Search.

Verwendet ChromaDB als lokale Vektordatenbank und sentence-transformers
für Embeddings. Der Index wird persistent gespeichert und kann mit Git
synchronisiert werden.
"""

import hashlib
import json
import re
from pathlib import Path
from mcp.types import Tool, TextContent
from ..paths import resolve_paths

# Shared cached model
from .shared import get_model, get_chromadb


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_index_vault",
        description="Indexiert die Vault für Semantic Search. Nur bei Änderungen nötig. Läuft inkrementell.",
        inputSchema={
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "description": "Komplett neu indexieren (ignoriert Cache)",
                    "default": False
                },
            },
            "required": []
        }
    )


def split_by_headers(content: str) -> list[dict]:
    """
    Splittet Markdown nach H1/H2 Überschriften.
    Jeder Chunk enthält den Text und den Section-Namen.
    """
    chunks = []
    
    # Split bei H1 oder H2
    sections = re.split(r'\n(?=#{1,2}\s)', content)
    
    for section in sections:
        if not section.strip():
            continue
            
        # Extrahiere Header
        header_match = re.match(r'^(#{1,2})\s+(.+)', section)
        section_name = header_match.group(2).strip() if header_match else ""
        
        # Max 2000 chars pro Chunk (für Embedding-Effizienz)
        text = section.strip()[:2000]
        
        chunks.append({
            "text": text,
            "section": section_name
        })
    
    # Fallback: Ganzes Dokument wenn keine Headers
    if not chunks and content.strip():
        chunks.append({
            "text": content.strip()[:2000],
            "section": ""
        })
    
    return chunks


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    """Indexiert die Vault für Semantic Search."""
    
    # Use cached dependencies
    try:
        chromadb = get_chromadb()
        model = get_model()
    except ImportError as e:
        return [TextContent(
            type="text",
            text=f"❌ Dependencies fehlen: {e}\n\nInstalliere mit:\npip install chromadb sentence-transformers"
        )]
    
    paths = resolve_paths(workspace_root)
    force = args.get("force", False)
    
    # Pfade
    vault_path = paths.knowledge_root
    index_path = paths.index_root
    hash_file = index_path / "file_hashes.json"
    
    if not vault_path.exists():
        return [TextContent(type="text", text=f"❌ Vault nicht gefunden: {vault_path}")]
    
    index_path.mkdir(parents=True, exist_ok=True)
    
    # ChromaDB Client (persistent)
    paths.chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(paths.chroma_path))
    
    # Collection mit Cosine Similarity
    collection = client.get_or_create_collection(
        name="vault",
        metadata={"hnsw:space": "cosine"}
    )
    
    # Model is cached via get_model() - loaded once at first use
    
    # Lade bestehende Hashes für inkrementelles Update
    existing_hashes = {}
    if hash_file.exists() and not force:
        try:
            existing_hashes = json.loads(hash_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing_hashes = {}
    
    # Finde alle Markdown-Dateien
    md_files = list(vault_path.rglob("*.md"))
    
    indexed = 0
    skipped = 0
    deleted = 0
    
    # Track welche Dateien noch existieren
    current_paths = set()
    
    for md_file in md_files:
        try:
            rel_path = str(md_file.relative_to(workspace_root)).replace("\\", "/")
        except ValueError:
            rel_path = str(md_file).replace("\\", "/")
        current_paths.add(rel_path)
        
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        
        # Hash für Inkrementelles Update
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Skip wenn unverändert
        if rel_path in existing_hashes and existing_hashes[rel_path] == content_hash:
            skipped += 1
            continue
        
        # Lösche alte Chunks dieser Datei (falls vorhanden)
        try:
            old_ids = collection.get(where={"path": rel_path})["ids"]
            if old_ids:
                collection.delete(ids=old_ids)
        except Exception:
            pass
        
        # Chunking nach Überschriften
        chunks = split_by_headers(content)
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{rel_path}#{i}"
            
            # Embedding erstellen
            embedding = model.encode(chunk["text"]).tolist()
            
            # In ChromaDB speichern
            collection.add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk["text"]],
                metadatas=[{
                    "path": rel_path,
                    "section": chunk.get("section", ""),
                    "chunk_index": i
                }]
            )
        
        existing_hashes[rel_path] = content_hash
        indexed += 1
    
    # Lösche Einträge für gelöschte Dateien
    for old_path in list(existing_hashes.keys()):
        if old_path not in current_paths:
            try:
                old_ids = collection.get(where={"path": old_path})["ids"]
                if old_ids:
                    collection.delete(ids=old_ids)
                    deleted += 1
            except Exception:
                pass
            del existing_hashes[old_path]
    
    # Speichere Hashes
    hash_file.write_text(json.dumps(existing_hashes, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # Statistiken
    total_chunks = collection.count()
    
    return [TextContent(
        type="text",
        text=f"""✅ Index aktualisiert

| Metrik | Wert |
|--------|------|
| Neu/Geändert | {indexed} |
| Unverändert | {skipped} |
| Gelöscht | {deleted} |
| **Dateien gesamt** | {len(md_files)} |
| **Chunks im Index** | {total_chunks} |
| Scope | `{vault_path}` |
"""
    )]
