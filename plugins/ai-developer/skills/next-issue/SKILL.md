---
name: next-issue
description: Get the next GitHub issue to work on, implement it in an isolated worktree, create a PR, and auto-merge when CI passes. Use this skill whenever the user wants to pick up the next issue, work on GitHub issues, or asks "what should I work on next?" — even if they don't say "next-issue" explicitly.
---

# Next Issue

This is a single-issue shortcut. It delegates to the `mini-sprint` skill with these overrides:

1. **NUM_ISSUES = 1** — select only the top priority issue
2. **Skip Phase 2 (Planning)** — no sprint plan needed for one issue; go straight to worktree setup
3. **No sprint report** — just log the result to the journal and AUTOBOT.log
4. **No user confirmation on issue selection** — the priority rules are encoded in the script; announce which issue you're picking up and why, then proceed immediately

Read and follow the `mini-sprint` skill (`${CLAUDE_PLUGIN_ROOT}/skills/mini-sprint/SKILL.md`) with the overrides above.

## Implementation Agents

When implementing the issue, use the same subagent strategy as `/implement`:

- **`frontend-developer`** — React and Frontend work
- **`backend-developer`** — FastAPI and backend logic
- **`cloud-architect`** — AWS, Terraform, or DevOps activities
- **`test-writer`** — Write new or updated tests for changed code (runs on sonnet to save tokens)
- **`test-runner`** — Python, JS, TS, TF, or other test execution
- **`code-auditor`** — Post-implementation audit for issues

After each code-change agent finishes:

1. Launch a `test-writer` agent to write any new or updated tests needed for the changed code
2. Launch a `test-runner` to validate all tests pass
3. Launch a `/codex:review` agent to see if we missed anything (ensure it knows the task/issue details). Requires the external `codex` plugin (`/plugin install codex@openai-codex`); if it isn't installed, skip this step and note it in the result.
4. Follow up with the appropriate developer agent to address any failures

Run `code-auditor` and pre-commit checks before committing.

Use the shared fetch script:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/mini-sprint/scripts/fetch_issues.py"
```
