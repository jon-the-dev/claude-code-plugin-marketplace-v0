# audit-code — shared reference

Every `audit-code-*` skill shares this contract: the same finding schema, the
same severity rubric, the same engineering standards, and the same reporting
flow. Read this file once per run, then apply it. Paths below use
`${CLAUDE_PLUGIN_ROOT}`, the absolute path to the installed `audit-code` plugin.

## Finding schema

Each sub-agent (and each standalone dimension skill) returns findings shaped
like this:

```json
{
  "type": "object",
  "properties": {
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "severity":       {"type": "string", "enum": ["critical","high","medium","low","info"]},
          "title":          {"type": "string"},
          "location":       {"type": "string", "description": "path:line"},
          "description":    {"type": "string"},
          "recommendation": {"type": "string"},
          "rationale":      {"type": "string"}
        },
        "required": ["severity","title","location","description","recommendation","rationale"]
      }
    }
  },
  "required": ["findings"]
}
```

If you find nothing, return an empty `findings` array. Do not invent findings to
look thorough.

## Severity rubric

Keep severities consistent across dimensions:

- **critical** — exploitable security hole, data loss, or production-down bug.
- **high** — broken functionality, real vulnerability with preconditions, severe
  perf cliff, or pervasive structural rot that blocks safe change.
- **medium** — impaired behavior with a workaround, meaningful tech debt.
- **low** — minor / cosmetic / edge-case.
- **info** — observation, no action required.

## Engineering standards

Hold the code to these limits when judging quality/maintainability findings:

- Functions ≤100 lines, cyclomatic complexity ≤8, ≤5 positional params.
- 100-char line length; absolute imports only (no `..` relative paths).
- Google-style docstrings on non-trivial public APIs.
- Self-documenting code; no commented-out code; fail-fast error handling with
  context. Never flag style preferences as bugs.

## Aggregated report JSON

The combined report written to `/tmp/audit-<project>.json` (and rendered to
HTML) uses this shape — note the extra `id` and `dimension` fields:

```json
{
  "project": "<project>",
  "scope": "<scope>",
  "generated": "<YYYY-MM-DD>",
  "findings": [
    {"id":"SEC-001","dimension":"security","severity":"critical",
     "title":"...","location":"path:line","description":"...",
     "recommendation":"...","rationale":"..."}
  ]
}
```

Assign stable IDs per dimension: `SEC-###` (security), `COR-###` (correctness),
`PERF-###` (performance), `QLT-###` (quality), `ARC-###` (architecture),
`DEP-###` (dependencies), `TST-###` (testing). Sort critical → info.

## Reporting flow

1. Derive `<project>`: `basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"`.
2. Write the aggregated report JSON to `/tmp/audit-<project>.json` with `Write`.
3. Render it:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render_report.py" /tmp/audit-<project>.json
   ```

   The script writes `~/.reports/audit-<project>.html`, opens it in the browser,
   and prints the path. Add `--csv` to also emit a spreadsheet.
4. Print a concise **Markdown summary to chat**: a one-line headline
   (`N findings: X critical, Y high, …`), a severity table, and the top
   critical/high findings with `path:line`. Do not dump every finding to chat —
   the HTML holds the full set.

## Follow-up offer

After presenting, use `AskUserQuestion` to offer:

- **File issues** — via the `issue-tracker` skill (one per finding, or only
  criticals/highs). Map severity to priority labels: critical→P0/P1, high→P2,
  medium→P3, low→P4.
- **Export CSV** — re-run the renderer with `--csv`.
- **Nothing** — stop here.

## Rules

- **Read-only.** Never edit source during an audit. If the user wants fixes,
  finish the report first, then treat fixing as a separate, approved task.
- **Evidence over opinion.** Every finding needs a real `path:line` and a
  concrete reason. Drop anything you can't point at.
- **No invented scope.** Audit what exists; don't propose rewrites of working
  code or features nobody asked for.
- **Be honest about coverage.** If a dimension was skipped or a large area went
  unread, say so. Never let truncation read as "all clear".
