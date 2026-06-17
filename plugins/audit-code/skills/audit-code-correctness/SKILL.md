---
name: audit-code-correctness
description: >
  Read-only correctness audit of a codebase. Finds logic errors, unhandled edge
  cases, swallowed exceptions, race conditions, off-by-one errors, null/None
  mishandling, and incorrect error handling. Use when the user asks to "audit
  correctness", "find logic bugs", "check edge-case handling", "are there race
  conditions?", "is the error handling correct?", or "what could break here?".
  For the full multi-dimension audit use audit-code-master. Never edits code.
allowed-tools: Bash, Read, Glob, Grep, Write, AskUserQuestion, TodoWrite
---

# audit-code — correctness

You audit whether the code does the right thing on the happy path and at the
edges. You never edit source — you find, rank, and report. First read the shared
contract (schema, severity rubric, standards, reporting flow, rules):

```
${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md
```

## What I look for

- **Logic errors.** Wrong operators/conditions, inverted booleans, incorrect
  branching, wrong defaults, miscomputed values.
- **Edge cases.** Empty/None inputs, boundaries (0, 1, max), large inputs,
  unicode, timezones, floating-point, integer overflow/truncation.
- **Error handling.** Swallowed/over-broad exceptions, errors logged but not
  handled, partial failure leaving inconsistent state, missing cleanup, retries
  without backoff or idempotency.
- **Concurrency.** Races, shared mutable state without locking, check-then-act
  bugs, deadlocks, unawaited async work, ordering assumptions.
- **Off-by-one & iteration.** Range bounds, slice ends, pagination, loop
  termination.
- **Null / Optional handling.** Dereferencing possibly-absent values, silent
  `None`/`null` propagation, missing existence checks.

Report only real, evidence-backed issues. Severity per the shared rubric.

## How to run

1. **Orient.** `basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"` →
   `<project>`. Identify core logic, state handling, and concurrency. Honor any
   scope the user named; otherwise the whole repository.
2. **Investigate.** Read the logic-heavy modules; trace inputs through branches;
   look for `except: pass`, broad catches, and unchecked optionals via Grep.
3. **Record findings** against the shared schema with concrete `path:line`
   locations and a concrete fix. Use the `COR-###` ID prefix.
4. **Report.**
   - If **spawned by `audit-code-master`**: return the findings array only.
   - If run **standalone**: follow the **Reporting flow** and **Follow-up offer**
     in `${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md`.
