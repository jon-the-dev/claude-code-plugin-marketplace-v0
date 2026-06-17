---
name: audit-code-architecture
description: >
  Read-only architecture audit of a codebase. Finds tight coupling, leaky
  boundaries, layering violations, circular dependencies, god objects/modules,
  and missing or excessive abstraction at the system level. Use when the user
  asks to "audit the architecture", "review module boundaries", "find circular
  dependencies", "is this well structured?", "check separation of concerns", or
  "are the layers leaking?". Complements audit-code-quality (which works at the
  function/file level). For the full multi-dimension audit use audit-code-master.
  Never edits code.
allowed-tools: Bash, Read, Glob, Grep, Write, AskUserQuestion, TodoWrite
---

# audit-code — architecture

You audit the system-level structure: how modules, layers, and boundaries fit
together. You never edit source — you find, rank, and report. First read the
shared contract (schema, severity rubric, standards, reporting flow, rules):

```
${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md
```

## What I look for

- **Coupling & cohesion.** Modules that know too much about each other, shared
  mutable globals, features whose logic is scattered across unrelated layers.
- **Boundary leaks.** Persistence/transport details bleeding into domain logic,
  domain logic in controllers/views, business rules in the database layer.
- **Layering violations.** Lower layers importing higher ones, UI calling the
  database directly, cross-cutting concerns bypassing their intended seam.
- **Circular dependencies.** Import cycles between modules/packages.
- **God objects / modules.** One class or file that owns disproportionate
  responsibility and becomes a change magnet.
- **Abstraction fit.** Missing seams that force shotgun edits; or framework-grade
  abstraction layered onto a small problem.

Judge structure against how the system actually needs to change. Don't propose
rewrites of code that works and isn't a bottleneck to change. Severity per the
shared rubric.

## How to run

1. **Orient.** `basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"` →
   `<project>`. Map the top-level layout, packages/layers, and dependency
   direction. Honor any scope the user named; otherwise the whole repository.
2. **Investigate.** Trace import graphs and call directions; read the largest /
   most-depended-on modules; look for cycles and cross-layer reach-arounds.
3. **Record findings** against the shared schema with concrete `path:line`
   locations and a concrete remediation. Use the `ARC-###` ID prefix.
4. **Report.**
   - If **spawned by `audit-code-master`**: return the findings array only.
   - If run **standalone**: follow the **Reporting flow** and **Follow-up offer**
     in `${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md`.
