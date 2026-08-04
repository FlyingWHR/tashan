#!/usr/bin/env python3
"""Every claim a page makes about itself must be true of that page.

WHY THIS EXISTS. An external audit found the site contradicting itself in five places at once, and
every one was a sentence asserting something the code did differently:

  - task and role pages said "ranked by tashan score" and sorted by (fit, instruction depth, score).
    The rendered order descended 71..51 and then restarted at 71, in plain sight, on every task page.
  - methodology.html said "the current version is s2" while production served s5 — two scorer bumps
    had shipped without anyone editing the prose.
  - pricing.html sold "the complete audit" while terms.html said "don't claim tashan has audited
    anything" and the scan reaches only npm-resolvable capabilities.
  - methodology.html said "there is no CVE scan" on a site whose paid tier is built around one.
  - about.html said the rank answers "did it work" while methodology said outcome quality is not
    measured and controlled evaluation is roadmap.

None of these were data bugs. The database was right every time. They are prose asserting facts that
live in code, with nothing checking the two agree — which is the same failure as slugify existing in
four places, one layer up. For a product whose entire claim is measurement, a page that misstates its
own ranking is not a typo; it is the product failing at the thing it sells.

Run: python3 tests/test_claims.py
"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
fail = 0


def ok(name, cond, detail=""):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  — " + detail) if detail and not cond else ""))


def text(p):
    t = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", open(p, encoding="utf-8").read())
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))


def scores_in_order(path):
    """The tashan scores as a reader meets them, top to bottom.

    Strip <script> first or the JSON-LD ItemList's ratingValue floods this with the same numbers in a
    different order. The selector is the rendered cell, `<span class="sig__val">`, because that is
    what a person actually reads down the page.
    """
    h = re.sub(r"<script[\s\S]*?</script>", " ", open(path, encoding="utf-8").read())
    return [int(x) for x in re.findall(r'<span class="sig__val">(\d+)</span>', h)]


print("# a page that states its ordering must use it")
# Category hubs claim "ranked by tashan score" and must therefore be descending by score.
for p in sorted(glob.glob(os.path.join(WEB, "category", "*.html"))):
    # RAW, not the tag-stripped body: the claim lives in <meta name="description"> and og:description,
    # which is what a search result and an answer engine quote. Reading only visible text made this
    # check skip every page silently — a guard that cannot find its own subject.
    raw = open(p, encoding="utf-8").read()
    sc = scores_in_order(p)
    if "ranked by tashan score" not in raw:
        continue
    # A guard that silently skips when the selector stops matching is not a guard. This check exists
    # because a page lied about its own ordering; if it cannot read the order, that is a failure.
    ok(f"{os.path.basename(p)} says 'ranked by tashan score' and is",
       bool(sc) and all(a >= b for a, b in zip(sc, sc[1:])),
       f"parsed {len(sc)} scores: {sc[:12]}")

# Task and role hubs sort by (fit, depth, score) and must NOT claim to rank by score.
for d in ("task", "role"):
    # raw again — the claim these pages used to make was in the meta description, exactly where a
    # body-text check would never have seen it.
    bad = [os.path.basename(p) for p in glob.glob(os.path.join(WEB, d, "*.html"))
           if "ranked by tashan score" in open(p, encoding="utf-8").read()]
    ok(f"no {d} page claims 'ranked by tashan score' (it sorts by fit, then depth, then score)",
       not bad, f"{len(bad)} do, e.g. {bad[:3]}")

print()
print("# the methodology must describe the scorer that actually ran")
export = json.load(open(os.path.join(WEB, "data", "capabilities.json"), encoding="utf-8"))
live = export.get("scorer")
meth = open(os.path.join(WEB, "methodology.html"), encoding="utf-8").read()
m = re.search(r'id="mScorer">([^<]+)<', meth)
ok("methodology names the live scorer version", bool(m) and m.group(1) == live,
   f"page says {m.group(1) if m else 'NOTHING'}, export says {live}")

print()
print("# no page may claim a completeness the coverage does not have")
caps = export["capabilities"]
scanned = sum(1 for c in caps if c.get("sec_scanned_at") or c.get("sec_advisory_count") is not None)
pct = 100.0 * scanned / max(len(caps), 1)
for pg in ("index.html", "pricing.html", "about.html", "methodology.html"):
    t = text(os.path.join(WEB, pg))
    bad = re.findall(r"complete audit|whole security audit|audited before you install|fully audited", t, re.I)
    ok(f"{pg} claims no blanket audit ({scanned}/{len(caps)} = {pct:.0f}% are scanned)",
       not bad, f"found: {sorted(set(bad))}")

print()
print("# claims the terms explicitly disclaim must not appear as marketing")
# terms.html says "we measure; we don't vouch" and "don't claim tashan certifies, endorses or has
# audited anything". Selling the opposite on another page is the contradiction, not the wording.
about = text(os.path.join(WEB, "about.html"))
ok("about.html does not claim the rank answers 'did it work'",
   "did it work" not in about, "methodology says outcome quality is not measured")

meth_t = text(os.path.join(WEB, "methodology.html"))
ok("methodology does not deny the CVE scan it documents elsewhere",
   "there is no CVE scan" not in meth_t)

print()
print("# reproducibility is a stronger claim than traceability — only claim what holds")
# Documentation grades come from an LLM, adoption from sampled config mining, discovery from
# rate-limited search. Those are traceable to public sources; a stranger cannot re-derive them
# without our snapshots, prompts and model version.
for pg in ("index.html", "terms.html", "methodology.html"):
    t = text(os.path.join(WEB, pg))
    ok(f"{pg} does not claim numbers are re-derivable by anyone",
       not re.search(r"re-?derivable", t, re.I))

print()
print(("CLAIMS OK" if not fail else "CLAIMS FAILED"))
sys.exit(fail)
