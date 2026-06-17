#!/usr/bin/env python3
"""Render a codebase-audit findings JSON file into a self-contained HTML report.

The audit-code skills aggregate their findings into a single JSON document, then
call this script to produce a styled, dependency-free HTML report under
~/.reports/ and open it in the default browser. Optionally also emits a CSV for
spreadsheet triage.

Usage:
    render_report.py FINDINGS_JSON [--no-open] [--csv]

The findings JSON schema:
    {
      "project": "maia",
      "scope": "whole repository",
      "generated": "2026-06-09",
      "findings": [
        {
          "id": "SEC-001",
          "dimension": "security",
          "severity": "critical",      # critical|high|medium|low|info
          "title": "Hard-coded MongoDB credentials",
          "location": "services/backend/app/database.py:14",
          "description": "...",
          "recommendation": "...",
          "rationale": "..."
        }
      ]
    }
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]
SEVERITY_COLOR = {
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#d97706",
    "low": "#65a30d",
    "info": "#0891b2",
}
FIELDS = ["id", "dimension", "severity", "title", "location",
          "description", "recommendation", "rationale"]


def _sort_key(finding: dict) -> tuple[int, str]:
    """Order findings by severity (critical first), then by id."""
    sev = finding.get("severity", "info").lower()
    rank = SEVERITY_ORDER.index(sev) if sev in SEVERITY_ORDER else len(SEVERITY_ORDER)
    return (rank, finding.get("id", ""))


def _counts(findings: list[dict]) -> dict[str, int]:
    """Tally findings per severity level."""
    tally = {sev: 0 for sev in SEVERITY_ORDER}
    for finding in findings:
        sev = finding.get("severity", "info").lower()
        tally[sev] = tally.get(sev, 0) + 1
    return tally


def _esc(value: str) -> str:
    """HTML-escape a value, treating None as empty string."""
    return html.escape(str(value or ""))


def _summary_badges(tally: dict[str, int]) -> str:
    """Render the severity summary badge row."""
    badges = []
    for sev in SEVERITY_ORDER:
        count = tally.get(sev, 0)
        if count == 0 and sev == "info":
            continue
        badges.append(
            f'<span class="badge" style="background:{SEVERITY_COLOR[sev]}">'
            f'{count} {sev.title()}</span>'
        )
    return "".join(badges)


def _finding_card(finding: dict) -> str:
    """Render a single finding as an HTML card."""
    sev = finding.get("severity", "info").lower()
    color = SEVERITY_COLOR.get(sev, "#6b7280")
    rows = []
    if finding.get("location"):
        rows.append(f'<div class="loc"><code>{_esc(finding["location"])}</code></div>')
    if finding.get("description"):
        rows.append(f'<p><strong>Issue.</strong> {_esc(finding["description"])}</p>')
    if finding.get("recommendation"):
        rows.append(f'<p><strong>Fix.</strong> {_esc(finding["recommendation"])}</p>')
    if finding.get("rationale"):
        rows.append(f'<p class="rationale"><strong>Why.</strong> {_esc(finding["rationale"])}</p>')
    return f"""
    <article class="card" style="border-left-color:{color}">
      <header>
        <span class="sev" style="background:{color}">{_esc(sev.upper())}</span>
        <span class="fid">{_esc(finding.get("id", ""))}</span>
        <span class="dim">{_esc(finding.get("dimension", ""))}</span>
        <h3>{_esc(finding.get("title", "Untitled finding"))}</h3>
      </header>
      {''.join(rows)}
    </article>"""


def build_html(data: dict) -> str:
    """Build the complete HTML document for an audit report."""
    findings = sorted(data.get("findings", []), key=_sort_key)
    tally = _counts(findings)
    project = _esc(data.get("project", "unknown"))
    scope = _esc(data.get("scope", "whole repository"))
    generated = _esc(data.get("generated") or datetime.now().strftime("%Y-%m-%d"))
    total = len(findings)
    cards = "\n".join(_finding_card(f) for f in findings) or \
        '<p class="clean">No findings. Clean bill of health.</p>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Audit — {project}</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         margin: 0; background: #0f172a; color: #e2e8f0; }}
  .wrap {{ max-width: 960px; margin: 0 auto; padding: 2.5rem 1.5rem 5rem; }}
  header.top {{ border-bottom: 1px solid #1e293b; padding-bottom: 1.5rem; margin-bottom: 2rem; }}
  h1 {{ margin: 0 0 .25rem; font-size: 1.7rem; }}
  .meta {{ color: #94a3b8; font-size: .9rem; }}
  .badges {{ margin: 1.25rem 0 .25rem; display: flex; gap: .5rem; flex-wrap: wrap; }}
  .badge {{ color: #fff; padding: .3rem .7rem; border-radius: 999px;
           font-size: .8rem; font-weight: 600; }}
  .card {{ background: #1e293b; border-left: 4px solid #6b7280; border-radius: 8px;
          padding: 1rem 1.25rem; margin: 1rem 0; }}
  .card header {{ display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; }}
  .card h3 {{ margin: .4rem 0 .6rem; font-size: 1.05rem; flex-basis: 100%; }}
  .sev {{ color: #fff; font-size: .68rem; font-weight: 700; padding: .15rem .5rem;
         border-radius: 4px; letter-spacing: .03em; }}
  .fid {{ font-family: ui-monospace, monospace; font-size: .8rem; color: #cbd5e1; }}
  .dim {{ font-size: .75rem; color: #64748b; text-transform: uppercase;
         letter-spacing: .05em; }}
  .loc code {{ background: #0f172a; padding: .15rem .45rem; border-radius: 4px;
             font-size: .82rem; color: #fbbf24; }}
  .card p {{ margin: .5rem 0; }}
  .rationale {{ color: #94a3b8; }}
  .clean {{ text-align: center; color: #65a30d; font-size: 1.2rem; padding: 3rem 0; }}
  footer {{ margin-top: 3rem; color: #475569; font-size: .8rem; text-align: center; }}
  code {{ font-family: ui-monospace, SFMono-Regular, monospace; }}
</style>
</head>
<body>
  <div class="wrap">
    <header class="top">
      <h1>Codebase Audit — {project}</h1>
      <div class="meta">Scope: {scope} &middot; {total} finding(s) &middot; Generated {generated}</div>
      <div class="badges">{_summary_badges(tally)}</div>
    </header>
    {cards}
    <footer>Generated by the audit-code plugin.</footer>
  </div>
</body>
</html>"""


def write_csv(data: dict, path: Path) -> None:
    """Write findings to a CSV file for spreadsheet triage."""
    findings = sorted(data.get("findings", []), key=_sort_key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(findings)


def main() -> int:
    """CLI entry point: render HTML (and optional CSV), then open in browser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("findings_json", help="Path to the findings JSON file")
    parser.add_argument("--no-open", action="store_true",
                        help="Do not open the report in a browser")
    parser.add_argument("--csv", action="store_true",
                        help="Also emit a CSV next to the HTML report")
    args = parser.parse_args()

    src = Path(args.findings_json).expanduser()
    if not src.is_file():
        print(f"error: findings file not found: {src}", file=sys.stderr)
        return 1
    data = json.loads(src.read_text(encoding="utf-8"))

    project = data.get("project", "unknown")
    out_dir = Path.home() / ".reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"audit-{project}.html"
    html_path.write_text(build_html(data), encoding="utf-8")
    print(f"HTML report: {html_path}")

    if args.csv:
        csv_path = out_dir / f"audit-{project}.csv"
        write_csv(data, csv_path)
        print(f"CSV report:  {csv_path}")

    if not args.no_open:
        webbrowser.open(html_path.as_uri())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
