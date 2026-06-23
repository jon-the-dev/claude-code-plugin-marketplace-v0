#!/usr/bin/env python3
"""Fetch open GitHub issues and output priority-sorted, token-efficient markdown for LLM consumption.

Priority rules (from /autobot:next-issue):
  1. cost-review-needed → skipped (shown at bottom)
  2. blocker → P0
  3. critical or security → P1
  4. high → P2
  5. bug beats feature at same level → tie-break
  6. medium → P3
  7. low → P4
  8. tests → P5
  9. Everything else → P6 (unsorted, still shown)
"""

import json
import subprocess
import sys

# Lower number = higher priority
PRIORITY_LABELS: dict[str, int] = {
    "blocker": 0,
    "critical": 1,
    "security": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
    "test": 5,
    "tests": 5,
}

SKIP_LABELS = {"cost-review-needed", "post-revenue", "on-hold"}
BUG_LABELS = {"bug"}

RANK_NAMES = {
    0: "P0-blocker",
    1: "P1-critical",
    2: "P2-high",
    3: "P3-medium",
    4: "P4-low",
    5: "P5-tests",
    6: "unranked",
    99: "skipped",
}


def fetch_issues() -> list[dict]:
    """Run gh issue list and return parsed JSON."""
    result = subprocess.run(
        [
            "gh", "issue", "list",
            "--state", "open",
            "--limit", "100",
            "--json", "number,title,labels,assignees,milestone,createdAt",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def rank_issue(issue: dict) -> tuple[int, int, str]:
    """Return sort key: (priority, bug_tiebreak, created).

    Lower tuple = higher priority. Bugs get 0 tiebreak (sort before non-bugs).
    """
    label_names = {l["name"] for l in issue.get("labels", [])}

    # Skipped labels go to the bottom
    if label_names & SKIP_LABELS:
        priority = 99
    else:
        # Find the highest (lowest number) matching priority
        priority = 6  # default: unranked
        for label in label_names:
            if label in PRIORITY_LABELS:
                priority = min(priority, PRIORITY_LABELS[label])

    # Bugs beat non-bugs at the same priority level
    is_bug = 0 if label_names & BUG_LABELS else 1

    # Older issues first within same rank
    created = issue.get("createdAt", "")

    return (priority, is_bug, created)


def to_markdown(issues: list[dict]) -> str:
    """Convert issues to a priority-sorted markdown table grouped by rank."""
    sorted_issues = sorted(issues, key=rank_issue)

    lines = [
        f"# Open Issues ({len(issues)})",
        "",
    ]

    footnotes = []
    current_rank = None

    for issue in sorted_issues:
        priority, _, _ = rank_issue(issue)
        rank_name = RANK_NAMES.get(priority, "unranked")

        # Group header when rank changes
        if rank_name != current_rank:
            current_rank = rank_name
            if len(lines) > 2:
                lines.append("")
            lines.append(f"## {rank_name}")
            lines.append("")
            lines.append("| # | Title | Labels | Created |")
            lines.append("| --- | --- | --- | --- |")

        num = issue["number"]
        labels = ", ".join(l["name"] for l in issue.get("labels", []))
        created = issue["createdAt"][:10]

        lines.append(f"| {num} | {issue['title']} | {labels} | {created} |")

        # Sparse fields as footnotes
        assignees = [a.get("login", a.get("name", "")) for a in issue.get("assignees", [])]
        milestone = issue.get("milestone", {}).get("title") if issue.get("milestone") else None

        parts = []
        if assignees:
            parts.append(f"assigned={','.join(assignees)}")
        if milestone:
            parts.append(f"milestone={milestone}")
        if parts:
            footnotes.append(f"- #{num}: {'; '.join(parts)}")

    if footnotes:
        lines.append("")
        lines.append("## Notes")
        lines.extend(footnotes)

    return "\n".join(lines)


def main():
    try:
        issues = fetch_issues()
    except subprocess.CalledProcessError as e:
        print(f"Error running gh: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: gh CLI not found. Install from https://cli.github.com", file=sys.stderr)
        sys.exit(1)

    print(to_markdown(issues))


if __name__ == "__main__":
    main()
