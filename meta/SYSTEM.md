# NOVA 2.0 System Overview

NOVA is a compact memory/context service for a local Markdown Knowledge Base.

## System Roles

```text
Operator        external actor that performs work
NOVA            context and memory service
Knowledge Base  durable Markdown store
Index           rebuildable search/cache layer
```

## Runtime Shape

```text
MCP client
  -> mcp/nova_mcp_core_server.py
  -> mcp/tools/*.py
  -> NOVA_KNOWLEDGE_ROOT
  -> NOVA_INDEX_ROOT
```

## Public Interface

- `nova_context_resolve`
- `nova_knowledge_query`
- `nova_knowledge_update`
- `nova_memory_maintain`

## Default Paths

```text
core:      /path/to/nova
knowledge: /path/to/nova-knowledge
index:     /path/to/nova/.nova/index
```

All paths are configurable by environment variables.

## Operational Checks

```bash
python mcp/check_server.py
python -m compileall -q .
python -m unittest discover -s tests -v
```

## Security Boundary

This repo should remain portable and shareable. Private notes, generated indexes, local config, and secrets stay out of git.
