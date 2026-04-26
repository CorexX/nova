# NOVA MCP Server

NOVA 2.0 exposes a minimal MCP interface for memory and context operations.

## Tools

| Tool | Purpose |
|---|---|
| `nova_context_resolve` | Select and return relevant context for a query |
| `nova_knowledge_query` | Search the Markdown Knowledge Base |
- `nova_knowledge_update` | Append durable knowledge updates with memory type, scope, lifecycle status, and optional supersedes metadata |
| `nova_memory_maintain` | Run health, validation, and indexing |

## Start

```bash
python mcp/nova_mcp_core_server.py
```

## Configuration

Environment variables:

```env
NOVA_CORE_ROOT=/path/to/nova
NOVA_KNOWLEDGE_ROOT=/path/to/nova-knowledge
NOVA_INDEX_ROOT=/path/to/nova/.nova/index
NOVA_SEARCH_ENABLED=true
NOVA_EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## Tool Details

### `nova_context_resolve`

Input:

- `query` required
- `project_hint` optional
- `token_budget` optional
- `scope` optional
- `include_inventory` optional

Output:

- `context_items`
- `sources`
- `confidence`
- optional `inventory`
- optional memory boundary directives for `query="session init"`

### `nova_knowledge_query`

Input:

- `query` required
- `project` optional
- `topic` optional
- `limit` optional

Output:

- ranked `matches` with path, snippet, score, and relevance reason

### `nova_knowledge_update`

Input:

- `content` required
- `source` required
- `project` optional
- `topic` optional
- `title` optional
- `confidence` optional
- `next_action` optional
- `memory_type` optional: `fact`, `preference`, `decision`, `task`, `procedure`, `episode`, `source`, `summary`, `question`, `constraint`, `entity`, `relationship`
- `scope` optional: `global`, `user`, `project`, `repo`, `task`, `session`, `agent`
- `status` optional lifecycle state: `active`, `candidate`, `superseded`, `stale`, `archived`, `rejected`
- `mode` optional: `append`, `dry_run`, `propose_patch`
- `supersedes` optional list of replaced memory ids

Output:

- written paths
- entry ids

### `nova_memory_maintain`

Input:

- `operation`: `health`, `index`, or `validate`
- `force` optional for index rebuild

Output:

- status
- details
- artifacts

## Boundary

The MCP server does not manage process lifecycle, agent behavior, scheduled work, or messaging. It only serves memory/context calls.
