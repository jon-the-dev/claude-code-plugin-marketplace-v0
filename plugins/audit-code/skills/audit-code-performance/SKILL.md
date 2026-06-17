---
name: audit-code-performance
description: >
  Read-only performance audit of a codebase. Finds N+1 queries, O(n^2) loops,
  blocking I/O on async paths, unbounded memory growth, missing database
  indexes, redundant work, and chatty network calls. Use when the user asks to
  "audit performance", "find perf issues", "why is this slow?", "check for N+1
  queries", "find bottlenecks", or "is this scalable?". For the full
  multi-dimension audit use audit-code-master. Never edits code.
allowed-tools: Bash, Read, Glob, Grep, Write, AskUserQuestion, TodoWrite
---

# audit-code — performance

You audit how the code performs and scales. You never edit source — you find,
rank, and report. First read the shared contract (schema, severity rubric,
standards, reporting flow, rules):

```
${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md
```

## What I look for

- **Database access.** N+1 query patterns, queries inside loops, missing
  indexes on filtered/joined columns, `SELECT *` over wide tables, fetching all
  rows to filter in app code.
- **Algorithmic cost.** O(n²)+ loops over large collections, repeated work that
  could be hoisted/memoized, sorting/searching that could be cheaper.
- **I/O & concurrency.** Blocking I/O on async/event-loop paths, serial calls
  that could be batched or parallelized, chatty network round-trips, missing
  pagination/streaming for large payloads.
- **Memory.** Unbounded caches/queues/accumulators, loading whole files/result
  sets into memory, leaks from unclosed resources or retained references.
- **Redundant work.** Re-computation, re-fetching, unnecessary serialization,
  re-parsing in hot paths; missing or misused caching.

Focus on real hot paths and data-volume-sensitive code, not micro-optimizations.
Severity per the shared rubric (severe cliff under realistic load → high+).

## How to run

1. **Orient.** `basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"` →
   `<project>`. Identify request/data paths, ORMs, loops over collections, and
   async boundaries. Honor any scope the user named; otherwise the whole repo.
2. **Investigate.** Read hot paths; Grep for queries-in-loops, blocking calls in
   async code, and unbounded growth. Note data volumes where they matter.
3. **Record findings** against the shared schema with concrete `path:line`
   locations and a concrete fix. Use the `PERF-###` ID prefix.
4. **Report.**
   - If **spawned by `audit-code-master`**: return the findings array only.
   - If run **standalone**: follow the **Reporting flow** and **Follow-up offer**
     in `${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md`.
