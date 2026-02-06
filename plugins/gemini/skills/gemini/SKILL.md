---
name: gemini
description: >
  Cross-model AI assistant via Google Gemini CLI. Invoke autonomously for:
  (1) Plan verification - validate implementation plans before execution,
  (2) QA review - second-opinion code review on completed work,
  (3) Context offloading - delegate research or analysis to free up context,
  (4) Cross-validation - verify critical decisions with an independent model.
  Trigger when: finalizing plans, completing implementation steps, context is heavy,
  or an independent perspective would catch blind spots.
user-invocable: false
allowed-tools: Bash(gemini *), Bash(cat *), Bash(echo *), Read
---

# Gemini Cross-Model Assistant

You have access to Google's Gemini CLI via the `gemini` command (it must be in PATH). Use it autonomously as a second AI to verify your work, offload research, and catch blind spots.

## When to invoke this skill

### Plan verification
Before executing a multi-step implementation plan, send the plan to Gemini for review. Ask it to identify gaps, risks, or missed edge cases.

### QA / code review
After completing a significant chunk of work (new feature, refactor, security change), pipe the changed files to Gemini for an independent review.

### Context offloading
When your context is getting heavy with research, delegate a bounded research question to Gemini. It returns a summary you can use without carrying the full exploration context.

### Cross-validation
For critical decisions (architecture choices, security implementations, data model design), get Gemini's independent take before committing.

## Command patterns

**Fast mode (default)** - No MCP servers, responds in seconds:
```bash
gemini -p "PROMPT" --allowed-mcp-server-names none 2>/dev/null
```

**Pipe file content for review:**
```bash
cat /path/to/file.py | gemini -p "PROMPT" --allowed-mcp-server-names none 2>/dev/null
```

**Multiple files:**
```bash
(echo "=== file1.py ===" && cat file1.py && echo "=== file2.py ===" && cat file2.py) | gemini -p "PROMPT" --allowed-mcp-server-names none 2>/dev/null
```

**Full mode** - With Gemini's own MCP servers (30s+ startup, use sparingly):
```bash
gemini -p "PROMPT" 2>/dev/null
```

## Constructing prompts for Gemini

Gemini has ZERO context about the project. Every prompt you send must be fully self-contained. Always include:

1. **Project context** - What the project is, what language/framework it uses, and the relevant tech stack
2. **File purpose** - What the file or code being reviewed does, where it fits in the architecture
3. **Specific ask** - What exactly you want Gemini to evaluate (not "review this" but "check this FastAPI endpoint for auth bypass vulnerabilities")
4. **Output format** - Explicit format constraint (bullets, numbered list, code only)
5. **Length constraint** - Keep responses bounded ("under 200 words", "top 5 issues only")

### Bad prompt (vague, no context)
```
Review this code for issues.
```

### Good prompt (self-contained, specific)
```
This is a FastAPI authentication middleware for a Python 3.12 web app using JWT tokens
and SQLAlchemy. It handles token validation and user session management.

Review this code for:
1. Authentication bypass vulnerabilities
2. Token validation edge cases
3. SQL injection risks
4. Race conditions in session handling

List findings by severity (critical/high/medium/low). No praise, findings only. Under 300 words.
```

### Plan verification prompt template
```
You are reviewing an implementation plan for a [project type] built with [tech stack].
The project [brief description of what it does].

Identify:
1. Missing steps or gaps
2. Risk areas or edge cases
3. Ordering issues (dependencies that should come first)
4. Security concerns

Plan:
[plan text]

Be concise. Bullet points only. Under 200 words.
```

### Code review prompt template
```
This is [language] code from a [project description] using [framework/libraries].
The code handles [what this specific code does].

Review for bugs, security issues, and design problems.
Focus on: [specific concerns].
List findings by severity (critical/high/medium/low).
Findings only, no praise. Under 300 words.
```

### Research offload prompt template
```
Research: [specific question].
Context: We are building [project description] with [tech stack].
Provide a concise summary with:
- Key findings (bullet points)
- Trade-offs if applicable
- Recommendation with rationale
Under 300 words.
```

## File safety

Before piping any file to Gemini, verify it does not contain secrets or credentials. **Never pipe files matching these patterns:**
- `.env`, `.env.*`
- `*.key`, `*.pem`, `*.p12`, `*.pfx`
- `credentials*`, `secrets*`, `*secret*`
- `*.tfvars` (may contain cloud credentials)
- `~/.ssh/*`, `~/.aws/*`, `~/.config/gcloud/*`

When in doubt, use `Read` to inspect the file first before piping it.

## Rules

- Always use `2>/dev/null` to suppress stderr noise from Gemini's config warnings
- Always default to `--allowed-mcp-server-names none` for speed (skips MCP server startup)
- Never pass secrets, API keys, or credentials in prompts or piped files
- If Gemini returns an empty response, errors, or returns a 429 rate limit, proceed with your own analysis and briefly note to the user that cross-validation was unavailable
- Report Gemini's findings to the user transparently - note agreements and disagreements
- Do not blindly adopt Gemini's suggestions - evaluate them critically against your own analysis

## How to present results

When Gemini returns useful findings, briefly report to the user:

> **Cross-check (Gemini):** [1-3 sentence summary of what Gemini flagged]
> **My assessment:** [whether you agree/disagree and why]

If Gemini was unavailable or errored:

> **Cross-check (Gemini):** Unavailable (timeout/error). Proceeding with own analysis.

Keep it brief. The user wants the value, not the process.
