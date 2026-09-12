#!/usr/bin/env python3
"""tashan — category hub pages and llms.txt over the ONE catalog.

THE FLYWHEEL. Every capability we measure should create indexable surface area, and every new surface
should link back into the ranked data. Concretely:

    capability page  ──▶  its category hub  ──▶  sibling capabilities doing the same job
           ▲                     │                          │
           └─────────────────────┴──────── /llms.txt ◀───────┘

ONE CATALOG. A user has a job ("query Postgres"), not a preference for artifact types — MCP server,
skill and CLI are properties of an answer, filterable, never separate pages. The former /skills/
directory was a silo built around our own ingestion pipeline and has been deleted; skills are rows in
the same index, carrying `rated=false` when we have no per-skill evidence rather than a fabricated score.

- /category/<id>.html   one hub per category, covering the whole catalog (rated rows ranked, catalogued
                        rows listed below) with ItemList + BreadcrumbList + FAQPage JSON-LD.
- /llms.txt             the answer-engine convention: a plain-markdown map with the data inline.

Every page emits ItemList + BreadcrumbList JSON-LD, and every list item links to a real prerendered
page. Stdlib only. Run after build.py's export (reads web/data/capabilities.json).
"""
import datetime as dt, glob, html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assets
import chrome
import icons
AV = str(assets.V)
DATA = os.path.join(ROOT, "web", "data", "capabilities.json")
CATS = os.path.join(ROOT, "web", "data", "categories.json")
BASE = "https://tashan.sh"
OUT_CAT = os.path.join(ROOT, "web", "category")

# Which head-to-head pages gen_compare actually wrote, read from ITS manifest rather than recomputed.
# Two copies of the pairing rule would drift, and a hub linking to a comparison that was never
# written is the orphan-in-reverse of the bug the task-hub floor already guards against.
def _compare_manifest():
    try:
        return json.load(open(os.path.join(ROOT, "web", "data", "compare.json")))["by_category"]
    except Exception:
        return {}

COMPARE = _compare_manifest()

def esc(s): return html.escape(str(s), quote=True)
def disp(c):
    """The human label from build.py's apply_labels, shipped in the export. See prerender.disp."""
    return c.get("label") or pretty(c.get("name") or "")


# id -> "Files & Memory". Read from the same categories.json the site renders, so a hub can never
# print a category name the rail does not use.
CAT_LABEL = {c["id"]: c["label"]
             for c in json.load(open(CATS, encoding="utf-8"))["categories"]}


def pretty(name):
    return re.sub(r"^mcp-", "", re.sub(r"^mcp-server-", "", re.sub(r"-mcp$", "",
        re.sub(r"^@modelcontextprotocol/server-", "", str(name)))))
def slugify(cid): return re.sub(r"[^a-z0-9]+", "-", str(cid).lower()).strip("-")
def clip(text, n):
    """Truncate on a word boundary. Cutting mid-word ('Run flexible…', 'view det…', 'Moni…') reads as
    broken output rather than as an abbreviation."""
    t = (text or "").strip()
    if len(t) <= n:
        return t
    cut = t[:n].rsplit(" ", 1)[0].rstrip(" ,.;:—-")
    return (cut or t[:n]) + "…"

# Derived per page from the url head() already receives, NOT a module constant. As a constant it was
# built with current=None, so browse.html — which IS the "Jobs" nav item — shipped without
# aria-current="page", and every pipeline run silently reverted the hand-fix that put it back. Hub
# pages are not nav items, so nothing matches and they render exactly as before.
def nav_for(url):
    return chrome.nav_html(url[len(BASE):] if url.startswith(BASE) else url)
FOOT = chrome.footer_html()


def head(title, desc, url, lds, extra=""):
    ld = "\n".join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False) + "</script>" for x in lds)
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n"
        '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>" + esc(title) + "</title>\n"
        '<meta name="description" content="' + esc(desc) + '">\n'
        '<meta name="theme-color" content="#0b0b0a">\n'
        '<link rel="canonical" href="' + chrome.canon(url) + '">\n'
        '<meta property="og:type" content="website">\n'
        '<meta property="og:title" content="' + esc(title) + '">\n'
        '<meta property="og:description" content="' + esc(desc) + '">\n'
        '<meta property="og:url" content="' + chrome.canon(url) + '">\n'
        '<meta property="og:image" content="' + BASE + '/assets/og.png">\n'
        '<meta property="og:image:width" content="1200">\n'
        '<meta property="og:image:height" content="630">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        '<meta name="twitter:image" content="' + BASE + '/assets/og.png">\n'
        '<link rel="icon" href="/assets/favicon.svg">\n'
        '<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">\n'
        '<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/Geist-Variable.woff2" crossorigin>\n'
        '<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/GeistMono-Variable.woff2" crossorigin>\n'
        '<link rel="stylesheet" href="/css/site.css?v=' + AV + '">\n'
        # THE MARKDOWN TWIN, DECLARED. Capability pages have announced theirs since the tier was
        # built; the hubs generated one and told nobody, which is the same orphan problem the module
        # docstring warns about for the hubs themselves. An answer engine cannot use a convention it
        # has to guess at. Emitted only where a twin is actually written — page 2+ of a paginated
        # category has none, and a rel=alternate to a 404 is worse than no declaration.
        + (('<link rel="alternate" type="text/markdown" href="'
            + esc(md_href(url)) + '" title="Plain-markdown version">\n') if md_href(url) else "")
        + extra + ld + "\n</head>\n<body>\n" + nav_for(url))


def md_href(url):
    """The .md twin's path for a hub URL, or "" where no twin is written."""
    p = url[len(BASE):] if url.startswith(BASE) else url
    if not p.endswith(".html"):
        return ""
    stem = p[:-5]
    if re.match(r"^/category/[a-z0-9-]+-\d+$", stem):   # paginated tail: twin lives on page 1
        return ""
    return stem + ".md" if stem.split("/")[1:2] and stem.split("/")[1] in ("category", "task", "role") else ""


T_SCORE = 'The tashan score, 0–100: upkeep and freshness, gated by real adoption and discounted where the evidence is thin. Every input is public and linked to its source.'
T_EV = "The raw public signal the score was derived from — npm weekly downloads, or stars on the capability's own repository, or the public configs and marketplaces that reference it"
T_HEALTH = 'Whether the project is still alive: active (recent work), stable (finished and still used), abandoned (archived or deprecated)'


def compact(n):
    if n is None:
        return ""
    n = float(n)
    if n >= 1e6: return ("%.1f" % (n / 1e6)).rstrip("0").rstrip(".") + "m"
    if n >= 1e3: return ("%.0f" % (n / 1e3)) + "k"
    return "%d" % n


def evidence(c):
    """Mirror of evidence() in web/js/index.js — the same evidence, phrased the same way."""
    if c.get("npm_downloads") is not None:
        return compact(c["npm_downloads"]) + "/wk"
    if c.get("gh_stars") is not None:
        return compact(c["gh_stars"]) + " \u2605"
    if c.get("config_reach"):
        return "{:,}".format(c["config_reach"]) + (" marketplaces" if c.get("kind") == "plugin" else " repos")
    return ""


def vitality_cell(c):
    """Mirror of vitalityCell() in web/js/index.js."""
    v = c.get("vitality")
    if v == "active":  return "active", "fresh--hot", ""
    if v == "stable":  return "stable", "fresh--warm", "Mature & maintained — quiet but still adopted"
    if v == "abandoned": return "abandoned", "fresh--cold", "Stale under issue pressure, deprecated, or archived"
    iso = c.get("npm_last_publish") or c.get("gh_pushed") or c.get("last_seen")
    if not iso:
        return "\u2014", "fresh--warm", ""
    try:
        t = dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return "\u2014", "fresh--warm", ""
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    months = (dt.datetime.now(dt.timezone.utc) - t).days / 30.44
    if months < 1.5: return "active", "fresh--hot", ""
    if months < 12:  return "%dmo" % round(months), "fresh--warm", ""
    return ("%.1f" % (months / 12)).rstrip("0").rstrip(".") + "y", "fresh--cold", ""


def sentence_case(p):
    """Upper-case the first LETTER only, leaving acronyms intact.

    str.capitalize() lower-cases everything after the first character, so
    kinds_phrase()'s "MCP servers, plugins & skills" came out as "Mcp servers…" — on the <h1> of
    all 22 role hubs and in their ItemList JSON-LD, while the <title> of the same page said MCP
    correctly. The first three characters of the biggest heading on the page, wrong.
    """
    return p[:1].upper() + p[1:] if p else p


def kinds_phrase(rows, amp=False):
    """Name the artifact types THIS page actually contains, in corpus order.

    A fixed noun is wrong on some page no matter which noun you pick. The role hubs said "MCP servers
    for <job>, ranked" over a table of 857 plugins and 202 skills and not one server — because task
    tags only exist for plugins and skills (tag_capabilities.py excludes the rest on purpose: an npm
    server's registry description is capped at 100 chars upstream, and tagging work-intent from one
    truncated sentence would manufacture precision). Widening the noun to cover all three just moved
    the overclaim: it then promised servers that still were not there.

    So read the rows. The heading can only name what the page can show.
    """
    have = {c.get("kind") for c in rows}
    parts = []
    if have - {"skill", "plugin"}: parts.append("MCP servers")
    if "plugin" in have: parts.append("plugins")
    if "skill" in have: parts.append("skills")
    if not parts: return "capabilities"
    if len(parts) == 1: return parts[0]
    joiner = " &amp; " if amp else " and "
    return ", ".join(parts[:-1]) + joiner + parts[-1]


def board(rows):
    """The ranked table, server-rendered — and structurally IDENTICAL to the one index.js builds.

    These were two different tables showing the same rows. The hub printed a bare score, a plain-text
    vitality word, an unlabelled Adoption integer and a long description column; the Index printed a
    score with a bar, a coloured vitality chip, a formatted evidence figure and the expertise verdict.
    Same data, two anatomies, two visual languages — so every hub looked like a worse version of the
    board it was supposed to extend. One row shape now, styled by the one set of rules in site.css.
    """
    out = ['<div class="board"><div class="board__scroll"><table class="board__t"><thead><tr>'
           '<th class="rank" scope="col">#</th><th scope="col">Capability</th>'
           '<th class="num" scope="col" title="' + esc(T_SCORE) + '">tashan</th>'
           '<th class="num" title="' + esc(T_EV) + '">Evidence</th>'
           '<th title="' + esc(T_HEALTH) + '">Health</th></tr></thead><tbody>']
    for i, c in enumerate(rows):
        href = "/capability/" + c["slug"] + ".html"
        t = c.get("tashan_score")
        org = c.get("official")
        off = (' <span class="official" title="Official from ' + esc(org) + '">\u2713 ' + esc(org) + "</span>") if org else ""
        vd = (" " + chrome.verdict_chip(c.get("expertise_verdict"))) if c.get("expertise_verdict") else ""
        dep = ' <span class="fresh fresh--cold">deprecated</span>' if c.get("npm_deprecated") else ""
        # THE FIT, SHOWN AND SOURCED. Ordering by fit is worth nothing if the reader cannot see which
        # rows are here because a grader read the capability against the rubric (primary) and which
        # are here because the author's own keyword happened to match a task synonym (supporting).
        # The title carries the evidence string, so "says who?" is answerable on the row itself.
        fit = c.get("_fit")
        fitchip = (' <span class="fit fit--' + esc(fit) + '" title="'
                   + esc(c.get("_fit_why") or "how this capability was matched to this work")
                   + '">' + esc(fit) + "</span>") if fit else ""
        ev = evidence(c)
        vtxt, vcls, vtitle = vitality_cell(c)
        score = ('<span class="unrated">not scored yet</span>' if t is None
                 else '<span class="sig__val">' + str(int(round(t))) + "</span>")
        out.append(
            '<tr data-href="' + href + '">'
            '<td class="rank">' + (str(i + 1) if t is not None else "\u00b7") + "</td>"
            '<td><div class="cap__name"><a class="cap__link" href="' + href + '">'
            + esc(disp(c)) + "</a>" + fitchip
            # The kind, as the dossier states it. This was {"skill":"skill"}.get(kind, "server") — a
            # one-key map whose DEFAULT relabelled all 3,495 plugins (the largest kind in the corpus)
            # and every remote/docker/python row as "server", 7,039 tags in total. A reader clicked a
            # row tagged "server" and landed on a dossier tagged "plugin". Mirrors prerender.py::313.
            + ' <span class="tag">' + esc(c.get("kind") or "") + "</span>"
            + off + vd + dep + "</div>"
            # The board and the dossier both stopped printing the raw id — a longer restatement of
            # the name directly above it. The hub kept printing it, so the same capability had a
            # different row anatomy depending on which page you reached it from. That exact
            # divergence (a hub table disagreeing with the board) has shipped here before.
            # NO CATEGORY ON THE ROW. It sat directly beneath the name and beside the score, in a
            # table where every other value is measured and checkable — and the classifier is right
            # about 6 times in 10 (23.5% recall on AI & Agents). A lyrics database read "Finance &
            # Crypto" with exactly the confidence of a download count.
            #
            # Suppressing it only when the model abstained was the first fix and it was half a fix:
            # the confident-but-wrong labels are the ones that mislead, and no threshold catches
            # those. A category is a browsing aid, so it now lives where browsing happens — the
            # category hubs, the index rail, and the dossier's link to its hub — and nowhere that
            # implies it was measured.
            + "</td>"
            '<td><div class="sig' + ("" if t is not None else " sig--none") + '">' + score
            + '<span class="bar" data-w="' + str(int(round(t or 0))) + '"><i></i></span></div></td>'
            '<td class="num">' + ('<span class="ev">' + esc(ev) + "</span>" if ev
                                  else '<span class="num--dim">\u2014</span>') + "</td>"
            '<td><span class="fresh ' + vcls + '"'
            + (' title="' + esc(vtitle) + '"' if vtitle else "") + ">" + esc(vtxt) + "</span></td>"
            "</tr>")
    out.append("</tbody></table></div></div>")
    return "".join(out)


CAT_PER_PAGE = int(os.environ.get("CAT_PER_PAGE", "120"))


CTA = ('<div class="procta">'
       '<div class="procta__t"><b>%s</b> <span class="procta__s">%s</span></div>'
       '<a class="btn btn--primary" href="/pricing.html" data-e="cta" data-k="%s">'
       'tashan Pro &mdash; $6/mo &rsaquo;</a></div>')

SEV_RANK = {"high": 0, "medium": 1, "low": 2}


def hub_pro(rows, what, key):
    """The Pro offer on a hub, argued from THIS shelf's own numbers.

    An audit by page type found the panel on 11,918 dossiers and on nothing else: these hubs carried
    a bare pricing link. They are the highest commercial intent on the site — somebody reading "best
    MCP server for X" or a head-to-head is deciding — and a decision is exactly when an offer is
    useful rather than an interruption.

    The line is built from the rows on the page, never generic, because a generic upsell repeated
    across 607 pages is banner blindness by the second one. It also has to stay honest about the
    split: the changes are listed IN FULL, free, a few centimetres above this panel. What Pro sells
    is not the fact that things move, it is being told the day one of YOURS does — which a static
    shelf cannot know by construction.
    """
    n_ch = sum(len(c.get("changes") or []) for c in rows)
    graded = sum(1 for c in rows if c.get("expertise_verdict"))
    if n_ch:
        lede = ("We recorded <b>" + f"{n_ch:,}" + (" change" if n_ch == 1 else " changes")
                + "</b> across " + what + " in the last 45 days &mdash; a new advisory, an install "
                "script appearing, a maintainer leaving. They are listed free above. Pro keeps "
                "the series behind each row, so a number today comes with a direction.")
    elif graded:
        lede = ("Nothing on this shelf moved in the last 45 days, and " + str(graded) + " of these "
                "are graded against their own documentation. Pro keeps the series behind each one, "
                "so you can see which are climbing and which are quietly sliding.")
    else:
        lede = ("This shelf ranks what is measured today. Pro keeps the series behind it, so you "
                "can tell a project getting better from one on its way down &mdash; and names a "
                "replacement for anything already dead.")
    return chrome.pro_panel(lede, key)


def changed_strip(rows, what):
    """What moved on this shelf lately — the one thing a ranked table cannot show.

    A hub answers "what should I use for X" and then never changes shape, so a reader has no reason
    to come back. This is the part that does move: change_events records install scripts appearing,
    permission surfaces widening, projects being deprecated — 404 of them, and until now they
    reached no page at all.

    FREE, and the whole strip is the argument for Pro rather than a teaser for it. Everything a hub
    knows is public evidence and belongs to everyone; what a subscription buys is being told the day
    it happens about the servers in YOUR config, which a static shelf cannot know by construction.
    A gate here would be theatre anyway — the same rows are ranked in full on the page below it.
    """
    ch = []
    for c in rows:
        for x in (c.get("changes") or []):
            ch.append((SEV_RANK.get(x.get("sev"), 3), x.get("at") or "", c, x))
    if not ch:
        # A QUIET SHELF STILL NEEDS THE LINE. 17 categories, 17 tasks and 4 roles had no change in
        # the window and therefore no strip and no case at all — the emptier the shelf, the more
        # likely a reader leaves without learning the product watches anything.
        return ('<p class="hubsub">Nothing on this shelf has moved in the last 45 days.</p>' + (CTA % ("Quiet is worth knowing.",
            "It stops being true without announcing itself &mdash; <code>tashan doctor</code> over your own config says which of yours moved.",
            "pro-hub-quiet")))
    ch.sort(key=lambda t: (t[0], t[1]))
    items = ""
    for _, _, c, x in ch[:4]:
        items += ('<li class="chg chg--' + esc(x.get("sev") or "low") + '">'
                  + '<span class="chg__at mono">' + esc((x.get("at") or "")[:10]) + '</span> '
                  + '<a class="link" href="/capability/' + esc(c.get("slug") or "") + '.html">'
                  + esc(display_name_of(c)) + "</a> &mdash; " + esc(x.get("what") or "")
                  + '</li>')
    n = len(ch)
    return ('<section class="changed"><h2 class="hubh2">Recently changed in ' + esc(what) + '</h2>'
            '<p class="hubsub">' + str(n) + (" change" if n == 1 else " changes")
            + ' recorded here in the last 45 days, newest and most serious first.</p>'
            '<ul class="chg-list">' + items + '</ul>'
            + (CTA % ("This page cannot know what you run.",
                    "tashan doctor reads your own config and names which of these you have "
                    "&mdash; Pro adds the history behind each, and what to move to.",
                    "pro-hub")) + "</section>")


def display_name_of(c):
    return c.get("label") or c.get("name") or c.get("id") or ""


def cat_page(cat, rows, all_cats, gen, page=1, pages=1, total=None):
    """One page of a category shelf.

    PAGINATED because these shelves outgrew a page. devtools reached 1,492 rows — 827 KB of HTML and
    roughly 30,000 DOM nodes, which a phone renders slowly and a reader cannot use: nobody scrolls
    1,492 rows to choose one tool. The audit measured it at 1,990 rows before the classifier fix
    redistributed them, so this is not a one-category problem, it is what every shelf does as the
    corpus grows.

    Page 1 keeps the bare /category/<id>.html URL — it is what is indexed and linked — and later
    pages take -2, -3. rel=prev/next declares the sequence so a crawler reads them as one shelf
    rather than as near-duplicates, and every page carries the full count so neither a reader nor an
    answer engine mistakes page 1 for the whole set.
    """
    label, cid = cat["label"], cat["id"]
    total = len(rows) if total is None else total
    slug_page = cid if page == 1 else f"{cid}-{page}"
    url = BASE + "/category/" + slug_page + ".html"
    pg_sfx = "" if pages == 1 else f" (page {page} of {pages})"
    title = "Best " + label + " " + kinds_phrase(rows) + ", ranked by the tashan score" + pg_sfx + " · tashan"
    desc = ("The " + str(total) + " " + label.lower() + " " + kinds_phrase(rows) + " tashan measures, ranked by tashan score — "
            "upkeep, freshness and real adoption from public evidence." + pg_sfx + " " + cat["blurb"])
    # rel=prev/next declares the sequence, so a crawler reads 13 devtools pages as one shelf instead
    # of as near-duplicate competitors to each other.
    rel = ""
    if page > 1:
        prev = cid if page == 2 else f"{cid}-{page-1}"
        rel += '<link rel="prev" href="' + BASE + "/category/" + prev + '.html">\n'
    if page < pages:
        rel += '<link rel="next" href="' + BASE + "/category/" + cid + f"-{page+1}" + '.html">\n' 
    top = ", ".join(disp(c) for c in rows[:5])
    lds = [
        {"@context": "https://schema.org", "@type": "ItemList", "name": label + " " + kinds_phrase(rows) + " ranked by the tashan score",
         "itemListOrder": "https://schema.org/ItemListOrderDescending", "numberOfItems": len(rows),
         "itemListElement": [
             {"@type": "ListItem", "position": i + 1,
              "item": {"@type": "SoftwareApplication", "name": disp(c),
                       "url": BASE + "/capability/" + c["slug"] + ".html",
                       "applicationCategory": "DeveloperApplication",
                       "aggregateRating": {"@type": "AggregateRating", "ratingValue": c["tashan_score"],
                                           "bestRating": 100, "worstRating": 0, "ratingCount": 1}}}
             for i, c in enumerate(rows[:25]) if c.get("tashan_score") is not None]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "The Index", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": label, "item": url}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": "What is the best " + label.lower() + " MCP server?",
             "acceptedAnswer": {"@type": "Answer", "text":
                ("By tashan's measured score, the highest-ranked are " + top + ". the score combines "
                 "upkeep and freshness, gated by real adoption — every input is public and "
                 "linked to its source.")}},
            {"@type": "Question", "name": "How many " + label.lower() + " MCP servers are there?",
             "acceptedAnswer": {"@type": "Answer", "text":
                ("tashan currently measures " + str(len(rows)) + " capabilities in this category out of "
                 "its full tracked corpus. The count moves as servers are published and as adoption changes.")}},
            {"@type": "Question", "name": "How is the ranking calculated?",
             "acceptedAnswer": {"@type": "Answer", "text":
                ("From public signal only: npm download volume and publish cadence, GitHub push/release "
                 "recency, contributor count, registry status, and how often the server appears in real "
                 "public agent configs. Nobody can pay to change a score, rank, or listing.")}}]},
    ]
    sib = "".join('<a class="chip" href="/category/' + c["id"] + '.html">' + esc(c["label"]) + "</a>"
                  for c in all_cats if c["id"] != cid)
    measured = [c for c in rows if c.get("expertise_verdict")]
    body = ('<main class="wrap" id="main">\n'
        '<p class="kicker"><a class="link" href="/">The Index</a> · ' + esc(label) + "</p>\n"
        "<h1>" + esc(label) + " " + kinds_phrase(rows, amp=True) + ", ranked</h1>\n"
        '<p class="lede">' + esc(cat["blurb"]) + " tashan measures <b>" + str(len(rows)) +
        "</b> capabilities here and ranks them by tashan score — a transparent composite of upkeep, "
        "freshness and real adoption. <a class=\"link\" href=\"/methodology.html\">How we measure &rsaquo;</a></p>\n"
        + board(rows) + changed_strip(rows, label) +
        ('<p class="note">' + str(len(measured)) + " of these have been expertise-graded against their "
         "documentation; the rest carry adoption and upkeep signal only. We publish what is "
         "measured and say plainly what isn't.</p>\n" if rows else "")
        + (('<h2>Head to head</h2>\n<p class="note">The question people actually ask, answered with '
            'two measurements taken the same day by the same scorer.</p>\n<div class="chips">'
            + "".join('<a class="chip" href="/compare/' + p["slug"] + '.html">'
                      + esc(p["a"]) + " vs " + esc(p["b"]) + "</a>" for p in COMPARE.get(cid, [])[:12])
            + "</div>\n") if COMPARE.get(cid) else "")
        + (('<nav class="pager mono" aria-label="Category pages">'
            + ('<a class="btn btn--ghost" href="/category/'
               + (cid if page == 2 else cid + "-" + str(page - 1)) + '.html">&lsaquo; previous</a>' if page > 1 else "")
            + '<span class="pager__at">' + str((page - 1) * CAT_PER_PAGE + 1) + "&ndash;"
            + str(min(page * CAT_PER_PAGE, total)) + " of " + f"{total:,}" + "</span>"
            + ('<a class="btn btn--ghost" href="/category/' + cid + "-" + str(page + 1)
               + '.html">next &rsaquo;</a>' if page < pages else "")
            + "</nav>\n") if pages > 1 else "")
        + '<h2>Other categories</h2>\n<div class="chips">' + sib + "</div>\n"
        '<p class="mt-12"><a class="btn btn--ghost" href="/">See the full Index &rsaquo;</a></p>\n'
        + hub_pro(rows, cat["label"] + " capabilities", "pro-category") +
        "</main>\n")
    return head(title, desc, url, lds, extra=rel) + body + FOOT + \
        '<script src="/js/terminal.js?v=' + AV + '" defer></script>\n' \
        '<script src="/js/site.js?v=' + AV + '" defer></script>\n</body>\n</html>\n'


TASKS = os.path.join(ROOT, "web", "data", "tasks.json")
TASK_MIN = 5     # a page needs a real shelf behind it; below this the task is listed, not published


def task_page(task, rows, all_tasks, gen):
    """A page per JOB, not per technology.

    The whole axis exists because every other directory in this field files by what a tool touches —
    `search / databases / browser automation / memory` — while people arrive knowing what they are
    trying to get done. What makes this defensible rather than editorial is the citation: the task is a
    real occupational process step from O*NET, and the page names the occupations that perform it. That
    is a claim with a source behind it, which "Productivity" never was.
    """
    slug, label = task["slug"], task["label"]
    url = BASE + "/task/" + slug + ".html"
    title = "Best " + kinds_phrase(rows) + " for " + label.lower() + " · tashan"
    # ORDERED AS IT IS ACTUALLY SORTED. This said "ranked by tashan score" while the sort below is
    # (fit, instruction depth, score) — three levels, lexicographic. The rendered order restarted at 71
    # after descending to 51, so the page contradicted its own first sentence in plain sight. The sort
    # is right for a recommendation; the sentence was describing a different one.
    desc = ("The " + str(len(rows)) + " capabilities tashan measures for " + label.lower() +
            " — ordered by how directly each one does this work, then by how well it documents itself, "
            "then by the tashan score. All from public evidence.")
    top = ", ".join(disp(c) for c in rows[:5])
    occs = task.get("occupations") or []
    steps = task.get("onet_steps") or []
    lds = [
        {"@context": "https://schema.org", "@type": "ItemList",
         "name": "Capabilities for " + label + ", ranked by the tashan score",
         "itemListOrder": "https://schema.org/ItemListOrderDescending", "numberOfItems": len(rows),
         "itemListElement": [
             {"@type": "ListItem", "position": i + 1,
              "item": {"@type": "SoftwareApplication", "name": disp(c),
                       "url": BASE + "/capability/" + c["slug"] + ".html",
                       "applicationCategory": "DeveloperApplication",
                       "aggregateRating": {"@type": "AggregateRating", "ratingValue": c["tashan_score"],
                                           "bestRating": 100, "worstRating": 0, "ratingCount": 1}}}
             for i, c in enumerate(rows[:25]) if c.get("tashan_score") is not None]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "The Index", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": label, "item": url}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": "What is the best " + kinds_phrase(rows).rstrip("s") + " for " + label.lower() + "?",
             "acceptedAnswer": {"@type": "Answer", "text":
                ("By tashan's measured score: " + top + ". the score combines upkeep and freshness, "
                 "gated by real adoption — every input is public and linked to its source.")}},
            {"@type": "Question", "name": "Who does " + label.lower() + " as part of their job?",
             "acceptedAnswer": {"@type": "Answer", "text":
                (("This is a process step performed by " + ", ".join(occs[:8]) +
                  (" and others" if len(occs) > 8 else "") + ", per the O*NET 30.3 occupational database.")
                 if occs else
                 ("This is work our corpus shows people doing that O*NET does not yet have a process "
                  "step for — agentic tooling post-dates its software survey."))}},
            {"@type": "Question", "name": "How is the ranking calculated?",
             "acceptedAnswer": {"@type": "Answer", "text":
                ("From public signal only: npm download volume and publish cadence, GitHub push/release "
                 "recency, contributor count, registry status, and how often a capability appears in "
                 "real public agent configs. Nobody can pay to change a score, rank, or listing.")}}]},
    ]
    sib = "".join('<a class="chip" href="/task/' + t["slug"] + '.html">' + esc(t["label"]) + "</a>"
                  for t in all_tasks if t["slug"] != slug)
    # The provenance block — the part a competitor cannot copy without the occupational data.
    if occs:
        who = ('<h2>Who does this work</h2>\n<p>O*NET records this as a core process step for <b>'
               + str(len(occs)) + "</b> occupations, including "
               + esc(", ".join(occs[:10])) + (" and others" if len(occs) > 10 else "") + ".</p>\n"
               + '<p class="note">Recorded there as: '
               + esc(" / ".join('"' + s.rstrip(".") + '"' for s in steps[:3])) + ". We publish it under "
               "the name practitioners use.</p>\n")
    else:
        who = ('<h2>Who does this work</h2>\n<p class="note">O*NET has no process step for this yet — its '
               "software occupations were surveyed before agentic tooling existed. We list it because the "
               "corpus plainly shows people doing it, and we say so rather than forcing it onto an "
               "unrelated step.</p>\n")
    body = ('<main class="wrap" id="main">\n'
        '<p class="kicker"><a class="link" href="/">The Index</a> · ' + esc(label) + "</p>\n"
        "<h1>" + esc(label) + "</h1>\n"
        '<p class="lede">' + esc(task.get("blurb", "")) + " tashan measures <b>" + str(len(rows)) +
        "</b> capabilities for this work and ranks them by tashan score — a transparent composite of "
        "upkeep, freshness and real adoption. "
        '<a class="link" href="/methodology.html">How we measure &rsaquo;</a></p>\n'
        + board(rows) + who + changed_strip(rows, task["label"])
        + '<h2>Other work</h2>\n<div class="chips">' + sib + "</div>\n"
        '<p class="note mt-8">Occupational data from the '
        '<a class="link" rel="nofollow" href="https://www.onetcenter.org/">O*NET 30.3 Database</a> by the '
        "U.S. Department of Labor, Employment and Training Administration, used under "
        '<a class="link" rel="nofollow" href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. '
        "tashan consolidated its process steps into the terms practitioners use; O*NET does not endorse "
        "this site.</p>\n"
        '<p class="mt-12"><a class="btn btn--ghost" href="/">See the full Index &rsaquo;</a></p>\n'
        + hub_pro(rows, task["label"], "pro-task") +
        "</main>\n")
    return head(title, desc, url, lds) + body + FOOT + \
        '<script src="/js/terminal.js?v=' + AV + '" defer></script>\n' \
        '<script src="/js/site.js?v=' + AV + '" defer></script>\n</body>\n</html>\n'


def repo_slug(repo): return slugify(repo)


MD_ROWS = int(os.environ.get("HUB_MD_ROWS", "40"))


def hub_markdown(kind, title, url, intro, rows, total=None, stack=None):
    """A hub as plain markdown, at the same path with .md.

    WHY. Every capability has had a markdown twin for weeks and the HUBS did not — and the hubs are
    where the questions live. "Best MCP server for X", "what should a data engineer install" are
    answered by /category/, /task/ and /role/, and an answer engine that will not run JS had to parse
    those out of a full page of chrome, filters and JSON-LD. The capability tier got the easy path;
    the pages people actually ask for did not.

    Derived from the SAME rows the HTML table renders, in the same order, so the two cannot disagree
    about a ranking. Ranking IS the claim here, so the order is stated rather than left implied, and
    a truncated shelf says how much it left out — a list that quietly stops at 40 reads as complete.
    """
    L = ["# " + title, "", "> " + intro, "",
         f"Source: {url}",
         "Ranked by " + ("fit for the task, then how well it documents itself, then the tashan score"
                         if kind in ("task", "role") else "the tashan score"),
         "  (upkeep and freshness, gated by real adoption). Public evidence only — nothing paid can",
         "  change a rank. Method: " + BASE + "/methodology.html", ""]
    if stack:
        L += ["## The short answer", ""]
        for s in stack:
            L.append(f"- **{s['label']}** — [{disp(s['cap'])}]({BASE}/capability/{s['cap']['slug']}.html)"
                     f" · tashan score {int(round(s['cap'].get('tashan_score') or 0))}")
        L.append("")
    shown = rows[:MD_ROWS]
    L += ["## Ranked", "",
          "| # | Capability | tashan score | Adoption evidence | Activity |",
          "|---|---|---|---|---|"]
    for i, c in enumerate(shown, 1):
        t = c.get("tashan_score")
        L.append(f"| {i} | [{disp(c)}]({BASE}/capability/{c['slug']}.html) "
                 f"| {int(round(t)) if t is not None else 'not scored'} "
                 f"| {evidence(c) or '—'} | {vitality_cell(c)[0]} |")
    n = total if total is not None else len(rows)
    if n > len(shown):
        L += ["", f"Showing the top {len(shown)} of {n:,}. The full ranked shelf is at {url}."]
    L += ["",
          "## What these numbers are not", "",
          "- The tashan score measures upkeep, freshness and adoption. It is **not** a security",
          "  verdict and **not** a measure of whether the capability works well.",
          "- `not scored` means too little public evidence to rank, never that something is bad.",
          "- The security audit is separate and free per capability, on each page above.", ""]
    return "\n".join(L)


def write_hub_md(path_html, text):
    """Write <page>.md beside <page>.html. Same convention as /capability/*.md."""
    with open(path_html[:-5] + ".md", "w", encoding="utf-8") as f:
        f.write(text)


def coverage_lines():
    """The measured-coverage block for llms.txt, from pipeline/coverage.py's own output.

    Returns a note rather than nothing when the file is missing: silence here would read as "fully
    covered", which is the one thing this block exists to prevent.
    """
    try:
        cov = json.load(open(os.path.join(ROOT, "web", "data", "coverage.json"), encoding="utf-8"))
        t, a = cov["tiers"]["top1000"], cov["all"]
    except (OSError, ValueError, KeyError):
        return ["", "Coverage figures unavailable in this build — treat every absence as unmeasured."]
    pct = lambda d, k: round(100.0 * d[k] / d["n"])
    return ["",
            f"- tashan score: {pct(t, 'score')}% of the top 1,000 ({pct(a, 'score')}% of all {a['n']:,} tracked)",
            f"- Security scan: {pct(t, 'scan')}% of the top 1,000 ({pct(a, 'scan')}% of all)",
            f"- Instruction-depth grade: {pct(t, 'grade')}% of the top 1,000 ({pct(a, 'grade')}% of all)",
            f"- Task mapping: {pct(t, 'task')}% of the top 1,000 ({pct(a, 'task')}% of all)",
            f"- All four on the same capability: {pct(t, 'full')}% of the top 1,000",
            "",
            "An absent value means UNMEASURED and never means zero, absent risk, or poor quality."]


def pricing_block():
    """What is free, what is paid, and what it costs — for the readers who cannot click a toggle.

    llms.txt is the file this project TELLS every AI crawler to read, and it never once said the
    price. An answer engine asked "how much is tashan" or "is the security data free" had nothing
    of ours to cite and would have to guess from a pricing page whose annual figure lived in a
    data attribute. We publish an agent-readability instrument; this was our own worst page.

    Read from data/entitlements.json so the number here cannot drift from the one Terms, Refunds
    and pricing.html are checked against.
    """
    ent = json.load(open(os.path.join(ROOT, "data", "entitlements.json"), encoding="utf-8"))
    pro = ent["tiers"]["pro"]
    ann = pro.get("annual") or {}
    price = pro["price"] + "/" + pro["cadence"]
    if ann.get("price"):
        price += " or " + ann["price"] + "/" + ann.get("cadence", "year")
    return [
        "Everything measured is free and needs no account: every tashan score and its inputs, "
        "every security finding's EXISTENCE and severity, advisory ids, the version that fixes "
        "them, and the install command. Quote any of it.",
        "",
        "**tashan Pro — " + price + ", 7 days free.** It buys depth about YOUR stack, never a "
        "different answer: the score history behind a capability, and `tashan doctor` run over "
        "the config on your own machine.",
        "",
        # Through our own origin, like every other buy button. An agent quoting the raw Polar URL
        # would send a human down the one route that skips the success_url repair.
        "- Buy: https://tashan.sh/api/buy?plan=monthly  (annual: /api/buy?plan=annual)",
        "- Terms and the full split: " + BASE + "/pricing.html",
        "- Paid endpoints answer an unauthenticated caller with **HTTP 402** and a JSON body "
        "carrying the price, the checkout URL and the free endpoints that answer the same "
        "question — so an agent never has to guess.",
        "- **Paying as software, not as a subscriber:** those same 402s speak "
        "[x402](https://github.com/coinbase/x402) v2 — a `PAYMENT-REQUIRED` header and an `accepts` "
        "array — so a caller with a wallet can pay per request instead of holding an account. "
        "`POST /v0.1/kit` costs $0.05 a call that way, `POST /v0.1/audit` $0.01, and one "
        "capability's history $0.01. "
        "The `accepts` array is absent until settlement is live on this deployment, because "
        "quoting a payment option we cannot verify would waste your signature.",
        "",
        "Nobody can pay to change a score, a rank, or a listing, and no listing is paid. If that "
        "were ever untrue the measurement would be worthless, so it is the one rule with a test "
        "of its own.",
        "",
    ]


def llms_txt(caps, cats, by_cat, gen, roles=()):
    """The /llms.txt convention: a plain-markdown map an answer engine can read without running JS."""
    L = ["# tashan", "",
         "> The intelligence layer for AI capabilities. tashan scores MCP servers and agent skills on "
         "public evidence — npm downloads and publish cadence, GitHub activity, registry status, and how "
         "often a server appears in real public agent configs. Nobody can pay to change a score, rank, or "
         "listing; payment buys depth and tooling only.", "",
         "Generated: " + (gen or "")[:10] + ". Capabilities tracked: " + str(len(caps)) +
         " ranked. Every number below links to the public source it came from.", "",
         # THE MARKDOWN CONVENTION, ANNOUNCED. Every capability has a plain-markdown twin at
         # <page>.md — no JS, no chrome, the same facts. They were generated and then mentioned
         # nowhere: not the sitemap, not a link, not here. An answer engine cannot use a convention
         # it has not been told about, and this file is the one place it looks.
         "## Read any capability as plain markdown", "",
         "Every capability page has a markdown twin at the same path plus `.md` — no JavaScript, no",
         "navigation, the same measurements. Fetch these instead of parsing HTML:", "",
         "    https://tashan.sh/capability/<slug>.md",
         "    e.g. https://tashan.sh/capability/pkg-tavily-mcp.md", "",
         # A DATED STREAM, so a crawler does not have to re-read 9,000 pages to find the twenty
         # that moved. It is also the only content here that is genuinely new rather than
         # recomputed: a score is a snapshot anyone could derive today, a change exists only
         # because somebody recorded yesterday.
         "## What changed, as a feed", "",
         "Advisories appearing, install scripts added, permission surfaces widening, projects",
         "abandoned — dated, newest first, with what changed and why it matters:", "",
         "    https://tashan.sh/changes.xml       Atom, 50 most recent",
         "",
         "## Answering one question, cheaply", "",
         "Do not fetch a whole feed to check one package. Both of these are keyless, CORS-open and",
         "answer in a few hundred bytes:", "",
         "    GET /v0.1/lookup?name=<package>     one measurement, or measured:false if we have none",
         "    GET /v0.1/search?q=<query>&limit=10 ranked matches, exact name first", "",
         "Send a User-Agent that identifies your client. Cloudflare refuses the literal string",
         "`Python-urllib` across its entire network — not a setting of ours, and it affects every",
         "site behind Cloudflare — so `urllib.request.urlopen(url)` with its default header gets a",
         "403 here and everywhere else. `requests`, curl, node-fetch and Go are all fine, as is",
         "urllib with one line:", "",
         "    r = urllib.request.Request(url, headers={\"User-Agent\": \"your-tool/1.0\"})", "",
         "Each response carries the score, what the score is NOT, the licence terms for quoting it,",
         "and a link to both the HTML page and its markdown twin. `measured:false` answers 200, not",
         "404 — we have no evidence for that package, which is not a finding about the package.", "",
         "The RANKED SHELVES have twins too, and these are the ones that answer a question rather",
         "than describe a thing — each carries the ranking, the ordering rule it used, and how many",
         "rows it left out:", "",
         "    https://tashan.sh/category/<id>.md    e.g. /category/database.md      — best in a category",
         "    https://tashan.sh/task/<slug>.md      e.g. /task/code-review.md       — best for a job to be done",
         "    https://tashan.sh/role/<id>.md        e.g. /role/data-engineer.md     — what a role installs,",
         "                                                                            opening with one pick per task",
         "",
         "Each one carries a labelled Facts block (score, adoption, upkeep, freshness, evidence",
         "coverage, instruction depth), the install command, and the risk scan — with every unknown",
         "stated as unknown rather than omitted. An absent line never means \"fine\".", "",
         "## How the score works", "",
         "- **tashan score** — composite of upkeep and freshness, gated by real adoption. 0–100.",
         "- **Adoption** — npm download volume (log) blended with config-adoption reach across public repos.",
         "- **Freshness** — recency of the most recent public activity: npm publish, git push, or release.",
         "- **Upkeep** — maintainer count, release cadence and freshness, penalised for deprecated/archived.",
         "- **Instruction depth** — an LLM grade of the capability's own documentation against a fixed rubric "
         "(deep / solid / thin) — how completely the documentation explains how to use it, and nothing "
         "else. Only a subset is graded; ungraded means ungraded, not zero.",

         "", "## The security audit (separate from the score)", "",
         "Every npm-published capability is checked against OSV.dev using the version you would "
         "install today, so a finding means the CURRENT release is affected. We also flag scripts "
         "that run at install time, whether the release carries a build attestation, and what the "
         "capability can reach on your machine (files, shell, network, browser, credentials, cloud) "
         "derived from its declared dependencies.",
         "",
         "- Anything OSV lists as malicious is refused a place on the board entirely.",
         "- We do NOT review source code, execute the capability, or test its output for prompt "
         "injection. A clean audit means nothing KNOWN is wrong.",
         # The advisory scan has the same shape of limit as the permission surface below, and until
         # now only one of the two was declared. OSV is queried by package NAME, so a server whose
         # transitive dependency carries a CVE reads clear. An agent quoting "no known advisories"
         # to a human needs to know what that sentence covers.
         "- Advisories are matched against the capability's OWN package name, not its dependency "
         "tree. A dependency's CVE will not appear here. Verified 15 Aug 2026 against live OSV over "
         "the 18 most-installed scanned packages: zero disagreements, so what is reported is "
         "accurate — this is a limit of SCOPE, not of correctness.",
         "- Permission surface UNDER-reports by design: a server can shell out using Node built-ins "
         "and declare nothing, so an empty result means 'nothing declared', not 'nothing possible'.",
         # WHAT WE HAVE NOT MEASURED, TOLD TO THE READER MOST AFFECTED BY IT. An agent that hits an
         # absence has to decide whether it means "unmeasured" or "nothing there", and it cannot ask.
         # Stating the coverage rate per axis lets it weigh an absence instead of guessing at one —
         # and it is the number this project is most tempted to leave out, which is why it is here.
         "", "## How much of this is measured", "",
         "Coverage is stated over the top 1,000 capabilities by adoption evidence, because an "
         "absence on something you looked up is what costs you — not a gap in the tail. Machine-"
         "readable at https://tashan.sh/data/coverage.json, re-measured on every run."] + coverage_lines() + [
         "", "## Top capabilities by tashan score", ""]
    for c in caps[:40]:
        L.append("- [" + disp(c) + "](" + BASE + "/capability/" + c["slug"] + ".html) — tashan score "
                 + str(c.get("tashan_score")) + (", " + c["vitality"] if c.get("vitality") else "")
                 + ". " + (c.get("description") or "").replace("\n", " ")[:150])
    # The agent-facing surfaces, announced where a crawler or an agent will actually look. An endpoint
    # nobody can discover is not distribution.
    L += ["", "## For agents", "",
          # THE MCP SERVER WAS MISSING FROM THIS FILE ENTIRELY. Everything else here is an endpoint
          # a crawler reads once; this is the one line that turns a reader into a caller. It is
          # published, works today (`npx -y tashan-cli mcp` answers initialize/tools/list), and an
          # agent that installs it asks us before every install rather than once.
          "- **Install tashan as an MCP server** — `claude mcp add tashan -- npx -y tashan-cli mcp`, "
          "or point any host at `npx -y tashan-cli mcp` over stdio. Three tools, all free, no "
          "account: `find_capability` (what should I install for X), `check_capability` (is this "
          "one safe and maintained), `audit_config` (what is already in this config, and what is "
          "wrong with it). Zero dependencies; `audit_config` reads local files and sends nothing.",
          "- [/v0.1/scores](" + BASE + "/v0.1/scores) — compact lookup, `name -> [score, vitality, "
          "evidence, slug]`. This is the BULK feed — to check ONE package use /v0.1/lookup instead. "
          "An absent name is UNMEASURED, not bad.",
          "- [/v0.1/servers](" + BASE + "/v0.1/servers) — full records, byte-compatible with the MCP "
          "registry shape; measurement under the `sh.tashan/measurement` key in `_meta`.",
          "- [/skill/SKILL.md](" + BASE + "/skill/SKILL.md) — install tashan as a capability and call it "
          "when choosing what to install.",
          "- `POST /v0.1/kit` — name a job (`{\"task\": \"web-scraping\"}`, or just say what you are "
          "trying to do: `{\"goal\": \"I need to scrape websites\"}`) and get the ranked "
          "shortlist for it, **free**, with everything we excluded and why. Add `{\"kit\": true}` "
          "to have it assembled: each pick pinned to the version the advisory scan actually "
          "cleared, plus a ready-to-paste config for your host. We do NOT sell anyone's skill or "
          "server content — every pick links to its own source and licence; what is paid for is the "
          "selection, the verified pin and the assembly.",
          "- `POST /v0.1/audit` with `{\"history\": true, \"count\": N}` — the PRICE of the paid half "
        "for N servers, as a spec-shaped 402 with x402 terms, naming nothing and auditing nothing. "
        "For an agent that must not upload a config in order to ask what something costs.",
        "- `POST /v0.1/audit` — send the servers in a config, get back every risk we hold about "
          "each one: advisories at the version installed today, deprecation, archived repos, a "
          "maintainer count that fell to one, registry removal. **Free, no account, no payment.** "
          "Add `{\"history\": true}` for the score series and the direction of travel behind each "
          "row, which is the paid half — a licence, or per call with x402.",
          "", "## What costs money", "",
          ] + pricing_block() + [
          "## By job", "",
          "One ranked page per job title. These answer \"what should I install for a <job>\" with "
          "measured rows rather than an opinion.", ""]
    for r, rows in roles:
        scored = [c for c in rows if c.get("tashan_score") is not None]
        L.append("- [" + r["label"] + "](" + BASE + "/role/" + r["id"] + ".html) — "
                 + str(len(rows)) + " measured. Top: "
                 + ", ".join(disp(c) for c in scored[:3]) + ".")
    L += ["", "## Categories", ""]
    for cat in cats:
        rows = by_cat.get(cat["id"], [])
        if not rows:
            continue
        L.append("- [" + cat["label"] + "](" + BASE + "/category/" + cat["id"] + ".html) — "
                 + str(len(rows)) + " measured. " + cat["blurb"]
                 + " Top: " + ", ".join(disp(c) for c in rows[:3]) + ".")
    # THE TWO SURFACES BUILT TO BE QUOTED go at the TOP of Reference, because they are the ones an
    # answer engine can actually use: dated facts and licensed aggregate numbers. Neither was
    # mentioned in this file at all, which meant the crawlers we explicitly invite in robots.txt had
    # no path to them.
    L += ["", "## Reference", "",
          "- [The ecosystem in numbers](" + BASE + "/stats.html) — how many capabilities exist, how "
          "many are scanned, how many are dying, how many ship with no build provenance. Every "
          "figure is a count of rows, recomputed nightly, CC BY 4.0 with a citation line. If you "
          "are writing about which MCP server to use, these are the numbers behind the rankings.",
          "- [What changed](" + BASE + "/changes.html) — a dated record of what moved: deprecations, "
          "abandonments, install scripts appearing, advisories landing, ownership changing. Built "
          "from a series that cannot be backfilled, so no other source can produce it. Also an "
          "Atom feed at " + BASE + "/changes.xml.",
          # THE ONLY SIGNAL HERE THAT IS MONEY, and the one an answer engine cannot get anywhere
          # else: a directory of x402 services publishes no evidence about any of them.
          "- [Who gets paid](" + BASE + "/paid.html) — settled x402 payments on Base, joined to the "
          "capabilities we measure. Of the listed payment addresses we could resolve, most have been "
          "paid at least once, but the MEDIAN service has earned well under a dollar in its entire "
          "life and two thirds of all volume belongs to one receiver. Quote the median beside the "
          "total: a sum is the one statistic a concentrated economy always passes. Machine-readable "
          "at " + BASE + "/data/demand.json. Read from a subgraph on The Graph Network through The "
          "Graph's Subgraph MCP server, so the query is reproducible — the page prints it.",
          "- [Methodology](" + BASE + "/methodology.html) — every input, weight and known limitation.",
          "- [Learn](" + BASE + "/learn/) — install guides and comparisons, backed by the live ranking.",
          "- [About](" + BASE + "/about.html) — who builds this and the payment firewall.",
          "", "## Citing tashan", "",
          "Scores change as evidence changes; cite the date. Attribute as: tashan (tashan.sh), "
          "measured " + (gen or "")[:10] + ". Full machine-readable export: " + BASE + "/data/capabilities.json",
          ""]
    return "\n".join(L)


def browse_page(cats, by_cat, tasks, pub, by_task, roles, gen, published_roles=()):
    """One parent for every hub.

    Two problems, one page. The Index sidebar was rendering all 95 facet values at once — Baymard's
    filter testing puts the readable ceiling around 10, past which the list stops being scannable and
    hides the other filter types from view. And the 15 category hubs plus 53 task hubs had no index
    anywhere: nothing on the site linked to the set, so they were orphans only the sitemap knew about.
    The sidebar now shows the ten biggest of each axis and sends everything else here.
    """
    url = BASE + "/browse.html"
    title = "Browse every category and task · tashan"
    desc = ("Every category and every job tashan measures MCP servers and agent skills against — "
            + str(len(cats)) + " categories and " + str(len(tasks)) + " tasks, each ranked on public evidence.")
    pub_slugs = {t["slug"] for t in pub}
    # A task with nothing measured behind it is not something to browse to — the link lands on an
    # empty shelf. We track the job (it stays in tasks.json, and the CLI still matches on it); we just
    # do not offer it as a way in until there is something to find.
    listable = [t for t in tasks if by_task.get(t["slug"])]
    empty = len(tasks) - len(listable)
    by_role = {}
    for t in listable:
        for r in (t.get("roles") or ["other"]):
            by_role.setdefault(r, []).append(t)
    role_label = {r["id"]: r["label"] for r in roles}

    lds = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": title, "url": url,
            "description": desc},
           {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
               {"@type": "ListItem", "position": 1, "name": "tashan", "item": BASE + "/"},
               {"@type": "ListItem", "position": 2, "name": "Browse", "item": url}]}]

    out = [head(title, desc, url, lds), icons.sprite(), '<main class="wrap" id="main">',
           '<header class="hubhead"><h1>Browse</h1>',
           '<p class="lede">Every category and every job we measure against. ',
           str(sum(len(v) for v in by_cat.values())), ' capabilities across ', str(len(cats)),
           ' categories and ', str(len(listable)), ' tasks.</p></header>']

    # ---- categories: the domain axis ----
    out.append('<section id="categories"><h2 class="hubh2">Categories</h2>')
    out.append('<div class="browsegrid">')
    for cat in sorted(cats, key=lambda c: -len(by_cat.get(c["id"], []))):
        rows = by_cat.get(cat["id"], [])
        if not rows:
            continue
        lead = next((r for r in rows if r.get("tashan_score") is not None), None)
        out.append('<a class="browsecard" href="/category/' + cat["id"] + '.html">'
                   + icons.use("cat-" + cat["id"]) +
                   '<span class="browsecard__t">' + esc(cat["label"]) + "</span>"
                   '<span class="browsecard__c mono">' + str(len(rows)) + "</span>"
                   + ('<span class="browsecard__lead">top: ' + esc(disp(lead)) + "</span>"
                      if lead else "") + "</a>")
    out.append("</div></section>")

    # ---- tasks: the job axis, grouped by who does the job ----
    out.append('<section id="tasks"><h2 class="hubh2">Tasks</h2>'
               '<p class="hubnote">A dashed tile has fewer than ' + str(TASK_MIN) + ' measured capabilities, '
               'so it has no page of its own yet and opens the filtered Index instead.'
               + ((' ' + str(empty) + ' more tasks we track have nothing measured behind them yet and are not '
                  'listed.') if empty else "") + '</p>')
    # A heading over one chip is pure overhead — seven roles hold one or two tasks each. They gather
    # into a single trailing group rather than fragmenting the page into 23 near-empty sections.
    ROLE_MIN = 3
    big = [r for r in by_role if len(by_role[r]) >= ROLE_MIN]
    small = [r for r in by_role if len(by_role[r]) < ROLE_MIN]
    groups = [(role_label.get(r, r), by_role[r]) for r in sorted(big, key=lambda r: -len(by_role[r]))]
    if small:
        seen, rest = set(), []
        for r in sorted(small, key=lambda r: role_label.get(r, r)):
            for t in by_role[r]:
                if t["slug"] not in seen:
                    seen.add(t["slug"]); rest.append(t)
        groups.append(("Also", rest))

    for rlabel, ritems in groups:
        items = sorted(ritems, key=lambda t: -len(by_task.get(t["slug"], [])))
        # the heading carries the role's icon; the tiles under it are individual tasks, which
        # have no icon of their own (69 of them, and a per-task mark would be noise not signal)
        role_id = next((r["id"] for r in roles if r["label"] == rlabel), "Also")
        hub = "/role/" + role_id + ".html" if role_id in published_roles else ""
        heading = (('<a class="link" href="' + hub + '">' + esc(rlabel) + " &rsaquo;</a>") if hub else esc(rlabel))
        out.append('<div class="browserole"><h3 class="browserole__h mono">'
                   + icons.use("role-" + role_id) + heading
                   + "</h3><div class=\"browsegrid browsegrid--tight\">")
        for t in items:
            n = len(by_task.get(t["slug"], []))
            published = t["slug"] in pub_slugs
            href = ("/task/" + t["slug"] + ".html") if published else ("/?task=" + t["slug"])
            out.append('<a class="browsecard' + ("" if published else " browsecard--thin") + '" href="' + href + '">'
                       '<span class="browsecard__t">' + esc(t["label"]) + "</span>"
                       '<span class="browsecard__c mono">' + str(n) + "</span></a>")
        out.append("</div></div>")
    out.append("</section>")

    out.append('<p class="hubback"><a class="link" href="/">&lsaquo; Back to the Index</a></p>')
    out.append("</main>" + FOOT + "</body></html>")
    return "".join(out)


ROLE_MIN = 8     # a job page needs a real shelf; below this the role is a filter, never a page


ROLE_BOARD_MAX = int(os.environ.get("ROLE_BOARD_MAX", "150"))
# The bar a capability must clear to be HEADLINED as the pick for a job.
STACK_MIN = float(os.environ.get("STACK_MIN", "65"))


def stack_picks(rows, tasks):
    """The picks themselves — [(task, capability)] — so the HTML and the markdown twin recommend the
    same things. Extracted from stack_for() when the .md tier arrived: two renderers choosing their
    own picks is exactly how a page and its machine-readable twin start disagreeing."""
    if not tasks:
        return []
    seen, picks = set(), []
    for t in tasks:
        slug = t.get("slug")
        if not slug:
            continue
        for c in rows:
            if (c.get("tashan_score") or 0) < STACK_MIN:
                continue
            if any(x.get("t") == slug and x.get("f") == "primary" for x in (c.get("tasks") or [])) \
                    and c["id"] not in seen:
                seen.add(c["id"])
                picks.append((t, c))
                break
        if len(picks) >= 6:
            break
    return picks if len(picks) >= 2 else []     # two rows is not a stack


def stack_for(role, rows, tasks):
    """One recommendation per job the role actually does — the decisional half of the page.

    A role page printed every capability that touched the job: 763 rows and 511 KB for
    "Software engineer". That is a catalogue, and nobody scrolls 763 heterogeneous artefacts to
    choose one. The question a reader arrives with is "what should I install for this work", and the
    answer is one item per task, not a ranking of everything.

    The rows are ALREADY sorted (fit, then instruction depth, then score), so the first row carrying
    a task is the best-fitting thing we measure for it — no new judgement, just the existing ordering
    read per task instead of globally. A task with nothing measured is omitted rather than filled
    with the least-bad option; an empty shelf is a truthful answer and a wrong recommendation is not.
    """
    picks = stack_picks(rows, tasks)
    if not picks:
        return ""
    out = ['<h2>The stack for this job</h2>',
           '<p class="lede">One pick per task, taken from the ranking below — best fit first, then how '
           'well it documents itself, then the tashan score.</p>',
           '<div class="stack">']
    for t, c in picks:
        sc = c.get("tashan_score")
        out.append('<a class="stack__row" href="/capability/' + (c.get("slug") or slugify(c["id"])) + '.html">'
                   + '<span class="stack__job">' + esc(t["label"]) + "</span>"
                   + '<span class="stack__cap">' + esc(disp(c)) + "</span>"
                   + '<span class="stack__sc mono">' + ("—" if sc is None else str(int(sc))) + "</span></a>")
    out.append("</div>")
    return "\n".join(out) + "\n"


def role_page(role, rows, tasks, all_roles, gen):
    """A page per JOB TITLE — the axis the homepage is sold on, and until now the only one with no URL.

    Categories say what a capability touches and tasks say what you are doing; a role is the union of
    the tasks one job actually performs, which is how people search ("mcp server for data engineers")
    and how an answer engine is asked. The union already existed in tasks.json and drove the homepage
    picker; it had no indexable page, so the one axis with the clearest query intent was invisible to
    every crawler. Nothing here is new measurement — it is the same ranked rows, filed under the job.
    """
    label, rid = role["label"], role["id"]
    url = BASE + "/role/" + rid + ".html"
    scored = [c for c in rows if c.get("tashan_score") is not None]
    title = "Best " + kinds_phrase(rows) + " for " + label.lower() + " · tashan"
    desc = ("The " + str(len(rows)) + " " + kinds_phrase(rows) + " tashan measures for " + label.lower() +
            " work — ordered by how directly each one does the job, then by how well it documents "
            "itself, then by the tashan score. All from public evidence, plus what each one can reach "
            "on your machine.")
    top = ", ".join(disp(c) for c in scored[:5])
    work = ", ".join(t["label"].lower() for t in tasks[:6])
    lds = [
        {"@context": "https://schema.org", "@type": "ItemList",
         "name": sentence_case(kinds_phrase(rows)) + " for " + label.lower() + ", ranked by the tashan score",
         "itemListOrder": "https://schema.org/ItemListOrderDescending", "numberOfItems": len(scored),
         "itemListElement": [
             {"@type": "ListItem", "position": i + 1,
              "item": {"@type": "SoftwareApplication", "name": disp(c),
                       "url": BASE + "/capability/" + c["slug"] + ".html",
                       "applicationCategory": "DeveloperApplication"}}
             for i, c in enumerate(scored[:25])]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "The Index", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "By job", "item": BASE + "/browse.html"},
            {"@type": "ListItem", "position": 3, "name": label, "item": url}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": "What is the best " + kinds_phrase(rows).rstrip("s") + " for a " + label.lower() + "?",
             "acceptedAnswer": {"@type": "Answer", "text":
                ("By tashan's measured score the highest-ranked for this work are " + top + ". The score "
                 "combines upkeep and freshness, gated by real adoption; every input is public and "
                 "linked to its source.")}},
            {"@type": "Question", "name": "What work does this cover?",
             "acceptedAnswer": {"@type": "Answer", "text":
                ("A " + label.lower() + " here is the union of the tasks that job performs — " + work +
                 " — so a capability appears if it is measured against any of them. " + str(len(rows)) +
                 " capabilities qualify today.")}},
            {"@type": "Question", "name": "Are these audited for security?",
             "acceptedAnswer": {"@type": "Answer", "text":
                ("Every capability tashan measures is checked against the OSV advisory database at the "
                 "version you would install today, for install-time scripts, for build provenance, and "
                 "for the permission surface its declared dependencies reach. The existence of a finding "
                 "is always free to see. The audit reads public evidence only and never executes "
                 "anything, so an empty result means nothing was declared, never that nothing is "
                 "possible.")}}]},
    ]
    chips = "".join('<a class="chip" href="/task/' + t["slug"] + '.html">' + esc(t["label"]) + "</a>"
                    for t in tasks if t.get("published"))
    sib = "".join('<a class="chip" href="/role/' + r["id"] + '.html">' + esc(r["label"]) + "</a>"
                  for r in all_roles if r["id"] != rid)
    graded = [c for c in rows if c.get("expertise_verdict")]
    body = ('<main class="wrap" id="main">\n'
        '<p class="kicker"><a class="link" href="/">The Index</a> · <a class="link" href="/browse.html">By job</a> · '
        + esc(label) + "</p>\n"
        "<h1>" + sentence_case(kinds_phrase(rows, amp=True)) + " for " + esc(label.lower()) + ", ranked</h1>\n"
        '<p class="lede">tashan measures <b>' + str(len(rows)) + "</b> capabilities against the work a "
        + esc(label.lower()) + " actually does" + (" — " + esc(work) if work else "") + " — and ranks them "
        "on public evidence alone: upkeep, freshness and real adoption. "
        '<a class="link" href="/methodology.html">How we measure &rsaquo;</a></p>\n'
        + stack_for(role, rows, tasks)
        + board(rows[:ROLE_BOARD_MAX]) + changed_strip(rows, role["label"]) +
        (('<p class="note">Showing the top ' + f"{ROLE_BOARD_MAX:,}" + " of " + f"{len(rows):,}"
          + ' — the rest are on the <a class="link" href="/">Index</a>, filterable by this job.</p>\n')
         if len(rows) > ROLE_BOARD_MAX else "")
        + ('<p class="note">' + str(len(graded)) + " of these have been expertise-graded against their own "
         "documentation; the rest carry adoption and upkeep signal only. We publish what is measured and "
         "say plainly what is not.</p>\n" if rows else "")
        + ('<h2>The work behind this job</h2>\n<div class="chips">' + chips + "</div>\n" if chips else "")
        + '<h2>Other jobs</h2>\n<div class="chips">' + sib + "</div>\n"
        '<p class="mt-12"><a class="btn btn--ghost" href="/?role=' + esc(rid) +
        '">Open this job on the Index &rsaquo;</a></p>\n'
        + hub_pro(rows, role["label"], "pro-role") +
        "</main>\n")
    return head(title, desc, url, lds) + body + FOOT + \
        '<script src="/js/terminal.js?v=' + AV + '" defer></script>\n' \
        '<script src="/js/site.js?v=' + AV + '" defer></script>\n</body>\n</html>\n'


def sweep(dirpath, keep):
    """Delete every hub page in `dirpath` whose stem is not in `keep` — HTML and markdown twin both.

    Three copies of this cleanup existed and only the category one removed the twin, so a task or
    role dropping below its floor lost the HTML and left the `.md` behind: served, unlinked, and
    frozen at whatever it said the day it was dropped.

    It also has to glob BOTH extensions rather than deriving the twin from the HTML. Fixing only
    the delete left role/educator.md in place, because educator.html had been removed by an earlier
    run — so nothing iterated over it to find its twin. An orphan the sweep cannot see is the one
    that survives, and the agent tier is a first-class surface here: a stale .md answers forever.
    """
    gone = set()
    for f in glob.glob(os.path.join(dirpath, "*.html")) + glob.glob(os.path.join(dirpath, "*.md")):
        stem = os.path.basename(f).rsplit(".", 1)[0]
        if stem not in keep:
            os.remove(f)
            gone.add(stem)
    return sorted(gone)


def main():
    d = json.load(open(DATA))
    gen = d.get("generated_at", "")
    caps = list(d["capabilities"])          # rated AND catalogued — one catalog, filterable by type
    for c in caps:
        c.setdefault("slug", slugify(c["id"]))
    cats = json.load(open(CATS))["categories"]
    by_cat = {}
    for c in caps:
        if c.get("category"):
            by_cat.setdefault(c["category"], []).append(c)
    for v in by_cat.values():
        v.sort(key=lambda x: -(x.get("tashan_score") or 0))

    os.makedirs(OUT_CAT, exist_ok=True)
    written = 0
    for cat in cats:
        rows = by_cat.get(cat["id"], [])
        if not rows:
            continue
        pages = max(1, -(-len(rows) // CAT_PER_PAGE))
        for pg in range(1, pages + 1):
            chunk = rows[(pg - 1) * CAT_PER_PAGE: pg * CAT_PER_PAGE]
            name = cat["id"] if pg == 1 else f'{cat["id"]}-{pg}'
            p = os.path.join(OUT_CAT, name + ".html")
            open(p, "w").write(cat_page(cat, chunk, cats, gen, page=pg, pages=pages, total=len(rows)))
            # Page 1 only. A markdown twin per pagination page would publish 13 near-identical files
            # for devtools and teach a summariser that the shelf is 120 long; the twin carries the
            # top of the whole shelf and says how much is below it.
            if pg == 1:
                write_hub_md(p, hub_markdown(
                    "category", cat["label"] + " — MCP servers and agent skills, ranked",
                    BASE + "/category/" + cat["id"] + ".html",
                    f'Every {cat["label"].lower()} capability tashan measures, ranked on public evidence.',
                    rows, total=len(rows)))
            written += 1
    # LEAVE NO ORPHAN BEHIND — the task and role loops have always done this; categories never did.
    # A shelf shrinks whenever the corpus does (the library gate alone removed hundreds), so
    # design-9.html outlived the ninth page of design: crawlable, in no sitemap, linked from nothing,
    # and frozen at whatever ?v= last wrote it — which is how it surfaced, as a stale asset version
    # failing bump_assets --check rather than as the dead page it actually was.
    keep = set()
    for cat in cats:
        rows = by_cat.get(cat["id"], [])
        if not rows:
            continue
        for pg in range(1, max(1, -(-len(rows) // CAT_PER_PAGE)) + 1):
            keep.add(cat["id"] if pg == 1 else f'{cat["id"]}-{pg}')
    orphans = sweep(OUT_CAT, keep)
    if orphans:
        print("category hubs: removed %d orphaned page(s): %s"
              % (len(orphans), ", ".join(orphans)[:90]))

    print("category hubs: %d written (%d categorised capabilities)" % (written, sum(len(v) for v in by_cat.values())))

    # ---- task hubs: one page per job, gated on having a real shelf behind it ----
    tasks = json.load(open(TASKS))["tasks"]
    # FIT FIRST, OPERATIONAL SCORE SECOND. These pages answer "what should I use for this work", and
    # they used to answer it by sorting on tashan_score alone — a number that measures upkeep,
    # freshness and adoption and says nothing whatsoever about whether a capability does the job. So
    # a broadly-adopted tool tagged with a task outranked one built for it, and the page that carries
    # the whole job-oriented positioning was ordered by the axis least related to the job.
    #
    # The fit level now leads. Within a level the operational score still decides, because between
    # two capabilities that are both FOR this work, "which is actually maintained and used" is
    # exactly the right tiebreak — that is what the score is good at.
    FIT_RANK = {"primary": 0, "supporting": 1, "incidental": 2}
    # THEN INSTRUCTION QUALITY, then the operational score. Fit alone still let a capability we had
    # READ and judged thin head the contract-review shelf over one we judged solid, because the two
    # were both primary and the thin one had marginally more adoption. Between two capabilities that
    # are both FOR the work, how well the thing is actually documented beats how many people happened
    # to install it. Ungraded sits between solid and thin deliberately: not knowing is not the same as
    # having looked and found it shallow, and it must not be punished as if it were.
    VERDICT_RANK = {"deep": 0, "solid": 1, None: 2, "thin": 3}
    by_task = {}
    for c in caps:
        for t in (c.get("tasks") or []):
            # incidental is never a recommendation; it stays out of the shelf entirely
            if t.get("f") == "incidental":
                continue
            by_task.setdefault(t["t"], []).append(dict(c, _fit=t.get("f") or "supporting",
                                                       _fit_why=t.get("e")))
    for v in by_task.values():
        v.sort(key=lambda x: (FIT_RANK.get(x.get("_fit"), 1),
                              VERDICT_RANK.get(x.get("expertise_verdict"), 2),
                              -(x.get("tashan_score") or 0)))
    out_task = os.path.join(ROOT, "web", "task")
    os.makedirs(out_task, exist_ok=True)
    # publishable tasks are the sibling set too — a chip must never link to a page that does not exist
    pub = [t for t in tasks
           if len([c for c in by_task.get(t["slug"], []) if c.get("tashan_score") is not None]) >= TASK_MIN]
    sweep(out_task, {t["slug"] for t in pub})    # a task can fall below the gate; leave no orphan
    for t in pub:
        rows = by_task.get(t["slug"], [])
        p = os.path.join(out_task, t["slug"] + ".html")
        open(p, "w").write(task_page(t, rows, pub, gen))
        write_hub_md(p, hub_markdown(
            "task", "What to use for " + t["label"].lower(),
            BASE + "/task/" + t["slug"] + ".html",
            t.get("blurb") or f'Capabilities measured for {t["label"].lower()}, best fit first.',
            rows))
    thin = len(tasks) - len(pub)
    print("task hubs: %d written, %d below the %d-capability floor (listed, not published)"
          % (len(pub), thin, TASK_MIN))


    # ---- role hubs: one page per JOB TITLE, the axis the homepage picker is built on ----
    roles = json.load(open(TASKS)).get("roles", [])
    pub_slugs = {t["slug"] for t in pub}
    out_role = os.path.join(ROOT, "web", "role")
    os.makedirs(out_role, exist_ok=True)
    role_tasks, by_role = {}, {}
    for t in tasks:
        for rid in (t.get("roles") or []):
            role_tasks.setdefault(rid, []).append(dict(t, published=t["slug"] in pub_slugs))
    for rid, ts in role_tasks.items():
        ts.sort(key=lambda t: -len(by_task.get(t["slug"], [])))
        seen = {}
        for t in ts:
            for c in by_task.get(t["slug"], []):
                prev = seen.get(c["id"])
                if prev is None or FIT_RANK.get(c.get("_fit"), 1) < FIT_RANK.get(prev.get("_fit"), 1):
                    seen[c["id"]] = c
        # Same ordering on the role page. A role is the union of its tasks, so a capability can reach
        # it through several — keep the STRONGEST fit it earned on any of them.
        by_role[rid] = sorted(seen.values(),
                              key=lambda x: (FIT_RANK.get(x.get("_fit"), 1),
                                             VERDICT_RANK.get(x.get("expertise_verdict"), 2),
                                             -(x.get("tashan_score") or 0)))
    pub_roles = [r for r in roles
                 if len([c for c in by_role.get(r["id"], []) if c.get("tashan_score") is not None]) >= ROLE_MIN]
    sweep(out_role, {r["id"] for r in pub_roles})  # a job can fall below the gate; leave no orphan
    for r in pub_roles:
        rrows, rtasks = by_role.get(r["id"], []), role_tasks.get(r["id"], [])
        p = os.path.join(out_role, r["id"] + ".html")
        open(p, "w").write(role_page(r, rrows, rtasks, pub_roles, gen))
        write_hub_md(p, hub_markdown(
            "role", "What a " + r["label"].lower() + " should install",
            BASE + "/role/" + r["id"] + ".html",
            r.get("blurb") or f'Capabilities measured for the work a {r["label"].lower()} does.',
            rrows,
            stack=[{"label": t["label"], "cap": c} for t, c in stack_picks(rrows, rtasks)]))
    print("role hubs: %d written, %d below the %d-capability floor (filter only, no page)"
          % (len(pub_roles), len(roles) - len(pub_roles), ROLE_MIN))

    open(os.path.join(ROOT, "web", "browse.html"), "w").write(
        browse_page(cats, by_cat, tasks, pub, by_task, roles, gen,
                    published_roles={r["id"] for r in pub_roles}))
    print("browse.html: %d categories + %d tasks indexed (%d hub pages adopted)"
          % (len(by_cat), len(tasks), len(by_cat) + len(pub)))

    open(os.path.join(ROOT, "web", "llms.txt"), "w").write(
        llms_txt(caps, cats, by_cat, gen, [(r, by_role.get(r["id"], [])) for r in pub_roles]))
    print("llms.txt: %d capabilities + %d categories indexed" % (min(40, len(caps)), len(by_cat)))


if __name__ == "__main__":
    main()
