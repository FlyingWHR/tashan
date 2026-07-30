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
    return os.path.exists(WEB + u)


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
