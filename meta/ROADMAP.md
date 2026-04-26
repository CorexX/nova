# NOVA 2.0 Roadmap

## Phase 1: Minimal Memory MCP

- Keep four tools only.
- Remove runtime/persona/workflow assets.
- Rewrite docs around the operator/context/knowledge split.
- Add contract tests.

## Phase 2: Context Packs

- Add explicit `context_pack` response structure.
- Improve source/citation formatting.
- Add token-budgeted summaries.

## Phase 3: Better Local Indexing

- Add SQLite metadata store.
- Add SQLite FTS/BM25 for exact recall.
- Keep vector retrieval as one signal, not the source of truth.

## Phase 4: Patch-Based Memory Writes

- Add proposed patch workflow.
- Track superseded/stale memories.
- Add duplicate and contradiction checks.

## Phase 5: Lightweight Temporal Graph

- Extract entities and relationships from Markdown.
- Store graph as rebuildable local index.
- Support temporal facts: observed_at, valid_from, valid_to.

## Explicit Non-Goals

- Chat UI
- Messaging gateway
- Cron scheduler
- Agent runtime
- Persona system
- LLM provider abstraction
