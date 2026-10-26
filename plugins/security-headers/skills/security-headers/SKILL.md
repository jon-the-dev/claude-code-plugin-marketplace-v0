---
name: security-headers
description: >
  Scan a website's HTTP security headers with securityheaders.com (with a
  built-in local grader as fallback), explain each missing or weak header, and
  produce concrete, platform-specific fixes for AWS (CloudFront response
  headers policies, ALB listener attributes, API Gateway, Amplify, S3 static
  sites, Elastic Beanstalk) and Cloudflare (Transform Rules, Managed
  Transforms, HSTS, Workers), then re-scan to prove the grade improved. Use
  this whenever the user mentions securityheaders.com, a security headers
  grade or score (A+, B, F), HSTS, Content-Security-Policy, X-Frame-Options,
  Permissions-Policy, Referrer-Policy, clickjacking, "harden my site", "check
  my headers", or wants to improve a website's security posture, even if they
  do not name the headers or the scanner explicitly.
allowed-tools: Bash, Read, Glob, Grep, Write, Edit, WebFetch, AskUserQuestion, TodoWrite
---

# security-headers

You scan a site the way securityheaders.com does, explain what is missing and
why it matters, and hand back fixes the user can apply on the platform that
actually serves the response. Then you verify.

Three things make this job go wrong when done casually, so keep them in mind:

- **Headers are set where the response is built, not where the user thinks.**
  A header added in the app is useless if CloudFront or Cloudflare strips or
  overrides it, and a header added at the edge is invisible on the origin URL.
  Find the layer that serves the public response before proposing a fix.
- **A bad Content-Security-Policy breaks sites; the other five headers almost
  never do.** Ship HSTS, X-Content-Type-Options, X-Frame-Options,
  Referrer-Policy, and Permissions-Policy straight away. Roll CSP out in
  Report-Only first unless the user accepts the risk or the site is trivial.
- **The scanner only sees one URL.** securityheaders.com scans the final URL
  after redirects. Scan the apex and `www`, and any separately served app or
  API host the user cares about.

## Tools you have

- `${CLAUDE_PLUGIN_ROOT}/skills/security-headers/scripts/scan_headers.py` —
  fetches the live headers, computes a local grade estimate using the same
  six core headers securityheaders.com grades, and (when reachable) asks
  securityheaders.com for its authoritative grade. Python 3 standard library
  only. Run `--help` for flags. Use `--json` when you need to compare
  before/after programmatically.
- `${CLAUDE_PLUGIN_ROOT}/skills/security-headers/references/grading.md` —
  how securityheaders.com grades, what its warnings mean, the current state
  of its API (the paid API was discontinued in April 2026; the website still
  works). Read this before interpreting a grade.
- `${CLAUDE_PLUGIN_ROOT}/skills/security-headers/references/headers.md` —
  recommended value, rationale, and pitfalls for every header the scanner
  checks, plus the CSP rollout playbook. Read the section for each header
  you are about to recommend.
- `${CLAUDE_PLUGIN_ROOT}/skills/security-headers/references/aws.md` — fixes
  per AWS service (CloudFront, ALB, API Gateway, Amplify, S3, Elastic
  Beanstalk, Lambda URLs/App Runner) with CLI, CloudFormation, Terraform, and
  CDK snippets.
- `${CLAUDE_PLUGIN_ROOT}/skills/security-headers/references/cloudflare.md` —
  fixes for Cloudflare zones (Managed Transform, Transform Rules, HSTS, API,
  Terraform, Workers, Pages `_headers`).

## Workflow

### 1. Establish the targets

Collect the URL(s). If the user gave a bare hostname, scan `https://` and
note whether `http://` redirects to it. Add `www.` or the apex when the site
has both. Ask only if the user gave nothing to go on.

### 2. Scan

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/security-headers/scripts/scan_headers.py" https://example.com
```

The script prints a markdown report: the securityheaders.com grade when it
could reach the scanner, the local estimate, per-header status, warnings
(leaky `Server`/`X-Powered-By`, deprecated headers, weak values), and the
redirect chain. Keep the JSON (`--json --out before.json`) so you can diff it
after the fix.

If securityheaders.com is unreachable from your environment (common in
sandboxes), say so plainly, lean on the local estimate, and give the user the
scan link so they can confirm:
`https://securityheaders.com/?q=<url>&followRedirects=on`.

If the user pasted or attached a header dump (`curl -D -` output, a scan
screenshot transcribed into text) or the target itself is unreachable, grade
the file instead of fetching:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/security-headers/scripts/scan_headers.py" --from-file headers.txt --url https://example.com --json --out before.json
```

The local letter is an estimate: it uses the same six headers and the same
CSP cap as the scanner, but the exact thresholds are not published, so it can
be one letter off. The *set* of missing and weak headers is what to act on.

### 3. Work out which layer serves the response

Look at the scanned headers and the repo before guessing:

| Evidence in response headers | Serving layer | Reference |
|---|---|---|
| `via: ... cloudfront`, `x-amz-cf-id`, `x-cache: ... cloudfront` | CloudFront | aws.md → CloudFront |
| `server: awselb/2.0` (or no `server` and an ALB in the IaC) | ALB | aws.md → ALB |
| `x-amzn-requestid`, `x-amz-apigw-id` | API Gateway | aws.md → API Gateway |
| `server: AmazonS3` without CloudFront headers | S3 website endpoint | aws.md → S3 |
| `server: cloudflare`, `cf-ray`, `cf-cache-status` | Cloudflare proxy | cloudflare.md |
| `x-amzn-trace-id` + nginx/apache `server` | Elastic Beanstalk / EC2 | aws.md → Beanstalk / origin |

Then grep the repo for `aws_cloudfront_distribution`, `ResponseHeadersPolicy`,
`aws_lb_listener`, `cloudflare_ruleset`, `customHttp.yml`, `_headers`,
`.platform/nginx`, `helmet`, `secure_headers`, or a `next.config` `headers()`
block. Prefer changing infrastructure-as-code that already exists over
console or one-off CLI changes, because the next deploy would otherwise undo
the fix.

When Cloudflare fronts an AWS origin, headers can live at either layer. Set
the static five at Cloudflare (closest to the user, applies to every origin)
and keep CSP wherever nonces are generated. Say which you chose and why.

### 4. Build the fix plan

Target the full securityheaders.com A+ set unless the user asked for less:

| Header | Default to propose |
|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (add `preload` only if the user wants the preload list and every subdomain is HTTPS) |
| `Content-Security-Policy` | Start from `default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests` and widen per inventory. Roll out as `Content-Security-Policy-Report-Only` first unless the site is a static page you can fully inventory. |
| `X-Frame-Options` | `DENY` (or `SAMEORIGIN` if the site frames itself) |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()` and widen per feature use |

Also propose removing or neutralising leaks (`Server` version strings,
`X-Powered-By`, `X-AspNet-Version`) and dropping deprecated headers
(`X-XSS-Protection`, `Expect-CT`, `Feature-Policy`, `Public-Key-Pins`),
because securityheaders.com flags them as warnings even though they do not
change the letter grade.

For CSP specifically: inventory script, style, image, font, connect, and
frame origins from the HTML and the app's bundles before writing the policy.
Explain the `'unsafe-inline'` trade-off: it keeps the site working but caps
the grade and defeats most of CSP's XSS protection; nonces or hashes are the
way out. `headers.md` has the full rollout playbook.

Write the plan as the concrete config change for the chosen layer, pulled
from the matching reference file: Terraform/CFN/CDK resource, CLI command,
or dashboard steps, in that order of preference.

### 5. Apply (only when asked, and only in code)

Edit IaC or app config in the repo when the user asked you to fix it. Never
run mutating `aws`, `wrangler`, or Cloudflare API calls, and never touch a
console setting, without the user confirming that specific command first:
header changes are live immediately on every response and a bad CSP or an
HSTS `preload` is hard to roll back. Read-only calls (`describe-*`, `get-*`,
`list-*`) are fine.

### 6. Verify

After the change is deployed (or the user says it is), re-run the scan and
diff against the saved JSON. Check:

- The headers appear on the public URL, not only on the origin.
- Each header appears exactly once (duplicate HSTS/CSP from two layers is a
  common regression).
- The site still works: for CSP, look for `Refused to ...` console errors or
  reports arriving at the report endpoint.
- The grade moved, and if it did not, why (cached response, wrong cache
  behavior, header set on the wrong listener or path).

## Report format

Use this shape for the final answer so the user can act without re-reading
the scan output:

```
# Security headers: <host>
Grade: <securityheaders.com grade or "local estimate: X"> → target A+

## Findings
- <header>: missing / weak (<value>) — why it matters in one line
...
## Warnings
- <leak or deprecated header>
## Fix (<layer>)
<the IaC/CLI/dashboard change, ready to apply>
## Rollout notes
- CSP: report-only first, where to watch reports, when to enforce
- Anything that could break (framing, embeds, HSTS preload)
## Verify
<the exact re-scan command and what to look for>
```

Keep the findings tied to evidence from the scan. Do not report a header as
missing on a URL you did not scan.

Size the report to the site. A one-page marketing site or a small business
WordPress install needs the fix, the two or three things that could break,
and the verify command; it does not need every directive explained. Save the
long form (drift analysis, per-directive rationale, staged rollout tables)
for sites where the user has signalled a change process or where CSP is
genuinely risky.
