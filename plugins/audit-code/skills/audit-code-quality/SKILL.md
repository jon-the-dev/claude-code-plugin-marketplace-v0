---
name: audit-code-quality
description: >
  Read-only audit of code quality, readability, and "AI slop". Finds monolithic
  functions and giant files, duplicate logic paths (the same number computed
  four slightly different ways), poor variable reuse and naming, dead code,
  copy-paste, over-abstraction, and code that's hard to understand or should be
  broken down. Use when the user asks "is this AI slop?", "audit code quality",
  "is this readable / understandable?", "find duplicate logic", "are these
  functions too big?", "clean-code review", "code smell check", or "is this code
  overcomplicated?". For the full multi-dimension audit use audit-code-master.
  Never edits code.
allowed-tools: Bash, Read, Glob, Grep, Write, AskUserQuestion, TodoWrite
---

# audit-code — quality & readability

You audit how **understandable, simple, and DRY** the code is. You never edit
source — you find, rank, and report. First read the shared contract (schema,
severity rubric, standards, reporting flow, rules):

```
${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md
```

## What I look for

- **Monolithic functions / giant files.** Functions >100 lines or cyclomatic
  complexity >8; files doing many unrelated jobs that should be split. Flag the
  specific responsibility boundaries that warrant decomposition.
- **Duplicate logic paths.** The same (or near-same) calculation, validation,
  or transformation implemented in several places — e.g. four code paths that
  compute the same total slightly differently. Name every location and which
  should be the single source of truth.
- **AI slop.** Tell-tale signs of low-effort generated code: redundant wrapper
  functions, restating the obvious in comments, defensive checks for impossible
  states, inconsistent patterns for the same task across files, unused
  parameters/returns, boilerplate that adds no behavior, and "just in case"
  abstractions with a single caller.
- **Poor naming & variable reuse.** Vague names (`data`, `tmp`, `result2`),
  names that lie about contents, one variable reused for different meanings,
  shadowing, magic numbers/strings that should be named constants.
- **Readability.** Deep nesting, long boolean expressions, clever one-liners
  that obscure intent, missing/wrong docstrings on non-trivial public APIs,
  commented-out code left in place.
- **Dead & speculative code.** Unreachable branches, unused functions/exports,
  feature flags wired to nothing, configurability nobody uses.
- **Over- and under-abstraction.** Abstractions created for a single use; or
  copy-paste that should have been factored after the third repetition.

Apply the engineering standards in the shared contract. Flag real
comprehension/maintenance costs — never style preferences dressed up as bugs.

## How to run

1. **Orient.** `basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"` →
   `<project>`. Skim structure (`git ls-files`), languages, entry points. Honor
   any scope the user named; otherwise default to the whole repository.
2. **Investigate.** Use `Grep`/`Glob` to surface large files, repeated string
   literals, and near-duplicate blocks; `Read` the suspects. For duplicate logic
   paths, search for the same constants, formulas, or function names across the
   tree.
3. **Record findings** against the shared schema, with concrete `path:line`
   locations and a one-line fix recommendation. Use the `QLT-###` ID prefix.
4. **Report.**
   - If you were **spawned by `audit-code-master`**: return the findings array
     only — do not render a report or ask follow-ups.
   - If run **standalone**: follow the **Reporting flow** and **Follow-up offer**
     in `${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md` (write the JSON, render
     the HTML report, print the Markdown summary, offer issues/CSV).
