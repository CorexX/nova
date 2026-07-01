#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${PLANNER_ENV_FILE:-$HOME/.hermes/secrets/planner.env}"

usage() {
  cat <<'USAGE'
Microsoft Planner helper for NOVA/Hermes.

Usage:
  scripts/planner.sh doctor
  scripts/planner.sh plans [text] [--format table|json]
  scripts/planner.sh plan <id-or-title> [--format markdown|json]
  scripts/planner.sh buckets <plan-id-or-title> [--format table|json]
  scripts/planner.sh tasks [plan-id-or-title] [--format table|json]
  scripts/planner.sh mine [--format table|json]
  scripts/planner.sh search <text> [plan-id-or-title] [--format table|json]
  scripts/planner.sh create-plan <title>
  scripts/planner.sh create-bucket <plan-id-or-title> <name>
  scripts/planner.sh create-task <plan-id-or-title> <bucket> <title>
  scripts/planner.sh scaffold-board <title> [bucket1 bucket2 ...]
  scripts/planner.sh raw <graph-path>

Config:
  Loads $HOME/.hermes/secrets/planner.env by default.
  Supported variables:
    PLANNER_TENANT_ID        (required)
    PLANNER_DEFAULT_PLAN_ID  (optional)

Auth:
  Uses Azure CLI login and requests a Microsoft Graph token for PLANNER_TENANT_ID.
  No PAT needed.

Examples:
  scripts/planner.sh doctor
  scripts/planner.sh plans
  scripts/planner.sh plan "My Projects"
  scripts/planner.sh buckets <plan-id>
  scripts/planner.sh tasks <plan-id>
  scripts/planner.sh search Roadmap "My Projects"
  scripts/planner.sh create-plan "Example Plan"
  scripts/planner.sh create-bucket "Example Plan" "Current"
  scripts/planner.sh create-task "Example Plan" "Current" "Set up review workflow"
  scripts/planner.sh scaffold-board "NOVA"
  scripts/planner.sh raw /me/planner/tasks?$top=5
USAGE
}

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

load_config() {
  if [[ ! -f "$CONFIG_FILE" ]]; then
    fail "Config file missing: $CONFIG_FILE. Copy scripts/planner.env.example there and fill it."
  fi

  set -a
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
  set +a

  : "${PLANNER_TENANT_ID:?PLANNER_TENANT_ID is required in $CONFIG_FILE}"
}

require_az() {
  command -v az >/dev/null 2>&1 || fail "Azure CLI 'az' is not installed or not in PATH."
}

require_python() {
  command -v python3 >/dev/null 2>&1 || fail "python3 is not installed or not in PATH."
}

rest_helper() {
  require_python
  python3 "$(dirname "$0")/planner_rest.py" "$@"
}

main() {
  local cmd="${1:-}"
  if [[ -z "$cmd" || "$cmd" == "-h" || "$cmd" == "--help" ]]; then
    usage
    exit 0
  fi
  shift || true

  require_az
  load_config

  case "$cmd" in
    doctor)
      echo "Azure CLI: $(az version --query '"'"'azure-cli'"'"' -o tsv 2>/dev/null || echo unknown)"
      echo "Planner tenant: $PLANNER_TENANT_ID"
      echo "Default plan: ${PLANNER_DEFAULT_PLAN_ID:-—}"
      rest_helper doctor
      ;;
    plans)
      rest_helper plans "$@"
      ;;
    plan)
      [[ "$#" -gt 0 ]] || fail "plan requires an id or title"
      rest_helper plan "$@"
      ;;
    buckets)
      local selector="${1:-}"
      if [[ -z "$selector" || "$selector" == -* ]]; then
        selector="${PLANNER_DEFAULT_PLAN_ID:-}"
      else
        shift || true
      fi
      [[ -n "$selector" ]] || fail "buckets requires a plan id/title or PLANNER_DEFAULT_PLAN_ID"
      rest_helper buckets "$selector" "$@"
      ;;
    tasks)
      local selector="${1:-}"
      if [[ -z "$selector" || "$selector" == -* ]]; then
        if [[ -n "${PLANNER_DEFAULT_PLAN_ID:-}" ]]; then
          rest_helper tasks "$PLANNER_DEFAULT_PLAN_ID" "$@"
        else
          rest_helper tasks "$@"
        fi
      else
        rest_helper tasks "$@"
      fi
      ;;
    mine)
      rest_helper mine "$@"
      ;;
    search)
      [[ "$#" -gt 0 ]] || fail "search requires text"
      rest_helper search "$@"
      ;;
    create-plan)
      [[ "$#" -gt 0 ]] || fail "create-plan requires a title"
      rest_helper create-plan "$@"
      ;;
    create-bucket)
      [[ "$#" -ge 2 ]] || fail "create-bucket requires <plan-id-or-title> <name>"
      rest_helper create-bucket "$@"
      ;;
    create-task)
      [[ "$#" -ge 3 ]] || fail "create-task requires <plan-id-or-title> <bucket> <title>"
      rest_helper create-task "$@"
      ;;
    scaffold-board)
      [[ "$#" -gt 0 ]] || fail "scaffold-board requires a title"
      rest_helper scaffold-board "$@"
      ;;
    raw)
      [[ "$#" -gt 0 ]] || fail "raw requires a graph path, e.g. /me/planner/tasks?$top=5"
      rest_helper raw "$@"
      ;;
    *)
      usage >&2
      fail "Unknown command: $cmd"
      ;;
  esac
}

main "$@"
