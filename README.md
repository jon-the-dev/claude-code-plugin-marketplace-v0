# Claude Code Marketplace

`jrs-plugins` — custom Claude Code plugins (skills, slash commands, agents, hooks, MCP servers).

## Install

```
/plugin marketplace add jon-the-dev/claude-code-plugin-marketplace-v0
/plugin install <plugin-name>@jrs-plugins
```

## Plugins

- **jr-repo-tools** — repo helper commands (e.g. `/go-live-check`) for quick code reviews.
- **runway** — Runway infrastructure deployment suite: agents, commands, hooks, and MCP servers.
- **gemini** — cross-model assistant via the Google Gemini CLI for plan verification, QA review, context offloading, and cross-validation.
- **audit-code** — read-only codebase audit suite. `audit-code-master` orchestrates parallel sub-agents across focused dimension skills — security, correctness, performance, quality (AI-slop / readability / duplicate logic), architecture, dependencies, testing, social-preview — and renders a styled HTML report. Each dimension also runs standalone for a targeted audit.
- **lang-specialists** — senior language/framework specialist agents: `fastapi-developer`, `node-specialist`, `react-specialist`, `rust-engineer`, `typescript-pro`, `vue-expert`.
- **devops-agents** — DevOps and platform agents: `terraform-agent` (HCP Terraform workflows via the bundled Terraform MCP server — set `TFE_TOKEN`, `TFE_ADDRESS`, and `ENABLE_TF_OPERATIONS` in your environment to enable HCP operations), `github-actions-expert` (secure CI/CD workflows, SHA pinning, OIDC), `owasp-compliance` (OWASP ASI Top 10 agent security checks), `api-architect` (layered API client code generation).
- **ai-developer** — AI-assisted development workflow suite: `mini-sprint` plans and runs a batch of issues in isolated worktrees with auto-merge on green CI, `next-issue` ships the single next issue end-to-end, and `issue-report` generates a GitHub issue report with historical burndown tracking. The `mini-sprint`/`next-issue` code-review step uses `/codex:review` from OpenAI's `codex` plugin (`/plugin install codex@openai-codex`); it's skipped automatically if that plugin isn't installed.
