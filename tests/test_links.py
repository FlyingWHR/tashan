#!/usr/bin/env python3
"""Every link and every install instruction must lead somewhere that exists.

    python3 tests/test_links.py              # internal links + known-dead targets (offline, always runs)
    LINKCHECK=1 python3 tests/test_links.py  # also fetch every external URL

A dead CTA is worse than a missing one: it costs the reader their intent. Two shipped here —
"Open a request ↗" pointed at github.com/tashan-sh/tashan/issues/new, and the plugin install
instruction says `/plugin marketplace add tashan-sh/tashan`. Neither repository exists, so the one
page asking people to engage sent them to a 404, and the plugin cannot be installed by anyone
following the documented command.

External fetching is opt-in because a test suite that fails when the network hiccups gets ignored,
and an ignored suite is worse than none. The offline half — internal resolution and the
known-unpublished list — catches the failures that actually shipped.
"""
import os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")

# Resources referenced by the site that do not exist yet. Each needs an account action the build
# cannot perform; listing them here keeps the promise visible instead of letting a 404 ship quietly.
# Remove an entry the moment the thing is published — the test then enforces that it stays alive.
UNPUBLISHED = {
    "github.com/tashan-sh/tashan": "the GitHub repo (blocks the plugin marketplace install and the "
                                   "grade-request CTA)",
}


def pages():
    for p in sorted(glob.glob(os.path.join(WEB, "*.html"))) + \
             sorted(glob.glob(os.path.join(WEB, "learn", "*.html"))):
        yield p
    # one generated page per template stands in for the ~5,800
    for rel in ("browse.html", "category/comms.html", "task/code-review.html"):
        p = os.path.join(WEB, rel)
        if os.path.exists(p):
            yield p
    caps = sorted(glob.glob(os.path.join(WEB, "capability", "*.html")))
    if caps:
        yield caps[0]


def exists(u):
    if u.endswith("/"):
        u += "index.html"
    if os.path.exists(WEB + u):
        return True
    # A Pages Function serves a route with no file behind it — /api/buy is functions/api/buy.js.
    # Resolved against the function tree rather than allow-listed by prefix, so a link to an /api/
    # route nobody implemented is still a dead link.
    fn = os.path.join(ROOT, "functions") + u
    return os.path.exists(fn + ".js") or os.path.exists(os.path.join(fn, "[[route]].js"))


def _changes_page_is_reachable_and_real():
    """/changes.html is the freshest surface we publish and the only one rivals cannot reproduce —
    it is built from a series that cannot be backfilled. It is also the easiest kind of page to
    ship as an orphan: generated nightly, linked from nothing, indexed by no one.

    So: it must exist, be in the sitemap, be linked from the shared footer (which puts it on every
    page a crawler already reaches), and actually contain dated events rather than an empty shell.
    """
    import re as _re
    out = []
    p = os.path.join(WEB, "changes.html")
    if not os.path.exists(p):
        return ["web/changes.html is missing — run pipeline/gen_changes.py"]
    h = open(p, encoding="utf-8").read()
    if "tashan recorded" not in h and "No consequential changes" not in h:
        out.append("changes.html has no summary sentence — the quotable fact is the point")
    if len(_re.findall(r'class="chg__i', h)) < 5:
        out.append("changes.html lists fewer than 5 events; it should carry the last 30 days")
    if not _re.search(r"\d{4}-\d{2}-\d{2}", h):
        out.append("changes.html shows no dates — 'dated' is the whole claim")
    sm = os.path.join(WEB, "sitemap.xml")
    if os.path.exists(sm) and "/changes<" not in open(sm, encoding="utf-8").read():
        out.append("changes.html is not in sitemap.xml — an unindexed page is not distribution")
    # Linked from somewhere a crawler already goes. The footer is baked into every generated page.
    idx = os.path.join(WEB, "index.html")
    if os.path.exists(idx) and "/changes" not in open(idx, encoding="utf-8").read():
        out.append("nothing on the homepage links to /changes — it is an orphan")
    return out


def main():
    fail, internal, external = [], set(), set()
    for p in pages():
        src = open(p, encoding="utf-8").read()
        rel = os.path.relpath(p, ROOT)
        for h in re.findall(r'href="([^"]+)"', src):
            h = h.replace("&amp;", "&")
            if h.startswith("/"):
                u = h.split("#")[0].split("?")[0]
                internal.add(u)
                if u and not exists(u):
                    fail.append(f"{rel}  ->  {u}  (no such file)")
            elif h.startswith("http"):
                external.add(h.split("#")[0])

    fail += _changes_page_is_reachable_and_real()

    # unpublished targets, wherever they appear — links, code blocks, install snippets
    for p in list(pages()) + [os.path.join(ROOT, "cli", "README.md")]:
        if not os.path.exists(p):
            continue
        src = open(p, encoding="utf-8").read()
        rel = os.path.relpath(p, ROOT)
        for target, why in UNPUBLISHED.items():
            slug = target.split("/", 1)[1]           # tashan-sh/tashan
            if target in src or re.search(r"marketplace add\s+" + re.escape(slug), src):
                fail.append(f"{rel} references {target}, which does not exist yet — {why}")

    if os.environ.get("LINKCHECK"):
        import urllib.request, urllib.error
        for u in sorted(external):
            if "tashan.sh" in u:
                continue                              # our own domain, not deployed yet
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 tashan-linkcheck"})
                code = urllib.request.urlopen(req, timeout=15).status
            except urllib.error.HTTPError as e:
                code = e.code
            except Exception as e:
                code = type(e).__name__
            if code != 200:
                fail.append(f"external link returns {code}: {u}")

    if fail:
        print(f"  FAIL  {len(fail)} dead link(s) / unpublished target(s):")
        for f in sorted(set(fail))[:20]:
            print("        " + f)
        return 1
    print(f"  ok    {len(internal)} internal links resolve"
          + (f", {len(external)} external checked" if os.environ.get("LINKCHECK")
             else f" ({len(external)} external — set LINKCHECK=1 to fetch them)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
