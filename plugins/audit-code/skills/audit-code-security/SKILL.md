---
name: audit-code-security
description: >
  Read-only security audit of a codebase. Finds hard-coded secrets, authn/authz
  gaps, injection (SQL/command/template), OWASP Top 10 issues, IaC misconfig,
  unsafe deserialization, missing input validation, and insecure defaults. Use
  when the user asks to "audit security", "security review the code", "find
  vulnerabilities", "check for hard-coded secrets", "is this code secure?", or
  "OWASP review". For the full multi-dimension audit use audit-code-master.
  Never edits code.
allowed-tools: Bash, Read, Glob, Grep, Write, AskUserQuestion, TodoWrite
---

# audit-code — security

You audit the security posture of the code. You never edit source — you find,
rank, and report. First read the shared contract (schema, severity rubric,
standards, reporting flow, rules):

```
${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md
```

## What I look for

- **Secrets in source.** API keys, tokens, passwords, private keys, connection
  strings committed to the repo or baked into images/config.
- **Authn / authz gaps.** Missing or broken authentication, missing
  authorization checks, IDOR, privilege escalation, trusting client-supplied
  identity.
- **Injection.** SQL/NoSQL, command, template, LDAP, header, and path-traversal
  injection from unsanitized input.
- **Input validation & output encoding.** Missing validation at trust
  boundaries, XSS, SSRF, open redirects, unsafe deserialization.
- **Crypto & transport.** Weak/rolled-your-own crypto, missing TLS, predictable
  randomness for security, hard-coded IVs/salts.
- **IaC & config misconfig.** Public buckets, over-broad IAM, open security
  groups, secrets in plaintext config, debug mode in production.

Report only real, evidence-backed issues. Severity per the shared rubric
(exploitable → critical).

## How to run

1. **Orient.** `basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"` →
   `<project>`. Identify the stack, entry points, and trust boundaries. Honor
   any scope the user named; otherwise the whole repository.
2. **Investigate.** Grep for secret patterns and dangerous sinks; read auth
   middleware, request handlers, query construction, and IaC. Trace untrusted
   input to sinks.
3. **Record findings** against the shared schema with concrete `path:line`
   locations and a concrete remediation. Use the `SEC-###` ID prefix.
4. **Report.**
   - If **spawned by `audit-code-master`**: return the findings array only.
   - If run **standalone**: follow the **Reporting flow** and **Follow-up offer**
     in `${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md`.
