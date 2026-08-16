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

import icons

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- the information architecture ---------------------------------------------------------------
# Four, not seven. A header is a claim about what matters, and seven flat links makes none — the
# product (Index), how to get it (Use it), why the numbers can be trusted (Methodology) and what it
# costs. About and Learn are supporting reading and live in the footer, where they already were.
# THE NAV NAMES THE JOBS TO BE DONE, not our internal furniture. "Index" is what we call the data,
# "Use it" is not a thing anyone is looking for, and Methodology sat in the top four while the
# job-oriented tier — 69 task pages and 21 role pages, the whole differentiation — was reachable only
# from a footer link and the search box. A visitor arrives wanting to find something for their work
# or to check what they already run; those are now the first two items.
#
# Methodology moves to the footer, where it already lives under "How it works". It is the page that
# proves the numbers, not the page that starts a visit.
#
# NOT "Compare": there is no /compare/ index page, only the 236 generated pairs, and test_chrome
# asserts every nav destination exists on disk — correctly, since a nav link to a 404 is worse than
# no link at all. Add the item when the index page exists.
NAV = [
    ("/", "Find skills"),
    ("/browse.html", "Jobs"),
    ("/start.html", "Doctor"),
    ("/pricing.html", "Pricing"),
]

# The account is not a sixth thing to read. It sits apart, as a glyph, in the corner — the position
# every customer already looks in.
ACCOUNT = ("/account.html", "Your account")

FOOTER = [
    ("Explore", [("/", "The Index"), ("/browse.html", "Browse"), ("/compare.html", "Compare"),
                 ("/start.html", "Use it"), ("/learn/", "Learn"), ("/for-hosts.html", "For hosts"),
                 ("/changes.html", "What changed"), ("/stats.html", "The numbers")]),
    ("How it works", [("/methodology.html", "Methodology"), ("/about.html", "About"),
                      ("/pricing.html", "Pricing"), ("/requests.html", "Requests")]),
    # CONTACT IN THE FOOTER, NOT ONLY BEHIND /support. hello@tashan.sh was on seven pages and
    # reachable from none of the other 9,700 — a reader on a capability page who wanted to correct
    # a grade or ask what a finding meant had no address in front of them. For an instrument that
    # publishes judgments about other people's work, being contactable is not a nicety.
    ("Your account", [("/account.html", "Account"), ("/support.html", "Support"),
                      ("/refunds.html", "Cancel & refunds"),
                      ("mailto:hello@tashan.sh", "hello@tashan.sh")]),
    ("Legal", [("/terms.html", "Terms"), ("/privacy.html", "Privacy")]),
    ("Sources", [("https://registry.modelcontextprotocol.io/", "MCP registry ↗"),
                 ("https://www.npmjs.com/", "npm ↗"), ("https://github.com/", "GitHub ↗")]),
]

TAGLINE = ("The measured layer for AI capabilities — MCP servers and agent skills, "
           "ranked on public evidence.")


# WHAT THE GRADE MEANS, defined once for every Python generator. The chips shipped as a bare word —
# "thin", "wrapper" — with nothing saying what the grader looked for, so a publisher reading their own
# page could not tell what would move it and a visitor could not tell what it measured.
#
# The field is INSTRUCTION DEPTH, not expertise. The rubric reads the capability's own documentation:
# per-tool docs, worked examples, setup and auth, a stated limitation. That is a real, checkable thing
# and it is not the same claim as "this team has domain expertise", which we never measured and were
# nonetheless asserting on every dossier and hub.
#
# THREE BANDS, ONE QUESTION. `wrapper` and `slop` were on this scale and did not belong. `wrapper`
# is a KIND of artifact: ranking a well-documented shim below a badly-documented original is a value
# judgment dressed as a measurement, so it is now a fact carrying the author's own words. `slop`
# claimed "AI-generated filler", which reading a README cannot establish — and both rows that
# carried it turned out to be ordinary factual findings, an announced shutdown and a documentation
# inconsistency. Softening the word to "low-quality" had treated the wording as the problem; the
# problem was that we could not support the claim at all.
VERDICT_LABEL = {"deep": "deep", "solid": "solid", "thin": "thin"}
VERDICT_BLURB = {
    "deep": "documents every tool, with worked examples, setup and a stated limitation",
    "solid": "documents the job properly, with examples you could follow",
    "thin": "shallow — says what it does, not how to actually use it",
}
FIELD_LABEL = "Instruction depth"


def verdict_chip(v, cls="vd"):
    """One chip, one definition. Empty string when the capability has not been graded — an absent
    grade must never render as a grade of nothing."""
    if not v:
        return ""
    return ('<span class="' + cls + " " + cls + "--" + v + '" title="'
            + FIELD_LABEL + ": " + VERDICT_BLURB.get(v, v) + '">'
            + VERDICT_LABEL.get(v, v) + "</span>")


def alias(name):
    """The server IDENTIFIER for `claude mcp add <alias> -- npx -y <pkg>`. Derived from the npm
    PACKAGE NAME, never from the display label.

    This existed as three divergent copies and two of them were broken. prerender.py fed the human
    label ("Context7") through `[^a-z0-9_-]` with no IGNORECASE, so every capital became "-" and a
    LEADING capital was then stripped: `claude mcp add ontext7`. 1,392 of 1,397 npm-backed pages
    shipped a command that cannot work — filesystem as `ilesystem`, sequential-thinking as
    `equential--hinking`, and 13 pages with no alias at all. gen_compare.py had a third spelling
    (`slug.replace("pkg-","")`), so the comparison page and the dossier told you to install the same
    package under different names.

    A label is prose and may contain spaces, capitals and "·"; a package name is already a valid
    identifier. Mirrors web/js/capability.js exactly — the two render the same command and must agree
    character for character. See [[prerender-and-capability-js-are-one-concept]].
    """
    n = re.sub(r"^@modelcontextprotocol/server-", "", str(name))
    n = re.sub(r"-mcp$", "", n)
    n = re.sub(r"^mcp-server-", "", n)
    n = re.sub(r"^mcp-", "", n)
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9_-]", "-", n, flags=re.I)).strip("-")


def canon(path):
    """The URL we DECLARE must be the URL that is SERVED.

    Cloudflare Pages serves an uploaded `foo.html` at `/foo` and 308-redirects `/foo.html` to it.
    Every canonical tag, og:url and sitemap entry we emitted ended in `.html`, so all 5,874 indexed
    URLs pointed at a redirect — and a canonical naming a redirecting URL is a conflicting signal to
    exactly the crawlers this project's whole distribution depends on.

    Internal href="…​.html" links are left alone: they 308 once, browsers cache it, and rewriting
    every link across four generators and fifteen pages is a far larger change than aligning the
    three signals that search actually reads.
    """
    if path.endswith("/index.html"):
        return path[: -len("index.html")]
    if path == "/index.html":
        return "/"
    return path[:-5] if path.endswith(".html") else path


def nav_html(current=None):
    links = "".join(
        f'<a href="{h}"{" aria-current=\"page\"" if h == current else ""}>{l}</a>' for h, l in NAV)
    href, label = ACCOUNT
    glyph = (f'<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" {icons.STYLE}>'
             f'<path d="{icons.UI["account"]}"/></svg>')
    # The SHELL of the signed-in state, not the state itself. This HTML is baked into ~5,900 static
    # pages, so it must be true for a signed-out reader and for a Pro customer both — js/site.js adds
    # the marks after /api/account answers. It starts neutral and only ever ADDS, so there is no
    # flash of a wrong state, and an unreachable API leaves it exactly as shipped: signed out.
    acct = (f'<a class="nav__acct" id="navAcct" href="{href}" title="{label}" aria-label="{label}"'
            f'{" aria-current=\"page\"" if href == current else ""}>{glyph}'
            '<span class="nav__pro mono" id="navPro" hidden>Pro</span></a>')
    # A keyboard user reaching the board on the Index had to tab past the brand, four links, the
    # account glyph, 28 tag chips, 15 category chips and every facet toggle first. Every page in this
    # site has a #main landmark; this is the one control that uses it. Visually hidden until focused,
    # which is the only correct behaviour — a permanently visible skip link is noise for the 99% and
    # a permanently hidden one is useless to the 1%.
    return ('<a class="skip" href="#main">Skip to content</a>'
            '<nav class="nav"><div class="wrap nav__in">'
            '<a class="brand" href="/"><span class="brand__mark"></span>tashan</a>'
            f'<div class="nav__links">{links}{acct}</div>'
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
            "<span>Measured from public sources, and checkable against them.</span></div></footer>")


NAV_RE = re.compile(r"(?:<a class=\"skip\"[^>]*>.*?</a>)?<nav class=\"nav\">.*?</nav>", re.S)
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


# ---- the one commercial panel, rendered on every surface that has an offer to make ---------------
PRO_PRICE = ("$6", "/mo")


def pro_panel(lede, key, extra=(), pid=None):
    """The Pro offer, one definition, used by prerender (dossiers), gen_hubs and gen_content.

    WHY IT MOVED HERE. An audit by page type found the panel on 11,918 capability dossiers and on
    NOTHING else: category, task, role and compare hubs — 607 pages — carried a bare pricing button,
    and the seven /learn/ explainers carried no call to action at all. Those hubs are the highest
    commercial intent on the site ("best MCP server for X", "X vs Y"): somebody reading a comparison
    is deciding, which is exactly when an offer is useful rather than rude.

    `lede` MUST be specific to the page. prerender's own note says a generic upsell across thousands
    of pages is banner blindness by the second page, and that is truer on a hub than on a dossier —
    so each caller passes a line built from that page's own measured numbers, and `extra` lets a
    surface add one bullet of its own.

    NO ACCENT COLOUR: brand/BRAND.md reserves jade for measured data, and an offer is not a
    measurement. `data-state="free"` is what site.js::proPaid() swaps so an active subscriber is
    never sold a trial.
    """
    bullets = list(extra) + [
        "Every score since we started measuring, for any capability",
        "The named replacement when something you run is dying &mdash; not just that it is",
        "<code>tashan doctor</code> over the config you already have, on your machine",
    ]
    return (
        '<section class="pro"' + (' id="' + pid + '"' if pid else '') + ' data-state="free">'
        '<div class="pro__hd"><span class="pro__tag mono">tashan Pro</span>'
        '<span class="pro__price mono">' + PRO_PRICE[0]
        + '<span class="pro__per">' + PRO_PRICE[1] + '</span></span></div>'
        '<p class="pro__lede">' + lede + '</p>'
        '<ul class="pro__list">' + "".join("<li>" + b + "</li>" for b in bullets[:3]) + '</ul>'
        '<p class="pro__cta"><a class="btn btn--primary" href="/pricing.html" '
        'data-e="cta" data-k="' + key + '">Start a 7-day trial &rsaquo;</a>'
        '<span class="pro__free mono"> Everything measured on this page stays free.</span></p>'
        '</section>')
