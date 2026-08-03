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


def head(title, desc, url, lds):
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
        + ld + "\n</head>\n<body>\n" + nav_for(url))


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
            '<div class="cap__id">' + esc(CAT_LABEL.get(c.get("category") or "", "")) + "</div></td>"
            '<td><div class="sig' + ("" if t is not None else " sig--none") + '">' + score
            + '<span class="bar" data-w="' + str(int(round(t or 0))) + '"><i></i></span></div></td>'
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
    title = "Best " + label + " " + kinds_phrase(rows) + ", ranked by the tashan score · tashan"
    desc = ("The " + str(len(rows)) + " " + label.lower() + " " + kinds_phrase(rows) + " tashan measures, ranked by tashan score — "
            "upkeep, freshness and real adoption from public evidence. " + cat["blurb"])
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
    body = ('<main class="wrap" id="main">\n'
        '<p class="kicker"><a class="link" href="/">The Index</a> · ' + esc(label) + "</p>\n"
        "<h1>" + esc(label) + " " + kinds_phrase(rows, amp=True) + ", ranked</h1>\n"
        '<p class="lede">' + esc(cat["blurb"]) + " tashan measures <b>" + str(len(rows)) +
        "</b> capabilities here and ranks them by tashan score — a transparent composite of upkeep, "
        "freshness and real adoption. <a class=\"link\" href=\"/methodology.html\">How we measure &rsaquo;</a></p>\n"
        + board(rows) +
        ('<p class="note">' + str(len(measured)) + " of these have been expertise-graded against their "
         "documentation; the rest carry adoption and upkeep signal only. We publish what is "
         "measured and say plainly what isn't.</p>\n" if rows else "")
        + (('<h2>Head to head</h2>\n<p class="note">The question people actually ask, answered with '
            'two measurements taken the same day by the same scorer.</p>\n<div class="chips">'
            + "".join('<a class="chip" href="/compare/' + p["slug"] + '.html">'
                      + esc(p["a"]) + " vs " + esc(p["b"]) + "</a>" for p in COMPARE.get(cid, [])[:12])
            + "</div>\n") if COMPARE.get(cid) else "")
        + '<h2>Other categories</h2>\n<div class="chips">' + sib + "</div>\n"
        '<p class="mt-12"><a class="btn btn--ghost" href="/">See the full Index &rsaquo;</a></p>\n'
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
    title = "Best " + kinds_phrase(rows) + " for " + label.lower() + " · tashan"
    desc = ("The " + str(len(rows)) + " capabilities tashan measures for " + label.lower() +
            ", ranked by tashan score — upkeep, freshness and real adoption, from public evidence only.")
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
    body = ('<main class="wrap" id="main">\n'
        '<p class="kicker"><a class="link" href="/">The Index</a> · ' + esc(label) + "</p>\n"
        "<h1>" + esc(label) + "</h1>\n"
        '<p class="lede">' + esc(task.get("blurb", "")) + " tashan measures <b>" + str(len(rows)) +
        "</b> capabilities for this work and ranks them by tashan score — a transparent composite of "
        "upkeep, freshness and real adoption. "
        '<a class="link" href="/methodology.html">How we measure &rsaquo;</a></p>\n'
        + board(rows) + who
        + '<h2>Other work</h2>\n<div class="chips">' + sib + "</div>\n"
        '<p class="note mt-8">Occupational data from the '
        '<a class="link" rel="nofollow" href="https://www.onetcenter.org/">O*NET 30.3 Database</a> by the '
        "U.S. Department of Labor, Employment and Training Administration, used under "
        '<a class="link" rel="nofollow" href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. '
        "tashan consolidated its process steps into the terms practitioners use; O*NET does not endorse "
        "this site.</p>\n"
        '<p class="mt-12"><a class="btn btn--ghost" href="/">See the full Index &rsaquo;</a></p>\n'
        "</main>\n")
    return head(title, desc, url, lds) + body + FOOT + \
        '<script src="/js/terminal.js?v=' + AV + '" defer></script>\n' \
        '<script src="/js/site.js?v=' + AV + '" defer></script>\n</body>\n</html>\n'


def repo_slug(repo): return slugify(repo)


def llms_txt(caps, cats, by_cat, gen, roles=()):
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
         "- **Instruction depth** — an LLM grade of the capability's own documentation against a fixed rubric "
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
         "and declare nothing, so an empty result means 'nothing declared', not 'nothing possible'.",         "", "## Top capabilities by tashan score", ""]
    for c in caps[:40]:
        L.append("- [" + disp(c) + "](" + BASE + "/capability/" + c["slug"] + ".html) — tashan score "
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
          "", "## By job", "",
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
    L += ["", "## Reference", "",
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
            " work, ranked by tashan score — upkeep, freshness and real adoption, all from public "
            "evidence, plus what each one can reach on your machine.")
    top = ", ".join(disp(c) for c in scored[:5])
    work = ", ".join(t["label"].lower() for t in tasks[:6])
    lds = [
        {"@context": "https://schema.org", "@type": "ItemList",
         "name": kinds_phrase(rows).capitalize() + " for " + label.lower() + ", ranked by the tashan score",
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
                 "re-derivable, and no position on this list can be bought.")}},
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
        "<h1>" + kinds_phrase(rows, amp=True).capitalize() + " for " + esc(label.lower()) + ", ranked</h1>\n"
        '<p class="lede">tashan measures <b>' + str(len(rows)) + "</b> capabilities against the work a "
        + esc(label.lower()) + " actually does" + (" — " + esc(work) if work else "") + " — and ranks them "
        "on public evidence alone: upkeep, freshness and real adoption. "
        '<a class="link" href="/methodology.html">How we measure &rsaquo;</a></p>\n'
        + board(rows) +
        ('<p class="note">' + str(len(graded)) + " of these have been expertise-graded against their own "
         "documentation; the rest carry adoption and upkeep signal only. We publish what is measured and "
         "say plainly what is not.</p>\n" if rows else "")
        + ('<h2>The work behind this job</h2>\n<div class="chips">' + chips + "</div>\n" if chips else "")
        + '<h2>Other jobs</h2>\n<div class="chips">' + sib + "</div>\n"
        '<p class="mt-12"><a class="btn btn--ghost" href="/?role=' + esc(rid) +
        '">Open this job on the Index &rsaquo;</a></p>\n'
        "</main>\n")
    return head(title, desc, url, lds) + body + FOOT + \
        '<script src="/js/terminal.js?v=' + AV + '" defer></script>\n' \
        '<script src="/js/site.js?v=' + AV + '" defer></script>\n</body>\n</html>\n'


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
    VERDICT_RANK = {"deep": 0, "solid": 1, None: 2, "thin": 3, "wrapper": 4, "slop": 5}
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
    for stale in glob.glob(os.path.join(out_task, "*.html")):
        if os.path.basename(stale)[:-5] not in {t["slug"] for t in pub}:
            os.remove(stale)                     # a task can fall below the gate; leave no orphan behind
    for t in pub:
        rows = by_task.get(t["slug"], [])
        open(os.path.join(out_task, t["slug"] + ".html"), "w").write(task_page(t, rows, pub, gen))
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
    for stale in glob.glob(os.path.join(out_role, "*.html")):
        if os.path.basename(stale)[:-5] not in {r["id"] for r in pub_roles}:
            os.remove(stale)                     # a job can fall below the gate; leave no orphan behind
    for r in pub_roles:
        open(os.path.join(out_role, r["id"] + ".html"), "w").write(
            role_page(r, by_role.get(r["id"], []), role_tasks.get(r["id"], []), pub_roles, gen))
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
