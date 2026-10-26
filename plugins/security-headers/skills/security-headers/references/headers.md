# Header reference: values, rationale, pitfalls

Read the section for each header you are about to recommend. Every value
below is a sane default for a typical web app; adjust to what the site
actually does and say when you deviate.

## Contents

1. Strict-Transport-Security
2. Content-Security-Policy (with rollout playbook)
3. X-Frame-Options
4. X-Content-Type-Options
5. Referrer-Policy
6. Permissions-Policy
7. Cross-Origin-* (COOP / COEP / CORP)
8. Headers to remove
9. Application-level helpers (when the edge is not the right place)

---

## 1. Strict-Transport-Security (HSTS)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

- Tells browsers to refuse plain HTTP for the host for `max-age` seconds.
  One year (31536000) is the conventional value; the scanner flags very
  short values.
- `includeSubDomains` is what you want on an apex, but it breaks any
  subdomain still served over HTTP (internal tools, mail webhosts,
  marketing microsites). Enumerate subdomains before adding it.
- `preload` submits the domain to the browser preload list via
  hstspreload.org. It is effectively permanent and requires `max-age` of at
  least one year plus `includeSubDomains`. Only add it when the user asks
  and understands removal takes months.
- Set it on HTTPS responses only. Make sure the HTTP listener redirects to
  HTTPS (301) rather than serving content.
- Set it in one layer only. Two HSTS headers (edge plus origin) is a
  common finding after a fix.

## 2. Content-Security-Policy (CSP)

The one header that can break a site. It controls which origins may load
scripts, styles, images, fonts, frames, and connections, and it is the only
graded header that actually mitigates XSS.

### Starting policy

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests
```

Widen each directive with the origins the inventory found. Common additions:

| Need | Directive change |
|---|---|
| Google Analytics / Tag Manager | `script-src ... https://www.googletagmanager.com; connect-src ... https://www.google-analytics.com https://analytics.google.com` |
| Google Fonts | `style-src ... https://fonts.googleapis.com; font-src ... https://fonts.gstatic.com` |
| Stripe | `script-src ... https://js.stripe.com; frame-src https://js.stripe.com https://hooks.stripe.com; connect-src ... https://api.stripe.com` |
| YouTube embeds | `frame-src https://www.youtube.com https://www.youtube-nocookie.com` |
| Images from S3/CloudFront or a CDN | `img-src 'self' data: https://<bucket-or-cdn-host>` |
| Inline styles from a UI framework | prefer hashes/nonces; `style-src 'unsafe-inline'` does not cap the grade but weakens the policy |
| Inline scripts you cannot remove yet | `script-src 'nonce-<random>'` per response, or `'sha256-<hash>'` per script; `'unsafe-inline'` caps the grade |
| `eval` from a legacy bundle | `'unsafe-eval'` caps the grade; fix the bundle (often a dev-mode build or old template library) |

`frame-ancestors` is the modern replacement for `X-Frame-Options`; keep both
because the scanner and older browsers still look for the header.
`frame-ancestors` cannot be used in a `<meta>` tag or in Report-Only mode in
some browsers, which is another reason to set CSP as a header.

### Rollout playbook

1. **Inventory.** Fetch the HTML of the main pages and list every external
   `src`, `href` for stylesheets/fonts, `fetch`/XHR/WebSocket endpoints,
   iframes, and inline `<script>`/`<style>` blocks. For SPAs, check the
   bundle for dynamic script injection (analytics, chat widgets, A/B tools).
2. **Report-Only first.** Ship the policy as
   `Content-Security-Policy-Report-Only` with `report-to`/`report-uri` so
   violations are logged, not enforced. Report endpoints: report-uri.com
   (Scott Helme's service, pairs with securityheaders.com), a Cloudflare
   Worker, an API Gateway + Lambda, or any HTTPS endpoint that accepts JSON
   POSTs. Note that Report-Only does not count toward the grade.
3. **Watch for a release cycle,** fix the policy, then switch the header
   name to `Content-Security-Policy`. Keep Report-Only alongside for a
   stricter candidate policy if you want to keep tightening.
4. **Nonces for inline scripts.** A nonce must be generated per response, so
   it has to be set where HTML is rendered (the app, a Lambda@Edge/CloudFront
   Function that rewrites HTML, or a Cloudflare Worker), not in a static
   response headers policy. Static sites usually use hashes instead.
5. **Never ship `default-src *`** or a policy that merely echoes "allow
   everything". It gets the green row and no protection; say so if the user
   suggests it.

## 3. X-Frame-Options

```
X-Frame-Options: DENY
```

- `DENY` unless the site legitimately frames its own pages, then
  `SAMEORIGIN`. `ALLOW-FROM` is unsupported; use CSP `frame-ancestors` for
  allow-listing specific partner origins.
- Prevents clickjacking. Sites embedded in third-party iframes (widgets,
  checkout pages, portals) need the CSP `frame-ancestors` allow-list instead
  of a blanket deny; the scanner still wants the header present.

## 4. X-Content-Type-Options

```
X-Content-Type-Options: nosniff
```

- Stops MIME sniffing, which matters for user uploads and misconfigured
  `Content-Type`. Essentially zero breakage risk, but make sure static
  assets are served with correct `Content-Type` (S3 uploads with a missing
  type become `binary/octet-stream`, and `nosniff` will then block scripts
  and styles).

## 5. Referrer-Policy

```
Referrer-Policy: strict-origin-when-cross-origin
```

- Browser default since 2020, so adopting it changes nothing for modern
  browsers while satisfying the scanner. `no-referrer` is stricter and
  breaks some analytics attribution and CSRF checks that rely on `Referer`.
  `unsafe-url` and `no-referrer-when-downgrade` are flagged as weak.

## 6. Permissions-Policy

```
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=(), interest-cohort=()
```

- Disables browser features the page does not use, for the page and any
  frames. Re-enable per feature as `geolocation=(self)` or
  `payment=(self "https://js.stripe.com")` when the site needs it.
- `interest-cohort=()` is a no-op now that FLoC is gone but still common;
  harmless to include.
- The old `Feature-Policy` header is deprecated; replace, do not duplicate.

## 7. Cross-Origin-Opener-Policy / Embedder-Policy / Resource-Policy

Not graded, listed as "upcoming". Reasonable additions:

```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
```

- COOP `same-origin` isolates the browsing context (defends against
  Spectre-style attacks and `window.opener` abuse). Breaks OAuth popups that
  rely on `window.opener`; use `same-origin-allow-popups` there.
- CORP `same-origin` stops other origins from loading your resources. If
  other sites must load your images/fonts/scripts (a CDN host, an embeddable
  widget), use `cross-origin` on those assets.
- COEP `require-corp` is the one that breaks things: every cross-origin
  resource must opt in via CORP or CORS. Only needed for `SharedArrayBuffer`
  / high-resolution timers. Default to not setting it.

## 8. Headers to remove

| Header | Why | How |
|---|---|---|
| `Server: nginx/1.x` etc. | version leak | `server_tokens off;` (nginx), `ServerTokens Prod` (Apache), ALB `routing.http.response.server.enabled=false`, Cloudflare rewrites it to `cloudflare` when proxied, CloudFront passes origin's value unless a response headers policy `RemoveHeaders` entry strips it |
| `X-Powered-By` | framework/version leak | Express `app.disable('x-powered-by')`, PHP `expose_php=Off`, ASP.NET `<httpRuntime enableVersionHeader="false"/>` plus `removeServerHeader`, or strip at the edge |
| `X-AspNet-Version`, `X-AspNetMvc-Version` | version leak | `MvcHandler.DisableMvcResponseHeader = true`, `enableVersionHeader="false"` |
| `X-XSS-Protection` | deprecated, enabled buggy filters | remove, or set `0` if a scanner elsewhere demands it |
| `Expect-CT`, `Public-Key-Pins` | dropped by browsers | remove |
| `Feature-Policy` | renamed | replace with `Permissions-Policy` |

## 9. Application-level helpers

When the edge is the wrong place (per-response CSP nonces, a site not behind
CloudFront/ALB/Cloudflare, local dev parity), set headers in the app:

- **Node/Express:** `helmet` (`app.use(helmet({ contentSecurityPolicy: {...} }))`). Helmet's defaults set all six plus COOP/CORP.
- **Next.js:** `headers()` in `next.config.js` for static values; middleware for nonces.
- **Django:** `SECURE_HSTS_SECONDS`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS`, `SECURE_REFERRER_POLICY`, plus `django-csp` or `django-permissions-policy`.
- **Rails:** `config.force_ssl` (HSTS), `config.action_dispatch.default_headers`, `content_security_policy` initializer, `permissions_policy` initializer.
- **FastAPI/Starlette:** a small middleware that sets the headers on every response; or `secure` package.
- **nginx:** `add_header ... always;` in the server block (note `add_header` in a nested `location` replaces the parent's list, so repeat them or use an `include`).
- **Apache:** `Header always set ...` in the vhost.

Remember the edge still has to pass them through: CloudFront forwards origin
response headers by default; Cloudflare does too; ALB header modification
overwrites only the headers you configure.
