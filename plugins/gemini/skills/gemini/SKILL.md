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
allowed-tools: Bash(gemini *), Bash(cat *), Bash(timeout *), Read
---

# Gemini Cross-Model Assistant

You have access to Google's Gemini CLI at `/opt/homebrew/bin/gemini`. Use it autonomously as a second AI to verify your work, offload research, and catch blind spots.

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
timeout 60 gemini -p "PROMPT" --allowed-mcp-server-names none 2>/dev/null
```

**Pipe file content for review:**
```bash
cat /path/to/file.py | timeout 60 gemini -p "PROMPT" --allowed-mcp-server-names none 2>/dev/null
```

**Multiple files:**
```bash
(echo "=== file1.py ===" && cat file1.py && echo "=== file2.py ===" && cat file2.py) | timeout 60 gemini -p "PROMPT" --allowed-mcp-server-names none 2>/dev/null
```

**Full mode** - With Gemini's own MCP servers (30s+ startup, rare):
```bash
timeout 120 gemini -p "PROMPT" 2>/dev/null
```

## Prompt engineering for Gemini

Be direct and structured. Gemini responds best to:
- Specific task with clear scope
- Explicit output format (bullets, numbered list, code only)
- Length constraint ("under 200 words", "top 5 issues only")
- Role framing ("You are reviewing this as a senior security engineer")

### Plan verification prompt template
```
Review this implementation plan for a [description]. Identify:
1. Missing steps or gaps
2. Risk areas or edge cases
3. Ordering issues
4. Security concerns

Plan:
[plan text]

Be concise. Bullet points only.
```

### Code review prompt template
```
Review this [language] code for bugs, security issues, and design problems.
Focus on: [specific concerns].
List findings by severity (critical/high/medium/low).
Code only, no praise.
```

### Research offload prompt template
```
Research: [specific question].
Provide a concise summary with:
- Key findings (bullet points)
- Trade-offs if applicable
- Recommendation
Under 300 words.
```

## Rules

- Always use `2>/dev/null` to suppress stderr noise
- Always default to `--allowed-mcp-server-names none` for speed
- Always wrap with `timeout 60` (or `timeout 120` for full mode)
- Never pass secrets, API keys, or credentials in prompts
- If Gemini errors or returns a 429, proceed with your own analysis silently
- Report Gemini's findings to the user transparently - note agreements and disagreements
- Do not blindly adopt Gemini's suggestions - evaluate them critically

## How to present results

When Gemini returns useful findings, briefly report to the user:

> **Cross-check (Gemini):** [1-3 sentence summary of what Gemini flagged]
> **My assessment:** [whether you agree/disagree and why]

Keep it brief. The user wants the value, not the process.
