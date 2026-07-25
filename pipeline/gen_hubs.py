#!/usr/bin/env python3
"""tashan — category hub pages, the skills directory, and llms.txt.

THE FLYWHEEL. Every capability we measure should create indexable surface area, and every new surface
should link back into the ranked data. Concretely:

    capability page  ──▶  its category hub  ──▶  sibling capabilities in that category
           ▲                     │                          │
           └──────── /skills/ ───┴──────── /llms.txt ◀───────┘

- /category/<id>.html   one hub per taxonomy category, listing that category's measured capabilities
                        ranked by trust. Targets the real query shape ("best MCP server for databases")
                        with a live, data-backed ranking rather than a hand-curated opinion list —
                        which is also what makes it citable by answer engines.
- /skills/              the agent-skills directory. Skills are kept OFF the trust board on purpose
                        (see ingest_skills.py: their signals are repo-level, so a 400-skill monorepo
                        would score identically and bury independently-measured servers) — but they
                        are real capabilities people search for, so they get their own ranked-by-source
                        directory that says plainly what is and isn't measured about them.
- /llms.txt             the emerging convention for answer engines: a plain-markdown map of the site
                        with the data inline, so a model can cite tashan without rendering JS.

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
OUT_SKILL = os.path.join(ROOT, "web", "skills")

def esc(s): return html.escape(str(s), quote=True)
def pretty(name):
    return re.sub(r"^mcp-", "", re.sub(r"^mcp-server-", "", re.sub(r"-mcp$", "",
        re.sub(r"^@modelcontextprotocol/server-", "", str(name)))))
def slugify(cid): return re.sub(r"[^a-z0-9]+", "-", str(cid).lower()).strip("-")

NAV = ('<nav class="nav"><div class="wrap nav__in">'
       '<a class="brand" href="/"><span class="brand__mark"></span>tashan<small>v2 · public-signal</small></a>'
       '<div class="nav__links"><a href="/">Index</a><a href="/skills/">Skills</a>'
       '<a href="/methodology.html">Methodology</a>'
       '<a href="/pricing.html">Pricing</a><a href="/learn/">Learn</a><a href="/about.html">About</a></div></div></nav>')
FOOT = ('<footer class="footer"><div class="wrap footer__in">'
        '<div class="footer__brand"><span class="brand"><span class="brand__mark"></span>tashan</span>'
        '<p class="footer__tag">The measured layer for AI capabilities — MCP servers and agent skills, ranked on public evidence.</p></div>'
        '<nav class="footer__col"><p class="footer__h">Explore</p><a href="/">The Index</a><a href="/skills/">Skills</a>'
        '<a href="/learn/">Learn</a><a href="/requests.html">Requests</a></nav>'
        '<nav class="footer__col"><p class="footer__h">Trust</p><a href="/methodology.html">Methodology</a>'
        '<a href="/about.html">About</a><a href="/pricing.html">Pricing</a></nav>'
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
        d = (c.get("description") or "")[:110]
        out.append('<tr><td class="rank">' + str(i + 1) + '</td>'
                   '<td><a class="link" href="' + href + '">' + esc(pretty(c["name"])) + "</a></td>"
                   '<td class="num"><b>' + (str(c["trust"]) if c.get("trust") is not None else "—") + "</b></td>"
                   "<td>" + esc(c.get("vitality") or "—") + "</td>"
                   '<td class="num">' + (str(c["adoption"]) if c.get("adoption") is not None else "—") + "</td>"
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


PER_PAGE = 150      # keeps every generated page under ~70 KB; the 400-skill repos were shipping 300 KB


def skill_page_name(repo, pg):
    return repo_slug(repo) + (("-" + str(pg + 1)) if pg else "") + ".html"


def skill_repo_page(repo, group, pg, pages, gen):
    """One page per source repo, paginated. The single combined page was 375 KB — too heavy to load and
    too unfocused to rank; these are ~40 KB and each targets a real query ("obra superpowers skills")."""
    part = group[pg * PER_PAGE:(pg + 1) * PER_PAGE]
    url = BASE + "/skills/" + skill_page_name(repo, pg)
    suffix = (" (page " + str(pg + 1) + " of " + str(pages) + ")") if pages > 1 else ""
    title = repo + " — " + str(len(group)) + " agent skills, indexed" + suffix + " · tashan"
    desc = ("Every SKILL.md in " + repo + " (" + str(len(group)) + " skills), with descriptions and "
            "direct source links. Agent skills are folders an AI loads on demand." + suffix)
    lds = [
        {"@context": "https://schema.org", "@type": "ItemList", "name": repo + " agent skills",
         "numberOfItems": len(part), "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "name": s["name"],
              "item": {"@type": "SoftwareSourceCode", "name": s["name"],
                       "description": (s.get("description") or "")[:200],
                       "codeRepository": "https://github.com/" + repo}}
             for i, s in enumerate(part[:60])]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "The Index", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Skills", "item": BASE + "/skills/"},
            {"@type": "ListItem", "position": 3, "name": repo, "item": url}]},
    ]
    items = "".join(
        '<li><b>' + esc(s["name"]) + "</b> — " + esc((s.get("description") or "")[:200]) +
        (' <a class="link" href="' + esc(s["homepage"]) + '" rel="noopener">source ↗</a>' if s.get("homepage") else "") +
        "</li>" for s in part)
    pager = ""
    if pages > 1:
        pager = '<nav class="chips" style="margin-top:var(--sp-8)">' + "".join(
            ('<span class="chip chip--on">' + str(i + 1) + "</span>") if i == pg else
            ('<a class="chip" href="/skills/' + skill_page_name(repo, i) + '">' + str(i + 1) + "</a>")
            for i in range(pages)) + "</nav>"
    body = ('<main class="wrap">\n'
        '<p class="kicker"><a class="link" href="/">The Index</a> · '
        '<a class="link" href="/skills/">Skills</a> · ' + esc(repo) + "</p>\n"
        "<h1>" + esc(repo) + "</h1>\n"
        '<p class="lede"><b>' + str(len(group)) + "</b> agent skills indexed from this repository"
        + (", showing " + str(len(part)) + " on this page" if pages > 1 else "") + ". "
        'Install one by copying its folder into <code>~/.claude/skills/</code> (user scope) or '
        "<code>.claude/skills/</code> (project scope).</p>\n"
        '<p><a class="link" href="https://github.com/' + esc(repo) + '" rel="noopener">'
        "View " + esc(repo) + " on GitHub ↗</a></p>\n"
        '<ul class="skills">' + items + "</ul>\n" + pager +
        '<p style="margin-top:var(--sp-12)"><a class="btn btn--ghost" href="/skills/">All skill sources &rsaquo;</a></p>\n'
        "</main>\n")
    return head(title, desc, url, lds) + body + FOOT + \
        '<script src="/js/terminal.js?v=' + AV + '" defer></script>\n' \
        '<script src="/js/site.js?v=' + AV + '" defer></script>\n</body>\n</html>\n'


def skills_page(skills, gen):
    url = BASE + "/skills/"
    title = "Agent Skills directory — every SKILL.md we can find · tashan"
    desc = ("A directory of " + str(len(skills)) + " agent skills (the SKILL.md format Claude and other "
            "agents load on demand), indexed from public repositories with source links.")
    by_repo = {}
    for s in skills:
        by_repo.setdefault(s.get("source_repo") or "unknown", []).append(s)
    lds = [
        {"@context": "https://schema.org", "@type": "ItemList", "name": "Agent Skills directory",
         "numberOfItems": len(skills), "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "name": s["name"],
              "item": {"@type": "SoftwareSourceCode", "name": s["name"],
                       "description": (s.get("description") or "")[:300],
                       "codeRepository": "https://github.com/" + s["source_repo"] if s.get("source_repo") else None}}
             for i, s in enumerate(skills[:40])]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "The Index", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Skills", "item": url}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": "What is an agent skill?",
             "acceptedAnswer": {"@type": "Answer", "text":
                ("A folder containing a SKILL.md file with YAML frontmatter (name, description) that an "
                 "agent loads on demand. Unlike an MCP server it runs no process — it is instruction "
                 "content the model reads when the task matches. Install by dropping the folder into "
                 "~/.claude/skills/ for user scope or .claude/skills/ inside a project.")}},
            {"@type": "Question", "name": "Are skills scored like MCP servers?",
             "acceptedAnswer": {"@type": "Answer", "text":
                ("No, and we don't pretend otherwise. A skill is a folder inside a repository, so the only "
                 "public maintenance signal available is the repository's — every skill in a monorepo would "
                 "share one score. Skills are therefore listed and grouped by source rather than ranked on "
                 "the trust board.")}}]},
    ]
    sections = []
    # Official sources first, then by size. Sorting purely by count led the directory with 400
    # auto-generated "*-automation" stubs and buried Anthropic's own skills — the opposite of the
    # signal a quality-first index should send.
    def rank(kv):
        repo = kv[0]
        return (0 if repo.startswith("anthropics/") else 1, -len(kv[1]), repo)
    for repo, group in sorted(by_repo.items(), key=rank):
        sample = ", ".join(s["name"] for s in sorted(group, key=lambda x: x["name"])[:10])
        sections.append(
            '<h2><a class="link" href="/skills/' + repo_slug(repo) + '.html">' + esc(repo) + "</a> "
            '<small class="muted">' + str(len(group)) + " skills</small></h2>\n"
            "<p>" + esc(sample) + ("…" if len(group) > 10 else "") + "</p>\n"
            '<p><a class="link" href="/skills/' + repo_slug(repo) + '.html">'
            "Browse all " + str(len(group)) + " &rsaquo;</a></p>\n")
    body = ('<main class="wrap">\n'
        '<p class="kicker"><a class="link" href="/">The Index</a> · Skills</p>\n'
        "<h1>Agent Skills directory</h1>\n"
        '<p class="lede"><b>' + str(len(skills)) + "</b> skills indexed from public repositories. A skill is a "
        "<code>SKILL.md</code> folder an agent loads on demand — no process, no install step beyond dropping "
        "the folder into <code>~/.claude/skills/</code>.</p>\n"
        '<div class="callout"><b>What we do not claim.</b> These are catalogued, not trust-ranked. A skill '
        "lives inside a repository, so the only public maintenance evidence is that repository's — every "
        "skill in a 400-skill monorepo would carry an identical score. Publishing that as a per-skill "
        "ranking would be a number with no meaning behind it, so we don't. "
        '<a class="link" href="/methodology.html">What we do measure &rsaquo;</a></div>\n'
        + "".join(sections) +
        '<p style="margin-top:var(--sp-12)"><a class="btn btn--ghost" href="/">See the ranked Index &rsaquo;</a></p>\n'
        "</main>\n")
    return head(title, desc, url, lds) + body + FOOT + \
        '<script src="/js/terminal.js?v=' + AV + '" defer></script>\n' \
        '<script src="/js/site.js?v=' + AV + '" defer></script>\n</body>\n</html>\n'


def llms_txt(caps, cats, by_cat, skills, gen):
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
    L += ["", "## Agent skills", "",
          "- [Skills directory](" + BASE + "/skills/) — " + str(len(skills)) + " SKILL.md capabilities "
          "indexed from public repositories. Catalogued, not trust-ranked: a skill inside a monorepo has "
          "only its repository's maintenance signal, so a per-skill score would be meaningless.",
          "", "## Reference", "",
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
    caps = [c for c in d["capabilities"] if c.get("trust") is not None]
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

    # skills come from the DB, not the export (they're deliberately off the trust board)
    skills = []
    try:
        import sqlite3
        con = sqlite3.connect("file:" + os.path.join(ROOT, "data", "tashan.db") + "?mode=ro", uri=True)
        skills = [{"name": n, "description": de, "source_repo": sr, "homepage": hp}
                  for n, de, sr, hp in con.execute(
                      "SELECT name, description, source_repo, homepage FROM capabilities "
                      "WHERE kind='skill' ORDER BY name")]
        con.close()
    except Exception as e:
        print("  (skills unavailable: %s)" % e)
    if skills:
        os.makedirs(OUT_SKILL, exist_ok=True)
        open(os.path.join(OUT_SKILL, "index.html"), "w").write(skills_page(skills, gen))
        by_repo = {}
        for s in skills:
            by_repo.setdefault(s.get("source_repo") or "unknown", []).append(s)
        npages = 1
        for repo, group in by_repo.items():
            group = sorted(group, key=lambda x: x["name"])
            pages = max(1, -(-len(group) // PER_PAGE))
            for pg in range(pages):
                open(os.path.join(OUT_SKILL, skill_page_name(repo, pg)), "w").write(
                    skill_repo_page(repo, group, pg, pages, gen))
                npages += 1
        print("skills directory: %d skills across %d repos (%d pages)"
              % (len(skills), len(by_repo), npages))

    open(os.path.join(ROOT, "web", "llms.txt"), "w").write(llms_txt(caps, cats, by_cat, skills, gen))
    print("llms.txt: %d capabilities + %d categories indexed" % (min(40, len(caps)), len(by_cat)))


if __name__ == "__main__":
    main()
