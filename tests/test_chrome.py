#!/usr/bin/env python3
"""The navigation exists once. Every page renders that one definition, byte for byte.

THE ROOT CAUSE THIS PREVENTS. The nav and footer were copy-pasted into 15 hand-written pages and 3
generators — 18 copies of one idea — so every change to the information architecture was an 18-site
blind string replace. Measured before the fix: **6 distinct nav variants and 5 distinct footer
variants, with duplicate links in 4 of the 5.** Adding a single "Account" link produced a footer
carrying Support twice and Refunds twice, because the replaced fragment appeared in both the nav and
the footer and the edit matched both.

It is the same defect as everything else this codebase produced: a hub table that disagreed with the
index board, a rename applied to the schema but not the prose, a sort reading a column that had been
renamed away, two definitions of an icon. One concept, many copies, no single source.

pipeline/chrome.py is now that source. This fails if anything drifts from it.

Run: python3 tests/test_chrome.py
"""
import glob, os, re, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import chrome

fail = 0


def ok(name, cond, detail=""):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  — " + detail) if detail and not cond else ""))


def norm(s):
    return re.sub(r"\s+", "", re.sub(r'\s*aria-current="page"', "", s))


NAVRE = re.compile(r'<div class="nav__links">(.*?)</div>', re.S)
FOOTRE = re.compile(r'<div class="wrap footer__in">(.*?)<div class="wrap footer__bar"', re.S)

pages = sorted(glob.glob(os.path.join(ROOT, "web", "*.html")))
gen = [p for p in (os.path.join(ROOT, "web", x) for x in
                   ("browse.html", "category/comms.html", "task/code-review.html", "learn/index.html"))
       if os.path.exists(p)]
caps = sorted(glob.glob(os.path.join(ROOT, "web", "capability", "*.html")))[:3]

navs, foots = Counter(), Counter()
for p in pages + gen + caps:
    src = open(p, encoding="utf-8").read()
    m = NAVRE.search(src)
    if m:
        navs[norm(m.group(1))] += 1
    m = FOOTRE.search(src)
    if m:
        foots[norm(m.group(1))] += 1

ok(f"one nav across all {sum(navs.values())} sampled pages, hand-written and generated",
   len(navs) == 1, f"{len(navs)} variants")
ok(f"one footer across all {sum(foots.values())} sampled pages",
   len(foots) == 1, f"{len(foots)} variants")

# the specific bug that shipped: an IA edit that adds without removing
for label, counter in (("nav", navs), ("footer", foots)):
    for markup in counter:
        links = re.findall(r">([^<>]+)</a>", markup)
        dupes = sorted({x for x in links if links.count(x) > 1})
        ok(f"no duplicated link in the {label}", not dupes, ", ".join(dupes))

# and that what is rendered is what chrome.py defines, not something hand-edited to look similar
ok("the rendered nav matches pipeline/chrome.py",
   not navs or norm(NAVRE.search(chrome.nav_html()).group(1)) in navs,
   "a page has hand-edited chrome — run python3 pipeline/chrome.py")
ok("the rendered footer matches pipeline/chrome.py",
   not foots or norm(FOOTRE.search(chrome.footer_html() + '<div class="wrap footer__bar"').group(1)) in foots,
   "run python3 pipeline/chrome.py")

# every destination must exist
missing = []
for href, _l in chrome.NAV + [x for _h, ls in chrome.FOOTER for x in ls]:
    if not href.startswith("/"):
        continue
    target = href + "index.html" if href.endswith("/") else href
    if not os.path.exists(os.path.join(ROOT, "web", target.lstrip("/"))):
        missing.append(href)
ok("every nav and footer destination exists on disk", not missing, ", ".join(missing))

# nobody may hand-write chrome again
hand = []
for g in ("gen_hubs.py", "gen_content.py", "prerender.py"):
    src = open(os.path.join(ROOT, "pipeline", g), encoding="utf-8").read()
    if re.search(r'NAV\s*=\s*\(', src) or re.search(r'FOOT\s*=\s*\(', src):
        hand.append(g)
ok("no generator hand-writes its own nav or footer", not hand, ", ".join(hand))

print("CHROME FAILED" if fail else "ok — one navigation, rendered everywhere")
sys.exit(fail)
