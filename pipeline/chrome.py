#!/usr/bin/env python3
"""The site's navigation and footer, defined once and written into every page.

    python3 pipeline/chrome.py            # rewrite the chrome on every page
    python3 pipeline/chrome.py --check    # fail if any page has drifted

WHY THIS EXISTS. The nav and footer were copy-pasted into 15 hand-written pages and 3 generators —
18 copies of one idea. Every change to the information architecture was therefore an 18-site blind
string replace, and they drifted exactly as you would expect: 6 distinct nav variants, 5 distinct
footer variants, and duplicate links in 4 of the 5. Adding one "Account" link produced a footer with
Support twice and Refunds twice, because the replaced fragment appeared in both the nav and the
footer and the edit matched both.

This is the same root cause as every other defect this codebase produced this week — a hub table
that disagreed with the index board, a rename applied to the schema but not the prose, a sort
reading a column that had been renamed away. One concept, many copies, no single definition.

So: the IA is data here. Change the lists below and re-run. Nothing else in the repo may hand-write
a nav or a footer, and tests/test_chrome.py fails if anything does.
"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- the information architecture ---------------------------------------------------------------
NAV = [
    ("/", "Index"),
    ("/start.html", "Use it"),
    ("/methodology.html", "Methodology"),
    ("/learn/", "Learn"),
    ("/about.html", "About"),
    ("/pricing.html", "Pricing"),
    ("/account.html", "Account"),
]

FOOTER = [
    ("Explore", [("/", "The Index"), ("/browse.html", "Browse"), ("/start.html", "Use it"),
                 ("/learn/", "Learn"), ("/for-hosts.html", "For hosts")]),
    ("How it works", [("/methodology.html", "Methodology"), ("/about.html", "About"),
                      ("/pricing.html", "Pricing"), ("/requests.html", "Requests")]),
    ("Your account", [("/account.html", "Account"), ("/support.html", "Support"),
                      ("/refunds.html", "Cancel & refunds")]),
    ("Legal", [("/terms.html", "Terms"), ("/privacy.html", "Privacy")]),
    ("Sources", [("https://registry.modelcontextprotocol.io/", "MCP registry ↗"),
                 ("https://www.npmjs.com/", "npm ↗"), ("https://github.com/", "GitHub ↗")]),
]

TAGLINE = ("The measured layer for AI capabilities — MCP servers and agent skills, "
           "ranked on public evidence.")


def nav_html(current=None):
    links = "".join(
        f'<a href="{h}"{" aria-current=\"page\"" if h == current else ""}>{l}</a>' for h, l in NAV)
    return ('<nav class="nav"><div class="wrap nav__in">'
            '<a class="brand" href="/"><span class="brand__mark"></span>tashan</a>'
            f'<div class="nav__links">{links}</div>'
            "</div></nav>")


def footer_html():
    cols = ""
    for heading, links in FOOTER:
        a = "".join(
            f'<a href="{h}"{" rel=\"noopener\"" if h.startswith("http") else ""}>{l}</a>'
            for h, l in links)
        cols += f'<nav class="footer__col"><p class="footer__h">{heading}</p>{a}</nav>'
    return ('<footer class="footer"><div class="wrap footer__in">'
            '<div class="footer__brand"><span class="brand"><span class="brand__mark"></span>tashan</span>'
            f'<p class="footer__tag">{TAGLINE}</p>'
            '<p class="footer__meta" id="footMethod"></p></div>'
            f"{cols}</div>"
            '<div class="wrap footer__bar"><span>© 2026 SeroLabs, Inc.</span>'
            "<span>Every score re-derivable from public evidence.</span></div></footer>")


NAV_RE = re.compile(r"<nav class=\"nav\">.*?</nav>", re.S)
FOOT_RE = re.compile(r"<footer class=\"footer\">.*?</footer>", re.S)


def apply(path, check=False):
    """Return True when the file's chrome had drifted from the definition."""
    src = open(path, encoding="utf-8").read()
    route = "/" + os.path.relpath(path, os.path.join(ROOT, "web")).replace(os.sep, "/")
    if route == "/index.html":
        route = "/"
    out = NAV_RE.sub(lambda _m: nav_html(route), src, count=1)
    out = FOOT_RE.sub(lambda _m: footer_html(), out, count=1)
    if out == src:
        return False
    if not check:
        open(path, "w", encoding="utf-8").write(out)
    return True


def main():
    check = "--check" in sys.argv
    pages = sorted(glob.glob(os.path.join(ROOT, "web", "*.html")))
    drifted = [p for p in pages if apply(p, check)]
    if check and drifted:
        print(f"  FAIL  {len(drifted)} page(s) have hand-edited chrome: "
              + ", ".join(os.path.basename(p) for p in drifted))
        print("        run python3 pipeline/chrome.py — never edit a nav or footer by hand")
        return 1
    print(f"  chrome: {len(NAV)} nav links, {sum(len(l) for _, l in FOOTER)} footer links "
          f"-> {len(drifted) if not check else 0} page(s) rewritten, {len(pages)} checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
