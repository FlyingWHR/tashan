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
import glob, html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assets
import icons
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
       '<a class="brand" href="/"><span class="brand__mark"></span>tashan</a>'
       '<div class="nav__links"><a href="/">Index</a><a href="/start.html">Use it</a>'
       '<a href="/methodology.html">Methodology</a><a href="/learn/">Learn</a>'
       '<a href="/about.html">About</a><a href="/pricing.html">Pricing</a></div></div></nav>')
FOOT = ('<footer class="footer"><div class="wrap footer__in">'
        '<div class="footer__brand"><span class="brand"><span class="brand__mark"></span>tashan</span>'
        '<p class="footer__tag">The measurement layer for AI capabilities — MCP servers and agent skills, '
        'measured on public evidence.</p></div>'
        '<nav class="footer__col"><p class="footer__h">Explore</p><a href="/">The Index</a>'
        '<a href="/start.html">Use it</a><a href="/browse.html">Browse</a><a href="/learn/">Learn</a>'
        '<a href="/for-hosts.html">For hosts</a></nav>'
        '<nav class="footer__col"><p class="footer__h">tashan score</p><a href="/methodology.html">Methodology</a>'
        '<a href="/about.html">About</a><a href="/pricing.html">Pricing</a><a href="/requests.html">Requests</a></nav>'
        '<nav class="footer__col"><p class="footer__h">Sources</p>'
        '<a href="https://registry.modelcontextprotocol.io/" rel="noopener">MCP registry ↗</a>'
        '<a href="https://www.npmjs.com/" rel="noopener">npm ↗</a>'
        '<a href="https://github.com/" rel="noopener">GitHub ↗</a></nav>'
        # Selling on this site means every page needs the legal surfaces, not just the hand-written
        # eleven — these three generators produce ~5,800 of them.
        '<nav class="footer__col"><p class="footer__h">Legal</p><a href="/terms.html">Terms</a>'
        '<a href="/privacy.html">Privacy</a><a href="/refunds.html">Refunds</a>'
        '<a href="/support.html">Support</a></nav></div>'
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
        '<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/SpaceGrotesk-Variable.woff2" crossorigin>\n'
        '<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/Geist-Variable.woff2" crossorigin>\n'
        '<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/GeistMono-Variable.woff2" crossorigin>\n'
        '<link rel="stylesheet" href="/css/site.css?v=' + AV + '">\n'
        + ld + "\n</head>\n<body>\n" + NAV)


T_SCORE = 'The tashan score, 0–100: upkeep and freshness, gated by real adoption and discounted where the evidence is thin. Every input is public and re-derivable, and no position can be bought.'
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


def board(rows):
    """The ranked table, server-rendered — and structurally IDENTICAL to the one index.js builds.

    These were two different tables showing the same rows. The hub printed a bare score, a plain-text
    vitality word, an unlabelled Adoption integer and a long description column; the Index printed a
    score with a bar, a coloured vitality chip, a formatted evidence figure and the expertise verdict.
    Same data, two anatomies, two visual languages — so every hub looked like a worse version of the
    board it was supposed to extend. One row shape now, styled by the one set of rules in site.css.
    """
    out = ['<div class="board"><div class="board__scroll"><table class="board__t"><thead><tr>'
           '<th class="rank">#</th><th>Capability</th>'
           '<th class="num" title="' + esc(T_SCORE) + '">tashan</th>'
           '<th class="num" title="' + esc(T_EV) + '">Evidence</th>'
           '<th title="' + esc(T_HEALTH) + '">Health</th></tr></thead><tbody>']
    for i, c in enumerate(rows):
        href = "/capability/" + c["slug"] + ".html"
        t = c.get("tashan_score")
        org = c.get("official")
        off = (' <span class="official" title="Official from ' + esc(org) + '">\u2713 ' + esc(org) + "</span>") if org else ""
        vd = (' <span class="vd vd--' + esc(c["expertise_verdict"]) + '">' + esc(c["expertise_verdict"])
              + "</span>") if c.get("expertise_verdict") else ""
        dep = ' <span class="fresh fresh--cold">deprecated</span>' if c.get("npm_deprecated") else ""
        ev = evidence(c)
        vtxt, vcls, vtitle = vitality_cell(c)
        score = ('<span class="unrated">not scored yet</span>' if t is None
                 else '<span class="sig__val">' + str(int(round(t))) + "</span>")
        out.append(
            '<tr data-href="' + href + '">'
            '<td class="rank">' + (str(i + 1) if t is not None else "\u00b7") + "</td>"
            '<td><div class="cap__name"><a class="cap__link" href="' + href + '">'
            + esc(pretty(c["name"])) + "</a>"
            ' <span class="tag">' + esc({"skill": "skill"}.get(c.get("kind"), "server")) + "</span>"
            + off + vd + dep + "</div>"
            '<div class="cap__id">' + esc(c["id"]) + "</div></td>"
            '<td><div class="sig' + ("" if t is not None else " sig--none") + '">' + score
            + '<span class="bar"><i style="width:' + str(int(round(t or 0))) + '%"></i></span></div></td>'
            '<td class="num">' + ('<span class="ev">' + esc(ev) + "</span>" if ev
                                  else '<span class="num--dim">\u2014</span>') + "</td>"
            '<td><span class="fresh ' + vcls + '"'
            + (' title="' + esc(vtitle) + '"' if vtitle else "") + ">" + esc(vtxt) + "</span></td>"
            "</tr>")
    out.append("</tbody></table></div></div>")
    return "".join(out)


def cat_page(cat, rows, all_cats, gen):
    label, cid = cat["label"], cat["id"]
    url = BASE + "/category/" + cid + ".html"
    title = "Best " + label + " MCP servers, ranked by the tashan score · tashan"
    desc = ("The " + str(len(rows)) + " " + label.lower() + " MCP servers tashan measures, ranked by tashan score — "
            "upkeep, freshness and real adoption from public evidence. " + cat["blurb"])
    top = ", ".join(pretty(c["name"]) for c in rows[:5])
    lds = [
        {"@context": "https://schema.org", "@type": "ItemList", "name": label + " MCP servers ranked by trust",
         "itemListOrder": "https://schema.org/ItemListOrderDescending", "numberOfItems": len(rows),
         "itemListElement": [
             {"@type": "ListItem", "position": i + 1,
              "item": {"@type": "SoftwareApplication", "name": pretty(c["name"]),
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
        "</b> capabilities here and ranks them by tashan score — a transparent composite of upkeep, "
        "freshness and real adoption. <a class=\"link\" href=\"/methodology.html\">How we measure &rsaquo;</a></p>\n"
        + board(rows) +
        ('<p class="note">' + str(len(measured)) + " of these have been expertise-graded against their "
         "documentation; the rest carry adoption and upkeep signal only. We publish what is "
         "measured and say plainly what isn't.</p>\n" if rows else "")
        + '<h2>Other categories</h2>\n<div class="chips">' + sib + "</div>\n"
        '<p style="margin-top:var(--sp-12)"><a class="btn btn--ghost" href="/">See the full Index &rsaquo;</a></p>\n'
        "</main>\n")
    return head(title, desc, url, lds) + body + FOOT + \
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
    title = "Best MCP servers and skills for " + label.lower() + ", ranked by the tashan score · tashan"
    desc = ("The " + str(len(rows)) + " capabilities tashan measures for " + label.lower() +
            ", ranked by tashan score — upkeep, freshness and real adoption, from public evidence only.")
    top = ", ".join(pretty(c["name"]) for c in rows[:5])
    occs = task.get("occupations") or []
    steps = task.get("onet_steps") or []
    lds = [
        {"@context": "https://schema.org", "@type": "ItemList",
         "name": "Capabilities for " + label + ", ranked by trust",
         "itemListOrder": "https://schema.org/ItemListOrderDescending", "numberOfItems": len(rows),
         "itemListElement": [
             {"@type": "ListItem", "position": i + 1,
              "item": {"@type": "SoftwareApplication", "name": pretty(c["name"]),
                       "url": BASE + "/capability/" + c["slug"] + ".html",
                       "applicationCategory": "DeveloperApplication",
                       "aggregateRating": {"@type": "AggregateRating", "ratingValue": c["tashan_score"],
                                           "bestRating": 100, "worstRating": 0, "ratingCount": 1}}}
             for i, c in enumerate(rows[:25]) if c.get("tashan_score") is not None]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "The Index", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": label, "item": url}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": "What is the best MCP server or skill for " + label.lower() + "?",
             "acceptedAnswer": {"@type": "Answer", "text":
                ("By tashan's measured score: " + top + ". the score combines upkeep and freshness, "
                 "gated by real adoption — every input is public and re-derivable, and no ranking "
                 "position can be purchased.")}},
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
    body = ('<main class="wrap">\n'
        '<p class="kicker"><a class="link" href="/">The Index</a> · ' + esc(label) + "</p>\n"
        "<h1>" + esc(label) + "</h1>\n"
        '<p class="lede">' + esc(task.get("blurb", "")) + " tashan measures <b>" + str(len(rows)) +
        "</b> capabilities for this work and ranks them by tashan score — a transparent composite of "
        "upkeep, freshness and real adoption. "
        '<a class="link" href="/methodology.html">How we measure &rsaquo;</a></p>\n'
        + board(rows) + who
        + '<h2>Other work</h2>\n<div class="chips">' + sib + "</div>\n"
        '<p class="note" style="margin-top:var(--sp-8)">Occupational data from the '
        '<a class="link" rel="nofollow" href="https://www.onetcenter.org/">O*NET 30.3 Database</a> by the '
        "U.S. Department of Labor, Employment and Training Administration, used under "
        '<a class="link" rel="nofollow" href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. '
        "tashan consolidated its process steps into the terms practitioners use; O*NET does not endorse "
        "this site.</p>\n"
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
         "- **tashan score** — composite of upkeep and freshness, gated by real adoption. 0–100.",
         "- **Adoption** — npm download volume (log) blended with config-adoption reach across public repos.",
         "- **Freshness** — recency of the most recent public activity: npm publish, git push, or release.",
         "- **Upkeep** — maintainer count, release cadence and freshness, penalised for deprecated/archived.",
         "- **Expertise** — an LLM grade of the capability's own documentation against a fixed rubric "
         "(deep / solid / thin / wrapper / slop). Only a subset is graded; ungraded means ungraded, not zero.",

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
         "- Permission surface UNDER-reports by design: a server can shell out using Node built-ins "
         "and declare nothing, so an empty result means 'nothing declared', not 'nothing possible'.",         "", "## Top capabilities by measured trust", ""]
    for c in caps[:40]:
        L.append("- [" + pretty(c["name"]) + "](" + BASE + "/capability/" + c["slug"] + ".html) — tashan score "
                 + str(c.get("tashan_score")) + (", " + c["vitality"] if c.get("vitality") else "")
                 + ". " + (c.get("description") or "").replace("\n", " ")[:150])
    # The agent-facing surfaces, announced where a crawler or an agent will actually look. An endpoint
    # nobody can discover is not distribution.
    L += ["", "## For agents", "",
          "- [/v0.1/scores](" + BASE + "/v0.1/scores) — compact lookup, `name -> [score, vitality, "
          "evidence]`, ~50 KB gzipped. Fetch once, look up locally. An absent name is UNMEASURED, not bad.",
          "- [/v0.1/servers](" + BASE + "/v0.1/servers) — full records, byte-compatible with the MCP "
          "registry shape; measurement under the `sh.tashan/measurement` key in `_meta`.",
          "- [/skill/SKILL.md](" + BASE + "/skill/SKILL.md) — install tashan as a capability and call it "
          "when choosing what to install.",
          "", "## Categories", ""]
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


def browse_page(cats, by_cat, tasks, pub, by_task, roles, gen):
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

    out = [head(title, desc, url, lds), icons.sprite(), '<main class="wrap">',
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
                   + ('<span class="browsecard__lead">top: ' + esc(pretty(lead["name"])) + "</span>"
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
        out.append('<div class="browserole"><h3 class="browserole__h mono">'
                   + icons.use("role-" + role_id) + esc(rlabel)
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
        open(os.path.join(OUT_CAT, cat["id"] + ".html"), "w").write(cat_page(cat, rows, cats, gen))
        written += 1
    print("category hubs: %d written (%d categorised capabilities)" % (written, sum(len(v) for v in by_cat.values())))

    # ---- task hubs: one page per job, gated on having a real shelf behind it ----
    tasks = json.load(open(TASKS))["tasks"]
    by_task = {}
    for c in caps:
        for t in (c.get("tasks") or []):
            by_task.setdefault(t["t"], []).append(c)
    for v in by_task.values():
        v.sort(key=lambda x: -(x.get("tashan_score") or 0))
    out_task = os.path.join(ROOT, "web", "task")
    os.makedirs(out_task, exist_ok=True)
    # publishable tasks are the sibling set too — a chip must never link to a page that does not exist
    pub = [t for t in tasks
           if len([c for c in by_task.get(t["slug"], []) if c.get("tashan_score") is not None]) >= TASK_MIN]
    for stale in glob.glob(os.path.join(out_task, "*.html")):
        if os.path.basename(stale)[:-5] not in {t["slug"] for t in pub}:
            os.remove(stale)                     # a task can fall below the gate; leave no orphan behind
    for t in pub:
        rows = by_task.get(t["slug"], [])
        open(os.path.join(out_task, t["slug"] + ".html"), "w").write(task_page(t, rows, pub, gen))
    thin = len(tasks) - len(pub)
    print("task hubs: %d written, %d below the %d-capability floor (listed, not published)"
          % (len(pub), thin, TASK_MIN))


    roles = json.load(open(TASKS)).get("roles", [])
    open(os.path.join(ROOT, "web", "browse.html"), "w").write(
        browse_page(cats, by_cat, tasks, pub, by_task, roles, gen))
    print("browse.html: %d categories + %d tasks indexed (%d hub pages adopted)"
          % (len(by_cat), len(tasks), len(by_cat) + len(pub)))

    open(os.path.join(ROOT, "web", "llms.txt"), "w").write(llms_txt(caps, cats, by_cat, gen))
    print("llms.txt: %d capabilities + %d categories indexed" % (min(40, len(caps)), len(by_cat)))


if __name__ == "__main__":
    main()
