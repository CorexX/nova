# NOVA 2.0 Contracts

## Purpose

NOVA is a Memory / Context System. It provides retrieval, context packaging, indexing, and append-first persistence over a local Markdown Knowledge Base.

NOVA is not an operator runtime.

## Boundary Contract

NOVA owns:

- resolving relevant context
- querying durable knowledge
- writing durable knowledge updates
- maintaining derived indexes
- reporting memory-engine health

NOVA does not own:

- chat sessions
- personas
- LLM provider configuration
- cron scheduling
- messaging gateways
- autonomous planning
- code execution
- project orchestration
- process restart/lifecycle management beyond serving MCP requests

## Storage Contract

- Source of truth: `NOVA_KNOWLEDGE_ROOT`
- Default local knowledge root: `/path/to/nova-knowledge`
- Generated indexes: `NOVA_INDEX_ROOT`
- Generated indexes are disposable and rebuildable.
- Private knowledge must not be committed to this repository.

## Configuration Contract

Configuration priority:

1. Environment variables
2. `nova.toml`
3. Defaults

Supported variables:

- `NOVA_CORE_ROOT`
- `NOVA_KNOWLEDGE_ROOT`
- `NOVA_INDEX_ROOT`
- `NOVA_CHROMA_PATH`
- `NOVA_SEARCH_ENABLED`
- `NOVA_EMBEDDING_MODEL`

## MCP Tool Contract

The stable NOVA 2.0 tool surface is:

- `nova_context_resolve`
- `nova_knowledge_query`
- `nova_knowledge_update`
- `nova_memory_maintain`

No new tool should be added unless it directly serves memory/context responsibilities.

## Context Contract

`nova_context_resolve` returns a compact, cited, task-relevant context response.

Required output qualities:

- query echoed back
- selected items include path and snippet
- sources include path and score when available
- confidence is explicit
- inventory is optional
- context is deduplicated by path

## Query Contract

`nova_knowledge_query` searches the Knowledge Base and returns ranked matches.

Required output qualities:

- no hallucinated paths
- no hidden source selection
- project/topic filters are path-based unless a richer index exists
- empty results are valid and explicit

## Write Contract

`nova_knowledge_update` persists durable insights.

Rules:

- `content` and `source` are required.
- Writes are append-first.
- Existing notes must not be silently overwritten.
- Each write should include project/topic/source/confidence where available.
- Each write may include `memory_type`, `scope`, lifecycle `status`, and `supersedes` metadata.
- Lifecycle `status` values are controlled: `active`, `candidate`, `superseded`, `stale`, `archived`, `rejected`.
- Patch-based writes must be explicit and reviewable.

## Maintenance Contract

`nova_memory_maintain` supports:

- `health`
- `index`
- `validate`

It must not support process restart. Lifecycle belongs to the operator environment.

## Provenance Contract

Every durable memory should preserve enough information to answer:

- where did this come from?
- when was it recorded?
- what project/topic does it affect?
- how confident is it?
- what should happen next, if anything?

## Quality Contract

Before changes are considered ready:

```bash
python -m compileall -q .
python -m unittest discover -s tests -v
```
