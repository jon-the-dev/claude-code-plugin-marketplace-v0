# How securityheaders.com grades, and how to read its output

## Status of the service (as of late 2026)

- **Website scanner: working, free.** `https://securityheaders.com/?q=<url>&followRedirects=on`
  scans one URL and renders an HTML report. Adding `&hide=on` keeps the scan
  off the public "recent scans" list, which matters for internal hosts.
- **Paid JSON API: discontinued.** `api.securityheaders.com` (authenticated
  with an `x-api-key` header, parameters `q`, `hide`, `followRedirects`)
  stopped taking new keys and was shut down in April 2026. If the user still
  has a key that works, `scan_headers.py` will use it when
  `SECURITYHEADERS_API_KEY` is set, but do not design anything around it.
- **Grade without parsing HTML.** Historically the website returned the
  grade in an `X-Grade` response header on the scan page (and a base64 JSON
  blob in `X-Score`). The script reads `X-Grade` when present and falls back
  to parsing the HTML. If both fail, treat the remote grade as unknown and
  use the local estimate.

Do not scrape securityheaders.com in a loop. One scan per URL per change is
plenty; the service is free and rate-limits abusive clients.

## What is graded

Six headers decide the letter grade. securityheaders.com shows each as a
green (present and sane), yellow/orange (present but weak), or red (missing)
row:

| Header | What "green" needs |
|---|---|
| `Strict-Transport-Security` | present on an HTTPS response, sensible `max-age` (the scanner only sees it over HTTPS) |
| `Content-Security-Policy` | present; `'unsafe-inline'`/`'unsafe-eval'` in `script-src` or `default-src` trigger a warning and a **grade cap** (the old API exposed this as `gradeCap`), so a site can have all six headers and still not get A+ |
| `X-Frame-Options` | `DENY` or `SAMEORIGIN` (`ALLOW-FROM` is obsolete). A CSP `frame-ancestors` directive is the modern replacement, but the scanner still expects the header |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | any policy except `unsafe-url`; `no-referrer-when-downgrade` is flagged as weak |
| `Permissions-Policy` | present (the scanner does not deeply validate the directive list) |

Rule of thumb for the letter grade: all six present and sane gives an **A**,
with **A+** when CSP is present without a cap-triggering directive and
nothing else is flagged. Each missing core header costs roughly one letter.
Warnings (below) do not move the letter on their own but do stop A+.
Treat this as the behaviour observed on real scans, not a published formula:
the live scan is the authority, and the local estimate in `scan_headers.py`
exists for environments that cannot reach the site.

## Warnings and "upcoming" headers

Shown below the graded table. They do not change the letter but the scanner
calls them out, and users notice them:

- **Information leakage:** `Server` with a product/version (`nginx/1.18.0`,
  `Apache/2.4.41`, `Microsoft-IIS/10.0`), `X-Powered-By`, `X-AspNet-Version`,
  `X-AspNetMvc-Version`. A bare `Server: cloudflare` or `Server: AmazonS3` is
  reported but is not a version leak.
- **Deprecated headers:** `X-XSS-Protection` (recommend removing it, or `0`;
  it enabled buggy browser filters), `Expect-CT` (browsers dropped it),
  `Feature-Policy` (renamed to `Permissions-Policy`), `Public-Key-Pins`.
- **Upcoming / "additional" headers:** `Cross-Origin-Opener-Policy`,
  `Cross-Origin-Embedder-Policy`, `Cross-Origin-Resource-Policy`. The
  scanner suggests them (often in report-only form first) but does not grade
  them. Worth adding on sites without third-party embeds; COEP in particular
  breaks pages that load cross-origin resources without CORP/CORS headers.
- **Raw headers:** the report lists every response header it saw. Use that
  list to spot duplicates (two `Strict-Transport-Security` lines from two
  layers) and cache-layer fingerprints (`via`, `x-cache`, `cf-ray`) that tell
  you where the response is really assembled.

## Reading a scan that disagrees with your fix

- **Fix applied, grade unchanged:** the scanner follows redirects, so it may
  have graded `https://www.` while you changed the apex, or vice versa. Check
  the "scanned URL" the report shows. CloudFront also serves cached
  responses without re-running a newly attached response headers policy
  until the object expires or is invalidated.
- **Header present on origin, missing on scan:** the edge (CloudFront
  behavior without the policy, Cloudflare rule with a non-matching
  expression, ALB listener on the wrong port) is not passing or adding it.
- **Grade capped at A despite six green rows:** CSP contains
  `'unsafe-inline'` or `'unsafe-eval'` in a script-controlling directive.
  Move to nonces/hashes, or accept the cap and say so.
- **HSTS shows missing on an HTTP URL:** expected. HSTS is ignored over HTTP
  and the scanner reports it only on HTTPS responses. Scan the HTTPS URL.
