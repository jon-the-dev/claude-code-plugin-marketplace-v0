# Cloudflare: where to set security headers

Everything here applies only to hostnames that are **proxied** (orange
cloud). DNS-only records bypass Cloudflare entirely, in which case fix the
origin (aws.md) instead.

## Contents

1. Decide: Managed Transform vs Transform Rule
2. Transform Rule via dashboard
3. Transform Rule via API
4. Transform Rule via Terraform
5. HSTS (Edge Certificates setting)
6. Workers / Snippets for dynamic CSP
7. Cloudflare Pages `_headers`
8. Caveats and verification

---

## 1. Managed Transform vs Transform Rule

**Managed Transform "Add security headers"** (Rules → Settings → Managed
Transforms) is one click and adds:

```
x-content-type-options: nosniff
x-xss-protection: 1; mode=block
x-frame-options: SAMEORIGIN
referrer-policy: same-origin
expect-ct: max-age=86400, enforce
```

It does not add HSTS, CSP, or Permissions-Policy, and two of the headers it
adds (`X-XSS-Protection`, `Expect-CT`) are deprecated and show up as
warnings on securityheaders.com. It gets a site from F to roughly C. Use it
only as a stopgap; a custom Transform Rule reaches A+ and does not count
against the plan's rule quota any differently.

**Transform Rule → Modify Response Header** is the right tool: one rule can
carry every header (set, or remove) with an expression that scopes it to a
host or path. Available on all plans; the Free plan allows a small number of
rules, so pack the headers into one rule.

## 2. Transform Rule via dashboard

Rules → Overview → Create rule → Response Header Transform Rule (older UI:
Rules → Transform Rules → Modify Response Header).

- Expression: `true` for all traffic, or `(http.host eq "example.com")`, or
  `(http.host eq "example.com" and not starts_with(http.request.uri.path, "/embed/"))` when one path must be framed.
- Add operations, each **Set static**:

| Header | Value |
|---|---|
| `Strict-Transport-Security` | prefer section 5 instead; if set here, do not also enable the Edge Certificates toggle |
| `Content-Security-Policy` | `default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests` |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()` |

- Add **Remove** operations for `X-Powered-By`, `X-AspNet-Version`,
  `X-XSS-Protection` (if the origin sends them). Cloudflare already rewrites
  `Server` to `cloudflare`, which the scanner does not treat as a leak.

"Set static" overwrites a header the origin sent; "Add" would append a
second one, which is a regression on HSTS and CSP, so always use Set.

## 3. Transform Rule via API

Token needs **Zone → Transform Rules → Edit** on the zone. Writing the
phase entrypoint replaces the zone's response-header transform rules, so
fetch it first and merge if rules already exist.

```bash
ZONE_ID=...; export CLOUDFLARE_API_TOKEN=...
# inspect what exists
curl -sS "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rulesets/phases/http_response_headers_transform/entrypoint" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN"

# replace the phase with one rule carrying all headers
curl -sS -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rulesets/phases/http_response_headers_transform/entrypoint" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" -H "Content-Type: application/json" \
  --data @- <<'JSON'
{
  "rules": [
    {
      "description": "Security headers (A+ on securityheaders.com)",
      "expression": "true",
      "action": "rewrite",
      "action_parameters": {
        "headers": {
          "Content-Security-Policy":   { "operation": "set", "value": "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests" },
          "X-Frame-Options":           { "operation": "set", "value": "DENY" },
          "X-Content-Type-Options":    { "operation": "set", "value": "nosniff" },
          "Referrer-Policy":           { "operation": "set", "value": "strict-origin-when-cross-origin" },
          "Permissions-Policy":        { "operation": "set", "value": "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()" },
          "X-Powered-By":              { "operation": "remove" },
          "X-XSS-Protection":          { "operation": "remove" }
        }
      }
    }
  ]
}
JSON
```

To add a rule without replacing others: `POST .../rulesets/{ruleset_id}/rules`
with the single rule object, where `ruleset_id` comes from the entrypoint GET.

## 4. Terraform (`cloudflare_ruleset`)

Provider v4 syntax:

```hcl
resource "cloudflare_ruleset" "security_headers" {
  zone_id = var.zone_id
  name    = "Security headers"
  kind    = "zone"
  phase   = "http_response_headers_transform"

  rules {
    description = "Security headers (A+ on securityheaders.com)"
    expression  = "true"
    action      = "rewrite"
    action_parameters {
      headers {
        name      = "Content-Security-Policy"
        operation = "set"
        value     = "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests"
      }
      headers {
        name      = "X-Frame-Options"
        operation = "set"
        value     = "DENY"
      }
      headers {
        name      = "X-Content-Type-Options"
        operation = "set"
        value     = "nosniff"
      }
      headers {
        name      = "Referrer-Policy"
        operation = "set"
        value     = "strict-origin-when-cross-origin"
      }
      headers {
        name      = "Permissions-Policy"
        operation = "set"
        value     = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"
      }
      headers {
        name      = "X-Powered-By"
        operation = "remove"
      }
    }
  }
}

resource "cloudflare_zone_settings_override" "tls" {
  zone_id = var.zone_id
  settings {
    always_use_https = "on"
    security_header {
      enabled            = true
      max_age            = 31536000
      include_subdomains = true
      preload            = false
      nosniff            = true
    }
  }
}
```

Provider v5 moved `rules` and `headers` to list attributes
(`rules = [{ ... action_parameters = { headers = { "X-Frame-Options" = { operation = "set", value = "DENY" } } } }]`)
and replaced `cloudflare_zone_settings_override` with per-setting
`cloudflare_zone_setting` resources; match whatever version the repo pins.

## 5. HSTS

Cloudflare has a dedicated HSTS setting: SSL/TLS → Edge Certificates →
HTTP Strict Transport Security (HSTS). It asks you to acknowledge the risk,
then takes `max-age`, `includeSubDomains`, `preload`, and a "No-Sniff" toggle
(which also sends `X-Content-Type-Options: nosniff`).

API equivalent (token needs Zone Settings → Edit):

```bash
curl -sS -X PATCH "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/security_header" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" -H "Content-Type: application/json" \
  --data '{"value":{"strict_transport_security":{"enabled":true,"max_age":31536000,"include_subdomains":true,"preload":false,"nosniff":true}}}'
```

Use either this setting or a Transform Rule for HSTS, not both, or the
scanner's raw-header list will show two `Strict-Transport-Security` lines.
Also turn on **Always Use HTTPS** (SSL/TLS → Edge Certificates) so HTTP
redirects before HSTS is even consulted, and keep SSL mode at **Full
(strict)** so the Cloudflare-to-origin leg is not plain HTTP behind the
HSTS promise.

## 6. Workers / Snippets for dynamic CSP

When CSP needs a per-response nonce (inline scripts you cannot hash), a
Worker on the route can generate one and inject it into both the header and
the HTML:

```js
export default {
  async fetch(request, env, ctx) {
    const nonce = btoa(crypto.getRandomValues(new Uint8Array(16)).join(""));
    const res = await fetch(request);
    const rewritten = new HTMLRewriter()
      .on("script", { element(e) { e.setAttribute("nonce", nonce); } })
      .transform(res);
    const headers = new Headers(rewritten.headers);
    headers.set("Content-Security-Policy", `default-src 'self'; script-src 'self' 'nonce-${nonce}'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'`);
    headers.delete("X-Powered-By");
    return new Response(rewritten.body, { status: rewritten.status, headers });
  }
};
```

Keep the static five headers in a Transform Rule even when a Worker exists;
it is cheaper and survives Worker changes. Snippets (paid plans) can do the
same header logic without HTML rewriting.

## 7. Cloudflare Pages

Add a `_headers` file to the build output directory:

```
/*
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  Content-Security-Policy: default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()
```

Transform Rules on the custom domain also work for Pages projects and win
over `_headers` when both set the same header with "Set static".

## 8. Caveats and verification

- Transform Rules run on every response including cache hits, so no purge
  is needed; changes are live within seconds.
- Rules scoped by `http.host` do not match the `*.pages.dev` or
  `*.workers.dev` hostnames unless listed.
- Cloudflare's own headers (`cf-ray`, `cf-cache-status`, `server: cloudflare`,
  `alt-svc`, `nel`, `report-to`) are normal and not graded. If the scanner
  reports `Server: cloudflare` as information disclosure, it is cosmetic.
- When Cloudflare fronts CloudFront or an ALB that also sets headers, the
  Transform Rule's "Set static" wins; remove the inner copy to avoid
  confusion when debugging the origin directly.

```bash
curl -sS -D - -o /dev/null https://example.com/ | grep -iE '^(strict-transport|content-security|x-frame|x-content-type|referrer|permissions|server|cf-ray)'
# bypass Cloudflare to see what the origin sends (needs the origin IP and the host header)
curl -sS -D - -o /dev/null --resolve example.com:443:ORIGIN_IP https://example.com/
```
