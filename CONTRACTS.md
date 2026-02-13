# Contracts - nova-core

## Purpose
`nova-core` provides MCP tools, skills, and orchestration logic. It must not own private knowledge content.

## Inputs
- Environment variables:
  - `NOVA_CORE_ROOT` (optional): absolute path to `nova-core`.
  - `NOVA_WORKSPACE_ROOT` (optional): workspace root containing `nova-core` and `nova-knowledge`.
  - `NOVA_KNOWLEDGE_ROOT` (optional): absolute path to `nova-knowledge`.
  - `NOVA_INDEX_ROOT` (optional): absolute path for index storage.
  - Optional n8n integration:
    - `N8N_BASE_URL` (optional)
    - `N8N_API_KEY` (optional)
    - `N8N_INSECURE_TLS` (optional)
- Files:
  - `core/CORE.md`
  - `core/PRINCIPLES.md`
  - `meta/ARCHITECTURE.md`

## Outputs
- MCP tool responses (`TextContent`) for context/search/worklog/testing/etc.
- Optional writes to knowledge files through tool operations (for example `WORKLOG.md` append).
- Optional search index data under `NOVA_INDEX_ROOT` (default: `nova-core/index`).

## Impact on NOVA
- `nova-core` can run without fixed sibling paths and is portable across workspaces.
- Search/index persistence is controlled by `NOVA_INDEX_ROOT`, reducing accidental repo coupling.
- Missing or wrong env paths now surface as configuration issues instead of implicit path fallbacks.

## Documentation Boundary
- Public system documentation lives in `meta/SYSTEM.md`.
- Sensitive operational details must stay outside `nova-core` (see `../nova-knowledge/SYSTEM_PRIVATE.md`).

## Non-goals
- No hard dependency on sibling folder names in tool code paths.
- No direct ownership of customer/private working data structures.
- No mandatory dependency on n8n for startup or core tool usage.
