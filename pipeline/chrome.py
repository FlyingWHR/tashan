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
    # "Check my setup" REPLACED "Doctor" (/start.html), which named our furniture: a page about
    # installing our CLI. /audit.html does the same job in the browser with nothing to install, and
    # it was the only page on the site where a visitor could DO anything rather than read about it.
    # /start.html keeps its footer slot for people who want the CLI.
    ("/audit.html", "Check my setup"),
    ("/pricing.html", "Pricing"),
]

# The account is not a sixth thing to read. It sits apart, as a glyph, in the corner — the position
# every customer already looks in.
ACCOUNT = ("/account.html", "Your account")

FOOTER = [
    ("Explore", [("/", "The Index"), ("/browse.html", "Browse"), ("/compare.html", "Compare"),
                 ("/audit.html", "Check my setup"),
                 ("/start.html", "Use it"), ("/learn/", "Learn"), ("/for-hosts.html", "For hosts"),
                 ("/changes.html", "What changed"), ("/stats.html", "The numbers"),
                 # The money signal needs a door. A page nothing links to is a page nobody reads,
                 # and this one carries the only evidence here that is not a proxy for demand.
                 ("/paid.html", "Who gets paid")]),
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

# THE TOOLBOX IS THEIRS; THE CHECKING IS OURS. "The measured layer for AI capabilities" named our
# method and our schema — two engineering nouns and a process — which is what the reader least needs
# from a tagline. A tool is what MCP's own spec calls these things AND what someone's mother would
# call them, which almost never happens; "your AI's toolbox" keeps ownership with the reader, since
# we host nothing and supply nothing. `capability` stays where it belongs: the database, the export
# fields, /v0.1 and the CLI's JSON.
#
# AND IT DOES NOT EXPLAIN ITSELF. The second clause — "tools and skills, with the evidence behind
# every score" — was the tagline apologising for the first clause. A positioning line that has to
# gloss its own nouns is not finished; the evidence claim is made eleven times elsewhere on every
# page, by showing the evidence.
TAGLINE = "The trusted directory for your AI's toolbox."


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
            # The wordmark is wrapped so the NAV can drop it under 40rem and still show all four
            # links (they needed 323px and had 250px, which clipped "Pricing"). The footer keeps
            # it — there is room there, and that is where a wordmark actually signs the page.
            '<a class="brand" href="/"><span class="brand__mark"></span>'
            '<span class="brand__wm">tashan</span></a>'
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
            # THE SIGN-OFF. Hermes closes on "THE INTERNET'S OWN AI" — four words that claim a
            # position and explain nothing. The old line here spent eleven words defending our
            # method in the one slot on the page where nobody is arguing with us.
            "<span>Measured from public sources. Every tool, on the record.</span></div></footer>")


NAV_RE = re.compile(r"(?:<a class=\"skip\"[^>]*>.*?</a>)?<nav class=\"nav\">.*?</nav>", re.S)
FOOT_RE = re.compile(r"<footer class=\"footer\">.*?</footer>", re.S)


# A hand-written page opts into the commercial panel by carrying this marker. The panel is then
# rendered from pro_panel() like every generated surface, so there is still exactly ONE definition of
# the offer. Copying the markup into a static page by hand is how the price ends up different on one
# page from every other, which is the drift tests/test_claims.py exists to catch — this makes that
# impossible instead of merely detected.
PRO_MARK_RE = re.compile(r'<section class="pro"[^>]*data-pro="([a-z0-9-]+)"[^>]*>.*?</section>|'
                         r'<!--PRO:([a-z0-9-]+)-->', re.S)

# The lede for each opted-in static page, in its own words. A generic upsell repeated across a site
# is banner blindness; the panel's own docstring says so.
STATIC_PRO = {
    # The homepage panel used to be hand-copied markup carrying its own price string — the drift this
    # marker exists to prevent, sitting on the highest-traffic page on the site. Its free step also
    # used to be "install our CLI", which is a strange thing to ask of someone who has been on the
    # site for nine seconds now that the same answer is one paste away.
    # (lede, starts_hidden). Hidden means the page's own JS reveals it once a finding has earned it.
    # NOT "the watch" and NOT "tells you the day it changes". `watch` is status:planned in
    # entitlements.json — proactive notification does not exist. The copy that stood here promised it
    # in words the keyword guard could not see, which is worse than the version that trips the guard.
    # What Pro actually ships is `history` and `replacement`, so that is what this sells.
    "home": ("Every score, finding and advisory above is free, forever, no account. An index cannot "
             "know which of them <em>you</em> run. "
             '<a class="link" href="/audit.html">Paste your config</a> and see &mdash; free, nothing '
             "to install. Pro adds the series behind each row, and names the replacement when "
             "something you depend on is dying.", False),
    "audit": ("That is where they stand today. Pro adds every score and signal behind them since we "
              "started measuring, so you can see which are getting better and which are quietly "
              "sliding &mdash; and names a replacement for anything already dying.", True),
}


def apply(path, check=False):
    """Return True when the file's chrome had drifted from the definition."""
    src = open(path, encoding="utf-8").read()
    route = "/" + os.path.relpath(path, os.path.join(ROOT, "web")).replace(os.sep, "/")
    if route == "/index.html":
        route = "/"
    out = NAV_RE.sub(lambda _m: nav_html(route), src, count=1)
    out = FOOT_RE.sub(lambda _m: footer_html(), out, count=1)

    def _pro(m):
        key = m.group(1) or m.group(2)
        spec = STATIC_PRO.get(key)
        if not spec:
            return m.group(0)
        lede, starts_hidden = spec
        # `hidden` ONLY where the page earns the offer from its own results — /audit reveals it once
        # a reader has findings in front of them. A panel that greets someone before they have
        # pasted anything is the standing nag this project has a rule against; a panel hidden on a
        # page with nothing to earn it is just an offer nobody ever sees.
        attrs = ' data-pro="' + key + '"' + (" hidden" if starts_hidden else "")
        return (pro_panel(lede, "pro-" + key, pid=None)
                .replace('<section class="pro"', '<section class="pro"' + attrs, 1))

    out = PRO_MARK_RE.sub(_pro, out, count=1)
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
        "The whole series behind any row, back to the first day we measured it",
        "The replacement, named &mdash; not just the news that something died",
        "<code>tashan doctor</code> over your own config, on your own machine",
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


# THE ENTRY POINT LIVES AT THE BOTTOM, and it has to. pro_panel() below used to be defined AFTER
# `sys.exit(main())`, so importing this module worked fine (generators only ever imported it) while
# running it as a script raised NameError the moment apply() needed the panel. Same shape as the
# appended-test trap this repo already documents: anything after sys.exit(main()) does not exist yet
# when main() runs.
if __name__ == "__main__":
    sys.exit(main())
