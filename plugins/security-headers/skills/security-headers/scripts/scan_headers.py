#!/usr/bin/env python3
"""Scan a URL's HTTP security headers the way securityheaders.com does.

Two sources of truth, used together:

1. Local scan: fetch the URL (following redirects), inspect the final
   response headers, and compute a grade estimate using the six headers
   securityheaders.com grades. Works offline from the scanner.
2. Remote scan (default on): ask securityheaders.com for its grade via the
   website scan page (X-Grade header or HTML parse). The paid JSON API was
   discontinued in April 2026; if SECURITYHEADERS_API_KEY is set the script
   still tries api.securityheaders.com first for users with a surviving key.

Standard library only. Exit code 0 on a completed scan, 2 on fetch failure.

Usage:
  scan_headers.py https://example.com            # markdown report
  scan_headers.py https://example.com --json     # JSON to stdout
  scan_headers.py https://example.com --json --out before.json
  scan_headers.py https://example.com --no-remote
  scan_headers.py --diff before.json after.json  # compare two JSON scans
  scan_headers.py --from-file headers.txt --url https://example.com
                                                 # grade a saved `curl -D -` dump (no network)
"""

import argparse
import base64
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.client import HTTPResponse

USER_AGENT = "security-headers-skill/0.1 (+https://github.com/jon-the-dev/claude-code-plugin-marketplace-v0)"
CORE = [
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
]
UPCOMING = [
    "cross-origin-opener-policy",
    "cross-origin-embedder-policy",
    "cross-origin-resource-policy",
]
DEPRECATED = {
    "x-xss-protection": "deprecated; remove it (or set 0). Browsers dropped the filter and it caused bugs.",
    "expect-ct": "deprecated; browsers no longer honour Expect-CT. Remove it.",
    "feature-policy": "replaced by Permissions-Policy. Replace, do not duplicate.",
    "public-key-pins": "HPKP is dead and dangerous. Remove it.",
    "public-key-pins-report-only": "HPKP is dead. Remove it.",
}
LEAK_HEADERS = ["server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version", "x-generator", "x-drupal-cache"]
GRADE_BY_PRESENT = {6: "A", 5: "B", 4: "C", 3: "D", 2: "E", 1: "F", 0: "F"}
GRADE_ORDER = ["F", "E", "D", "C", "B", "A", "A+"]


# --------------------------------------------------------------------------- fetch

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _opener(insecure: bool):
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=ctx))


def fetch_chain(url: str, timeout: float, insecure: bool, max_hops: int = 10):
    """Follow redirects manually so the chain is visible. Returns (chain, final)."""
    opener = _opener(insecure)
    chain = []
    current = url
    for _ in range(max_hops):
        req = urllib.request.Request(current, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
        try:
            resp: HTTPResponse = opener.open(req, timeout=timeout)
            status = resp.status
            headers = resp.getheaders()
            body = resp.read(200_000)
        except urllib.error.HTTPError as e:
            status = e.code
            headers = e.headers.items()
            body = e.read(200_000) if hasattr(e, "read") else b""
        hop = {"url": current, "status": status, "headers": [[k, v] for k, v in headers]}
        chain.append(hop)
        location = next((v for k, v in headers if k.lower() == "location"), None)
        if status in (301, 302, 303, 307, 308) and location:
            current = urllib.parse.urljoin(current, location)
            continue
        hop["body"] = body.decode("utf-8", "replace")
        return chain, hop
    raise RuntimeError("too many redirects")


def parse_header_dump(text: str):
    """Parse a saved `curl -sS -D - ...` dump (or raw header block).

    Returns (chain, final) in the same shape fetch_chain() returns. Several
    HTTP blocks (redirects) are kept in order; the last one is the final hop.
    Lines before the first HTTP/ status line (shell prompts, commands) are
    ignored, as is anything after the first blank line following a block.
    """
    blocks = []
    cur = None
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        m = re.match(r"^HTTP/\d(?:\.\d)?\s+(\d{3})", line)
        if m:
            cur = {"status": int(m.group(1)), "headers": []}
            blocks.append(cur)
            continue
        if cur is None:
            continue
        if not line.strip():
            cur = None  # end of this block; a later HTTP/ line starts the next
            continue
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            if re.match(r"^[A-Za-z0-9-]+$", k.strip()):
                cur["headers"].append([k.strip(), v.strip()])
    if not blocks:
        # no status lines at all: treat every "Name: value" line as a header
        hdrs = []
        for raw in text.splitlines():
            line = raw.strip()
            if ":" in line:
                k, v = line.split(":", 1)
                if re.match(r"^[A-Za-z0-9-]+$", k.strip()):
                    hdrs.append([k.strip(), v.strip()])
        if not hdrs:
            raise ValueError("no HTTP status line or header lines found in the file")
        blocks = [{"status": 200, "headers": hdrs}]
    return blocks, blocks[-1]


def header_map(items):
    """lower-case name -> list of values (duplicates preserved)."""
    out = {}
    for k, v in items:
        out.setdefault(k.lower(), []).append(v.strip())
    return out


# --------------------------------------------------------------------------- analysis

def analyse(final_url: str, hmap: dict):
    https = final_url.lower().startswith("https://")
    findings = []
    warnings = []
    present = 0
    cap = None  # grade cap from CSP weakness

    def add(name, status, value, note):
        findings.append({"header": name, "status": status, "value": value, "note": note})

    # HSTS
    v = hmap.get("strict-transport-security")
    if not https:
        add("Strict-Transport-Security", "n/a", None, "scanned over HTTP; HSTS only counts on an HTTPS response")
    elif not v:
        add("Strict-Transport-Security", "missing", None, "browsers may still accept plain HTTP for this host")
    else:
        m = re.search(r"max-age\s*=\s*(\d+)", v[0], re.I)
        age = int(m.group(1)) if m else 0
        if age < 15552000:
            add("Strict-Transport-Security", "weak", v[0], f"max-age {age}s is under six months; use 31536000")
        else:
            add("Strict-Transport-Security", "ok", v[0], "")
        present += 1

    # CSP
    v = hmap.get("content-security-policy")
    ro = hmap.get("content-security-policy-report-only")
    if not v:
        note = "no enforced CSP; the only graded header that mitigates XSS"
        if ro:
            note += " (a Report-Only policy is present but does not count)"
        add("Content-Security-Policy", "missing", ro[0] if ro else None, note)
    else:
        csp = v[0]
        script_dirs = {}
        for d in csp.split(";"):
            parts = d.strip().split()
            if parts:
                script_dirs[parts[0].lower()] = " ".join(parts[1:])
        scope = script_dirs.get("script-src", script_dirs.get("default-src", ""))
        notes = []
        if "'unsafe-inline'" in scope and "'nonce-" not in scope and "'sha256-" not in scope and "'strict-dynamic'" not in scope:
            notes.append("'unsafe-inline' in script scope caps the grade and defeats XSS protection; move to nonces/hashes")
            cap = "A"
        if "'unsafe-eval'" in scope:
            notes.append("'unsafe-eval' in script scope caps the grade")
            cap = "A"
        if scope.strip() in ("*", "") and "default-src" in script_dirs and script_dirs["default-src"].strip() == "*":
            notes.append("policy allows every origin; it earns the row but protects nothing")
        if "frame-ancestors" not in script_dirs:
            notes.append("consider adding frame-ancestors (modern clickjacking control)")
        add("Content-Security-Policy", "weak" if cap else "ok", csp, "; ".join(notes))
        present += 1

    # XFO
    v = hmap.get("x-frame-options")
    if not v:
        add("X-Frame-Options", "missing", None, "page can be framed (clickjacking)")
    else:
        val = v[0].upper()
        if val in ("DENY", "SAMEORIGIN"):
            add("X-Frame-Options", "ok", v[0], "")
        else:
            add("X-Frame-Options", "weak", v[0], "only DENY or SAMEORIGIN are honoured; ALLOW-FROM is obsolete (use CSP frame-ancestors)")
        present += 1

    # XCTO
    v = hmap.get("x-content-type-options")
    if not v:
        add("X-Content-Type-Options", "missing", None, "browsers may MIME-sniff responses")
    else:
        if v[0].lower() == "nosniff":
            add("X-Content-Type-Options", "ok", v[0], "")
        else:
            add("X-Content-Type-Options", "weak", v[0], "value must be nosniff")
        present += 1

    # Referrer-Policy
    v = hmap.get("referrer-policy")
    if not v:
        add("Referrer-Policy", "missing", None, "full URLs may leak in Referer to third parties")
    else:
        val = v[0].lower()
        if "unsafe-url" in val or val == "no-referrer-when-downgrade":
            add("Referrer-Policy", "weak", v[0], "weak policy; use strict-origin-when-cross-origin")
        else:
            add("Referrer-Policy", "ok", v[0], "")
        present += 1

    # Permissions-Policy
    v = hmap.get("permissions-policy")
    if not v:
        note = "browser features (camera, mic, geolocation...) not restricted"
        if hmap.get("feature-policy"):
            note += " (legacy Feature-Policy present; rename it)"
        add("Permissions-Policy", "missing", None, note)
    else:
        add("Permissions-Policy", "ok", v[0], "")
        present += 1

    # duplicates
    for name in CORE:
        if len(hmap.get(name, [])) > 1:
            warnings.append(f"{name} appears {len(hmap[name])} times (set in more than one layer?)")

    # leaks
    for name in LEAK_HEADERS:
        for val in hmap.get(name, []):
            if name == "server" and val.lower() in ("cloudflare", "amazons3", "awselb/2.0", "nginx", "apache", "", "github.com", "vercel", "netlify"):
                continue
            if name == "server" and not re.search(r"\d", val):
                continue
            warnings.append(f"{name}: {val} (information leak; remove the version or the header)")

    # deprecated
    for name, why in DEPRECATED.items():
        if name in hmap:
            warnings.append(f"{name}: {hmap[name][0]} ({why})")

    upcoming = {n: hmap.get(n, [None])[0] for n in UPCOMING}

    grade = GRADE_BY_PRESENT[present]
    if present == 6 and cap is None and not any(f["status"] == "weak" for f in findings):
        grade = "A+"
    if cap and GRADE_ORDER.index(grade) > GRADE_ORDER.index(cap):
        grade = cap

    return {
        "grade_estimate": grade,
        "core_present": present,
        "grade_cap": cap,
        "findings": findings,
        "warnings": warnings,
        "upcoming": upcoming,
        "https": https,
    }


# --------------------------------------------------------------------------- remote

def remote_grade(url: str, timeout: float):
    """Ask securityheaders.com. Returns dict with source/grade/missing/error."""
    key = os.environ.get("SECURITYHEADERS_API_KEY")
    q = urllib.parse.quote(url, safe="")
    opener = urllib.request.build_opener()  # follow redirects here
    if key:
        api = f"https://api.securityheaders.com/?q={q}&hide=on&followRedirects=on"
        req = urllib.request.Request(api, headers={"x-api-key": key, "User-Agent": USER_AGENT})
        try:
            with opener.open(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
            summary = data.get("summary", {})
            return {
                "source": "api.securityheaders.com (legacy key)",
                "grade": summary.get("grade"),
                "grade_cap": summary.get("gradeCap"),
                "missing": [h for h, c in summary.get("headers", {}).items() if str(c).lower() == "red"],
                "scanned_url": summary.get("site"),
            }
        except Exception as e:  # fall through to the website
            api_err = f"{type(e).__name__}: {e}"
    else:
        api_err = None

    page = f"https://securityheaders.com/?q={q}&hide=on&followRedirects=on"
    req = urllib.request.Request(page, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    try:
        with opener.open(req, timeout=timeout) as r:
            hdrs = {k.lower(): v for k, v in r.getheaders()}
            html = r.read(2_000_000).decode("utf-8", "replace")
    except Exception as e:
        return {"source": "securityheaders.com", "grade": None, "error": f"{type(e).__name__}: {e}", "api_error": api_err, "scan_link": page}

    out = {"source": "securityheaders.com", "scan_link": page, "api_error": api_err}
    grade = hdrs.get("x-grade")
    if not grade:
        m = re.search(r'class="score[^"]*"[^>]*>\s*<span>\s*([A-FR][+-]?)\s*</span>', html, re.I)
        grade = m.group(1) if m else None
    if hdrs.get("x-score"):
        try:
            out["x_score"] = json.loads(base64.b64decode(hdrs["x-score"]).decode("utf-8", "replace"))
        except Exception:
            pass
    out["grade"] = grade
    missing = re.findall(r'table_red"[^>]*>\s*([A-Za-z-]+)\s*<', html)
    if missing:
        out["missing"] = sorted(set(missing))
    m = re.search(r'Site:\s*</th>\s*<td[^>]*>\s*(?:<a[^>]*>)?\s*([^<\s]+)', html)
    if m:
        out["scanned_url"] = m.group(1)
    if grade is None:
        out["error"] = "page fetched but no grade found (markup changed?); open scan_link to read it"
    return out


# --------------------------------------------------------------------------- output

def to_markdown(result: dict) -> str:
    a = result["analysis"]
    r = result.get("remote") or {}
    lines = [f"# Security headers scan: {result['final_url']}", ""]
    if r.get("grade"):
        lines.append(f"**securityheaders.com grade: {r['grade']}**" + (f" (capped at {r['grade_cap']})" if r.get("grade_cap") else ""))
        if r.get("scanned_url"):
            lines.append(f"Scanned URL per scanner: {r['scanned_url']}")
    elif r:
        lines.append(f"securityheaders.com: unavailable ({r.get('error', 'unknown')}). Open {r.get('scan_link', '')} to confirm.")
    lines.append(f"**Local grade estimate: {a['grade_estimate']}** ({a['core_present']}/6 core headers present" + (f", capped at {a['grade_cap']} by CSP" if a["grade_cap"] else "") + ")")
    lines.append("")
    if len(result["chain"]) > 1:
        lines.append("Redirect chain: " + " -> ".join(f"{h['url']} [{h['status']}]" for h in result["chain"]))
        lines.append("")
    lines.append("| Header | Status | Value | Note |")
    lines.append("|---|---|---|---|")
    for f in a["findings"]:
        val = (f["value"] or "")
        if len(val) > 120:
            val = val[:117] + "..."
        val = val.replace("|", "\\|")
        lines.append(f"| {f['header']} | {f['status']} | `{val}` | {f['note']} |" if val else f"| {f['header']} | {f['status']} |  | {f['note']} |")
    lines.append("")
    if a["warnings"]:
        lines.append("## Warnings")
        lines += [f"- {w}" for w in a["warnings"]]
        lines.append("")
    up = [f"{k}: {v}" for k, v in a["upcoming"].items() if v]
    lines.append("## Upcoming headers (not graded)")
    lines.append("- " + ("; ".join(up) if up else "none of Cross-Origin-Opener-Policy / Embedder-Policy / Resource-Policy present"))
    lines.append("")
    lines.append("## Fingerprint (which layer built this response)")
    fp = []
    hm = header_map(result["chain"][-1]["headers"])
    for name in ("server", "via", "x-cache", "x-amz-cf-id", "x-amz-cf-pop", "cf-ray", "cf-cache-status", "x-amzn-requestid", "x-amz-apigw-id", "x-amzn-trace-id", "x-vercel-id", "x-powered-by"):
        if name in hm:
            fp.append(f"{name}: {hm[name][0]}")
    lines.append("- " + ("; ".join(fp) if fp else "no CDN/load balancer fingerprint headers seen"))
    lines.append("")
    lines.append("## Raw response headers (final hop)")
    lines.append("```")
    lines += [f"{k}: {v}" for k, v in result["chain"][-1]["headers"]]
    lines.append("```")
    return "\n".join(lines)


def diff(before: dict, after: dict) -> str:
    b, a = before["analysis"], after["analysis"]
    lines = [f"# Before/after: {after['final_url']}", ""]
    rb = (before.get("remote") or {}).get("grade")
    ra = (after.get("remote") or {}).get("grade")
    lines.append(f"securityheaders.com grade: {rb or '?'} -> {ra or '?'}")
    lines.append(f"local estimate: {b['grade_estimate']} -> {a['grade_estimate']}")
    lines.append("")
    lines.append("| Header | Before | After |")
    lines.append("|---|---|---|")
    bf = {f["header"]: f for f in b["findings"]}
    for f in a["findings"]:
        o = bf.get(f["header"], {})
        marker = "" if o.get("status") == f["status"] else " **changed**"
        lines.append(f"| {f['header']} | {o.get('status', '?')} | {f['status']}{marker} |")
    gone = [w for w in b["warnings"] if w not in a["warnings"]]
    new = [w for w in a["warnings"] if w not in b["warnings"]]
    if gone:
        lines += ["", "Warnings resolved:"] + [f"- {w}" for w in gone]
    if new:
        lines += ["", "New warnings:"] + [f"- {w}" for w in new]
    return "\n".join(lines)


# --------------------------------------------------------------------------- main

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("url_from_pos", nargs="?", metavar="url", help="URL or hostname to scan (https:// assumed if no scheme)")
    p.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    p.add_argument("--out", help="also write the JSON result to this file")
    p.add_argument("--no-remote", action="store_true", help="skip securityheaders.com; local analysis only")
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument("--insecure", action="store_true", help="do not verify TLS on the target (staging certs)")
    p.add_argument("--diff", nargs=2, metavar=("BEFORE_JSON", "AFTER_JSON"), help="compare two saved JSON scans and exit")
    p.add_argument("--from-file", metavar="HEADERS_TXT", help="grade a saved `curl -D -` header dump instead of fetching; implies --no-remote")
    p.add_argument("--url", help="with --from-file: the URL the dump came from (decides whether HSTS counts; defaults to https://<unknown>)")
    args = p.parse_args(argv)

    if args.diff:
        with open(args.diff[0]) as f1, open(args.diff[1]) as f2:
            print(diff(json.load(f1), json.load(f2)))
        return 0
    if args.from_file:
        label = args.url or args.url_from_pos or "https://unknown.invalid/"
        url = label if re.match(r"^https?://", label, re.I) else "https://" + label
        try:
            with open(args.from_file, errors="replace") as fh:
                chain, final = parse_header_dump(fh.read())
        except Exception as e:
            sys.stderr.write(f"could not parse {args.from_file}: {type(e).__name__}: {e}\n")
            return 2
        for i, hop in enumerate(chain):
            hop["url"] = url if i == len(chain) - 1 else f"{url} (hop {i + 1})"
        args.no_remote = True
    else:
        if not args.url_from_pos:
            p.error("url is required unless --diff or --from-file is used")
        url = args.url_from_pos if re.match(r"^https?://", args.url_from_pos, re.I) else "https://" + args.url_from_pos
        try:
            chain, final = fetch_chain(url, args.timeout, args.insecure)
        except Exception as e:
            sys.stderr.write(f"fetch failed for {url}: {type(e).__name__}: {e}\n")
            return 2

    hmap = header_map(final["headers"])
    result = {
        "requested_url": url,
        "final_url": final["url"],
        "status": final["status"],
        "chain": [{k: v for k, v in h.items() if k != "body"} for h in chain],
        "analysis": analyse(final["url"], hmap),
        "remote": None if args.no_remote else remote_grade(url, args.timeout),
        "source": "file:" + args.from_file if args.from_file else "live",
    }

    if args.out:
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(to_markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
