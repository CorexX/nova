#!/usr/bin/env python3
"""Small Microsoft Planner REST helper for agent-friendly summaries.

Reads configuration from environment variables loaded by scripts/planner.sh:
- PLANNER_TENANT_ID
- PLANNER_DEFAULT_PLAN_ID (optional)

Authentication uses Azure CLI's cached login and requests a Microsoft Graph token.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from typing import Any


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"ERROR: {name} is required")
    return value


def non_empty_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


TENANT_ID = require_env("PLANNER_TENANT_ID")
DEFAULT_PLAN_ID = os.environ.get("PLANNER_DEFAULT_PLAN_ID", "").strip() or None
GRAPH_ROOT = "https://graph.microsoft.com/v1.0"


def get_graph_token() -> str:
    cmd = [
        "az",
        "account",
        "get-access-token",
        "--resource-type",
        "ms-graph",
        "--tenant",
        TENANT_ID,
        "-o",
        "json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or "ERROR: failed to acquire Microsoft Graph token")
    data = json.loads(proc.stdout)
    return data["accessToken"]


TOKEN = get_graph_token()


def request_full(
    url: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Perform a Graph request and return both the JSON body and response headers.

    Headers are returned so callers can read the ETag required for Planner
    PATCH operations (Graph mandates an If-Match precondition on updates).
    """
    data = None
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8")
            resp_headers = {key: value for key, value in resp.headers.items()}
            return (json.loads(raw) if raw else {}), resp_headers
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"ERROR: Microsoft Graph returned HTTP {exc.code}: {raw[:1200]}") from exc


def request_json(url: str, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload, _ = request_full(url, method=method, body=body)
    return payload


def graph_url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return GRAPH_ROOT + path


def graph_get(path: str) -> dict[str, Any]:
    return request_json(graph_url(path))


def graph_post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    return request_json(graph_url(path), method="POST", body=body)


def graph_get_paged(path: str) -> list[dict[str, Any]]:
    url = graph_url(path)
    items: list[dict[str, Any]] = []
    while url:
        data = request_json(url)
        items.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
    return items


def me() -> dict[str, Any]:
    return graph_get("/me?$select=id,userPrincipalName,displayName")


def my_tasks() -> list[dict[str, Any]]:
    return graph_get_paged("/me/planner/tasks?$top=100")


def plan_by_id(plan_id: str) -> dict[str, Any]:
    return graph_get(f"/planner/plans/{urllib.parse.quote(plan_id)}")


def bucket_by_id(bucket_id: str) -> dict[str, Any]:
    return graph_get(f"/planner/buckets/{urllib.parse.quote(bucket_id)}")


def tasks_for_plan(plan_id: str) -> list[dict[str, Any]]:
    return graph_get_paged(f"/planner/plans/{urllib.parse.quote(plan_id)}/tasks?$top=100")


def buckets_for_plan(plan_id: str) -> list[dict[str, Any]]:
    return graph_get_paged(f"/planner/plans/{urllib.parse.quote(plan_id)}/buckets?$top=100")


def default_user_container_url() -> str:
    user = me()
    user_id = non_empty_str(user.get("id"))
    if not user_id:
        raise SystemExit("ERROR: Could not resolve /me id for Planner container")
    return f"{GRAPH_ROOT}/users/{user_id}"


def create_plan(title: str, container_url: str | None = None) -> dict[str, Any]:
    return graph_post(
        "/planner/plans",
        {
            "title": title,
            "container": {"url": container_url or default_user_container_url()},
        },
    )


def create_bucket(plan_id: str, name: str) -> dict[str, Any]:
    return graph_post(
        "/planner/buckets",
        {
            "name": name,
            "planId": plan_id,
        },
    )


def find_bucket(plan_id: str, selector: str) -> dict[str, Any]:
    buckets = buckets_for_plan(plan_id)
    for bucket in buckets:
        if non_empty_str(bucket.get("id")) == selector:
            return bucket
    selector_lower = selector.strip().lower()
    matches = [bucket for bucket in buckets if selector_lower == (bucket.get("name") or "").strip().lower()]
    if not matches:
        raise SystemExit(f"ERROR: No bucket matched in plan {plan_id}: {selector}")
    if len(matches) > 1:
        ids = ", ".join(non_empty_str(bucket.get("id")) or "?" for bucket in matches)
        raise SystemExit(f"ERROR: Multiple buckets matched '{selector}' in plan {plan_id}: {ids}")
    return matches[0]


def create_task(plan_id: str, bucket_id: str, title: str) -> dict[str, Any]:
    return graph_post(
        "/planner/tasks",
        {
            "planId": plan_id,
            "bucketId": bucket_id,
            "title": title,
        },
    )


def task_details(task_id: str) -> tuple[dict[str, Any], str]:
    """Return a task's details payload plus its ETag (needed for PATCH)."""
    payload, headers = request_full(graph_url(f"/planner/tasks/{urllib.parse.quote(task_id)}/details"))
    etag = headers.get("ETag") or headers.get("etag") or payload.get("@odata.etag") or ""
    return payload, etag


def update_task_details(
    task_id: str,
    description: str | None = None,
    checklist: list[str] | None = None,
    preview_type: str | None = None,
) -> dict[str, Any]:
    """Set a Planner task's description and/or checklist via Graph PATCH.

    Graph requires an If-Match precondition carrying the current ETag, which we
    read from a fresh GET. Checklist entries are written as a
    plannerChecklistItems open-type map keyed by a stable index id.
    """
    _, etag = task_details(task_id)
    if not etag:
        raise SystemExit("ERROR: Could not resolve task details ETag for PATCH")
    body: dict[str, Any] = {}
    if description is not None:
        body["description"] = description
    if checklist:
        items: dict[str, Any] = {}
        for index, text in enumerate(checklist, start=1):
            items[f"{index:04d}"] = {
                "@odata.type": "microsoft.graph.plannerChecklistItem",
                "title": text,
                "isChecked": False,
            }
        body["checklistItems"] = items
    if preview_type:
        body["previewType"] = preview_type
    if not body:
        raise SystemExit("ERROR: Nothing to update (provide description and/or checklist)")
    url = graph_url(f"/planner/tasks/{urllib.parse.quote(task_id)}/details")
    payload, _ = request_full(url, method="PATCH", body=body, extra_headers={"If-Match": etag, "Prefer": "return=representation"})
    return payload or {"updated": True, "taskId": task_id}


def visible_plans(tasks: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    plans = graph_get_paged("/me/planner/plans?$top=100")
    plans.sort(key=lambda plan: (plan.get("title") or "").lower())
    return plans


def normalize_plan(plan: dict[str, Any], task_count: int | None = None) -> dict[str, Any]:
    container = plan.get("container") or {}
    return {
        "id": plan.get("id"),
        "title": plan.get("title"),
        "createdDateTime": plan.get("createdDateTime"),
        "owner": plan.get("owner"),
        "containerUrl": container.get("url"),
        "taskCount": task_count,
    }


def normalize_bucket(bucket: dict[str, Any], task_count: int | None = None) -> dict[str, Any]:
    return {
        "id": bucket.get("id"),
        "name": bucket.get("name"),
        "planId": bucket.get("planId"),
        "orderHint": bucket.get("orderHint"),
        "taskCount": task_count,
    }


def normalize_task(task: dict[str, Any], bucket_name: str | None = None) -> dict[str, Any]:
    return {
        "id": task.get("id"),
        "title": task.get("title"),
        "planId": task.get("planId"),
        "bucketId": task.get("bucketId"),
        "bucketName": bucket_name,
        "percentComplete": task.get("percentComplete"),
        "priority": task.get("priority"),
        "startDateTime": task.get("startDateTime"),
        "dueDateTime": task.get("dueDateTime"),
        "createdDateTime": task.get("createdDateTime"),
        "completedDateTime": task.get("completedDateTime"),
        "hasDescription": task.get("hasDescription"),
    }


def find_plan(selector: str | None) -> dict[str, Any] | None:
    if not selector:
        if DEFAULT_PLAN_ID:
            return plan_by_id(DEFAULT_PLAN_ID)
        return None

    try:
        return plan_by_id(selector)
    except SystemExit:
        pass

    tasks = my_tasks()
    plans = visible_plans(tasks)
    selector_lower = selector.lower()
    matches = [plan for plan in plans if selector_lower in (plan.get("title") or "").lower()]
    if not matches:
        raise SystemExit(f"ERROR: No visible plan matched: {selector}")
    if len(matches) > 1:
        titles = ", ".join(f"{plan.get('title')} ({plan.get('id')})" for plan in matches[:6])
        raise SystemExit(f"ERROR: Multiple plans matched '{selector}': {titles}")
    return matches[0]


def resolve_bucket_names(tasks: list[dict[str, Any]]) -> dict[str, str]:
    bucket_names: dict[str, str] = {}
    bucket_ids = sorted(
        bucket_id
        for bucket_id in (non_empty_str(task.get("bucketId")) for task in tasks)
        if bucket_id
    )
    for bucket_id in bucket_ids:
        try:
            bucket_names[bucket_id] = bucket_by_id(bucket_id).get("name") or ""
        except SystemExit:
            bucket_names[bucket_id] = ""
    return bucket_names


def ensure_unique_plan_title(title: str) -> None:
    existing = [plan for plan in visible_plans() if (plan.get("title") or "").strip().lower() == title.strip().lower()]
    if existing:
        ids = ", ".join(non_empty_str(plan.get("id")) or "?" for plan in existing)
        raise SystemExit(f"ERROR: Plan title already exists: {title} ({ids})")


def print_table(headers: list[str], rows: list[list[Any]]) -> None:
    if not rows:
        print("No results.")
        return
    widths = [len(header) for header in headers]
    string_rows = [["" if value is None else str(value) for value in row] for row in rows]
    for row in string_rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))
    print("  ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers)))
    for row in string_rows:
        print("  ".join(value.ljust(widths[idx]) for idx, value in enumerate(row)))


def command_doctor(_: argparse.Namespace) -> None:
    proc = subprocess.run(["az", "account", "show", "-o", "json"], capture_output=True, text=True, timeout=45)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or "ERROR: az account show failed")
    account = json.loads(proc.stdout)
    me_data = me()
    tasks = my_tasks()
    plans = visible_plans(tasks)
    print(f"Azure account: {account.get('user', {}).get('name', '—')}")
    print(f"Azure default tenant: {account.get('tenantId', '—')}")
    print(f"Planner tenant: {TENANT_ID}")
    print(f"Graph /me: OK ({me_data.get('displayName', '—')} / {me_data.get('userPrincipalName', '—')})")
    print(f"Visible Planner tasks: {len(tasks)}")
    print(f"Visible plans via my tasks: {len(plans)}")
    if DEFAULT_PLAN_ID:
        try:
            plan = plan_by_id(DEFAULT_PLAN_ID)
            print(f"Default plan: OK ({plan.get('title', '—')} / {plan.get('id', '—')})")
        except SystemExit as exc:
            print(str(exc))


def command_plans(args: argparse.Namespace) -> None:
    tasks = my_tasks()
    by_plan = Counter(
        plan_id
        for plan_id in (non_empty_str(task.get("planId")) for task in tasks)
        if plan_id
    )
    plans = []
    for plan in visible_plans(tasks):
        title = plan.get("title") or ""
        if args.text and args.text.lower() not in title.lower():
            continue
        plan_id = non_empty_str(plan.get("id"))
        plans.append(normalize_plan(plan, task_count=by_plan.get(plan_id or "", 0)))
    if args.format == "json":
        print(json.dumps(plans, ensure_ascii=False, indent=2))
        return
    rows = [[p["id"], p["title"], p["taskCount"]] for p in plans]
    print_table(["Plan ID", "Title", "Visible Tasks"], rows)


def command_plan(args: argparse.Namespace) -> None:
    plan = find_plan(args.selector)
    if plan is None:
        raise SystemExit("ERROR: No plan selector given and no PLANNER_DEFAULT_PLAN_ID configured")
    plan_id = non_empty_str(plan.get("id"))
    if not plan_id:
        raise SystemExit("ERROR: Resolved plan has no id")
    tasks = tasks_for_plan(plan_id)
    buckets = buckets_for_plan(plan_id)
    bucket_counts = Counter(
        bucket_id
        for bucket_id in (non_empty_str(task.get("bucketId")) for task in tasks)
        if bucket_id
    )
    payload = {
        "plan": normalize_plan(plan, len(tasks)),
        "buckets": [normalize_bucket(bucket, bucket_counts.get(non_empty_str(bucket.get("id")) or "", 0)) for bucket in buckets],
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"# Planner Plan — {plan.get('title')}")
    print()
    print(f"- Plan ID: {plan_id}")
    print(f"- Owner: {plan.get('owner') or '—'}")
    print(f"- Visible tasks in plan: {len(tasks)}")
    print(f"- Buckets: {len(buckets)}")
    print()
    print("## Buckets")
    if not buckets:
        print("- No buckets found.")
    for bucket in buckets:
        item = normalize_bucket(bucket, bucket_counts.get(non_empty_str(bucket.get("id")) or "", 0))
        print(f"- {item['name']} ({item['id']}): {item['taskCount']} task(s)")


def command_buckets(args: argparse.Namespace) -> None:
    plan = find_plan(args.selector)
    if plan is None:
        raise SystemExit("ERROR: No plan selector given and no PLANNER_DEFAULT_PLAN_ID configured")
    plan_id = non_empty_str(plan.get("id"))
    if not plan_id:
        raise SystemExit("ERROR: Resolved plan has no id")
    tasks = tasks_for_plan(plan_id)
    bucket_counts = Counter(
        bucket_id
        for bucket_id in (non_empty_str(task.get("bucketId")) for task in tasks)
        if bucket_id
    )
    buckets = [normalize_bucket(bucket, bucket_counts.get(non_empty_str(bucket.get("id")) or "", 0)) for bucket in buckets_for_plan(plan_id)]
    if args.format == "json":
        print(json.dumps({"plan": normalize_plan(plan, len(tasks)), "buckets": buckets}, ensure_ascii=False, indent=2))
        return
    rows = [[b["id"], b["name"], b["taskCount"]] for b in buckets]
    print_table(["Bucket ID", "Name", "Tasks"], rows)


def command_tasks(args: argparse.Namespace) -> None:
    if args.selector:
        plan = find_plan(args.selector)
        if plan is None:
            raise SystemExit("ERROR: No plan selector given and no PLANNER_DEFAULT_PLAN_ID configured")
        plan_id = non_empty_str(plan.get("id"))
        if not plan_id:
            raise SystemExit("ERROR: Resolved plan has no id")
        tasks = tasks_for_plan(plan_id)
    else:
        plan = None
        tasks = my_tasks()
    bucket_names = resolve_bucket_names(tasks)
    normalized = [normalize_task(task, bucket_names.get(non_empty_str(task.get("bucketId")) or "", "")) for task in tasks]
    normalized.sort(key=lambda item: ((item.get("bucketName") or "").lower(), (item.get("title") or "").lower()))
    if args.format == "json":
        payload: dict[str, Any] = {"tasks": normalized}
        if plan is not None:
            payload["plan"] = normalize_plan(plan, len(tasks))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    rows = [[t["id"], t["bucketName"], t["percentComplete"], t["dueDateTime"], t["title"]] for t in normalized]
    print_table(["Task ID", "Bucket", "%", "Due", "Title"], rows)


def command_mine(args: argparse.Namespace) -> None:
    args.selector = None
    command_tasks(args)


def command_search(args: argparse.Namespace) -> None:
    selector = args.selector
    if selector:
        plan = find_plan(selector)
        if plan is None:
            raise SystemExit("ERROR: No plan selector given and no PLANNER_DEFAULT_PLAN_ID configured")
        plan_id = non_empty_str(plan.get("id"))
        if not plan_id:
            raise SystemExit("ERROR: Resolved plan has no id")
        tasks = tasks_for_plan(plan_id)
    else:
        plan = None
        tasks = my_tasks()
    bucket_names = resolve_bucket_names(tasks)
    needle = args.text.lower()
    matches = []
    for task in tasks:
        title = task.get("title") or ""
        if needle in title.lower():
            matches.append(normalize_task(task, bucket_names.get(non_empty_str(task.get("bucketId")) or "", "")))
    if args.format == "json":
        payload: dict[str, Any] = {"tasks": matches}
        if plan is not None:
            payload["plan"] = normalize_plan(plan, len(tasks))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    rows = [[t["id"], t["bucketName"], t["percentComplete"], t["dueDateTime"], t["title"]] for t in matches]
    print_table(["Task ID", "Bucket", "%", "Due", "Title"], rows)


def command_create_plan(args: argparse.Namespace) -> None:
    ensure_unique_plan_title(args.title)
    created = create_plan(args.title)
    print(json.dumps(normalize_plan(created), ensure_ascii=False, indent=2))


def command_create_bucket(args: argparse.Namespace) -> None:
    plan = find_plan(args.selector)
    if plan is None:
        raise SystemExit("ERROR: No plan selector given and no PLANNER_DEFAULT_PLAN_ID configured")
    plan_id = non_empty_str(plan.get("id"))
    if not plan_id:
        raise SystemExit("ERROR: Resolved plan has no id")
    existing = [bucket for bucket in buckets_for_plan(plan_id) if (bucket.get("name") or "").strip().lower() == args.name.strip().lower()]
    if existing:
        ids = ", ".join(non_empty_str(bucket.get("id")) or "?" for bucket in existing)
        raise SystemExit(f"ERROR: Bucket already exists in plan '{plan.get('title')}': {args.name} ({ids})")
    created = create_bucket(plan_id, args.name)
    print(json.dumps(normalize_bucket(created), ensure_ascii=False, indent=2))


def command_create_task(args: argparse.Namespace) -> None:
    plan = find_plan(args.selector)
    if plan is None:
        raise SystemExit("ERROR: No plan selector given and no PLANNER_DEFAULT_PLAN_ID configured")
    plan_id = non_empty_str(plan.get("id"))
    if not plan_id:
        raise SystemExit("ERROR: Resolved plan has no id")
    bucket = find_bucket(plan_id, args.bucket)
    bucket_id = non_empty_str(bucket.get("id"))
    if not bucket_id:
        raise SystemExit("ERROR: Resolved bucket has no id")
    existing_tasks = tasks_for_plan(plan_id)
    title_lower = args.title.strip().lower()
    duplicates = [task for task in existing_tasks if (task.get("title") or "").strip().lower() == title_lower]
    if duplicates:
        ids = ", ".join(non_empty_str(task.get("id")) or "?" for task in duplicates)
        raise SystemExit(f"ERROR: Task title already exists in plan '{plan.get('title')}': {args.title} ({ids})")
    created = create_task(plan_id, bucket_id, args.title)
    print(json.dumps(normalize_task(created, bucket.get("name") or ""), ensure_ascii=False, indent=2))


def command_task_details(args: argparse.Namespace) -> None:
    description: str | None = None
    if args.description_file:
        description = open(args.description_file, "r", encoding="utf-8").read()
    elif args.description is not None:
        description = args.description
    checklist = list(args.check) if args.check else None
    if description is None and not checklist and not args.show:
        raise SystemExit("ERROR: provide --description/--description-file and/or --check, or use --show")
    if args.show:
        payload, etag = task_details(args.task_id)
        checklist_items = payload.get("checklistItems") or {}
        out = {
            "taskId": args.task_id,
            "etag": etag,
            "description": payload.get("description"),
            "previewType": payload.get("previewType"),
            "checklist": [
                {"id": key, "title": (val or {}).get("title"), "isChecked": (val or {}).get("isChecked")}
                for key, val in sorted(checklist_items.items())
            ],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    result = update_task_details(
        args.task_id,
        description=description,
        checklist=checklist,
        preview_type=args.preview_type,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def command_scaffold_board(args: argparse.Namespace) -> None:
    ensure_unique_plan_title(args.title)
    created_plan = create_plan(args.title)
    plan_id = non_empty_str(created_plan.get("id"))
    if not plan_id:
        raise SystemExit("ERROR: Created plan returned no id")
    bucket_names = args.buckets or ["Inbox", "Current", "Next", "Blocked", "Done"]
    created_buckets = [normalize_bucket(create_bucket(plan_id, bucket_name)) for bucket_name in bucket_names]
    payload = {"plan": normalize_plan(created_plan), "buckets": created_buckets}
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def command_raw(args: argparse.Namespace) -> None:
    data = graph_get(args.path)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent-friendly Microsoft Planner helper")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Verify tenant/token access and visible plans")
    doctor.set_defaults(func=command_doctor)

    plans = sub.add_parser("plans", help="List visible plans inferred from my tasks")
    plans.add_argument("text", nargs="?")
    plans.add_argument("--format", choices=["table", "json"], default="table")
    plans.set_defaults(func=command_plans)

    plan = sub.add_parser("plan", help="Summarize a plan by id or title")
    plan.add_argument("selector")
    plan.add_argument("--format", choices=["markdown", "json"], default="markdown")
    plan.set_defaults(func=command_plan)

    buckets = sub.add_parser("buckets", help="List buckets for a plan")
    buckets.add_argument("selector")
    buckets.add_argument("--format", choices=["table", "json"], default="table")
    buckets.set_defaults(func=command_buckets)

    tasks = sub.add_parser("tasks", help="List tasks for a plan, or all visible tasks when omitted")
    tasks.add_argument("selector", nargs="?")
    tasks.add_argument("--format", choices=["table", "json"], default="table")
    tasks.set_defaults(func=command_tasks)

    mine = sub.add_parser("mine", help="Alias for visible tasks via /me/planner/tasks")
    mine.add_argument("--format", choices=["table", "json"], default="table")
    mine.set_defaults(func=command_mine)

    search = sub.add_parser("search", help="Search task titles")
    search.add_argument("text")
    search.add_argument("selector", nargs="?")
    search.add_argument("--format", choices=["table", "json"], default="table")
    search.set_defaults(func=command_search)

    create_plan_parser = sub.add_parser("create-plan", help="Create a new Planner plan in the current user's container")
    create_plan_parser.add_argument("title")
    create_plan_parser.set_defaults(func=command_create_plan)

    create_bucket_parser = sub.add_parser("create-bucket", help="Create a bucket in an existing plan")
    create_bucket_parser.add_argument("selector")
    create_bucket_parser.add_argument("name")
    create_bucket_parser.set_defaults(func=command_create_bucket)

    create_task_parser = sub.add_parser("create-task", help="Create a task in a specific bucket of a plan")
    create_task_parser.add_argument("selector")
    create_task_parser.add_argument("bucket")
    create_task_parser.add_argument("title")
    create_task_parser.set_defaults(func=command_create_task)

    task_details_parser = sub.add_parser("task-details", help="Show or set a task's description and checklist")
    task_details_parser.add_argument("task_id")
    task_details_parser.add_argument("--description", default=None, help="Set the task description (inline text)")
    task_details_parser.add_argument("--description-file", default=None, help="Read the task description from a file")
    task_details_parser.add_argument("--check", action="append", default=[], help="Add a checklist item (repeatable)")
    task_details_parser.add_argument("--preview-type", choices=["automatic", "noPreview", "checklist", "description", "reference"], default=None)
    task_details_parser.add_argument("--show", action="store_true", help="Print current details instead of updating")
    task_details_parser.set_defaults(func=command_task_details)

    scaffold_board = sub.add_parser("scaffold-board", help="Create a plan plus a minimal default bucket set")
    scaffold_board.add_argument("title")
    scaffold_board.add_argument("buckets", nargs="*")
    scaffold_board.set_defaults(func=command_scaffold_board)

    raw = sub.add_parser("raw", help="GET an arbitrary Microsoft Graph path")
    raw.add_argument("path")
    raw.set_defaults(func=command_raw)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
