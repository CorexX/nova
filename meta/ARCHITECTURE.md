# NOVA 2.0 Architecture

## One Sentence

NOVA is a local-first Memory / Context System that exposes a Markdown Knowledge Base to operators through a small MCP interface.

## Responsibility Split

```text
Operator        -> decides, plans, executes
NOVA            -> retrieves, packages, persists context
Knowledge Base  -> stores durable, human-readable knowledge
```

NOVA is deliberately the middle layer. It is not the operator and it is not the private knowledge itself.

## System Diagram

```text
+------------------+
| Operator         |
| action runtime   |
+--------+---------+
         |
         | MCP calls
         v
+--------+---------+
| NOVA 2.0         |
| Memory / Context |
+--------+---------+
         |
         +----------------------+----------------------+
                                |                      |
                                v                      v
                    +-----------+---------+  +---------+----------+
                    | Markdown Knowledge  |  | Derived Indexes    |
                    | Base                |  | FTS/vector/graph   |
                    +---------------------+  +--------------------+
```

## Layers

### 1. MCP Interface

File: `mcp/nova_mcp_core_server.py`

Exposes exactly four memory/context tools:

- `nova_context_resolve`
- `nova_knowledge_query`
- `nova_knowledge_update`
- `nova_memory_maintain`

### 2. Tool Layer

Files: `mcp/tools/*.py`

Each tool maps one external operation to local knowledge/index behavior. Tools return JSON in `TextContent`.

### 3. Configuration Layer

File: `mcp/tools/paths.py`

Resolves:

- core root
- knowledge root
- index root
- search settings

Priority: environment variables > `nova.toml` > defaults.

### 4. Knowledge Layer

External path, usually:

```text
/path/to/nova-knowledge
```

This is the source of truth. It remains private and separate from this repo.

### 5. Index Layer

Generated under `NOVA_INDEX_ROOT`, usually:

```text
/path/to/nova/.nova/index
```

Current index artifacts:

- `file_hashes.json`
- `semantic_index.json`

Future index options:

- SQLite metadata store
- SQLite FTS/BM25
- local vector index
- lightweight temporal graph

All indexes are rebuildable.

## Data Flow: Context Resolve

```text
query
  -> resolve config
  -> search index
  -> deduplicate by path
  -> apply optional project/scope hints
  -> return snippets + sources + confidence
```

## Data Flow: Knowledge Update

```text
content + source + metadata
  -> choose target knowledge directory
  -> create note or append section
  -> return written path and entry id
```

## Data Flow: Index

```text
Markdown files
  -> split by headings
  -> hash files
  -> embed changed chunks
  -> write semantic_index.json
  -> write file_hashes.json
```

## Design Constraints

- Local-first
- Markdown source of truth
- Private knowledge outside repo
- Minimal MCP surface
- Generated indexes ignored by git
- Append-first persistence
- No runtime/operator responsibilities

## Future Architecture

NOVA should evolve toward hybrid retrieval:

```text
metadata filters + full-text search + vector search + recency + graph expansion
```

But only after the minimal memory surface remains stable and tested.
