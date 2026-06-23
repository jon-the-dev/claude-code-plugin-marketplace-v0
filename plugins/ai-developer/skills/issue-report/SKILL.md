---
name: issue-report
description: "Generate a Github issue report with historical burndown tracking"
---

# issue-report

Collect open issues for the current repo, dump a timestamped JSON snapshot to `~/.reports/`, then generate a markdown summary and HTML leadership dashboard with trend charts showing burndown over time.

## Execution

**Dispatch this work to a Haiku subagent.** The work is mostly deterministic (run `gh` commands, parse JSON, render templated markdown/HTML), so it doesn't need Opus. Invoke the `Agent` tool with:

- `subagent_type: "general-purpose"`
- `model: "haiku"`
- `description: "Generate issue report"`
- `prompt`: A self-contained brief that includes the current working directory (so the agent runs `gh` against the right repo) and the full set of phases below (Phase 1 collect/dump, Phase 2 load history, Phase 3 generate reports), plus the Rules section. The agent will not see this conversation, so the prompt must inline everything it needs.

When the subagent returns, relay its summary (file paths written, total issue count, delta from previous run) to the user. Do not re-do the work in the main session.

## Outcome

- JSON snapshot written to `~/.reports/{repo-name}-data-{timestamp}.json`
- Markdown summary written to `~/.reports/ISSUE_REPORT-{repo-name}.md`
- HTML dashboard written to `~/.reports/ISSUE_REPORT-{repo-name}.html`
- HTML includes trend charts if prior snapshots exist

---

## Phase 1: Collect & Dump

### 1a: Identify the repo

```bash
REPO_NAME=$(basename $(git remote get-url origin) .git)
REPO_FULL=$(gh repo view --json nameWithOwner -q .nameWithOwner)
```

### 1b: Fetch open issues

```bash
gh issue list --state open --limit 500 --json number,title,labels,assignees,milestone,body,createdAt
```

### 1c: Categorize each issue

Assign priority and category using these rules:

| Label(s) | Priority |
|-----------|----------|
| `blocker` | P0 |
| `critical`, `security` | P1 |
| `bug` + `high` | P2 |
| `bug` + `medium` | P3 |
| `bug` + `low` | P4 |
| `enhancement` + `high` | P5 |
| `enhancement`, `feature` | P6 |
| `chore`, `tech-debt`, `documentation` | P7 |

Category mapping: `security` label → security, `bug` → bug, `feature`/`enhancement` → feature, `infra`/`deployment` → infra, `documentation` → docs, `chore`/`tech-debt` → tech-debt.

Issues with `cost-review-needed` or `on-hold` labels → skipped (shown separately).

### 1d: Create the snapshot directory

```bash
mkdir -p ~/.reports
```

### 1e: Write the JSON snapshot

Build a JSON object matching this schema and write it to `~/.reports/{REPO_NAME}-data-{TIMESTAMP}.json` where TIMESTAMP is ISO 8601 format with colons replaced by hyphens (e.g., `2026-04-05T14-30-00`):

```json
{
  "version": 1,
  "repo": "jon-the-dev/skynet-bot",
  "repo_name": "skynet-bot",
  "timestamp": "2026-04-05T14:30:00Z",
  "summary": {
    "total": 42,
    "by_priority": { "P0": 1, "P1": 3, "P2": 8, "P3": 12, "P4": 10, "P5": 5, "P6": 3 },
    "by_category": { "security": 2, "bug": 15, "feature": 12, "infra": 5, "docs": 3, "tech-debt": 5 }
  },
  "issues": [
    {
      "number": 42,
      "title": "Fix auth bypass",
      "labels": ["security", "critical"],
      "priority": "P1",
      "category": "security",
      "created_at": "2026-03-01T10:00:00Z",
      "assignees": ["jon"]
    }
  ]
}
```

---

## Phase 2: Load History

### 2a: Find all snapshots for this repo

Glob `~/.reports/{REPO_NAME}-data-*.json` and sort by timestamp ascending.

### 2b: Build the trend dataset

From each snapshot, extract `{ timestamp, summary }`. This becomes the `TREND_DATA` array. Cap at the most recent 30 snapshots for chart rendering.

### 2c: Compute delta

Compare the current snapshot's `summary.total` to the previous snapshot's. Record the delta (`+N` or `-N`) for display in the header.

---

## Phase 3: Generate Reports

### 3a: Markdown Summary

Write `~/.reports/ISSUE_REPORT-{REPO_NAME}.md` with:

- Report header with repo name, date, commit SHA
- Delta from last run (if history exists)
- Summary table (total issues, breakdown by priority tier)
- Prioritized issue list grouped by tier
- Recommended next actions
- Flag `cost-review-needed` issues separately

### 3b: HTML Leadership Dashboard

Generate a single-file HTML report saved to `~/.reports/ISSUE_REPORT-{REPO_NAME}.html`. Inline CSS, no external dependencies except Google Fonts. Minimal inline JS for trend charts only.

**Embed data in the HTML:**

```html
<script>
  const TREND_DATA = [ /* array of { timestamp, summary } from all snapshots */ ];
  const CURRENT_DATA = { /* full latest snapshot */ };
</script>
```

**Overall tone:** Dark, industrial-utilitarian dashboard. Think ops console, not marketing site. Information-dense but scannable.

**Design system:**

- **Background:** Near-black (#0c0c0e) with subtle ambient radial gradient accents for depth
- **Surfaces:** Layered dark cards (#141417, #1a1a1f) with thin borders (#2a2a32) and subtle hover states
- **Typography:** DM Sans for body text, JetBrains Mono for issue numbers and code-like elements
- **Color language:** Priority-driven — red for P0, orange for P1, blue for P2, gray for P3, purple for deferred. Amber/gold (#f59e0b) as primary accent
- **Spacing:** Generous vertical section padding (40px), tight internal card padding

**Layout structure (in order):**

1. **Header** — Report title, repo name, date, key stats as chip-style badges (blocker count, total issues). **Delta badge:** `+5 since last run` or `-3 since last run` — green for decrease, red for increase, gray if first run.

2. **Summary cards** — Horizontal grid of cards (one per priority tier) showing count, label, subtitle. Left-border color-coded by severity.

3. **Trends section** — Visible only if 2+ snapshots exist. Two inline SVG charts rendered by JS:
   - **Total Issues Over Time:** Line chart, ~600px wide, ~200px tall. X-axis: run dates (MMM DD). Y-axis: total count. Amber (#f59e0b) line with dots. Grid lines in #2a2a32. Tooltip on hover.
   - **Priority Breakdown Over Time:** Stacked area chart, same dimensions. One band per priority tier (P0-P4+) using the existing color language.
   - **First run:** Section hidden entirely. **One prior run:** Two points connected by a line. **50+ runs:** Use last 30 snapshots only.

4. **Critical alert callout** — Red-tinted banner if P0 blockers exist, with icon and prose summary

5. **Issue listings by tier** — Each priority tier as its own section with header + badge. Issues as rows: issue number (mono font, linked to GitHub), title + label chips, category note, status action chip. Highlight recommended "work next" issue with amber accent border and "Work Next" badge.

6. **Breakdown & risk analysis** — Two-column grid: left has horizontal bar chart by category (security, bugs, features, infra, docs, tech debt); right lists top risks with severity indicators.

7. **Recommended execution order** — Vertical timeline with numbered steps. First item highlighted in amber. Each step shows issue number, title, label chips.

8. **Leadership decision box** — Amber-bordered card with key decisions needed and bottom line summary.

9. **Footer** — Minimal, centered, one-line metadata

**Component patterns:**

- **Label chips:** Tiny uppercase text, colored background + border (security=red, bug=orange, feature=blue, infra=purple, docs=green)
- **Issue rows:** Grid layout with hover state, consistent column alignment
- **Section badges:** Uppercase, letter-spaced, pill-shaped, color-coded
- **Bar charts:** Pure CSS, gradient fills on fixed-width tracks with count labels
- **Age badges:** Days since creation, green (<7d) → yellow (7-30d) → orange (30-90d) → red (>90d)

**Responsive + print:** Mobile-friendly grid collapse. Print stylesheet swaps to white background. `print-color-adjust: exact`.

**Animation:** CSS-only fadeInUp on initial load with staggered delays. No JS for animations.

**No-JS fallback:** If JS is disabled, trend charts don't render. All other sections work fine (pure CSS).

---

## Rules

- Always create `~/.reports/` if it doesn't exist before writing
- Every issue number in HTML must link to `https://github.com/{REPO_FULL}/issues/{NUMBER}`
- HTML must be self-contained (inline CSS, inline data, Google Fonts only external dep)
- Sort issues within each tier by age (oldest first)
- Retain all JSON snapshots — never delete or overwrite previous dumps
- After generating, print file paths and a brief summary to console
