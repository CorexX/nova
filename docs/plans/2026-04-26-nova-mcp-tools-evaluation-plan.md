# NOVA MCP Tools Evaluation and Improvement Plan

> **For Hermes:** Use `subagent-driven-development` if this plan is implemented task-by-task.

**Goal:** Evaluate the current NOVA MCP tool surface, define the best possible version of each tool, and plan focused improvements without turning NOVA back into an operator runtime.

**Architecture:** NOVA stays a local-first Markdown memory/context engine exposed over MCP. The public surface remains intentionally small: context resolution, knowledge query, knowledge update, and memory maintenance. Improvements should harden retrieval quality, provenance, indexing, validation, and write safety rather than add runtime behavior.

**Tech Stack:** Python, MCP, Markdown, local filesystem, JSON semantic index today, sentence-transformers, future SQLite metadata/FTS, optional vector retrieval.

---

## 1. Executive Summary

NOVA is in the right conceptual place: small MCP surface, clear boundary, Markdown source of truth, rebuildable index. The current implementation is a solid Phase-1 prototype, but it is still too vector-only, too implicit in metadata, and too weak in validation/write semantics for long-term trust.

Current state:

- Public MCP tools: exactly 4.
- Index: rebuilt successfully; 477 Markdown files, 3320 chunks.
- Current index schema: `id`, `path`, `section`, `line_start`, `line_end`, `memory_type`, `chunk_index`, `text`, `embedding`.
- Tool tests: partially present, but current unittest run fails due test import shadowing of installed `mcp` package.
- Retrieval works, but line metadata is lost in `semantic_search` results from JSON index because `search_shared._search_from_semantic_index()` only returns `path` and `section` in `meta`.

The next best version is not more tools first. It is better contracts and better internals behind the four tools.

---

## 2. Boundary: What Belongs in NOVA

### Belongs

- Resolving compact task context from durable knowledge.
- Searching Markdown knowledge with ranked, cited results.
- Persisting durable insights append-first or as explicit patch proposals.
- Maintaining indexes and validating memory-engine health.
- Rebuildable metadata, full-text, vector, and later graph indexes.
- Provenance: path, section, line range, observed time, confidence, source.
- Memory lifecycle metadata: active, candidate, stale, superseded, archived.
- Scope metadata: global, user, project, repo, task, session, agent/operator.

### Does not belong

- Chat/session runtime.
- Telegram/Discord/message gateway logic.
- Cron/scheduling.
- LLM provider abstraction.
- Agent personas.
- Autonomous planning/execution.
- Code execution.
- Project creation or project management workflow beyond memory primitives.
- Process restart/lifecycle management except reporting health.

Rule of thumb: if it acts in the world, it belongs to Hermes/operator. If it remembers, retrieves, validates, or writes knowledge, it may belong to NOVA.

---

## 3. Tool-by-Tool Evaluation

## 3.1 `nova_context_resolve`

### Current version

**Purpose:** Returns selected context for a query using semantic search, optional scope filtering, project hint boosting, optional inventory, and a structured `context_pack`.

**Current inputs:**

- `query` required
- `project_hint` optional
- `token_budget` optional
- `scope` optional
- `include_inventory` optional

**Current strengths:**

- Correctly sits at the top of the memory stack: it packages context, not just raw search.
- Has `context_pack` shape with decisions, constraints, questions, tasks, facts, and source files.
- Deduplicates by path.
- Supports a session-init-style core directive payload.
- Simple enough to understand.

**Current weaknesses:**

- Deduplication by path is too aggressive: one file can contain multiple highly relevant sections, but only one survives.
- `token_budget` only controls top-k roughly; it does not actually budget returned text.
- `project_hint` is just score boosting after retrieval; it should also influence candidate selection/filtering.
- `scope` is substring matching, not a structured scope model.
- `context_pack.summary` is just the top snippet, not a synthesized or extractive summary.
- Retrieval is vector-only today; exact terms, file names, tags, and recency are not first-class signals.
- Citations currently lose `line_start`, `line_end`, and `memory_type` when read through JSON semantic index search.
- Confidence is average similarity score, not calibrated confidence.

### Best possible version

`nova_context_resolve` should become NOVA's main high-level retrieval primitive: a deterministic, cited, token-budgeted context pack builder.

Target behavior:

- Uses hybrid retrieval:
  - metadata filters
  - path/project filters
  - exact/BM25 search
  - vector similarity
  - recency boost
  - optional graph expansion later
- Preserves section-level citations:
  - path
  - section
  - line_start
  - line_end
  - memory_type
  - chunk_id
- Deduplicates by semantic unit, not only by file path.
- Groups context into typed blocks:
  - decisions
  - constraints
  - facts
  - procedures
  - open questions
  - recent activity/episodes
  - sources/reference docs
- Enforces actual budget:
  - max chars/tokens per item
  - max items per type
  - total response budget
- Returns transparent ranking:
  - final_score
  - vector_score
  - text_score
  - metadata_boosts
  - why_selected
- Provides explicit gaps:
  - `missing_context`
  - `low_confidence_reasons`
  - `recommended_queries`
- Does not perform actions, create tasks, schedule work, or decide execution.

### What belongs here

- Context packaging.
- Context inventory.
- Session-init memory boundary reminders.
- Ranking explanations.
- Cited snippets.

### What does not belong here

- Writing memory.
- Planning autonomous task execution.
- Triggering maintenance/index rebuild automatically unless explicitly requested elsewhere.
- Summarizing with an LLM inside NOVA. If summarization is needed, return extractive summaries or let the operator synthesize.

### Priority improvements

1. Preserve full metadata from semantic index search.
2. Replace path-level dedupe with `(path, section, chunk_index)` dedupe and only collapse later in presentation.
3. Add actual budget trimming.
4. Add structured filters: `project`, `memory_type`, `path_prefix`, `status`.
5. Add hybrid retrieval backend after SQLite FTS exists.

---

## 3.2 `nova_knowledge_query`

### Current version

**Purpose:** Semantic search over the knowledge base returning ranked matches.

**Current inputs:**

- `query` required
- `project` optional path substring
- `topic` optional path substring
- `limit` optional

**Current strengths:**

- Minimal and useful.
- Explicit empty result behavior.
- Basic path filtering.
- Returns snippets, scores, and relevance reason.

**Current weaknesses:**

- Vector-only search misses exact identifiers, ticket IDs, paths, names, tags, and commands.
- `project` and `topic` are substring filters, not metadata-aware filters.
- Deduplicates by path, hiding multiple section hits.
- `why_relevant` is always `semantic_similarity`, which is true but not informative.
- No line ranges/sections in output even though the index has them.
- No query modes: exact, semantic, hybrid, recent, path.
- No result facets/grouping.
- No stale-index warning.

### Best possible version

`nova_knowledge_query` should be the low-level, transparent search API. It should not package context like `context_resolve`; it should expose ranked evidence.

Target behavior:

- Input:
  - `query`
  - `limit`
  - `mode`: `hybrid | semantic | full_text | path | metadata`
  - `project`
  - `topic`
  - `memory_type`
  - `path_prefix`
  - `modified_after` / `observed_after` later
  - `include_text`: false by default, optional full chunk
- Output:
  - matches with `id`, `path`, `section`, `line_start`, `line_end`, `memory_type`, `snippet`
  - `scores`: vector/text/recency/final
  - `why_relevant`: exact matched terms, semantic match, path match, type match
  - `facets`: counts by memory_type/path prefix/project
  - `index_status`: model, updated_at, stale flag

### What belongs here

- Raw search and evidence discovery.
- Debuggable scoring.
- Filters and facets.
- Exact recall and semantic recall.

### What does not belong here

- Context-pack synthesis.
- Writes or patches.
- Execution recommendations beyond maybe `related_queries`.

### Priority improvements

1. Return full chunk metadata.
2. Add query mode parameter, even if only `semantic` and `path` work at first.
3. Stop path-level dedupe by default; add `dedupe='none|path|section'`.
4. Add SQLite FTS/BM25 and hybrid score fusion.
5. Add index freshness info to every response.

---

## 3.3 `nova_knowledge_update`

### Current version

**Purpose:** Append-first persistence of durable insights.

**Current inputs:**

- `content` required
- `source` required
- `project` optional
- `topic` optional
- `title` optional
- `confidence` optional
- `next_action` optional

**Current strengths:**

- Correctly append-first.
- Requires source.
- Adds confidence and next action.
- Creates Markdown humans can read.
- Avoids silent overwrite.

**Current weaknesses:**

- Target path selection is fuzzy and can write to surprising places.
- No dry-run/proposal mode.
- No duplicate detection before writing.
- No contradiction/staleness handling.
- No stable memory id in frontmatter/block metadata.
- No structured frontmatter per entry.
- No write classification: fact vs decision vs preference vs episode etc.
- No validation of source format.
- No automatic index update or clear `index_stale=true` output after writing.
- Confidence invalid values are silently converted to `None` rather than returning validation warning.

### Best possible version

`nova_knowledge_update` should become a safe memory write API with two modes: append now for low-risk captures, propose patch for curated changes.

Target behavior:

- Input:
  - `content`
  - `source`
  - `memory_type`
  - `scope`
  - `project`
  - `topic`
  - `title`
  - `confidence`
  - `next_action`
  - `mode`: `append | propose_patch | dry_run`
  - `target_path` optional but validated inside knowledge root
  - `supersedes` optional
- Output:
  - `status`
  - `entry_id`
  - `written_paths` or `proposed_patch_path`
  - `target_reason`
  - `duplicate_candidates`
  - `index_stale`
  - `validation_warnings`
- Entry format:
  - stable id
  - observed_at
  - source
  - project/topic/scope
  - memory_type
  - confidence
  - lifecycle state
  - supersedes/superseded_by fields when applicable

### What belongs here

- Append-first writes.
- Patch proposals.
- Duplicate detection.
- Write validation.
- Staleness/lifecycle metadata.

### What does not belong here

- Direct destructive edits without explicit patch approval.
- Project scaffolding or folder creation beyond the target note path needed for a memory write.
- Scheduling follow-up actions.

### Priority improvements

1. Add `memory_type`, `scope`, `mode`, and optional `target_path`.
2. Add dry-run/propose output before direct writes become the default for ambiguous targets.
3. Add stable entry IDs and block/frontmatter metadata.
4. Add duplicate candidate search before write.
5. Mark or report index stale after a successful write.

---

## 3.4 `nova_memory_maintain`

### Current version

**Purpose:** Health, validation, and index rebuild.

**Current inputs:**

- `operation`: `health | index | validate`
- `force` optional for indexing

**Current strengths:**

- Clear maintenance boundary.
- No restart/process lifecycle behavior, correctly.
- Rebuilds semantic index from Markdown.
- Incremental rebuild uses file hashes.
- Health reports vault/index/search/boundary.

**Current weaknesses:**

- `validate` is too shallow: only checks root existence and root separation.
- Index uses MD5; fine for change detection but should be named non-security hash or changed to SHA-256 for audit clarity.
- Index stores absolute paths when knowledge root is outside workspace; this reduces portability and leaks local structure into index.
- Chunking only splits H1/H2 and truncates each section to 2000 chars; nested sections and long runbooks lose detail.
- Metadata classification is keyword-based and misses preferences, episodes, summaries, entities, relationships.
- No index schema validation.
- No stale index detection against file hashes except during rebuild.
- No FTS/metadata index.
- Embedding model config is read, but `search_shared.get_model()` ignores configured model and always defaults unless explicitly passed.
- No backup/atomic write strategy for index files.

### Best possible version

`nova_memory_maintain` should be a safe, auditable maintenance API for generated memory artifacts.

Target behavior:

- Operations:
  - `health`
  - `index`
  - `validate`
  - possibly `stats` later, or include stats in health
- Health should report:
  - vault existence/file count
  - index existence/freshness/schema/model/dimensions
  - dependency readiness
  - stale files count
  - write permissions
  - generated artifacts ignored by git
- Validate should check:
  - no private vault inside core repo unless explicitly configured
  - no generated indexes tracked in git
  - index schema valid
  - paths canonical and portable
  - duplicate IDs
  - missing citations/line ranges
  - invalid memory types/scopes
  - broken internal wiki links optionally
- Index should:
  - build metadata index and FTS index in SQLite
  - keep semantic embeddings as one signal
  - write atomically
  - support incremental updates robustly
  - preserve relative paths against knowledge root
  - include schema version and migration strategy

### What belongs here

- Health and validation.
- Index creation and repair.
- Stats and diagnostics.
- Schema migration for generated artifacts.

### What does not belong here

- Restarting the MCP server.
- Managing Hermes config.
- Git pushing/pulling the vault.
- Running project workflows.

### Priority improvements

1. Fix configured embedding model usage.
2. Preserve relative paths and full metadata in index/search results.
3. Add atomic writes for `semantic_index.json` and `file_hashes.json`.
4. Expand `validate` into real schema/freshness checks.
5. Add SQLite metadata + FTS index.

---

## 4. Cross-Cutting Gaps

### 4.1 Retrieval backend

Current retrieval is semantic-vector-first. This is fine for concepts, weak for exact recall. Best version uses hybrid retrieval:

```text
candidate generation = path filters + metadata filters + FTS/BM25 + vector
ranking = weighted score fusion + recency + project/type boosts
response = cited chunks with transparent score components
```

### 4.2 Metadata model

Current metadata is enough for proof of concept but not enough for long-term memory hygiene.

Target minimal metadata:

```yaml
id: mem_or_chunk_stable_id
type: fact|preference|decision|task|procedure|episode|source|summary|question|constraint|entity|relationship
scope: global|user|project|repo|task|session|agent
project: optional
repo: optional
topic: optional
status: active|candidate|superseded|stale|archived|rejected
source: required for writes
observed_at: datetime
valid_from: optional datetime
valid_to: optional datetime
confidence: 0.0-1.0
path: source markdown path
section: heading
line_start: int
line_end: int
supersedes: optional list
```

### 4.3 Index portability

Current index uses absolute paths because the knowledge root is outside `/path/to/nova`. Better: store paths relative to `knowledge_root` plus explicit `knowledge_root_id` or configured root. Return absolute paths only when needed at runtime.

### 4.4 Tests

Current quality gate fails:

```text
python -m unittest discover -s tests -v
```

Failure cause: `tests/test_context_packs.py` stubs only `mcp.types`, then imports `from mcp.tools...`; Python resolves installed `mcp` package first and fails because the stubbed `mcp.types` lacks symbols expected by the installed package.

Fix: import NOVA modules via a stable local package/path, or rename local `mcp` package to avoid conflict with the installed MCP SDK. Short-term test fix: put repo root ahead of site-packages and stub full `mcp` package namespace before importing local modules. Better structural fix: rename local module package to `nova_mcp` or `nova_tools` and keep only server integration importing SDK `mcp`.

---

## 5. Recommended Public Tool Surface

Keep exactly four public tools for now:

1. `nova_context_resolve`
2. `nova_knowledge_query`
3. `nova_knowledge_update`
4. `nova_memory_maintain`

Do not add these yet:

- `project_create`
- `project_continue`
- `system_maintain`
- `chat_*`
- `schedule_*`
- `agent_*`
- `execute_*`

Possible later additions only after the four are mature:

- `nova_memory_get`: fetch exact memory/doc/chunk by id/path.
- `nova_memory_propose_patch`: explicit patch workflow for curated edits.
- `nova_episode_record`: low-friction event capture separate from durable facts.

Even those should be challenged hard before adding. Small interface, sharp axe.

---

## 6. Implementation Roadmap

## Phase 0: Fix the quality gate

### Task 0.1: Fix test import collision

**Objective:** Make `python -m unittest discover -s tests -v` pass reliably.

**Files:**

- Modify: `tests/test_context_packs.py`
- Possibly modify: local package layout in later phase

**Steps:**

1. Update the test to import local NOVA modules without triggering installed `mcp` package imports.
2. Ensure `mcp.types` stub is available for local modules.
3. Run:

```bash
python -m unittest discover -s tests -v
```

Expected: all tests pass.

### Task 0.2: Add regression test for semantic index metadata preservation

**Objective:** Ensure line ranges and memory types survive search.

**Files:**

- Modify/Create: `tests/test_search_shared.py`

**Expected assertion:** `_search_from_semantic_index()` returns metadata containing `section`, `line_start`, `line_end`, `memory_type`, `chunk_index`, and `id`.

---

## Phase 1: Make current tools trustworthy

### Task 1.1: Preserve full metadata in `search_shared`

**Objective:** Fix current citation loss.

**Files:**

- Modify: `mcp/tools/search_shared.py`

**Change:** In `_search_from_semantic_index()`, include full metadata:

```python
"meta": {
    "id": item.get("id", ""),
    "path": item.get("path", ""),
    "section": item.get("section", ""),
    "line_start": item.get("line_start"),
    "line_end": item.get("line_end"),
    "memory_type": item.get("memory_type", "fact"),
    "chunk_index": item.get("chunk_index"),
}
```

**Verify:** Existing context pack test should assert line ranges from JSON-index path.

### Task 1.2: Add metadata to `nova_knowledge_query` output

**Objective:** Make query results fully cited.

**Files:**

- Modify: `mcp/tools/knowledge_query.py`
- Test: `tests/test_knowledge_query.py`

**Output fields to add:**

- `id`
- `section`
- `line_start`
- `line_end`
- `memory_type`
- `chunk_index`

### Task 1.3: Make dedupe configurable

**Objective:** Avoid hiding multiple relevant sections.

**Files:**

- Modify: `mcp/tools/knowledge_query.py`
- Modify: `mcp/tools/context_resolve.py`

**Add input:**

```json
"dedupe": {"type": "string", "enum": ["none", "path", "section"], "default": "section"}
```

For `context_resolve`, default should probably be `section`; for raw query, default should be `none` or `section`.

### Task 1.4: Add actual budget enforcement to context resolve

**Objective:** Ensure `token_budget` controls response size.

**Files:**

- Modify: `mcp/tools/context_resolve.py`

**Approach:** Use character approximation initially: `budget_chars = token_budget * 4`. Trim snippets and max item count by type until under budget.

---

## Phase 2: Strengthen writes

### Task 2.1: Add write mode

**Objective:** Support safe write previews.

**Files:**

- Modify: `mcp/tools/knowledge_update.py`
- Test: `tests/test_knowledge_update.py`

**Add input:**

```json
"mode": {"type": "string", "enum": ["append", "dry_run", "propose_patch"], "default": "append"}
```

### Task 2.2: Add memory metadata fields

**Objective:** Make writes indexable and auditable.

**Files:**

- Modify: `mcp/tools/knowledge_update.py`

**Add inputs:**

- `memory_type`
- `scope`
- `target_path`
- `supersedes`

**Validation:** reject invalid memory types/scopes with structured error.

### Task 2.3: Add duplicate candidate detection

**Objective:** Reduce memory pollution.

**Files:**

- Modify: `mcp/tools/knowledge_update.py`

**Approach:** Before write, run `semantic_search(content, top_k=5)` and return candidates above threshold. In `append` mode, still write but warn; in `dry_run`/`propose_patch`, surface candidates prominently.

### Task 2.4: Report index staleness after write

**Objective:** Operator knows whether rebuild is needed.

**Files:**

- Modify: `mcp/tools/knowledge_update.py`

**Output:**

```json
"index_stale": true,
"recommended_maintenance": {"operation": "index", "force": false}
```

---

## Phase 3: Better maintenance and validation

### Task 3.1: Use configured embedding model

**Objective:** Respect `NOVA_EMBEDDING_MODEL` consistently.

**Files:**

- Modify: `mcp/tools/search_shared.py`
- Modify: `mcp/tools/memory_maintain.py`

**Change:** Pass `cfg.embedding_model` into `batch_encode_texts()` and `encode_text()` or store model cache by model name.

### Task 3.2: Make index writes atomic

**Objective:** Avoid corrupted index files on interruption.

**Files:**

- Modify: `mcp/tools/memory_maintain.py`
- Possibly add helper: `mcp/tools/common.py`

**Approach:** write to `.tmp`, then `Path.replace()`.

### Task 3.3: Store relative paths against knowledge root

**Objective:** Make index portable and cleaner.

**Files:**

- Modify: `mcp/tools/memory_maintain.py`
- Modify: `mcp/tools/search_shared.py`

**Index field policy:**

- `path`: relative to knowledge root
- optional `absolute_path` should not be stored; compute only at runtime if required

### Task 3.4: Expand validate

**Objective:** Make `validate` a real trust check.

**Files:**

- Modify: `mcp/tools/memory_maintain.py`
- Modify: `mcp/tools/health_checks.py`

**Checks:**

- knowledge root exists and is not core root
- index files exist and parse
- index schema version supported
- duplicate IDs absent
- all chunks have path/text/embedding/metadata
- file hashes align with current vault
- generated artifacts not tracked by git
- memory types in controlled vocabulary

---

## Phase 4: Hybrid retrieval

### Task 4.1: Add SQLite metadata store

**Objective:** Stop loading 30MB JSON for every search and enable structured filters.

**Files:**

- Create: `mcp/tools/index_store.py`
- Modify: `mcp/tools/memory_maintain.py`
- Modify: `mcp/tools/search_shared.py`

**Tables:**

- `chunks`
- `files`
- `embeddings` or external vector blob mapping
- FTS virtual table for chunk text

### Task 4.2: Add FTS/BM25

**Objective:** Exact recall for identifiers, commands, tickets, paths.

**Files:**

- Modify/Create: `mcp/tools/index_store.py`
- Modify: `mcp/tools/search_shared.py`

### Task 4.3: Add score fusion

**Objective:** Make retrieval explainable and robust.

**Output scores:**

```json
"scores": {
  "vector": 0.71,
  "text": 0.83,
  "recency": 0.12,
  "metadata": 0.20,
  "final": 0.76
}
```

---

## 7. Acceptance Criteria

The improvement pass is successful when:

- `python -m compileall -q .` passes.
- `python -m unittest discover -s tests -v` passes.
- `nova_memory_maintain health` reports OK for vault/index/search/boundary.
- `nova_knowledge_query` returns line-level citations from the rebuilt JSON index.
- `nova_context_resolve` returns cited, budget-aware context packs without losing multiple sections from one file.
- `nova_knowledge_update` can dry-run and append with stable metadata.
- `nova_memory_maintain validate` catches schema/freshness/path problems.
- No new operator-runtime tools are added.

---

## 8. Recommended Next Action

Start with Phase 0 and Phase 1. They are small, high-value, and fix immediate trust issues:

1. Fix the test import collision.
2. Preserve index metadata through search.
3. Add full citations to `knowledge_query`.
4. Make dedupe configurable.
5. Add real budget enforcement.

Only after that should NOVA move to write safety and SQLite/FTS. The revolution must first pass unit tests, comrade.
