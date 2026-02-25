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

## Session Init Contract
- Single start call: `nova_context_resolve(query="session init", include_inventory=true)`.
- Successful init response must include:
  - semantic context (`context_items`, `sources`, `confidence`)
  - compact structure snapshot (`inventory`)
  - core runtime rules (`core_directives`)
- If the tool call fails:
  - caller reports failure briefly
  - caller reads `core/CORE.md` locally
  - caller continues with best available local context

## Workflow Contract (Runtime)
- Canonical sequence: `init -> intent -> context -> action -> persist -> review`.
- Step I/O:
  - `init`: Input user turn start, Output `core_directives + inventory + initial context`.
  - `intent`: Input user request, Output classified intent (`continue/new/query/capture/system`).
  - `context`: Input intent + optional project hint, Output focused context.
  - `action`: Input focused context, Output result draft/change.
  - `persist`: Input result draft, Output persisted record or explicit skip reason.
  - `review`: Input persisted record(s), Output concise done/persisted/next summary.

## Persistence Contract
- Write mode default: `auto_with_confirm`.
- Candidate events:
  - knowledge improvement replacing/updating existing content
  - decision with impact
  - new/escalated risk
  - completed work block (offered via confirm)
- No-write exceptions:
  - brainstorming without reliable statement
  - uncertain raw ideas without source/traceability
- Destination mapping (single-source):
  - chronology/time -> `WORKLOG.md`
  - content insight -> `knowledge/*`
  - current focus/next -> `CURRENT.md`
  - open work -> `TICKETS.md`
- No duplicate policy:
  - no knowledge body in worklog, only reference pointer when needed.

## Minimal Metadata Contract (Format-Agnostic)
- Required informational fields (independent of file format):
  - `source`
  - `project`
  - `topic`
  - `confidence_or_uncertainty`
  - `next_action`
  - `timestamp`

## Persistence Quality Gate
- Persist if at least 3 of 4 criteria are met:
  - concrete
  - traceable
  - source-attributed
  - action-relevant

## Project Identification Contract
- Resolver must choose a project path deterministically when confidence is clear.
- If ambiguous: ask user with 2-3 concrete options (Safe-Ask).

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
