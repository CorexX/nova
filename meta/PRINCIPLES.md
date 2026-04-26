# NOVA 2.0 Principles

## Core Principle

NOVA remembers. Operators act.

## Non-Negotiables

1. **Memory / context only** — NOVA does not become an operator runtime.
2. **Markdown is source of truth** — human-readable knowledge wins over generated indexes.
3. **Indexes are disposable** — all generated search state must be rebuildable.
4. **Private knowledge stays out of core** — `nova-knowledge` is separate from this repo.
5. **Append-first writes** — preserve history unless an explicit patch says otherwise.
6. **Provenance matters** — durable memory needs source, scope, confidence, and time where possible.
7. **Small tool surface** — every MCP tool must pay rent.
8. **Context economy** — return relevant context, not maximal context.

## Memory Classes

NOVA should support these concepts without overbuilding the ontology:

- fact
- preference
- decision
- task
- procedure
- episode
- source
- summary
- question
- constraint
- entity
- relationship

## Scope Model

Useful memory is scoped:

- global
- user
- project
- repo
- task
- session
- agent/operator

## Write Policy

NOVA may create or append knowledge files. It should not silently rewrite existing durable knowledge.

Preferred write behavior:

1. record source
2. include project/topic
3. include confidence if known
4. include next action if useful
5. append rather than replace

## Retrieval Policy

Retrieval should be:

- source-attributed
- deduplicated
- filtered by scope where possible
- ranked transparently
- compact enough to be useful

## Anti-Patterns

| Avoid | Why |
|---|---|
| Agent personas in NOVA | operator concern |
| Cron jobs in NOVA | operator/runtime concern |
| Chat session ownership | operator concern |
| Generated DBs in git | not source truth |
| Vector-only memory | weak exact recall and provenance |
| Silent overwrites | destroys history |
| Tool sprawl | makes the boundary blurry |

## Commit Style

Use boring commits:

```text
feat: add memory context behavior
fix: correct index validation
docs: update architecture
refactor: simplify path config
test: add memory contract tests
```
