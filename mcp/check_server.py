#!/usr/bin/env python3
"""
Quick Check: MCP Server Dependencies & Health
Führe dieses Script aus um zu prüfen ob alles bereit ist.

Usage: python check_server.py
"""

import sys
import os
from pathlib import Path
from tools.paths import resolve_paths

print("=" * 60)
print("NOVA MCP Server - Dependency Check")
print("=" * 60)
print()

# Python Info
print(f"Python: {sys.version}")
print(f"Executable: {sys.executable}")
print()

# Check Dependencies
deps = {
    "mcp": "MCP Protocol (required)",
    "chromadb": "Vector Database (for search)",
    "sentence_transformers": "Embeddings (for search)",
}

all_ok = True
for module, desc in deps.items():
    try:
        __import__(module)
        print(f"✅ {module:<25} - {desc}")
    except ImportError:
        print(f"❌ {module:<25} - {desc} - MISSING!")
        all_ok = False

print()

# Check Workspace
workspace = Path(__file__).parent.parent.parent
paths = resolve_paths(workspace)
core_md = paths.core_md
knowledge = paths.knowledge_root

print(f"Workspace: {workspace}")
print(f"  CORE.md exists: {'✅' if core_md.exists() else '❌'}")
print(f"  nova-knowledge exists: {'✅' if knowledge.exists() else '❌'}")
print()

# Check Index
index_path = paths.chroma_path
hash_file = paths.index_root / "file_hashes.json"

if index_path.exists():
    print(f"✅ ChromaDB Index exists: {index_path}")
else:
    print(f"⚠️  ChromaDB Index not found (will be created on first use)")

if hash_file.exists():
    import json
    try:
        hashes = json.loads(hash_file.read_text())
        print(f"   Indexed files: {len(hashes)}")
    except:
        pass

print()

# Test Model Loading
if all_ok:
    print("Testing embedding model loading...")
    try:
        from tools.search.shared import get_model
        import time
        start = time.time()
        model = get_model()
        elapsed = time.time() - start
        print(f"✅ Model loaded in {elapsed:.1f}s")
        
        # Quick embedding test
        test = model.encode("test query")
        print(f"   Embedding dimension: {len(test)}")
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        all_ok = False

print()
print("=" * 60)
if all_ok:
    print("✅ ALL CHECKS PASSED - Server should work!")
else:
    print("❌ SOME CHECKS FAILED - Fix issues above")
    print()
    print("To install missing dependencies:")
    print("  pip install -r nova-core/requirements.txt")
print("=" * 60)
