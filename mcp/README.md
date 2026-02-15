# NOVA MCP Server

MCP server for NOVA v2 tools.

## Scope

This MCP package currently exposes only v2 tools from `mcp/tools/v2`.
Legacy adapters in `mcp/tools/*` (context/git/n8n/sessions/testing/worklog/old search) were removed from runtime surface.

## Exposed Tools

| Tool | Purpose |
|---|---|
| `nova_context_resolve` | Resolve relevant working context via semantic retrieval |
| `nova_project_continue` | Continue a project with status and next steps |
| `nova_project_create` | Create a structured NOVA project scaffold |
| `nova_knowledge_query` | Semantic knowledge query |
| `nova_knowledge_update` | Append-first persistence of new knowledge |
| `nova_system_maintain` | Operations: `health`, `index`, `restart` |

## Runtime Structure

```text
mcp/
|- nova_mcp_core_server.py
|- README.md
`- tools/
   |- __init__.py
   |- paths.py
   |- health/
   |  |- __init__.py
   |  `- checks.py
   |- search/
   |  |- __init__.py
   |  `- shared.py
   `- v2/
      |- __init__.py
      |- common.py
      |- context_resolve.py
      |- knowledge_query.py
      |- knowledge_update.py
      |- project_continue.py
      |- project_create.py
      `- system_maintain.py
```

## Architecture Diagram

```mermaid
flowchart TD
    A[Client MCP Host] --> B[nova_mcp_core_server.py]
    B --> C[nova_context_resolve]
    B --> D[nova_project_continue]
    B --> E[nova_project_create]
    B --> F[nova_knowledge_query]
    B --> G[nova_knowledge_update]
    B --> H[nova_system_maintain]

    C --> S[tools/search/shared.py]
    F --> S
    H --> S
    C --> P[tools/paths.py]
    D --> P
    E --> P
    F --> P
    G --> P
    H --> P
    H --> HC[tools/health/checks.py]
```

## Semantic Retrieval/Data Flow

```mermaid
sequenceDiagram
    participant T as v2 tool
    participant P as paths.py
    participant S as search/shared.py
    participant C as chroma.sqlite3

    T->>P: resolve_paths(workspace_root)
    T->>S: semantic_search(...) or batch_encode_texts(...)
    S->>C: read embeddings / vectors
    C-->>S: nearest results
    S-->>T: ranked matches
```

## Operations (`nova_system_maintain`)

- `health`: grouped runtime checks
- `index`: rebuild/update semantic index artifacts
- `restart`: delayed self-terminate for MCP restart handoff

`test` is not part of `nova_system_maintain`.

## Notes

- `tools/search/shared.py` is the shared semantic layer used by `nova_context_resolve`, `nova_knowledge_query`, and indexing paths.
- MCP server restart is required after schema or tool-surface changes.
