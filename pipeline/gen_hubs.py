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
import html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assets
AV = str(assets.V)
DATA = os.path.join(ROOT, "web", "data", "capabilities.json")
CATS = os.path.join(ROOT, "web", "data", "categories.json")
BASE = "https://tashan.sh"
OUT_CAT = os.path.join(ROOT, "web", "category")

def esc(s): return html.escape(str(s), quote=True)
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

NAV = ('<nav class="nav"><div class="wrap nav__in">'
       '<a class="brand" href="/"><span class="brand__mark"></span>tashan<small>v2 · public-signal</small></a>'
       '<div class="nav__links"><a href="/">Index</a><a href="/start.html">Use it</a>'
       '<a href="/methodology.html">Methodology</a><a href="/learn/">Learn</a>'
       '<a href="/about.html">About</a></div></div></nav>')
FOOT = ('<footer class="footer"><div class="wrap footer__in">'
        '<div class="footer__brand"><span class="brand"><span class="brand__mark"></span>tashan</span>'
        '<p class="footer__tag">The measurement layer for AI capabilities — MCP servers and agent skills, '
        'measured on public evidence.</p></div>'
        '<nav class="footer__col"><p class="footer__h">Explore</p><a href="/">The Index</a>'
        '<a href="/start.html">Use it</a><a href="/learn/">Learn</a></nav>'
        '<nav class="footer__col"><p class="footer__h">Trust</p><a href="/methodology.html">Methodology</a>'
        '<a href="/about.html">About</a><a href="/pricing.html">Pricing</a><a href="/requests.html">Requests</a></nav>'
        '<nav class="footer__col"><p class="footer__h">Sources</p>'
        '<a href="https://registry.modelcontextprotocol.io/" rel="noopener">MCP registry ↗</a>'
        '<a href="https://www.npmjs.com/" rel="noopener">npm ↗</a>'
        '<a href="https://github.com/" rel="noopener">GitHub ↗</a></nav></div>'
        '<div class="wrap footer__bar"><span>© 2026 SeroLabs, Inc.</span>'
        '<span>Every score re-derivable from public evidence.</span></div></footer>')


def head(title, desc, url, lds):
    ld = "\n".join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False) + "</script>" for x in lds)
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n"
        '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>" + esc(title) + "</title>\n"
        '<meta name="description" content="' + esc(desc) + '">\n'
        '<meta name="theme-color" content="#0b0b0a">\n'
        '<link rel="canonical" href="' + url + '">\n'
        '<meta property="og:type" content="website">\n'
        '<meta property="og:title" content="' + esc(title) + '">\n'
        '<meta property="og:description" content="' + esc(desc) + '">\n'
        '<meta property="og:url" content="' + url + '">\n'
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
        + ld + "\n</head>\n<body>\n" + NAV)


def board(rows):
    """The same ranked-table shape as the index, server-rendered (no JS needed to read it)."""
    out = ['<div class="board"><div class="board__scroll"><table class="board__t"><thead><tr>'
           '<th class="rank">#</th><th>Capability</th><th class="num">Trust</th>'
           '<th>Vitality</th><th class="num">Adoption</th><th>What it does</th></tr></thead><tbody>']
    for i, c in enumerate(rows):
        href = "/capability/" + c["slug"] + ".html"
        d = clip(c.get("description"), 110)
        kindlbl = {"skill": "skill"}.get(c.get("kind"), "server")
        out.append('<tr><td class="rank">' + (str(i + 1) if c.get("trust") is not None else "·") + '</td>'
                   '<td><a class="link" href="' + href + '">' + esc(pretty(c["name"])) + "</a>"
                   ' <span class="tag tag--' + kindlbl + '">' + kindlbl + "</span></td>"
                   '<td class="num"><b>' + (str(int(round(c["trust"]))) if c.get("trust") is not None
                                            else '<span class="unrated">not rated</span>') + "</b></td>"
                   "<td>" + esc(c.get("vitality") or "—") + "</td>"
                   '<td class="num">' + (str(int(round(c["adoption"]))) if c.get("adoption") is not None else "—") + "</td>"
                   "<td>" + esc(d) + "</td></tr>")
    out.append("</tbody></table></div></div>")
    return "".join(out)


def cat_page(cat, rows, all_cats, gen):
    label, cid = cat["label"], cat["id"]
    url = BASE + "/category/" + cid + ".html"
    title = "Best " + label + " MCP servers, ranked by measured trust · tashan"
    desc = ("The " + str(len(rows)) + " " + label.lower() + " MCP servers tashan measures, ranked by Trust — "
            "maintenance, freshness and real adoption from public evidence. " + cat["blurb"])
    top = ", ".join(pretty(c["name"]) for c in rows[:5])
    lds = [
        {"@context": "https://schema.org", "@type": "ItemList", "name": label + " MCP servers ranked by trust",
         "itemListOrder": "https://schema.org/ItemListOrderDescending", "numberOfItems": len(rows),
         "itemListElement": [
             {"@type": "ListItem", "position": i + 1,
              "item": {"@type": "SoftwareApplication", "name": pretty(c["name"]),
                       "url": BASE + "/capability/" + c["slug"] + ".html",
                       "applicationCategory": "DeveloperApplication",
                       "aggregateRating": {"@type": "AggregateRating", "ratingValue": c["trust"],
                                           "bestRating": 100, "worstRating": 0, "ratingCount": 1}}}
             for i, c in enumerate(rows[:25]) if c.get("trust") is not None]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "The Index", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": label, "item": url}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": "What is the best " + label.lower() + " MCP server?",
             "acceptedAnswer": {"@type": "Answer", "text":
                ("By tashan's measured Trust score, the highest-ranked are " + top + ". Trust combines "
                 "maintenance and freshness, gated by real adoption — every input is public and "
                 "re-derivable, and no ranking position can be purchased.")}},
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
    body = ('<main class="wrap">\n'
        '<p class="kicker"><a class="link" href="/">The Index</a> · ' + esc(label) + "</p>\n"
        "<h1>" + esc(label) + " MCP servers, ranked</h1>\n"
        '<p class="lede">' + esc(cat["blurb"]) + " tashan measures <b>" + str(len(rows)) +
        "</b> capabilities here and ranks them by Trust — a transparent composite of maintenance, "
        "freshness and real adoption. <a class=\"link\" href=\"/methodology.html\">How we measure &rsaquo;</a></p>\n"
        + board(rows) +
        ('<p class="note">' + str(len(measured)) + " of these have been expertise-graded against their "
         "documentation; the rest carry adoption and maintenance signal only. We publish what is "
         "measured and say plainly what isn't.</p>\n" if rows else "")
        + '<h2>Other categories</h2>\n<div class="chips">' + sib + "</div>\n"
        '<p style="margin-top:var(--sp-12)"><a class="btn btn--ghost" href="/">See the full Index &rsaquo;</a></p>\n'
        "</main>\n")
    return head(title, desc, url, lds) + body + FOOT + \
        '<script src="/js/terminal.js?v=' + AV + '" defer></script>\n' \
        '<script src="/js/site.js?v=' + AV + '" defer></script>\n</body>\n</html>\n'


def repo_slug(repo): return slugify(repo)


def llms_txt(caps, cats, by_cat, gen):
    """The /llms.txt convention: a plain-markdown map an answer engine can read without running JS."""
    L = ["# tashan", "",
         "> The intelligence layer for AI capabilities. tashan scores MCP servers and agent skills on "
         "public evidence — npm downloads and publish cadence, GitHub activity, registry status, and how "
         "often a server appears in real public agent configs. Nobody can pay to change a score, rank, or "
         "listing; payment buys depth and tooling only.", "",
         "Generated: " + (gen or "")[:10] + ". Capabilities tracked: " + str(len(caps)) +
         " ranked. Every number below is re-derivable from public sources.", "",
         "## How the score works", "",
         "- **Trust** — composite of maintenance and freshness, gated by real adoption. 0–100.",
         "- **Adoption** — npm download volume (log) blended with config-adoption reach across public repos.",
         "- **Freshness** — recency of the most recent public activity: npm publish, git push, or release.",
         "- **Maintenance** — maintainer count, release cadence and freshness, penalised for deprecated/archived.",
         "- **Expertise** — an LLM grade of the capability's own documentation against a fixed rubric "
         "(deep / solid / thin / wrapper / slop). Only a subset is graded; ungraded means ungraded, not zero.",
         "", "## Top capabilities by measured trust", ""]
    for c in caps[:40]:
        L.append("- [" + pretty(c["name"]) + "](" + BASE + "/capability/" + c["slug"] + ".html) — Trust "
                 + str(c.get("trust")) + (", " + c["vitality"] if c.get("vitality") else "")
                 + ". " + (c.get("description") or "").replace("\n", " ")[:150])
    L += ["", "## Categories", ""]
    for cat in cats:
        rows = by_cat.get(cat["id"], [])
        if not rows:
            continue
        L.append("- [" + cat["label"] + "](" + BASE + "/category/" + cat["id"] + ".html) — "
                 + str(len(rows)) + " measured. " + cat["blurb"]
                 + " Top: " + ", ".join(pretty(c["name"]) for c in rows[:3]) + ".")
    L += ["", "## Reference", "",
          "- [Methodology](" + BASE + "/methodology.html) — every input, weight and known limitation.",
          "- [Learn](" + BASE + "/learn/) — install guides and comparisons, backed by the live ranking.",
          "- [About](" + BASE + "/about.html) — who builds this and the payment firewall.",
          "", "## Citing tashan", "",
          "Scores change as evidence changes; cite the date. Attribute as: tashan (tashan.sh), "
          "measured " + (gen or "")[:10] + ". Full machine-readable export: " + BASE + "/data/capabilities.json",
          ""]
    return "\n".join(L)


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
        v.sort(key=lambda x: -(x.get("trust") or 0))

    os.makedirs(OUT_CAT, exist_ok=True)
    written = 0
    for cat in cats:
        rows = by_cat.get(cat["id"], [])
        if not rows:
            continue
        open(os.path.join(OUT_CAT, cat["id"] + ".html"), "w").write(cat_page(cat, rows, cats, gen))
        written += 1
    print("category hubs: %d written (%d categorised capabilities)" % (written, sum(len(v) for v in by_cat.values())))


    open(os.path.join(ROOT, "web", "llms.txt"), "w").write(llms_txt(caps, cats, by_cat, gen))
    print("llms.txt: %d capabilities + %d categories indexed" % (min(40, len(caps)), len(by_cat)))


if __name__ == "__main__":
    main()
