---
name: audit-code-dependencies
description: >
  Read-only dependency audit of a codebase. Finds outdated or known-vulnerable
  packages, unused dependencies, unpinned/floating versions, license risk, and
  unjustified new dependencies. Use when the user asks to "audit dependencies",
  "check for vulnerable packages", "find unused dependencies", "are versions
  pinned?", "review the dependency tree", or "any license risks?". For the full
  multi-dimension audit use audit-code-master. Never edits code.
allowed-tools: Bash, Read, Glob, Grep, Write, AskUserQuestion, TodoWrite
---

# audit-code — dependencies

You audit the third-party dependency surface. You never edit source or run
package upgrades — you find, rank, and report. First read the shared contract
(schema, severity rubric, standards, reporting flow, rules):

```
${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md
```

## What I look for

- **Vulnerable packages.** Dependencies with known CVEs or advisories; prefer
  the project's own audit tooling when present (`pip-audit`, `npm audit`,
  `pnpm audit`, `cargo audit`, `osv-scanner`) and read lockfiles.
- **Outdated versions.** Significantly stale majors, or pinned-to-broken.
- **Unpinned / floating versions.** Ranges or `latest` that make builds
  non-reproducible; lockfile missing or out of sync with manifests.
- **Unused & duplicate deps.** Declared-but-never-imported packages; multiple
  packages doing the same job; heavy deps used for one trivial helper.
- **License risk.** Copyleft/incompatible licenses for the project's intended
  distribution; missing license metadata.
- **Supply-chain hygiene.** Unjustified new dependencies (each is attack surface
  and maintenance burden), abandoned/unmaintained packages.

Run read-only audit commands only; never modify manifests or lockfiles. Map
advisory severity to the shared rubric.

## How to run

1. **Orient.** `basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"` →
   `<project>`. Locate manifests/lockfiles (`package.json`, `pnpm-lock.yaml`,
   `requirements*.txt`, `Pipfile.lock`, `pyproject.toml`, `Cargo.lock`, `go.mod`).
2. **Investigate.** Run the appropriate read-only audit tool if available; diff
   declared vs imported packages to find unused ones; check pinning and
   licenses. If a tool isn't installed, say so rather than guessing CVEs.
3. **Record findings** against the shared schema with concrete locations
   (`manifest:line` or `package@version`) and a concrete fix. Use the `DEP-###`
   ID prefix.
4. **Report.**
   - If **spawned by `audit-code-master`**: return the findings array only.
   - If run **standalone**: follow the **Reporting flow** and **Follow-up offer**
     in `${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md`.
