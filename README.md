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
- **audit-code** — read-only codebase audit suite. `audit-code-master` orchestrates parallel sub-agents across seven focused dimension skills — security, correctness, performance, quality (AI-slop / readability / duplicate logic), architecture, dependencies, testing — and renders a styled HTML report. Each dimension also runs standalone for a targeted audit.
