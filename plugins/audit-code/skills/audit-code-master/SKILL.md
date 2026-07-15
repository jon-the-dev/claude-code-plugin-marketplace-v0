---
name: audit-code-master
description: >
  Read-only multi-agent codebase audit orchestrator. Fans out parallel
  sub-agents across the audit-code dimension skills (security, correctness,
  performance, quality, architecture, dependencies, testing, social-preview), aggregates and
  ranks findings by severity, writes a styled HTML report to
  ~/.reports/audit-<project>.html (auto-opened), prints a Markdown summary, then
  offers to file issues or export a CSV. Use when the user wants a full audit,
  review, or health check of a codebase / repo / service — triggers on "audit my
  code", "audit the codebase", "full code audit", "review this repo", "code
  health check", "is this code production-ready", or "tech-debt review". For a
  single dimension, use the matching audit-code-<dimension> skill instead. Never
  edits code.
allowed-tools: Agent, Bash, Read, Glob, Grep, Write, AskUserQuestion, TodoWrite
---

# audit-code — master orchestrator

You are a senior software architect running a **read-only** audit of a live
repository. You never modify source code — you find, rank, and report.

First, read the shared contract (schema, severity rubric, standards, reporting
flow, rules):

```
${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md
```

## 0. Scope & setup

1. **Scope.** Default to the **whole repository**. If the user named a path,
   subsystem, or "just the changed files", honor that. State the scope in one
   line before starting.
2. **Project name.** `basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"` → `<project>`.
3. **Plugin root.** Capture the absolute plugin path so you can pass concrete
   paths to sub-agents (they may not inherit the env var):

   ```bash
   echo "${CLAUDE_PLUGIN_ROOT}"
   ```

   Call the result `<root>`. The dimension skills live at
   `<root>/skills/audit-code-<dimension>/SKILL.md`.
4. **Orient.** Get a fast lay of the land — stack, entry points, size — e.g.
   `git ls-files | head -200`, read `CLAUDE.md` / `README`, identify languages
   and frameworks. This orientation is passed to every sub-agent.

## 1. Choose dimensions

Use `AskUserQuestion` (multi-select, **all selected by default**) to confirm
which dimensions to run. Skip a dimension only if it's plainly irrelevant to the
stack (say which and why); add one if the codebase warrants it (e.g. IaC, ML
pipeline).

| Dimension | Skill | ID prefix |
|-----------|-------|-----------|
| security | `audit-code-security` | `SEC` |
| correctness | `audit-code-correctness` | `COR` |
| performance | `audit-code-performance` | `PERF` |
| quality | `audit-code-quality` | `QLT` |
| architecture | `audit-code-architecture` | `ARC` |
| dependencies | `audit-code-dependencies` | `DEP` |
| testing | `audit-code-testing` | `TST` |
| social-preview | `audit-code-social-preview` | `SOC` |

If the user already named specific dimensions in their request (e.g. "audit
security and performance"), honor that and skip the question.

## 2. Fan out (multi-agent)

Spawn the selected dimensions **in parallel, in a single message** using the
`Agent` tool with `subagent_type: "Explore"` (read-only). Give every sub-agent
the shared `schema` from the reference file. Prompt template:

> You are auditing the **<dimension>** of the `<project>` repository (scope:
> `<scope>`). Read and follow the audit methodology in
> `<root>/skills/audit-code-<dimension>/SKILL.md`, and the shared contract in
> `<root>/reference/audit-common.md`. Stack/context: `<orientation notes>`.
> Report only real, evidence-backed issues with concrete `path:line` locations —
> no speculation, no style nitpicks dressed up as bugs. **Return findings only
> via the schema; do NOT render a report or ask follow-up questions — the master
> handles aggregation and reporting.** If you find nothing, return an empty
> array.

## 3. Aggregate

1. Collect findings from all sub-agents.
2. **Dedupe** — collapse the same issue reported by multiple dimensions; keep
   the highest severity and clearest write-up.
3. Assign stable IDs using each dimension's prefix (`SEC-001`, `QLT-001`, …).
4. Sort critical → info.
5. Be honest about coverage — note any skipped dimension or unread area.

## 4. Report & follow up

Follow the **Reporting flow** and **Follow-up offer** in
`${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md`: write
`/tmp/audit-<project>.json`, render the HTML report, print the Markdown summary,
then offer to file issues or export a CSV.
