---
name: audit-code-testing
description: >
  Read-only audit of a codebase's tests. Finds coverage gaps, untested error and
  edge paths, tests that assert implementation instead of behavior, flaky
  patterns, over-mocking, and missing regression tests. Use when the user asks to
  "audit the tests", "review test coverage", "are the tests any good?", "what's
  untested?", "do the tests check behavior or implementation?", or "find flaky
  tests". For the full multi-dimension audit use audit-code-master. Never edits
  code.
allowed-tools: Bash, Read, Glob, Grep, Write, AskUserQuestion, TodoWrite
---

# audit-code — testing

You audit the quality and coverage of the test suite. You never edit source or
tests — you find, rank, and report. First read the shared contract (schema,
severity rubric, standards, reporting flow, rules):

```
${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md
```

## What I look for

- **Coverage gaps.** Core logic, service layers, and error paths with no tests;
  modules with zero coverage; critical flows lacking integration/E2E coverage.
- **Edge & error paths.** Tests only exercise the happy path; empty inputs,
  boundaries, malformed data, and failure modes the code handles go untested.
- **Behavior vs implementation.** Tests asserting internal calls, private state,
  or exact log strings — brittle to refactors that don't change behavior.
- **Mocking.** Mocking logic the test should exercise (vs only mocking slow /
  non-deterministic / external boundaries); mocks that let real bugs through.
- **Flakiness.** Time/sleep-based waits, ordering/network dependence, shared
  mutable state between tests, reliance on real external services.
- **Regression safety.** Past bug fixes with no test pinning them; assertions so
  loose they can't fail.

Judge against the project's stated testing standards when present. Severity per
the shared rubric (untested critical path / error handling → high+).

## How to run

1. **Orient.** `basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"` →
   `<project>`. Locate the test suites, framework, and any coverage config.
   Honor any scope the user named; otherwise the whole repository.
2. **Investigate.** Map tests to the modules they cover; read tests for the
   most critical/most complex code; check error-path and edge coverage. Use
   coverage output if readily available — don't fabricate percentages.
3. **Record findings** against the shared schema with concrete `path:line`
   locations and a concrete fix. Use the `TST-###` ID prefix.
4. **Report.**
   - If **spawned by `audit-code-master`**: return the findings array only.
   - If run **standalone**: follow the **Reporting flow** and **Follow-up offer**
     in `${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md`.
