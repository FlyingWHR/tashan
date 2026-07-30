#!/usr/bin/env python3
"""Generate docs/PRODUCT-TREE.md — every route, what it is for, and what it depends on.

    python3 pipeline/gen_product_tree.py

Two days of polish found the same class of bug over and over: a label that disagreed with the board
it belonged to, a sort reading a column that had been renamed away, a hub table with a different row
anatomy from the Index, 68 hub pages with no index page, a rename applied to the schema and to no
prose. None of those are hard to see — they are hard to LOOK for, because nothing enumerated the
surfaces to check.

This enumerates them. Facts are derived from disk on every run (title, scripts, data fetched,
inbound links, generator, gate state) so they cannot drift. PURPOSE is hand-written below, because a
machine cannot tell you what a page is FOR, and a page nobody can describe in one line is a page
that should not exist.

tests/test_product_tree.py fails when a route exists with no entry here.
"""
import json, os, re, sys, glob
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
OUT = os.path.join(ROOT, "docs", "PRODUCT-TREE.md")

# The two things a machine cannot derive. One line each; if a purpose needs two, the page is doing
# two jobs. GATE is declared rather than sniffed: inferring it from the text marked support.html and
# terms.html as gated because they MENTION the licence key, and refunds/privacy as paid because they
# link to billing. All four are free to read. Derived facts stay derived; product facts get declared.
#   free      readable by anyone
#   sells     carries a checkout button
#   post-sale reached after paying
#   gated     withholds content without a licence
PURPOSE = {
    "/index.html":        ("The Index. Find a capability by job or category, ranked and audited.", "free"),
    "/browse.html":       ("Parent index for every category and task hub — the full taxonomy.", "free"),
    "/start.html":        ("How to use it: the CLI, the MCP server, the plugin.", "free"),
    "/methodology.html":  ("How every number is derived, so the score is re-checkable.", "free"),
    "/about.html":        ("Why a rater that sells nothing it measures is the only kind worth reading.", "free"),
    "/pricing.html":      ("What Pro costs and exactly what it adds.", "sells"),
    "/requests.html":     ("Ask for a capability to be measured.", "free"),
    "/for-hosts.html":    ("For IDEs and agent hosts: swap one base URL, get the measurement.", "free"),
    "/capability.html":   ("Client-side dossier fallback (?id=). Prerendered twins are the canonical URLs.", "free"),
    "/welcome.html":      ("Post-checkout: activate the licence. noindex, reached only from Polar.", "post-sale"),
    "/support.html":      ("How to get help, and what we can see when you ask.", "free"),
    "/terms.html":        ("Terms of service.", "free"),
    "/privacy.html":      ("What we collect, which is close to nothing.", "free"),
    "/refunds.html":      ("Cancellation and the 7-day refund.", "post-sale"),
    "/learn/":            ("Answer-engine landing pages for high-intent questions.", "free"),
}

# Surfaces that are not pages but are product, and get audited the same way.
NON_PAGE = [
    ("cli/tashan.mjs",   "CLI", "search / top / info / add / doctor / activate / mcp"),
    ("cli/mcp.mjs",      "MCP server", "find_capability / check_capability / audit_config"),
    ("functions/api/history.js", "Paid API", "score history, licence-gated"),
    ("functions/api/polar.js",   "Webhook", "Polar billing events -> entitlement"),
    ("functions/api/_license.js","Gate", "shared licence validation, fails closed"),
    ("plugin/.claude-plugin/plugin.json", "Claude Code plugin", "installs the MCP server"),
    ("web/llms.txt",     "Answer-engine feed", "site summary + top capabilities"),
]


def visible_title(html):
    m = re.search(r"<title>([^<]*)</title>", html)
    return m.group(1).strip() if m else "—"


def route_of(path):
    rel = "/" + os.path.relpath(path, WEB).replace(os.sep, "/")
    return rel


def main():
    pages = sorted(glob.glob(os.path.join(WEB, "*.html")))
    learn = sorted(glob.glob(os.path.join(WEB, "learn", "*.html")))

    # inbound links across every hand-written page (generated trees are counted in bulk below)
    inbound = Counter()
    for p in pages + learn:
        for href in re.findall(r'href="(/[^"]*)"', open(p, encoding="utf-8").read()):
            inbound[href.split("#")[0].split("?")[0]] += 1

    rows = []
    for p in pages:
        r = route_of(p)
        src = open(p, encoding="utf-8").read()
        js = sorted(set(re.findall(r'src="/js/([a-z]+)\.js', src)))
        # Data is fetched from the JS module, not named in the HTML — reading only the page missed
        # every dependency on the Index, which is the page with the most of them.
        data = set(re.findall(r'/data/([a-z_]+\.json)', src))
        for mod in js:
            jp = os.path.join(WEB, "js", mod + ".js")
            if os.path.exists(jp):
                data |= set(re.findall(r'/data/([a-z_]+\.json)', open(jp, encoding="utf-8").read()))
        data = sorted(data)
        declared = PURPOSE.get(r)
        purpose, gated = declared if isinstance(declared, tuple) else (declared or "", "?")
        noindex = "noindex" in src
        rows.append({
            "route": r, "title": visible_title(src), "purpose": purpose,
            "js": js, "data": data, "gate": gated, "noindex": noindex,
            "inbound": inbound.get(r, 0) + (inbound.get("/", 0) if r == "/index.html" else 0),
        })

    gen = []
    for sub, generator in (("capability", "prerender.py"), ("category", "gen_hubs.py"),
                           ("task", "gen_hubs.py"), ("skills", "gen_hubs.py"),
                           ("learn", "gen_content.py")):
        d = os.path.join(WEB, sub)
        if os.path.isdir(d):
            n = len([f for f in os.listdir(d) if f.endswith(".html")])
            if n:
                gen.append((f"/{sub}/*.html", n, generator))

    missing = [r["route"] for r in rows if not r["purpose"]]

    out = ["# Product tree",
           "",
           "Every surface this product exposes, what it is for, and what it reads. Regenerate with",
           "`python3 pipeline/gen_product_tree.py`; `tests/test_product_tree.py` fails when a route",
           "exists on disk with no purpose written here.",
           "",
           "Derived columns come from disk on every run. **Purpose** is hand-written in",
           "`pipeline/gen_product_tree.py` — a page nobody can describe in one line should not exist.",
           "",
           "## Pages",
           "",
           "| Route | Purpose | JS | Data | Gate | Inbound |",
           "|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (-x["inbound"], x["route"])):
        out.append(f"| `{r['route']}`{' *(noindex)*' if r['noindex'] else ''} | {r['purpose'] or '**— UNDESCRIBED —**'} "
                   f"| {', '.join(r['js']) or '—'} | {', '.join(r['data']) or '—'} "
                   f"| {r['gate']} | {r['inbound']} |")

    out += ["", "## Generated trees", "",
            "| Route pattern | Pages | Generator |", "|---|---|---|"]
    for pat, n, g in gen:
        out.append(f"| `{pat}` | {n:,} | `pipeline/{g}` |")

    out += ["", "## Non-page surfaces", "", "| File | Kind | Exposes |", "|---|---|---|"]
    for f, kind, exposes in NON_PAGE:
        mark = "" if os.path.exists(os.path.join(ROOT, f)) else "  **MISSING**"
        out.append(f"| `{f}`{mark} | {kind} | {exposes} |")

    out += ["", "## Guards", "",
            "Each of these exists because the failure it prevents already shipped once.", ""]
    for t in sorted(glob.glob(os.path.join(ROOT, "tests", "test_*.py"))
                    + glob.glob(os.path.join(ROOT, "cli", "*.test.mjs"))
                    + glob.glob(os.path.join(ROOT, "functions", "api", "*.test.mjs"))):
        doc = open(t, encoding="utf-8").read()
        m = re.search(r'"""([^\n]+)', doc) or re.search(r"^// ([^\n]+)", doc, re.M)
        out.append(f"- `{os.path.relpath(t, ROOT)}` — {m.group(1).strip() if m else ''}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"  {len(rows)} pages, {sum(n for _, n, _ in gen):,} generated, "
          f"{len(NON_PAGE)} non-page surfaces -> docs/PRODUCT-TREE.md")
    if missing:
        print(f"  {len(missing)} route(s) with no purpose written: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
