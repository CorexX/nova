# NOVA 2.0

> Local-first Memory / Context System for agentic work.

NOVA 2.0 is a small, focused context layer. It does not operate, chat, schedule, or execute tasks. It remembers.

The project separates three responsibilities:

```text
Operator        -> plans and acts
Context System  -> retrieves, packages, and persists relevant memory
Knowledge Base  -> stores durable human-readable knowledge
```

NOVA is the **Context System** in that split. It exposes a minimal MCP interface over a Markdown knowledge base so any operator can ask: "What context matters here?" and "Where should this durable insight be stored?"

## Project Vision

Modern AI operators are useful but stateless. They can reason over a task, but they forget decisions, project history, constraints, and source context unless every session is manually reloaded.

NOVA solves that missing layer:

> NOVA turns a local Markdown knowledge base into a structured, searchable, source-attributed memory system.

The goal is not to replace a human-readable vault. The goal is to make that vault useful to operators without dumping the whole thing into a prompt.

## What NOVA Is

- A local-first Memory / Context System
- An MCP server with a deliberately small tool surface
- A bridge between operators and a Markdown Knowledge Base
- A context pack assembler with sources and confidence
- A persistence helper for append-first knowledge updates
- A rebuildable indexing layer over durable files

## What NOVA Is Not

NOVA is not an agent runtime.

It does not own:

- chat sessions
- personas
- cron scheduling
- messaging gateways
- LLM provider configuration
- autonomous planning
- code execution
- project orchestration

Those belong to an operator. NOVA only supplies memory and context.

## Architecture

```text
                 +----------------+
                 |    Operator    |
                 | plans + acts   |
                 +-------+--------+
                         |
                         | MCP
                         v
              +----------+-----------+
              |      NOVA 2.0        |
              | Memory / Context     |
              +----------+-----------+
                         |
        +----------------+----------------+
        |                                 |
        v                                 v
+-------+---------+              +--------+--------+
| Knowledge Base  |              | Derived Indexes |
| Markdown + Git  |              | search/cache    |
+-----------------+              +-----------------+
```

### Source of Truth

The Knowledge Base is the source of truth. Indexes are generated artifacts.

```text
Markdown files -> parser/indexer -> semantic_index.json / future SQLite FTS / graph
```

If an index is deleted, NOVA should be able to rebuild it from the Knowledge Base.

## Tool Surface

NOVA intentionally exposes only four MCP tools:

| Tool | Purpose |
|---|---|
| `nova_context_resolve` | Build a focused context response for a query |
| `nova_knowledge_query` | Search the Knowledge Base semantically |
| `nova_knowledge_update` | Append-first persistence for durable insights |
| `nova_memory_maintain` | Health, validation, and indexing |

Anything beyond this is suspicious until proven useful. Small interface, sharp axe.

## Memory Principles

1. **Markdown first** — humans can read and edit the source.
2. **Indexes are disposable** — generated search data is not source truth.
3. **Provenance required** — useful memory points back to files/sources.
4. **Append before overwrite** — preserve history unless a patch is explicit.
5. **Context is selected** — return the smallest useful context, not the biggest possible dump.
6. **Boundary stays clean** — NOVA remembers; an operator acts.

## Repository Layout

```text
nova/
├── README.md
├── CONTRACTS.md
├── requirements.txt
├── mcp/
│   ├── nova_mcp_core_server.py
│   ├── check_server.py
│   ├── README.md
│   └── tools/
│       ├── common.py
│       ├── context_resolve.py
│       ├── health_checks.py
│       ├── knowledge_query.py
│       ├── knowledge_update.py
│       ├── memory_maintain.py
│       ├── paths.py
│       └── search_shared.py
├── meta/
│   ├── ARCHITECTURE.md
│   ├── PRINCIPLES.md
│   ├── ROADMAP.md
│   └── SYSTEM.md
├── templates/
│   └── knowledge/
└── tests/
```

## Configuration

NOVA reads configuration in this order:

1. Environment variables
2. `nova.toml`
3. Defaults

Common environment variables:

```env
NOVA_CORE_ROOT=/path/to/nova
NOVA_KNOWLEDGE_ROOT=/path/to/nova-knowledge
NOVA_INDEX_ROOT=/path/to/nova/.nova/index
NOVA_SEARCH_ENABLED=true
NOVA_EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## Running the MCP Server

```bash
python mcp/nova_mcp_core_server.py
```

## Maintenance

Run a lightweight local check:

```bash
python mcp/check_server.py
```

Rebuild the memory index through the MCP tool:

```json
{
  "operation": "index",
  "force": false
}
```

## Development

Compile all Python files:

```bash
python -m compileall -q .
```

Run tests with the standard library test runner:

```bash
python -m unittest discover -s tests -v
```

## Design Bias

NOVA should be boring infrastructure: predictable, auditable, local, and small.

If a feature smells like operator behavior, it probably belongs outside NOVA.
