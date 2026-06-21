# Local Helper Scripts

Small local wrappers that sit next to NOVA and support adjacent operator workflows. They are not part of the NOVA MCP core itself.

## Scope Boundary

- NOVA core = memory/context retrieval and persistence
- local scripts here = operational helpers for systems around NOVA
- source of truth for task state can live outside NOVA, e.g. Microsoft Planner or Azure DevOps

## Azure DevOps helper

Files:
- `ado.sh`
- `ado_rest.py`
- `azure-devops.env.example`

Purpose:
- read-oriented Azure DevOps access for example-client/UCL work
- safe wrapper around Azure CLI / REST calls

Typical commands:
- `bash scripts/ado.sh doctor`
- `bash scripts/ado.sh epics`
- `bash scripts/ado.sh epic 154167`
- `bash scripts/ado.sh children 154167`

Secrets/config:
- real secret file lives outside the repo: `/path/to/.hermes/secrets/azure-devops.env`
- required vars:
  - `AZURE_DEVOPS_EXT_PAT`
  - `AZURE_DEVOPS_ORG_URL`
  - `AZURE_DEVOPS_PROJECT`

## Microsoft Planner helper

Files:
- `planner.sh`
- `planner_rest.py`
- `planner.env.example`

Purpose:
- inspect and mutate Microsoft Planner boards through Microsoft Graph
- use Planner as task-state truth while Knowledge keeps context

Auth/config:
- uses Azure CLI cached login, no PAT
- local config file lives outside the repo: `/path/to/.hermes/secrets/planner.env`
- expected vars:
  - `PLANNER_TENANT_ID`
  - `PLANNER_DEFAULT_PLAN_ID` (optional)

Typical commands:
- `bash scripts/planner.sh doctor`
- `bash scripts/planner.sh plans`
- `bash scripts/planner.sh tasks "example-client / UCL"`
- `bash scripts/planner.sh create-plan "Homelab"`
- `bash scripts/planner.sh create-bucket "Homelab" "Current"`
- `bash scripts/planner.sh create-task "Homelab" "Current" "Restore-Drill dokumentieren und durchführen"`
- `bash scripts/planner.sh scaffold-board "NOVA"`
- `python3 scripts/planner_rest.py task-details <task-id> --show`
- `python3 scripts/planner_rest.py task-details <task-id> --description "..." [--check "Item 1" --check "Item 2"]`
- `python3 scripts/planner_rest.py task-details <task-id> --description-file plan.txt`

### Task details (description / checklist)

`task-details` reads or sets a Planner task's rich detail fields via Graph
`GET`/`PATCH /planner/tasks/{id}/details` (ETag/If-Match handled automatically).

- `--show` prints current description + checklist.
- `--description` / `--description-file` set the description body.
- `--check` (repeatable) adds checklist items.

**Permission caveat (verified 2026-06):** the Azure CLI cached token
(`az account get-access-token --resource-type ms-graph`) carries directory
scopes but **not `Tasks.ReadWrite`**. With that token, writing the
`description` field works, but writing native `checklistItems` silently
no-ops (Graph returns 2xx and discards the items). Until a dedicated app
registration with `Tasks.ReadWrite` is available, embed step lists inside
the description instead of relying on the native checklist. This is the
trigger for Workstream D (nova-assistant-mcp) needing its own app reg.

Current board model:
- `example-client / UCL`
- `NOVA`
- `Personal Ops`
- `Homelab`

Default bucket scaffold:
- `Inbox`
- `Current`
- `Next`
- `Blocked`
- `Done`

Guideline:
- prefer one board per real workstream/project
- not one board per technical repository

## Planner -> Knowledge sync

Files:
- `planner-sync.sh`
- `planner_sync.py`

Purpose:
- keep linked Markdown checkboxes aligned with Planner completion state
- Planner is state truth for linked tasks
- Markdown remains context truth

Link format on Markdown checkbox lines:
- `<!-- planner_task:TASK_ID -->`

Behavior:
- `inventory` = show linked tasks and unlinked open checkboxes
- `report` = show drift between Planner and Markdown
- `reconcile` = mark Markdown task done when linked Planner task is done
- intentionally no automatic reopen from Markdown side and no bulk auto-import of every checkbox

Typical commands:
- `bash scripts/planner-sync.sh inventory`
- `bash scripts/planner-sync.sh report`
- `bash scripts/planner-sync.sh reconcile`

Current initial linked files:
- `/path/to/nova-knowledge/projects/client/example-client/projects/ucl/backlog.md`
- `/path/to/nova-knowledge/projects/personal/nova/backlog.md`
- `/path/to/nova-knowledge/projects/personal/personal-taxes/backlog.md`
- `/path/to/nova-knowledge/projects/personal/homelab/backlog.md`
- `/path/to/nova-knowledge/status.md`

## Guardrails

- ask Alex before adding newly created tasks to Planner
- use Planner as task-state truth only for explicitly linked tasks
- keep credentials out of the repo
- do not treat these helper scripts as NOVA core architecture
