#!/usr/bin/env python3
"""tashan site test suite — structure, load budgets, SEO/AEO, CSP.

Runs against the built web/ tree (static checks) and, if a server is reachable,
against live HTTP (waterfall + status codes). Dependency-free (stdlib only).

    python3 tests/test_site.py                 # static + live (auto-detects :4173)
    python3 tests/test_site.py --url http://127.0.0.1:4173
    python3 tests/test_site.py --static-only   # no server needed

Exit code is the number of failed checks (0 = all green), so it drops into CI.
"""
import argparse, glob, gzip, json, os, re, sys, time
import http.client
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")

# --- budgets (the numbers a "snappy" static store must hold) ---
CAP_HTML_MAX = 20 * 1024        # a prerendered detail page, gzipped-off
# Slim board index, gzipped (what prod ships). Raised 45 -> 55 KB on 31 Jul 2026 to carry `label`,
# the human name, because the board was rendering npm coordinates: "@supabase/mcp-server-supabase"
# headlining a row whose second line was "pkg:@supabase/mcp-server-supabase". Costed the alternatives
# first — deriving the label client-side saves only 4.5 KB because half the rows need the whole-corpus
# view anyway, and dropping the raw `name` breaks CLI search for the 1,064 rows with no npm package,
# where it is the only coordinate they have. +6.5 KB gz is ~50ms on slow 3G for a board a person can
# read. Do not spend the rest of this headroom without measuring what it buys.
INDEX_JSON_GZ_MAX = 55 * 1024
PAGE_TTFB_MAX = 0.20            # seconds, local server
NO_RUNTIME_BIG_EXPORT = "capabilities.json"  # must never be fetched at runtime

results = []  # (ok, name, detail)

# THE URL WE DECLARE MUST BE THE URL THAT IS SERVED. Cloudflare Pages serves an uploaded `foo.html`
# at `/foo` and 308-redirects `/foo.html`. Every canonical, og:url and sitemap entry we emitted ended
# in `.html`, so all 5,874 indexed URLs named a redirect — a conflicting signal to exactly the
# crawlers this project's distribution depends on. Caught only by deploying and curling the result.
def _check_declared_urls():
    import glob as _g
    bad_canon, bad_loc = [], []
    for f in (_g.glob(os.path.join(WEB, "*.html")) + _g.glob(os.path.join(WEB, "category", "*.html"))
              + _g.glob(os.path.join(WEB, "capability", "*.html"))[:200]):
        src = open(f, encoding="utf-8").read()
        for m in re.finditer(r'(?:rel="canonical" href|property="og:url" content)="([^"]+)"', src):
            if m.group(1).endswith(".html"):
                bad_canon.append(os.path.basename(f))
                break
    sm = os.path.join(WEB, "sitemap.xml")
    if os.path.exists(sm):
        bad_loc = [u for u in re.findall(r"<loc>([^<]+)</loc>", open(sm, encoding="utf-8").read())
                   if u.endswith(".html")]
    results.append((not bad_canon,
                    "no canonical/og:url ends in .html (Pages 308s those to the clean URL)",
                    f"{len(bad_canon)} page(s), e.g. {bad_canon[:3]}"))
    results.append((not bad_loc, "no sitemap <loc> ends in .html",
                    f"{len(bad_loc)} URL(s), e.g. {bad_loc[:2]}"))


_check_declared_urls()
def check(name, ok, detail=""):
    results.append((bool(ok), name, detail))
    print(("  ok  " if ok else " FAIL ") + name + (("  — " + detail) if detail and not ok else ""))
    return ok

def slugify(cid):
    return re.sub(r"[^a-z0-9]+", "-", cid.lower()).strip("-")

# ---------------------------------------------------------------- static checks
def load_board():
    d = json.load(open(os.path.join(WEB, "data", "index.json")))
    return d["capabilities"] if isinstance(d, dict) else d

def page_slugs():
    return {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(WEB, "capability", "*.html"))}

def read_island(path):
    m = re.search(r'id="cap-data">(.*?)</script>', open(path, encoding="utf-8").read(), re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))["c"] if m else None

def static_checks():
    print("\n# structure")
    board = load_board()
    have = page_slugs()
    want = {slugify(r["id"]) for r in board}

    # 1. every board row has a real page — no 404 on click (the bug we just fixed).
    # The slim index no longer SHIPS `slug`: it is exactly slugify(id), and a second copy of every id
    # cost ~9 KB gz of a 45 KB budget. The board derives it in JS, so this now also proves the derived
    # form still lands on a real file.
    missing = [s for s in want if s not in have]
    check("every board row has a prerendered page", not missing,
          f"{len(missing)} rows 404 e.g. {missing[:3]}")

    # 1b. the JS derivation must stay byte-identical to slugify() — if it drifts, EVERY listing 404s
    # at once, and nothing else in this suite would notice because both sides here are Python.
    JS_SLUG = '.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")'
    for f in ("index.js", "terminal.js"):
        src = open(os.path.join(WEB, "js", f), encoding="utf-8").read()
        check(f"js/{f} derives the slug exactly as build.py slugify()", JS_SLUG in src,
              "capHref no longer matches — listings would 404")

    # 2. no orphan pages. NOTE: "board" here is the SLIM index (the interactive leaderboard, capped for
    # download weight). Pages are generated from the BULK export, which is deliberately larger — static
    # HTML has no payload budget, so capping it was throwing away 3,148 scored capabilities that had
    # nowhere to live. The real invariant is pages == bulk export, not pages == board.
    bulk = json.load(open(os.path.join(WEB, "data", "capabilities.json")))
    want = {slugify(c["id"]) for c in bulk["capabilities"]}
    orphans = have - want
    check("no orphan pages (board == prerendered set)", not orphans,
          f"{len(orphans)} orphans e.g. {sorted(orphans)[:3]}")

    # 3. ONE catalog: a row either carries a trust score, or is explicitly marked unrated. What must never
    # happen is a row with no score and no explanation — that reads as a bug or a hidden zero. (This test
    # used to assert every row had a score, which was true only while the catalog held one artifact type.)
    unexplained = [r["id"] for r in board
                   if r.get("tashan_score") is None and r.get("rated") is not False]
    check("every unrated row is explicitly marked unrated", not unexplained,
          f"{len(unexplained)} rows with no trust and no rated=false")
    rated = [r for r in board if r.get("tashan_score") is not None]
    check("the catalog still has a rated core", len(rated) >= 500, f"only {len(rated)} rated")

    # 4. co-use links resolve to real pages (no slow legacy route, no 404)
    broken = 0; total = 0
    for p in glob.glob(os.path.join(WEB, "capability", "*.html")):
        c = read_island(p)
        if not c:
            continue
        for x in (c.get("co_used") or []):
            total += 1
            if slugify(x["id"]) not in have:
                broken += 1
    check(f"all {total} co-use links resolve to a page", broken == 0, f"{broken} broken")

    print("\n# no runtime fetch of the 1.2 MB export")
    # 5. no JS fetches the full export at runtime (only the slim index / inline island)
    offenders = []
    for jsf in glob.glob(os.path.join(WEB, "js", "*.js")):
        for ln in open(jsf, encoding="utf-8"):
            if "fetch(" in ln and NO_RUNTIME_BIG_EXPORT in ln:
                offenders.append(os.path.basename(jsf))
    check("no JS fetch()es capabilities.json", not offenders, f"in {offenders}")

    # 6. legacy ?id= path redirects instead of fetching, AND never redirects to itself (the reload-loop guard)
    capjs = open(os.path.join(WEB, "js", "capability.js"), encoding="utf-8").read()
    check("legacy ?id= route redirects to the prerendered page",
          '"/capability/" + slug(id)' in capjs and "location.replace(target)" in capjs)
    check("redirect guards against self-redirect (no reload loop)",
          "target !== location.pathname" in capjs)

    print("\n# load budgets")
    # 7. detail page HTML weight
    sizes = [(os.path.getsize(p), p) for p in glob.glob(os.path.join(WEB, "capability", "*.html"))]
    biggest = max(sizes)
    check(f"largest detail page <= {CAP_HTML_MAX//1024} KB",
          biggest[0] <= CAP_HTML_MAX,
          f"{biggest[0]//1024} KB — {os.path.basename(biggest[1])}")

    # 8. slim index gzipped weight (what prod actually ships)
    raw = open(os.path.join(WEB, "data", "index.json"), "rb").read()
    gz = len(gzip.compress(raw))
    check(f"index.json <= {INDEX_JSON_GZ_MAX//1024} KB gzipped",
          gz <= INDEX_JSON_GZ_MAX, f"{gz//1024} KB gz / {len(raw)//1024} KB raw")

    print("\n# SEO / AEO (every detail page must be indexable + citable)")
    sample = sorted(glob.glob(os.path.join(WEB, "capability", "*.html")))
    # spot-check a spread of 40 pages for the full head contract
    step = max(1, len(sample) // 40)
    need = {
        "<title>": lambda h: "<title>" in h and "tashan" in h[h.find("<title>"):h.find("</title>")+40],
        'meta description': lambda h: 'name="description"' in h,
        "canonical": lambda h: 'rel="canonical"' in h,
        "og:title": lambda h: 'property="og:title"' in h,
        "JSON-LD SoftwareApplication": lambda h: '"SoftwareApplication"' in h,
        "inline cap-data island": lambda h: 'id="cap-data"' in h,
    }
    fails = {k: [] for k in need}
    ldbad = []
    for p in sample[::step]:
        h = open(p, encoding="utf-8").read()
        for k, fn in need.items():
            if not fn(h):
                fails[k].append(os.path.basename(p))
        # every ld+json block must parse
        for m in re.finditer(r'application/ld\+json">(.*?)</script>', h, re.S):
            try:
                json.loads(m.group(1))
            except Exception:
                ldbad.append(os.path.basename(p))
    for k in need:
        check(f"detail pages have {k}", not fails[k], f"{len(fails[k])} missing e.g. {fails[k][:2]}")
    check("all JSON-LD blocks parse", not ldbad, f"bad in {ldbad[:2]}")

    # 9. home page structured data
    home = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()
    check("home has Organization + WebSite JSON-LD",
          '"Organization"' in home and '"WebSite"' in home)

    print("\n# sitemap")
    sm = open(os.path.join(WEB, "sitemap.xml"), encoding="utf-8").read()
    locs = set(re.findall(r"<loc>https://tashan\.sh(/capability/[^<]+)</loc>", sm))
    # The sitemap now declares CLEAN urls (Pages 308s the .html form), so strip the extension only
    # if it is still there rather than blindly chopping five characters off every slug.
    sm_slugs = {u.rsplit("/", 1)[-1].removesuffix(".html") for u in locs}
    check("sitemap lists exactly the prerendered pages", sm_slugs == have,
          f"sitemap {len(sm_slugs)} vs pages {len(have)}")

    print("\n# CSP / security headers")
    hdr = open(os.path.join(WEB, "_headers"), encoding="utf-8").read()
    for token in ["default-src 'self'", "form-action 'none'", "frame-ancestors 'none'", "X-Content-Type-Options: nosniff"]:
        check(f"_headers sets {token}", token in hdr)
    # no executable inline <script> in prerendered pages (only type=application/json + ld+json allowed under strict CSP)
    bad_inline = []
    for p in sample[::step]:
        h = open(p, encoding="utf-8").read()
        for m in re.finditer(r"<script([^>]*)>", h):
            attrs = m.group(1)
            if "src=" in attrs:
                continue
            if 'type="application/json"' in attrs or 'type="application/ld+json"' in attrs:
                continue
            bad_inline.append(os.path.basename(p))
            break
    check("no CSP-violating inline <script> in detail pages", not bad_inline, f"in {bad_inline[:2]}")

    print("\n# board navigation (must survive: rows are the primary board→detail path + crawlable links)")
    ijs = open(os.path.join(WEB, "js", "index.js"), encoding="utf-8").read()
    check("board rows carry a real <a> link to the detail page (crawlable, no-JS)",
          'class="cap__link" href="' in ijs)
    check("board wires whole-row click navigation", "rowsEl.onclick" in ijs and "getAttribute(\"data-href\")" in ijs)

    print("\n# analytics (first-party, cookieless, CSP-clean)")
    sjs = open(os.path.join(WEB, "js", "site.js"), encoding="utf-8").read()
    check("analytics beacons to same-origin /api/e", '"/api/e"' in sjs and "sendBeacon" in sjs)
    check("analytics honors Do-Not-Track / GPC", "doNotTrack" in sjs and "globalPrivacyControl" in sjs)
    check("analytics sets no cookie / localStorage", "document.cookie" not in sjs and "localStorage." not in sjs)
    check("window.t.track hook exposed for custom events", "window.t" in sjs and "track" in sjs)
    check("connect-src 'self' covers the beacon (no CSP change)", "connect-src 'self'" in hdr)
    ejs = os.path.join(ROOT, "functions", "api", "e.js")
    check("collector Function exists", os.path.exists(ejs))
    if os.path.exists(ejs):
        e = open(ejs, encoding="utf-8").read()
        check("collector exports toDataPoint + onRequestPost", "toDataPoint" in e and "onRequestPost" in e)
        check("collector stores no IP / raw referrer URL", ".ip" not in e and "cf.ip" not in e)

# ---------------------------------------------------------------- live checks
def http_get(url, method="GET"):
    u = urlparse(url)
    conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=5)
    t0 = time.time()
    conn.request(method, u.path or "/")
    r = conn.getresponse()
    body = r.read()
    dt = time.time() - t0
    conn.close()
    return r.status, dict(r.getheaders()), body, dt

def live_checks(base):
    print(f"\n# live HTTP ({base})")
    try:
        st, _, _, dt = http_get(base + "/")
    except Exception as e:
        check("server reachable", False, str(e))
        return
    check("home responds 200", st == 200, f"status {st}")
    check(f"home TTFB <= {PAGE_TTFB_MAX*1000:.0f}ms", dt <= PAGE_TTFB_MAX, f"{dt*1000:.0f}ms")

    board = load_board()
    # sample 25 detail pages across the board — all must be 200 and fast, none huge
    step = max(1, len(board) // 25)
    slow = []; notok = []; heavy = []
    for r in board[::step]:
        url = base + "/capability/" + r["slug"] + ".html"
        st, hd, body, dt = http_get(url)
        if st != 200:
            notok.append((r["slug"], st))
        if dt > PAGE_TTFB_MAX:
            slow.append((r["slug"], round(dt*1000)))
        if len(body) > CAP_HTML_MAX:
            heavy.append((r["slug"], len(body)))
    check("sampled detail pages all 200", not notok, f"{notok[:3]}")
    check("sampled detail pages all fast", not slow, f"slow: {slow[:3]}")
    check("sampled detail pages all within HTML budget", not heavy, f"{heavy[:2]}")

    # the 1.2 MB export must not be requested by a page load — assert it's not linked from JS
    # (belt-and-suspenders: fetch one detail page and confirm no capabilities.json reference in served HTML/JS)
    _, _, capjs, _ = http_get(base + "/js/capability.js")
    check("served capability.js does not fetch the big export",
          b"fetch(\"/data/capabilities.json\"" not in capjs and b"fetch('/data/capabilities.json'" not in capjs)


def cli_field_contract():
    """The `trust` -> `tashan_score` rename (SCHEMA_VERSION 5) updated the DB and the export and missed
    the CLI entirely: five call sites still read r.trust. `tashan top` returned "no matches" and every
    score in search/info/doctor rendered as an em-dash. Nothing failed, because the fixtures had been
    written with the old field name too — the tests agreed with the bug.

    So this asserts the CLI against the REAL published files, which a fixture cannot fake.
    """
    print()
    print("# CLI reads fields the data actually has")
    idx = json.load(open(os.path.join(WEB, "data", "index.json")))["capabilities"]
    lk = json.load(open(os.path.join(WEB, "data", "lookup.json")))["records"]
    check("index.json rows carry `tashan_score`", any("tashan_score" in r for r in idx[:50]))
    check("lookup.json records carry `tashan_score`", any("tashan_score" in r for r in lk[:50]))
    check("neither file carries the old `trust` field", not any("trust" in r for r in idx[:50] + lk[:50]))
    src = ""
    for f in ("tashan.mjs", "doctor.mjs", "mcp.mjs"):
        src += open(os.path.join(ROOT, "cli", f)).read()
    check("no CLI source reads the renamed `.trust`", ".trust" not in src)
    check("no CLI source reads the renamed `.maintenance`", ".maintenance" not in src)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:4173")
    ap.add_argument("--static-only", action="store_true")
    a = ap.parse_args()

    static_checks()
    if not a.static_only:
        # only run live checks if the server answers
        try:
            http_get(a.url + "/")
            live_checks(a.url)
        except Exception:
            print(f"\n# live HTTP — skipped (no server at {a.url}; run `cd web && python3 -m http.server 4173`)")

    cli_field_contract()

    # ---- titles must say something -------------------------------------------------------------------
    # Six pages shipped titles that were just their nav label — "About — tashan", "Terms — tashan". A
    # search result or an answer engine gets one line to decide relevance, and the brand name is the part
    # it already knows. 25 chars is not a style preference; below it there is no room for a claim.
    import glob as _glob, re as _re
    _thin = []
    for _f in sorted(_glob.glob(os.path.join(ROOT, "web", "*.html"))):
        _src = open(_f, encoding="utf-8").read()
        # A title is a SEARCH RESULT. A page marked noindex will never be one, so holding it to a
        # length written for snippets means padding a heading nobody will ever read in a SERP —
        # /account.html is the customer's own dashboard and is deliberately noindex.
        if _re.search(r'<meta name="robots"[^>]*noindex', _src):
            continue
        _m = _re.search(r"<title>([^<]*)</title>", _src)
        if not _m:
            _thin.append(os.path.basename(_f) + ": no <title> at all")
        elif len(_m.group(1).strip()) < 25:
            _thin.append(f"{os.path.basename(_f)}: {_m.group(1).strip()!r} ({len(_m.group(1).strip())} chars)")
    check("every page title is more than a nav label", not _thin, "; ".join(_thin[:4]))

    # ---- no inline style attributes, anywhere --------------------------------------------------------
    # web/_headers sends `style-src 'self'`, so a style="" attribute is DEAD in production — the browser
    # drops the declaration and logs a violation. pipeline/serve.py sends no CSP, so every one of these
    # rendered perfectly in local preview: ~33,000 shipped, including every score bar on the board and on
    # all 15 category hubs, which therefore rendered full width regardless of score. A capability scoring
    # 73 drew the same bar as one scoring 99, on the page whose entire purpose is the difference.
    # Declarations belong in web/css/site.css; data-driven widths use .bar[data-w=N]. In JS, assigning
    # el.style.x is fine (CSSOM is not governed by style-src) — it is the ATTRIBUTE that is blocked.
    _inline = []
    for _f in sorted(_glob.glob(os.path.join(ROOT, "web", "**", "*.html"), recursive=True)
                     + _glob.glob(os.path.join(ROOT, "web", "js", "*.js"))):
        _n = open(_f, encoding="utf-8").read().count('style="')
        if _n:
            _inline.append(f"{os.path.relpath(_f, ROOT)} ({_n})")
    check("no inline style attributes (CSP style-src 'self' blocks them in production)",
          not _inline, f"{len(_inline)} file(s): " + "; ".join(_inline[:4]))

    # A 404.html is what makes Pages return a real 404. Without it Pages falls back to serving
    # index.html with status 200, so every mistyped URL was a soft 404 a crawler would happily index.
    check("404.html exists (else Pages soft-404s every unknown URL as 200 + the homepage)",
          os.path.exists(os.path.join(ROOT, "web", "404.html")))

    # Tallied HERE, after the last check(). It used to be computed before the trailing checks, so those
    # printed FAIL and then exited 0 — a red line in the log that could not fail the build.
    failed = [r for r in results if not r[0]]
    print(f"\n{'='*48}\n{len(results)-len(failed)}/{len(results)} checks passed" +
          (f" · {len(failed)} FAILED" if failed else " · all green"))
    for ok, name, detail in failed:
        print(f"  FAIL  {name}  — {detail}")
    sys.exit(len(failed))

if __name__ == "__main__":
    main()

