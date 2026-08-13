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
# 24 KB, RAISED FROM 20 ON 11 AUG 2026, AND HERE IS THE ACCOUNTING — because raising a budget you
# have just breached is exactly how a guard stops meaning anything.
#
# The nightly went red twice on skill-tornado-doc-tdoc.html at 23 KB. Four sections were added to
# this page in a week: the security audit's change feed, the free doctor command, the Pro panel and
# the badge. Together they are 2.1 KB on a 16.6 KB page — real, but the offending page breaches at
# 21 KB without any of them, because it pairs a very long description with a full audit.
#
# I looked for waste first and there is little: the heaviest payload fields are description at 453 B
# and peers at 338 B, and the remaining 55 fields are keys and short values. The description does
# appear three times per page — visible HTML, the inline payload the client re-renders from, and
# the structured data — but that is the architecture earning its keep, not fat: the inline island is
# what stops every dossier fetching a 19 MB export.
#
# So the page genuinely says more than it did when 20 KB was set, and the number moves once, with
# the reason written down. It stays a ratchet: 24 is the measured worst case plus a little, not a
# round number chosen to be comfortable.
CAP_HTML_MAX = 24 * 1024        # a prerendered detail page, gzipped-off
# Slim board index, gzipped (what prod ships). Raised 45 -> 55 KB on 31 Jul 2026 to carry `label`,
# the human name, because the board was rendering npm coordinates: "@supabase/mcp-server-supabase"
# headlining a row whose second line was "pkg:@supabase/mcp-server-supabase". Costed the alternatives
# first — deriving the label client-side saves only 4.5 KB because half the rows need the whole-corpus
# view anyway, and dropping the raw `name` breaks CLI search for the 1,064 rows with no npm package,
# where it is the only coordinate they have. +6.5 KB gz is ~50ms on slow 3G for a board a person can
# read. Do not spend the rest of this headroom without measuring what it buys.
# Raised 55 -> 60 KB on 4 Aug 2026. The board went 1,590 -> 1,881 rows when npm discovery and skills
# discovery landed (nothing SEARCHED npm before; skills walked 7 hardcoded repos), which is corpus
# growth, not bloat. 56.1 KB gz. The cheaper alternatives were MEASURED first, as this comment's
# predecessor demands, and both were rejected on evidence:
#   - drop `label` where it equals `name`: 1 row of 1,881 qualifies. Saves 0.0 KB.
#   - drop `npm_pkg`, derivable as id[4:] for all 737 npm-backed rows: saves 3.1 KB and would fit —
#     but cli/doctor.mjs matches installed packages on it and cli/tashan.mjs prints the install
#     command from it, and EVERY ALREADY-INSTALLED CLI reads this same live file. Removing a field
#     the published client depends on breaks copies in the wild that can never be updated in step.
# So the honest fix is to pay the 1.1 KB: ~8ms on slow 3G for 291 more capabilities on the board.
# 5 Aug 2026 — this now measures board.json, the file the BROWSER fetches. index.json still holds
# ranked + catalogued rows because the published CLI reads it, but the board only needs the ranked
# slice to paint a ranking: splitting them took first paint from 56.8 KB to 40.4 KB and ended a
# budget that had been raised three times in three days (45 -> 55 -> 60) chasing corpus growth.
# Back to 45 KB, which is where it started, with the tail loading on idle.
INDEX_JSON_GZ_MAX = 45 * 1024
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
    d = json.load(open(os.path.join(WEB, "data", "board.json")))
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

    # 1c. AND NO THIRD PLACE. The two above are audited copies; a new page adding its own is the bug
    # that keeps happening — slugify has lived in fifteen places in this repo. compare.js wrote one,
    # dropped the export's `slug` override, and sent pkg:@stripe/mcp (official, 69) to
    # pkg-stripe-mcp.html — a page that EXISTS and belongs to third-party stripe-mcp at 45, under the
    # same displayed name. It never 404s, so check 1a above sails past it. terminal.js loads on every
    # page and exports window.tashanCapHref; there is no reason for a third derivation.
    rogue = []
    for f in sorted(os.listdir(os.path.join(WEB, "js"))):
        if not f.endswith(".js") or f in ("index.js", "terminal.js"):
            continue
        src = open(os.path.join(WEB, "js", f), encoding="utf-8").read()
        # The fallback in compare.js reads `c.slug || <derivation>` and is correct; a derivation with
        # no override in front of it is not.
        for m in re.finditer(r".{0,40}" + re.escape(JS_SLUG), src):
            if "slug ||" not in m.group(0):
                rogue.append(f"{f}: {m.group(0).strip()[:60]}")
    check("no other js/ file derives a capability slug without the export's override",
          not rogue, "; ".join(rogue[:3]) + " — use window.tashanCapHref(c)")

    # 2. no orphan pages. NOTE: "board" here is the SLIM index (the interactive leaderboard, capped for
    # download weight). Pages are generated from the BULK export, which is deliberately larger — static
    # HTML has no payload budget, so capping it was throwing away 3,148 scored capabilities that had
    # nowhere to live. The real invariant is pages == bulk export, not pages == board.
    bulk = json.load(open(os.path.join(WEB, "data", "capabilities.json")))
    # READ the export's slug; deriving it here made this check a FOURTH copy of the rule, and it
    # reported the three collision-disambiguated pages as orphans — the pages that exist precisely
    # because deriving is wrong for them.
    want = {c.get("slug") or slugify(c["id"]) for c in bulk["capabilities"]}
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
    raw = open(os.path.join(WEB, "data", "board.json"), "rb").read()
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
    # A SITEMAP IS A REQUEST TO INDEX, so it must agree with the robots tag on the page it lists.
    # This asserted sitemap == every prerendered page, which was right only while every page was
    # indexable. 770 dossiers are a name and one sentence and now carry noindex,follow: served,
    # useful to `doctor` and to the agent tier, but not submitted as pages worth ranking. Listing
    # one anyway is a contradictory signal to exactly the crawlers this project depends on.
    _noindexed = {os.path.basename(f)[:-5]
                  for f in glob.glob(os.path.join(ROOT, "web", "capability", "*.html"))
                  if 'name="robots" content="noindex' in open(f, encoding="utf-8").read()}
    _indexable = have - _noindexed
    check("sitemap lists exactly the pages that are indexable", sm_slugs == _indexable,
          f"sitemap {len(sm_slugs)} vs indexable {len(_indexable)} of {len(have)}; "
          f"listed-but-noindex {len(sm_slugs & _noindexed)}, missing {len(_indexable - sm_slugs)}")

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
    idx = json.load(open(os.path.join(WEB, "data", "board.json")))["capabilities"]
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

    # ---- the offer must be EARNED, page by page ------------------------------------------------------
    # A pitch on a page with nothing wrong is a lie about the product, and a standing banner across
    # 5,788 pages is the thing readers train themselves not to see. The offer may appear ONLY where
    # detail is genuinely withheld — which the page itself states in its own sub-line.
    _unearned = []
    for _f in sorted(_glob.glob(os.path.join(ROOT, "web", "capability", "*.html")))[:1500]:
        _s = open(_f, encoding="utf-8").read()
        _clean = "Nothing on this page is behind a licence" in _s or "Not scanned yet" in _s
        if _clean and "secoffer" in _s:
            _unearned.append(os.path.basename(_f))
    check("no upsell on a capability with nothing gated", not _unearned,
          f"{len(_unearned)} page(s): " + ", ".join(_unearned[:3]))

    # And the existence of a finding is never itself gated — that would make the audit a hostage
    # situation rather than a measurement.
    _hidden = [os.path.basename(_f) for _f in
               sorted(_glob.glob(os.path.join(ROOT, "web", "capability", "*.html")))[:1500]
               if "secoffer" in open(_f, encoding="utf-8").read()
               and "known advisor" not in open(_f, encoding="utf-8").read()
               and "install time" not in open(_f, encoding="utf-8").read()
               and "remote content" not in open(_f, encoding="utf-8").read().lower()]
    check("every offer names a finding the page already showed for free", not _hidden,
          f"{len(_hidden)}: " + ", ".join(_hidden[:3]))

    # ---- titles and descriptions must survive the cut ------------------------------------------------
    # Both are the one line a searcher — or an answer engine — reads before deciding. Over ~60 and
    # ~160 characters they are truncated mid-phrase, so the claim has to fit, not trail off. noindex
    # pages are exempt: they will never be a result.
    _serp = []
    for _f in sorted(_glob.glob(os.path.join(ROOT, "web", "*.html"))):
        _s = open(_f, encoding="utf-8").read()
        if _re.search(r'<meta name="robots"[^>]*noindex', _s):
            continue
        _t = _re.search(r"<title>([^<]*)</title>", _s)
        _d = _re.search(r'<meta name="description" content="([^"]*)"', _s)
        _b = os.path.basename(_f)
        if _t and len(_t.group(1)) > 62:
            _serp.append(f"{_b}: title {len(_t.group(1))}")
        if not _d:
            _serp.append(f"{_b}: no description")
        elif len(_d.group(1)) > 165:
            _serp.append(f"{_b}: desc {len(_d.group(1))}")
    check("every indexable page's title and description fit a search result", not _serp,
          "; ".join(_serp[:4]))

    # The corpus is declared as a citable Dataset — the entity an answer engine reads to learn that
    # the numbers it is about to quote come from a maintained machine-readable source.
    _home = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()
    check("home declares the corpus as a schema.org Dataset with real distributions",
          '"@type":"Dataset"' in _home and "/data/capabilities.json" in _home and "/v0.1/scores" in _home)

    # ---- keep the numbers that were measured ---------------------------------------------------------
    # Measured on the live origin: LCP 540-720ms, CLS 0.021-0.023, INP under 16ms, zero long tasks.
    # The suite has no browser, so it cannot re-measure — it can only protect the decision that bought
    # those numbers. The board opening as a teaser is that decision: at 100 rows it was a 7,500px
    # table and 75% of the page height, which is layout work on every load for rows nobody scrolled to.
    _ijs = open(os.path.join(ROOT, "web", "js", "index.js"), encoding="utf-8").read()
    _m = _re.search(r"var TEASER = (\d+), PAGE = (\d+)", _ijs)
    check("the board still opens as a teaser, not a wall of rows",
          bool(_m) and int(_m.group(1)) <= 25,
          f"TEASER={_m.group(1) if _m else 'MISSING'} — measured CWV assumed a small first paint")

    # The ?ref= on a pricing link is how we learn which dossiers convert. prerender.py and
    # capability.js both emit it for the same capability, and capability.js REPLACES the prerendered
    # page — so if they encode differently the same page reports under two keys and attribution
    # splits in half, silently. Both must percent-encode.
    _rawref = []
    for _f in sorted(_glob.glob(os.path.join(ROOT, "web", "capability", "*.html")))[:800]:
        if _re.search(r'ref=[^"&]*[:@/]', open(_f, encoding="utf-8").read()):
            _rawref.append(os.path.basename(_f))
    check("pricing ?ref= is percent-encoded server-side, as it is client-side", not _rawref,
          f"{len(_rawref)} page(s) e.g. {_rawref[:2]}")

    # ---- readable prose: no walls of text ------------------------------------------------------
    # "Big text chunks that feel like AI slop, horribly styled and hard to read" — measured, and
    # true. The pricing FAQ answered every question in a single 250-500 character paragraph (492 at
    # the worst) with the answer buried in the middle, on the page where somebody decides whether to
    # pay. Nobody reads a wall to find out what they are buying; they scan, and if the first line
    # does not answer the question they leave.
    #
    # A RATCHET, not a style opinion. The cap sits just above where the hand-written pages landed
    # after the rewrite, so prose can still be added freely but a NEW wall fails the build. Raising
    # it is then a deliberate act with a diff attached — which is the only thing that stops this
    # creeping back, because every one of those paragraphs was written one reasonable sentence at a
    # time. Reference and legal pages are exempt: they are read in full, not scanned.
    import html as _htmlmod
    PROSE_MAX, WALL_ALLOW = 240, 2
    EXEMPT = {"terms.html", "privacy.html"}   # legal text is read in full, not scanned
    # A PER-PAGE BASELINE, not an exemption. methodology.html is a reference document — 13,000
    # characters of argument that a reader consults rather than scans, and cutting the reasoning
    # would make it worth less, not more. Splitting took its longest run from 1,035 characters to
    # 542 and its walls from 21 to 15; the rest are single long sentences that need an editor, not
    # an algorithm. The baseline locks in what was won: it can improve, it cannot slide back.
    BASELINE = {"methodology.html": 15}
    _walls = []
    for _f in sorted(_glob.glob(os.path.join(ROOT, "web", "*.html"))
                     + _glob.glob(os.path.join(ROOT, "web", "learn", "*.html"))):
        if os.path.basename(_f) in EXEMPT:
            continue
        _src = open(_f, encoding="utf-8").read()
        if "<main" not in _src:
            continue
        _body = _src.split("<main", 1)[-1].split("</main>")[0]
        # THE LONGEST UNBROKEN RUN, not the longest element. A paragraph split into a lead plus
        # quieter continuation notes reads as several blocks and should count as several — measuring
        # the outer <li> instead reported a 658-character wall that a reader sees as three.
        _long = 0
        for _m in _re.finditer(r"<(p|li)[^>]*>(.*?)</\1>", _body, _re.S):
            _inner = _re.sub(r'<(p|span)[^>]*class="mnote[^"]*"[^>]*>.*?</\1>', " ",
                             _m.group(2), flags=_re.S)
            if len(_re.sub(r"\s+", " ",
                           _htmlmod.unescape(_re.sub(r"<[^>]+>", "", _inner))).strip()) > PROSE_MAX:
                _long += 1
        _cap = BASELINE.get(os.path.basename(_f), WALL_ALLOW)
        if _long > _cap:
            _walls.append(f"{os.path.basename(_f)}:{_long}>{_cap}")
    check(f"no page is a wall of text (max {WALL_ALLOW} paragraphs over {PROSE_MAX} chars)",
          not _walls, "; ".join(_walls[:6]))

    # ---- Cloudflare Pages hard limits ----------------------------------------------------------
    # A single file over 25 MiB fails the WHOLE deploy, not just that file, and the error arrives
    # after wrangler has walked the tree — the same shape as the 20,000-file ceiling already
    # guarded below. data/capabilities.json reached 25.8 MiB purely from indent=2 whitespace across
    # 10,755 rows; the values in it were 8.6 MiB. Minifying took it to 19.1, and this is the guard
    # that says so before a deploy does.
    #
    # THE THRESHOLD IS 24, NOT 22, AND THE REASON IS WHAT A RED SUITE COSTS. daily.yml withholds
    # every site artifact when the suite fails — correct, you do not publish from a broken state —
    # so a guard that trips while the file is still perfectly deployable does not protect a deploy,
    # it stops one. Seven of ten nightlies committed "retention only, site artifacts withheld", and
    # the board went 1,189 capabilities stale behind the database before anyone noticed. At 22 MiB
    # against a 25 MiB limit this guard was one 9% growth step from becoming that same freeze.
    # 24 still leaves a full MiB, and the size is now PRINTED every run so the trend is visible
    # long before it is urgent — the previous failure mode was nobody watching, not a wrong number.
    _sizes = []
    for _f in glob.glob(os.path.join(ROOT, "web", "**", "*"), recursive=True):
        if os.path.isfile(_f):
            _sizes.append((os.path.getsize(_f) / 1048576, os.path.relpath(_f, ROOT)))
    _sizes.sort(reverse=True)
    _big = [f"{n} {m:.1f} MiB" for m, n in _sizes if m > 24]
    check(f"no file is near Cloudflare Pages' 25 MiB per-file limit "
          f"(largest {_sizes[0][1]} {_sizes[0][0]:.1f} MiB)",
          not _big, "; ".join(_big[:3]))

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

