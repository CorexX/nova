# NOVA Memory/Context Engine Refactor Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Refactor NOVA into a lean local-first memory/context system for Hermes and other agents, removing everything that duplicates agent runtime, gateway, cron, persona, or workflow orchestration.

**Architecture:** Hermes remains the active agent runtime. NOVA becomes an MCP-callable memory/context engine over `/path/to/nova-knowledge`, with Markdown as source of truth and rebuildable indexes for search, retrieval, context packs, provenance, and later graph/temporal memory. NOVA does not own chat, cron, messaging, LLM providers, personas, autonomous task execution, or project-management behavior beyond memory primitives.

**Tech Stack:** Python, MCP, Markdown, local filesystem, SQLite/FTS planned, sentence-transformers/vector retrieval optional, `/path/to/nova-knowledge` as vault.

---

## 0. Source Research Snapshot

Live search and architecture review checked these current memory/context directions:

- Letta / MemGPT: core memory vs archival memory, explicit memory management, virtual context.
  - Source: https://www.letta.com/
  - Source: https://github.com/letta-ai/letta
  - Source: https://arxiv.org/abs/2310.08560
- Zep / Graphiti: temporal knowledge graph memory for agents.
  - Source: https://arxiv.org/abs/2501.13956
  - Source: https://github.com/getzep/graphiti
  - Source: https://www.getzep.com/
- mem0: universal memory layer with add/search/update/delete style APIs and scoping.
  - Source: https://github.com/mem0ai/mem0
  - Source: https://docs.mem0.ai/
- LangGraph memory: short-term thread memory vs long-term namespaced memory; semantic, episodic, procedural classes.
  - Source: https://docs.langchain.com/oss/python/langgraph/memory
- LlamaIndex context engineering / RAG: document nodes, metadata-rich indexes, routers, graph/vector/full-text retrieval.
  - Source: https://www.llamaindex.ai/blog/context-engineering-what-it-is-and-techniques-to-consider

### Conclusions for NOVA

1. **Do not build another agent runtime.** Hermes already pays that rent.
2. **Markdown remains source of truth.** Indexes are derived and disposable.
3. **Vector DB is not memory.** It is one retrieval signal.
4. **Use memory tiers:** profile/core, project, semantic facts, episodic events, procedural workflows, archival sources.
5. **Use hybrid retrieval:** metadata + full-text + vector + recency + graph expansion later.
6. **Every memory needs provenance:** file path, source block/lines where possible, timestamp, confidence, scope.
7. **Writes should be append-first or patch-proposed.** Avoid silent overwrite and avoid memory pollution.
8. **Temporal truth matters:** observed-at, valid-from, supersedes, stale/active status.

---

## 1. Target Positioning

### NOVA becomes

> A local-first Markdown-based memory and context engine that ingests, indexes, retrieves, packages, and curates durable context for Hermes Agent and other MCP-capable tools.

### NOVA explicitly stops being

- Agent runtime
- Chat interface
- Persona/prompt system
- Cron scheduler
- Telegram/gateway/server-mode implementation
- Copilot/Codex setup manager
- Autonomous planner
- Project-management assistant
- LLM provider integration layer

### Runtime ownership

```text
User / Telegram / CLI / Hermes session
        ↓
Hermes Agent
        ↓ MCP
NOVA Memory/Context Engine
        ↓
/path/to/nova-knowledge
        ↓
Derived local indexes
```

---

## 2. Final Lean Repository Shape

Target tree after cleanup:

```text
/path/to/nova/
├── README.md
├── CONTRACTS.md
├── requirements.txt
├── .env.example
├── .gitignore
├── docs/
│   └── plans/
│       └── 2026-04-26-nova-memory-context-refactor.md
├── mcp/
│   ├── README.md
│   ├── nova_mcp_core_server.py
│   ├── requirements.txt
│   └── tools/
│       ├── __init__.py
│       ├── common.py
│       ├── paths.py
│       ├── search_shared.py
│       ├── context_resolve.py
│       ├── knowledge_query.py
│       ├── knowledge_update.py
│       ├── memory_maintain.py
│       └── health_checks.py
├── tests/
│   └── mcp/
│       └── test_*.py
└── meta/
    ├── ARCHITECTURE.md
    ├── PRINCIPLES.md
    └── SYSTEM.md
```

Optional later:

```text
schemas/
├── memory.schema.json
└── context-pack.schema.json
```

---

## 3. Keep / Remove / Reshape

### Keep and harden

| Path | Reason |
|---|---|
| `mcp/nova_mcp_core_server.py` | MCP integration surface |
| `mcp/tools/context_resolve.py` | Main context pack/retrieval primitive |
| `mcp/tools/knowledge_query.py` | Memory search primitive |
| `mcp/tools/knowledge_update.py` | Persistence primitive, later patch-oriented |
| `mcp/tools/search_shared.py` | Current semantic search backend |
| `mcp/tools/paths.py` | Config boundary for core/vault/index paths |
| `mcp/tools/common.py` | Utility helpers |
| `mcp/tools/health_checks.py` | Keep only if memory-engine scoped |
| `README.md`, `CONTRACTS.md`, `mcp/README.md` | Rewrite to match new identity |
| `meta/ARCHITECTURE.md`, `meta/PRINCIPLES.md`, `meta/SYSTEM.md` | Rewrite/reduce to memory principles |

### Remove completely

| Path | Reason |
|---|---|
| `skills/` | Hermes owns skills/procedures |
| `playbooks/` | Hermes or nova-knowledge owns workflows; core should not |
| `templates/personas/` | Hermes owns persona/tone |
| `.github/copilot-instructions.md` | Agent-runtime prompt policy |
| `launcher.py` | Runtime/venv/server launcher duplication |
| `setup.py` | Broad client/setup/persona/knowledge bootstrapping duplication |
| `.nova-index/` | Generated index artifact must not be tracked |
| `__pycache__/` anywhere | Generated junk |

### Reshape

| Path | Change |
|---|---|
| `requirements.txt` | Remove `anthropic`; keep memory/index deps only |
| `.env.example` | Remove LLM/n8n/gateway keys; keep NOVA paths/search only |
| `mcp/tools/system_maintain.py` | Rename to `memory_maintain.py`; remove restart; keep health/index |
| `mcp/tools/project_continue.py` | Remove from registry; later replace by `get_context_pack(project=...)` behavior |
| `mcp/tools/project_create.py` | Remove from registry; project creation belongs to Hermes workflow or vault templates |
| `mcp/tools/paths.py` | Rename dataclass conceptually to `NovaMemoryConfig`; remove n8n/vault/persona leftovers |

---

## 4. Target Tool Surface

### Phase 1 MCP tools

Keep the public surface small:

1. `nova_context_resolve`
   - Input: `query`, optional `project_hint`, `scope`, `token_budget`, `include_inventory`
   - Output: context items, citations/sources, confidence, inventory if requested

2. `nova_knowledge_query`
   - Input: `query`, optional `project`, `topic`, `type`, `limit`
   - Output: ranked matches with snippets and sources

3. `nova_knowledge_update`
   - Input: `content`, `source`, optional `project`, `topic`, `title`, `confidence`, `next_action`
   - Output: written paths / proposed patch ids
   - Phase 1: append-first direct writes
   - Phase 2: patch proposal mode

4. `nova_memory_maintain`
   - Input: `operation = health | index | validate`
   - Output: status, details, artifacts
   - No restart. Hermes owns process lifecycle.

### Phase 2 tool additions, only after Phase 1 is stable

5. `nova_memory_get`
   - Fetch memory/document by id/path.

6. `nova_memory_propose_patch`
   - Generate a proposed Markdown patch for human/Hermes approval.

7. `nova_episode_record`
   - Record episodic events without promoting them to durable facts.

Do not add these until tests exist for the first four.

---

## 5. Memory Model

### Memory classes

Use a small controlled vocabulary:

```text
fact
preference
decision
task
procedure
episode
source
summary
question
constraint
entity
relationship
```

### Scopes

```text
global
user
project
repo
task
session
agent
```

### Lifecycle states

```text
active
candidate
superseded
stale
archived
rejected
```

### Minimal metadata contract

Every durable memory should be able to expose:

```yaml
id: mem_YYYYMMDD_slug_or_hash
type: decision
scope:
  user: alex
  project: nova
status: active
created: 2026-04-26
updated: 2026-04-26
confidence: 0.8
importance: 0.7
source:
  path: projects/internal/nova/...
  lines: null
tags: [nova, memory]
supersedes: []
expires: null
```

Do not require all existing vault files to have this immediately. Implement this as preferred schema for new writes and index normalization.

---

## 6. Context Pack Format

`nova_context_resolve` should evolve toward returning a structured context pack:

```json
{
  "status": "ok",
  "query": "refactor nova memory engine",
  "project_hint": "nova",
  "context_pack": {
    "summary": "NOVA is being refactored into a memory/context engine for Hermes.",
    "relevant_decisions": [],
    "relevant_constraints": [],
    "relevant_sources": [],
    "open_questions": [],
    "suggested_next_actions": []
  },
  "items": [
    {
      "path": "projects/internal/nova/knowledge/...md",
      "snippet": "...",
      "score": 0.72,
      "why_selected": "semantic+project+recent",
      "citation": {
        "path": "...",
        "section": "...",
        "lines": null
      }
    }
  ],
  "confidence": 0.71
}
```

Initial implementation can preserve current output fields and add `context_pack` later.

---

## 7. Implementation Tasks

### Task 1: Baseline cleanup branch verification

**Objective:** Ensure work happens on the correct branch and repo is clean before destructive cleanup.

**Files:** none

**Steps:**

1. Run:
   ```bash
   git branch --show-current
   git status --short
   ```
2. Expected branch:
   ```text
   refactor/memory-context-core
   ```
3. Expected status: only this plan file, if already created.

---

### Task 2: Remove generated artifacts and tracked index junk

**Objective:** Remove files that are generated or private-runtime state.

**Files:**
- Remove: `.nova-index/`
- Remove: any `__pycache__/`

**Steps:**

1. Run:
   ```bash
   git rm -r --cached .nova-index || true
   rm -rf .nova-index __pycache__ mcp/__pycache__ mcp/tools/__pycache__ skills/__pycache__
   ```
2. Patch `.gitignore` to include:
   ```gitignore
   # NOVA generated indexes
   .nova/
   .nova-index/
   **/chroma.sqlite3
   **/*.sqlite3

   # Python generated
   __pycache__/
   *.py[cod]
   .pytest_cache/
   ```
3. Verify:
   ```bash
   git status --short
   ```

---

### Task 3: Remove runtime/persona/workflow directories

**Objective:** Cut everything that duplicates Hermes runtime responsibilities.

**Files:**
- Remove: `skills/`
- Remove: `playbooks/`
- Remove: `templates/personas/`
- Remove: `.github/copilot-instructions.md`

**Steps:**

1. Run:
   ```bash
   git rm -r skills playbooks templates/personas .github/copilot-instructions.md
   ```
2. If `templates/knowledge/` remains, keep only if docs say NOVA can bootstrap a blank vault. Otherwise remove `templates/` entirely.
3. Verify no references to removed directories remain:
   ```bash
   python - <<'PY'
   from pathlib import Path
   needles = ['skills/', 'playbooks/', 'templates/personas', 'copilot-instructions']
   for p in Path('.').rglob('*'):
       if p.is_file() and '.git' not in p.parts:
           text = p.read_text(encoding='utf-8', errors='ignore')
           for n in needles:
               if n in text:
                   print(p, n)
   PY
   ```

---

### Task 4: Remove launcher/setup runtime duplication

**Objective:** Remove NOVA's own runtime setup/orchestration layer.

**Files:**
- Remove: `launcher.py`
- Remove: `setup.py`
- Modify: `README.md`
- Modify: `mcp/README.md`

**Steps:**

1. Run:
   ```bash
   git rm launcher.py setup.py
   ```
2. In docs, replace launcher-based startup with direct MCP command:
   ```bash
   python /path/to/nova/mcp/nova_mcp_core_server.py
   ```
3. State that Hermes should manage process/MCP config.

---

### Task 5: Narrow MCP registry to memory tools only

**Objective:** Ensure server exposes only memory/context primitives.

**Files:**
- Modify: `mcp/nova_mcp_core_server.py`
- Remove or stop registering: `mcp/tools/project_continue.py`
- Remove or stop registering: `mcp/tools/project_create.py`
- Rename/modify: `mcp/tools/system_maintain.py` → `mcp/tools/memory_maintain.py`

**Implementation sketch:**

```python
from tools import (
    context_resolve,
    knowledge_query,
    knowledge_update,
    memory_maintain,
)

server = Server("nova-memory")

TOOLS = {
    "nova_context_resolve": context_resolve,
    "nova_knowledge_query": knowledge_query,
    "nova_knowledge_update": knowledge_update,
    "nova_memory_maintain": memory_maintain,
}
```

**Verification:**

Run a small import check:

```bash
python -m compileall -q mcp
```

---

### Task 6: Replace `system_maintain` with `memory_maintain`

**Objective:** Remove process lifecycle operations and keep only memory maintenance.

**Files:**
- Rename: `mcp/tools/system_maintain.py` → `mcp/tools/memory_maintain.py`
- Modify: `mcp/tools/health_checks.py`

**Required API:**

```text
operation: health | index | validate
```

**Remove:**

- `restart`
- `delay_seconds`
- `os._exit`
- startup prewarm if it causes runtime ownership confusion; optional lazy init is fine

**Health should report:**

- `knowledge_root_exists`
- `knowledge_markdown_files`
- `index_root_exists`
- `semantic_index_exists`
- `search_enabled`
- `embedding_model`

---

### Task 7: Simplify configuration model

**Objective:** Remove unrelated integration/runtime config.

**Files:**
- Modify: `mcp/tools/paths.py`
- Modify: `.env.example`
- Modify: `requirements.txt`
- Modify: `mcp/requirements.txt`

**New config fields:**

```python
@dataclass(frozen=True)
class NovaMemoryConfig:
    core_root: Path
    knowledge_root: Path
    index_root: Path
    chroma_path: Path
    search_enabled: bool = True
    embedding_model: str = "all-MiniLM-L6-v2"
    search_top_k: int = 5
```

**Remove fields:**

- `vault_name`
- `daily_folder`
- `n8n_base_url`
- `n8n_api_key`
- `n8n_insecure_tls`
- logging if unused

**`.env.example`:**

```env
NOVA_CORE_ROOT=/path/to/nova
NOVA_KNOWLEDGE_ROOT=/path/to/nova-knowledge
NOVA_INDEX_ROOT=/path/to/nova/.nova/index
NOVA_SEARCH_ENABLED=true
NOVA_EMBEDDING_MODEL=all-MiniLM-L6-v2
NOVA_ALLOW_EXTERNAL_PATHS=false
```

**Requirements:** remove `anthropic`.

---

### Task 8: Rewrite README as memory/context engine

**Objective:** Make public positioning unambiguous.

**Files:**
- Modify: `README.md`

**Required sections:**

1. What NOVA is
2. What NOVA is not
3. Relationship to Hermes
4. Architecture diagram
5. Tool surface
6. Configuration
7. Indexing
8. Persistence rules
9. Development/test commands

**Key text:**

```md
NOVA is not an agent runtime. Hermes executes. NOVA remembers.
```

---

### Task 9: Rewrite CONTRACTS.md

**Objective:** Define strict memory engine contracts.

**Files:**
- Modify: `CONTRACTS.md`

**Required contracts:**

- Repository boundary
- Knowledge root boundary
- Read contract
- Write contract
- Context pack contract
- Index contract
- Provenance contract
- No-runtime contract

**No-runtime contract:**

```md
NOVA MUST NOT own chat sessions, gateway delivery, cron scheduling,
agent persona, model provider configuration, autonomous task execution,
or process lifecycle beyond serving MCP requests.
```

---

### Task 10: Rewrite meta docs

**Objective:** Remove old gateway/server/persona vision and encoding damage.

**Files:**
- Modify: `meta/ARCHITECTURE.md`
- Modify: `meta/PRINCIPLES.md`
- Modify: `meta/SYSTEM.md`
- Remove or rewrite: `meta/ROADMAP.md`

**Recommendation:** delete `meta/ROADMAP.md` and recreate a lean roadmap:

```md
# NOVA Roadmap

## Phase 1: Lean Memory MCP
## Phase 2: Context Packs
## Phase 3: Patch-based Memory Writes
## Phase 4: Hybrid Retrieval
## Phase 5: Lightweight Temporal Graph
```

---

### Task 11: Add tests before deeper refactors

**Objective:** Create minimum confidence net.

**Files:**
- Create: `tests/mcp/test_paths.py`
- Create: `tests/mcp/test_knowledge_update.py`
- Create: `tests/mcp/test_context_resolve_contract.py`
- Create: `tests/mcp/test_memory_maintain.py`

**Test principles:**

- Use `tmp_path` for fake knowledge root.
- Never write to `/path/to/nova-knowledge` during tests.
- Validate JSON shape.
- Validate append behavior.
- Validate missing root / disabled search errors.

**Example test sketch:**

```python
import json
from pathlib import Path

import pytest
from mcp.tools import knowledge_update

@pytest.mark.asyncio
async def test_knowledge_update_writes_append_first(tmp_path, monkeypatch):
    knowledge = tmp_path / "vault"
    knowledge.mkdir()
    monkeypatch.setenv("NOVA_KNOWLEDGE_ROOT", str(knowledge))
    monkeypatch.setenv("NOVA_CORE_ROOT", str(tmp_path / "core"))

    result = await knowledge_update.execute({
        "content": "NOVA should be memory-only.",
        "source": "test",
        "project": "nova",
        "topic": "architecture",
        "title": "Memory-only decision",
        "confidence": 0.9,
    }, tmp_path)

    payload = json.loads(result[0].text)
    assert payload["status"] == "ok"
    assert payload["written_paths"]
```

---

### Task 12: Run verification

**Objective:** Ensure branch is coherent.

**Commands:**

```bash
python -m compileall -q .
python -m pytest -q
python - <<'PY'
from mcp.nova_mcp_core_server import TOOLS
print(sorted(TOOLS))
assert sorted(TOOLS) == [
    'nova_context_resolve',
    'nova_knowledge_query',
    'nova_knowledge_update',
    'nova_memory_maintain',
]
PY
```

Expected:

```text
compileall passes
pytest passes
only four tools listed
```

---

## 8. Commit Plan

Commit in small chunks:

```bash
git add docs/plans/2026-04-26-nova-memory-context-refactor.md
git commit -m "docs: plan nova memory context refactor"

git add .gitignore
git rm -r --cached .nova-index || true
git commit -m "chore: remove generated index artifacts"

git rm -r skills playbooks templates/personas .github/copilot-instructions.md
git commit -m "chore: remove runtime workflow and persona assets"

git rm launcher.py setup.py
git commit -m "chore: remove standalone runtime setup layer"

git add mcp/
git commit -m "refactor: narrow nova mcp surface to memory tools"

git add README.md CONTRACTS.md meta/ mcp/README.md .env.example requirements.txt
git commit -m "docs: redefine nova as memory context engine"

git add tests/
git commit -m "test: add memory engine contract tests"
```

---

## 9. Definition of Done

NOVA is considered successfully narrowed when:

- Branch `refactor/memory-context-core` exists.
- No tracked generated index or pycache remains.
- No skills/playbooks/personas/launcher/setup runtime code remains.
- MCP server exposes only memory/context/maintenance tools.
- Docs say clearly: Hermes executes, NOVA remembers.
- `python -m compileall -q .` passes.
- `python -m pytest -q` passes.
- No test touches real `/path/to/nova-knowledge`.
- README contains a minimal Hermes MCP integration example.

---

## 10. Later, Not Now

Do not implement these during the cleanup pass:

- Full temporal graph
- LLM-based memory extraction
- Web UI
- Telegram gateway
- Daily briefing cron
- Autonomous consolidation
- Multi-agent project planning
- Hosted vector service

These are useful later, but they do not pay rent in the first cleanup pass.

---

## 11. Recommended Next Step

Start with Tasks 2–4: remove junk/runtime/persona/workflow material. Then narrow the MCP registry. Only after the tool surface is lean should docs and tests be finalized.

In Soviet filing cabinet terms: first remove the duplicate forms, then label the drawers.
