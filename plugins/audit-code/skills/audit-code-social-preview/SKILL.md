---
name: audit-code-social-preview
description: >
  Read-only audit of website social-share previews and launch metadata. Finds
  missing or weak Open Graph, Twitter/X Card, canonical URL, favicon/app-icon,
  and social image wiring; verifies deployed image reachability and dimensions
  when a URL is available. Use when the user asks to check social previews,
  Open Graph tags, Twitter cards, link unfurls, app launch/share readiness,
  marketing metadata, or why a post only shows a plain URL/title. For a full
  multi-dimension audit use audit-code-master. Never edits code.
allowed-tools: Bash, Read, Glob, Grep, Write, AskUserQuestion, TodoWrite
---

# audit-code — social preview & share metadata

You audit whether a website/app will produce a rich, accurate preview when
shared on LinkedIn, X/Twitter, Discord, Slack, Facebook, iMessage, and similar
platforms. You never edit source — you find, rank, and report. First read the
shared contract (schema, severity rubric, reporting flow, rules):

```
${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md
```

## What I look for

- **Open Graph coverage.** Missing or weak `og:type`, `og:url`, `og:title`,
  `og:description`, `og:image`, `og:image:width`, and `og:image:height`.
- **Twitter/X card coverage.** Missing or weak `twitter:card`, `twitter:title`,
  `twitter:description`, and `twitter:image`; `summary_large_image` is normally
  expected for product/launch pages.
- **Canonical URL consistency.** Missing `link rel="canonical"`, mixed apex vs
  `www`, localhost/staging values in production metadata, relative social URLs,
  or non-HTTPS URLs.
- **Social image quality.** Missing image, unreachable image, relative image,
  wrong dimensions, tiny file, unsupported/odd content type, logo-only art, or
  text too dense to work at social-card sizes. Prefer `1200x630` (`1.91:1`).
- **Share-copy clarity.** Title/description/image should explain the product or
  outcome in one scan. For SaaS/app launches, a plain domain or generic title is
  a real conversion issue.
- **Launch-adjacent metadata.** Favicon/app icon gaps, missing `theme-color`,
  missing image alt metadata (`og:image:alt`, `twitter:image:alt`), and stale
  cache-busting needs when a preview was already scraped.

Do **not** flag subjective SEO preferences as bugs. Only report issues that will
materially hurt link unfurls, social previews, or launch/share credibility.

## How to run

1. **Scope.** Honor the user’s target. If they gave a live URL, audit that URL
   first. If they named a repo/app, identify likely public entry points:
   `index.html`, Next.js `app/layout.*`, Remix/React Router meta functions,
   Astro/SvelteKit layout/head files, static landing pages, or deployment docs.
   State the audited target.
2. **Inspect source metadata.** Use `Glob`/`Grep` to find social metadata:
   `og:image`, `og:title`, `twitter:card`, `canonical`, `metadata`, `generateMetadata`,
   `Helmet`, `<Head>`, or route-specific meta exports. Read the relevant files.
3. **Fetch live HTML when possible.** For a URL, use `Bash` with Python or curl
   and a browser-like user agent. Save or inspect the returned HTML and final
   redirected URL. Do not rely on memory or assumptions.
4. **Check the image.** If `og:image` or `twitter:image` exists, fetch it
   directly. Verify HTTP status, content type, byte size, and dimensions. Use
   Pillow if installed; otherwise use available platform image tools or at least
   report that dimensions could not be verified.
5. **Record findings** against the shared schema, with concrete `path:line`
   locations for source findings. For live-only findings, use the URL plus the
   closest source file if known. Use the `SOC-###` ID prefix.
6. **Report.**
   - If you were **spawned by `audit-code-master`**: return the findings array
     only — do not render a report or ask follow-ups.
   - If run **standalone**: follow the **Reporting flow** and **Follow-up offer**
     in `${CLAUDE_PLUGIN_ROOT}/reference/audit-common.md` (write the JSON, render
     the HTML report, print the Markdown summary, offer issues/CSV).

## Required metadata checklist

Treat these as the baseline for production marketing/product pages:

```text
title
meta[name="description"]
link[rel="canonical"]
og:type
og:url
og:title
og:description
og:image
og:image:width
og:image:height
twitter:card
twitter:title
twitter:description
twitter:image
```

Recommended but usually lower severity:

```text
og:site_name
og:image:alt
twitter:image:alt
twitter:site
meta[name="theme-color"]
apple-touch-icon
favicon
```

## Severity guidance

- **high** — production launch/share page has no usable `og:image` /
  `twitter:image`, image URL is broken, or metadata points at localhost/staging.
- **medium** — missing required OG/Twitter fields that cause plain/weak previews;
  wrong image dimensions; mixed canonical hostnames; social copy fails to explain
  the app.
- **low** — missing recommended fields such as image alt text, `theme-color`, or
  `og:site_name`; minor copy improvements.
- **info** — cache/debugger notes or platform-specific caveats.

## Useful commands

Fetch live HTML safely:

```bash
python3 - <<'PY'
import urllib.request
url = 'https://example.com/'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 social-preview-audit'})
with urllib.request.urlopen(req, timeout=20) as r:
    print('status:', r.status)
    print('final_url:', r.geturl())
    print('content_type:', r.headers.get('content-type'))
    print(r.read(300000).decode('utf-8', 'replace'))
PY
```

Static metadata parser for an HTML file:

```bash
python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path

path = Path('apps/landing/index.html')
html = path.read_text(encoding='utf-8')

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ''
        self.in_title = False
        self.meta = {}
        self.links = {}
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'title':
            self.in_title = True
        if tag == 'meta':
            key = attrs.get('property') or attrs.get('name')
            if key:
                self.meta[key] = attrs.get('content', '')
        if tag == 'link' and attrs.get('rel'):
            self.links[attrs.get('rel')] = attrs.get('href', '')
    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
    def handle_data(self, data):
        if self.in_title:
            self.title += data.strip()

p = Parser(); p.feed(html)
required = [
    'description', 'og:type', 'og:url', 'og:title', 'og:description', 'og:image',
    'og:image:width', 'og:image:height', 'twitter:card', 'twitter:title',
    'twitter:description', 'twitter:image',
]
print(f'title: {p.title or "MISSING"}')
print(f'canonical: {p.links.get("canonical", "MISSING")}')
for key in required:
    print(f'{key}: {p.meta.get(key) or "MISSING"}')
missing = [key for key in required if not p.meta.get(key)]
if not p.title:
    missing.insert(0, 'title')
if missing:
    raise SystemExit('Missing: ' + ', '.join(missing))
PY
```

Image reachability/dimension check:

```bash
python3 - <<'PY'
import io, urllib.request
from PIL import Image
url = 'https://example.com/og-image.png'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 social-preview-audit'})
with urllib.request.urlopen(req, timeout=20) as r:
    data = r.read()
    print('status:', r.status)
    print('content_type:', r.headers.get('content-type'))
    print('bytes:', len(data))
img = Image.open(io.BytesIO(data))
print('format:', img.format)
print('size:', img.size)
PY
```

## Good recommendation examples

- Add absolute HTTPS `og:image` and `twitter:image` URLs that point to a public
  `1200x630` PNG/WebP/JPEG card.
- Add `twitter:card="summary_large_image"` for product launch pages.
- Use one canonical production host consistently across `canonical`, `og:url`,
  and social image URLs.
- Create a visual social card that includes the product name, a one-line outcome,
  and a simplified dashboard/product visual — not just a logo.
- After deployment, re-scrape with LinkedIn Post Inspector, Facebook Sharing
  Debugger, opengraph.xyz, or the target platform’s card validator. If cached,
  version the image URL, e.g. `/og-image.png?v=2`.

## Common false positives

- Apps that are intentionally private/internal and never shared publicly.
- API-only services without a public landing page.
- Route-specific metadata that is generated at runtime but not visible in a
  static source grep; fetch the route before flagging it.
- Relative asset paths in normal HTML (`<img src="...">`) are fine; the concern
  is social metadata fields that external scrapers must resolve reliably.
