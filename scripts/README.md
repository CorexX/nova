# Local Helper Scripts

Small local wrappers that sit next to NOVA and support adjacent operator workflows. They are not part of the NOVA MCP core itself.

## Scope Boundary

- NOVA core = memory/context retrieval and persistence
- local scripts here = operational helpers for systems around NOVA
- source of truth for task state can live outside NOVA, e.g. Microsoft Planner

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
- local config file lives outside the repo: `$HOME/.hermes/secrets/planner.env`
- expected vars:
  - `PLANNER_TENANT_ID`
  - `PLANNER_DEFAULT_PLAN_ID` (optional)

Typical commands:
- `bash scripts/planner.sh doctor`
- `bash scripts/planner.sh plans`
- `bash scripts/planner.sh tasks "<plan-id-or-title>"`
- `bash scripts/planner.sh create-plan "Example Plan"`
- `bash scripts/planner.sh create-bucket "Example Plan" "Current"`
- `bash scripts/planner.sh create-task "Example Plan" "Current" "Set up review workflow"`
- `bash scripts/planner.sh scaffold-board "Example Plan"`
- `python3 scripts/planner_rest.py task-details <task-id> --show`
- `python3 scripts/planner_rest.py task-details <task-id> --description "..." [--check "Item 1" --check "Item 2"]`
- `python3 scripts/planner_rest.py task-details <task-id> --description-file plan.txt`

### Task details (description / checklist)

`task-details` reads or sets a Planner task's rich detail fields via Graph
`GET`/`PATCH /planner/tasks/{id}/details` (ETag/If-Match handled automatically).

- `--show` prints current description + checklist.
- `--description` / `--description-file` set the description body.
- `--check` (repeatable) adds checklist items.

**Permission caveat:** the Azure CLI cached token
(`az account get-access-token --resource-type ms-graph`) carries directory
scopes but **not `Tasks.ReadWrite`**. With that token, writing the
`description` field works, but writing native `checklistItems` silently
no-ops (Graph returns 2xx and discards the items). Until a dedicated app
registration with `Tasks.ReadWrite` is available, embed step lists inside
the description instead of relying on the native checklist.

Default bucket scaffold:
- `Inbox`
- `Current`
- `Next`
- `Blocked`
- `Done`

Guideline:
- prefer one board per real workstream/project
- not one board per technical repository

## Guardrails

- confirm before adding newly created tasks to Planner
- use Planner as task-state truth only for explicitly linked tasks
- keep credentials out of the repo
- do not treat these helper scripts as NOVA core architecture
