#!/usr/bin/env python3
"""Quick health check for the NOVA memory engine."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from tools.paths import resolve_paths

workspace = Path(__file__).resolve().parent.parent
cfg = resolve_paths(workspace)

print("=" * 60)
print("NOVA 2.0 Memory Engine - Check")
print("=" * 60)
print(f"Python: {sys.version.split()[0]}")
print(f"Core root: {cfg.core_root}")
print(f"Knowledge root: {cfg.knowledge_root}")
print(f"Index root: {cfg.index_root}")
print()

required = ["mcp"]
optional = ["sentence_transformers", "chromadb"]
ok = True

for module in required:
    present = importlib.util.find_spec(module) is not None
    ok = ok and present
    print(f"{'OK' if present else 'MISSING'} required: {module}")
for module in optional:
    present = importlib.util.find_spec(module) is not None
    print(f"{'OK' if present else 'MISSING'} optional: {module}")

print()
print(f"Knowledge root exists: {cfg.knowledge_root.exists()}")
print(f"Markdown files: {sum(1 for _ in cfg.knowledge_root.rglob('*.md')) if cfg.knowledge_root.exists() else 0}")
print(f"Semantic index exists: {(cfg.index_root / 'semantic_index.json').exists()}")
print("=" * 60)
print("OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
