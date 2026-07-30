#!/usr/bin/env python3
"""tashan — prerender static, indexable capability pages + a full sitemap.

The Index's detail pages were client-rendered under ?id= — invisible to crawlers and AI answer engines.
This generates a real file per capability at web/capability/<slug>.html with:
  - a real <title>, meta description, canonical, Open Graph + Twitter tags
  - JSON-LD (SoftwareApplication + AggregateRating + BreadcrumbList + FAQPage) — rich results & AI citation
  - a server-rendered summary (real content crawlers see with JS off)
  - <meta name="cap-id"> so capability.js hydrates the full interactive page for humans
Then regenerates web/sitemap.xml with every page. Runs after build.py's export. Stdlib only.

ponytail: the summary is intentionally a subset of capability.js's render — the JSON-LD carries the
structured data, so we don't duplicate the whole client template in Python. Keep them loosely in sync.
"""
import json, os, re, html, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assets
AV = str(assets.V)   # single source of truth for cache-busting
DATA = os.path.join(ROOT, "web", "data", "capabilities.json")
OUT = os.path.join(ROOT, "web", "capability")
BASE = "https://tashan.sh"
os.makedirs(OUT, exist_ok=True)

# Which /task/ pages actually exist, and their labels. Read from disk rather than recomputed, so
# prerender can never link to a task page gen_hubs declined to write (the population floor means a task
# can drop below the threshold between runs).
def _published_tasks():
    import glob as _g
    have = {os.path.basename(p)[:-5] for p in _g.glob(os.path.join(ROOT, "web", "task", "*.html"))}
    labels = {}
    try:
        for t in json.load(open(os.path.join(ROOT, "web", "data", "tasks.json")))["tasks"]:
            labels[t["slug"]] = t["label"]
    except Exception:
        pass
    return have, labels

TASKS_PUBLISHED, TASK_LABEL = _published_tasks()

CAT = {"browser":"Browser & Web","search":"Search","database":"Database","devtools":"Dev Tools & CI",
       "cloud":"Cloud & Infra","files":"Files & Memory","data":"Data & Analytics","docs":"Docs & Knowledge",
       "comms":"Communication","design":"Design","ai":"AI & Agents","finance":"Finance & Crypto",
       "productivity":"Productivity","security":"Security","other":"Other"}

def slugify(cid): return re.sub(r"[^a-z0-9]+", "-", cid.lower()).strip("-")
def esc(s): return html.escape(str(s), quote=True)
def pretty(name):
    return re.sub(r"^mcp-", "", re.sub(r"^mcp-server-", "", re.sub(r"-mcp$", "",
        re.sub(r"^@modelcontextprotocol/server-", "", str(name)))))

def official_org(c):
    s = ((c.get("npm_pkg") or "") + " " + (c.get("source_repo") or "")).lower()
    if re.search(r"modelcontextprotocol|anthropic", s): return "Anthropic"
    if re.search(r"(^|[/@\s])openai", s): return "OpenAI"
    if re.search(r"google|googleapis|gemini", s): return "Google"
    if re.search(r"(^|[/@\s])microsoft|(^|/)azure", s): return "Microsoft"
    return None

def desc_for(c):
    n = pretty(c["name"])
    d = c.get("description") or (n + " — an AI capability (" + (c.get("kind") or "server") + ") tracked and scored by tashan on public evidence.")
    if c.get("tashan_score") is not None:
        d = d.rstrip(".") + ". tashan score " + str(c["tashan_score"]) + "/100"
        if c.get("expertise_verdict"): d += " · expertise: " + c["expertise_verdict"]
        d += "."
    return d[:300]

def faq(c):
    n = pretty(c["name"]); qa = []
    # Is it safe / trustworthy
    safe = "tashan scores " + n + " on public evidence — "
    parts = []
    if c.get("tashan_score") is not None: parts.append("tashan score " + str(c["tashan_score"]) + "/100")
    if c.get("vitality"): parts.append("it is currently " + c["vitality"])
    if c.get("single_maintainer"): parts.append("note: a single primary maintainer (bus-factor risk)")
    if c.get("gh_archived"): parts.append("warning: the repository is archived")
    # The security audit is real now, so this answer states its findings rather than disclaiming
    # them. It is the single most-repeated answer on the site (~5,800 pages) and the one an answer
    # engine is most likely to quote, so it must be specific about what was checked.
    n_adv = c.get("sec_advisory_count") or 0
    if c.get("sec_scanned_at"):
        if n_adv:
            parts.append("SECURITY: %d known advisor%s against the current release (%s)"
                         % (n_adv, "y" if n_adv == 1 else "ies",
                            (c.get("sec_max_severity") or "unrated").lower()))
        else:
            parts.append("no known advisories against the current release")
        if c.get("sec_install_script"):
            parts.append("it runs a script at install time")
        try:
            perms = json.loads(c.get("sec_permissions") or "[]")
        except (ValueError, TypeError):
            perms = []
        if perms:
            parts.append("its declared dependencies reach: " + ", ".join(perms))
    safe += (", ".join(parts) if parts else "see the measured signals") + \
        ". Audit scope: OSV advisories, install-time scripts, build provenance and declared " \
        "permission surface. We do not review source code or execute the capability."
    qa.append(("Is " + n + " safe and trustworthy?", safe))
    # How to install
    if c.get("kind") == "skill":
        inst = "Drop the skill folder into ~/.claude/skills/ (user scope) or .claude/skills/ (project scope)."
    elif c.get("npm_pkg"):
        inst = "In Claude Code: run `claude mcp add " + re.sub(r'[^a-z0-9_-]', '-', pretty(c['name'])).strip('-') + " -- npx -y " + c["npm_pkg"] + "`. In Cursor / Claude Desktop, add it to mcp.json / claude_desktop_config.json."
    else:
        inst = "Configure it from its source repository — it is a remote / registry server."
    qa.append(("How do I install " + n + "?", inst))
    # Who maintains
    who = []
    if c.get("gh_contributors") is not None: who.append(str(c["gh_contributors"]) + " GitHub contributors")
    if official_org(c): who.append("published by " + official_org(c))
    if c.get("source_repo"): who.append("source: " + c["source_repo"])
    qa.append(("Who maintains " + n + "?", (", ".join(who) if who else "See the linked source repository.") + "."))
    return qa

def jsonld(c):
    n = pretty(c["name"]); url = BASE + "/capability/" + c["slug"] + ".html"
    app = {"@context":"https://schema.org","@type":"SoftwareApplication","name": n,
           "description": desc_for(c), "applicationCategory":"DeveloperApplication",
           "operatingSystem":"Cross-platform","url": url}
    if c.get("source_repo"): app["codeRepository"] = "https://github.com/" + c["source_repo"]
    if c.get("gh_license"): app["license"] = c["gh_license"]
    if c.get("tashan_score") is not None:
        app["aggregateRating"] = {"@type":"AggregateRating","ratingValue": c["tashan_score"],
            "bestRating": 100, "worstRating": 0, "ratingCount": 1,
            "reviewAspect":"tashan tashan score (upkeep + freshness, gated by adoption)"}
    if c.get("npm_pkg"):
        app["offers"] = {"@type":"Offer","price":"0","priceCurrency":"USD"}
    crumbs = {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":"The Index","item": BASE + "/"},
        {"@type":"ListItem","position":2,"name": n, "item": url}]}
    faqld = {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
        {"@type":"Question","name": q, "acceptedAnswer":{"@type":"Answer","text": a}} for q, a in faq(c)]}
    return "\n".join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False) + "</script>"
                     for x in (app, crumbs, faqld))

NAV = ('<nav class="nav"><div class="wrap nav__in">'
       '<a class="brand" href="/"><span class="brand__mark"></span>tashan</a>'
       '<div class="nav__links"><a href="/">Index</a><a href="/start.html">Use it</a>'
       '<a href="/methodology.html">Methodology</a><a href="/learn/">Learn</a>'
       '<a href="/about.html">About</a><a href="/pricing.html">Pricing</a></div></div></nav>')
FOOT = ('<footer class="footer"><div class="wrap footer__in">'
        '<div class="footer__brand"><span class="brand"><span class="brand__mark"></span>tashan</span>'
        '<p class="footer__tag">The measurement layer for AI capabilities — MCP servers and agent skills, '
        'measured on public evidence.</p>'
        '<p class="footer__meta" id="footMethod">public-signal v2</p></div>'
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

def summary(c):
    """Server-rendered content crawlers see with JS off (capability.js replaces it for humans)."""
    n = pretty(c["name"]); rows = []
    def kv(k, v): rows.append("<li><b>" + esc(k) + ":</b> " + esc(v) + "</li>") if v not in (None, "", "—") else None
    kv("tashan score", c.get("tashan_score"))
    kv("Expertise", (str(c["expertise"]) + " (" + c["expertise_verdict"] + ")") if c.get("expertise") is not None and c.get("expertise_verdict") else c.get("expertise"))
    kv("Adoption", (compact(c["npm_downloads"]) + "/wk") if c.get("npm_downloads") is not None else (str(c.get("config_reach")) + " repos" if c.get("config_reach") else None))
    kv("Health", c.get("vitality"))
    kv("GitHub stars", fmt(c.get("gh_stars")) if c.get("gh_stars") is not None else None)
    kv("Contributors", c.get("gh_contributors"))
    kv("License", c.get("gh_license"))
    install = ""
    if c.get("npm_pkg"):
        install = '<p class="install__lbl mono">Install (Claude Code):</p><pre class="install__snip"><code>claude mcp add ' + \
            esc(re.sub(r'[^a-z0-9_-]', '-', n).strip('-')) + ' -- npx -y ' + esc(c["npm_pkg"]) + '</code></pre>'
    verdict = ('<div class="expert-read"><span class="vd vd--' + esc(c["expertise_verdict"]) + '">' + esc(c["expertise_verdict"]) +
               '</span><p>&ldquo;' + esc(c["expertise_note"]) + '&rdquo;</p></div>') if c.get("expertise_note") else ""
    # works-with (protocol-derived) — real content for "does X work with Cursor" queries
    if c.get("kind") == "skill": clients = ["Claude Code", "Cursor", "Codex CLI"]
    elif c.get("kind") == "remote": clients = ["Claude Code", "Cursor", "Claude Desktop", "Codex CLI", "Gemini CLI", "ChatGPT"]
    else: clients = ["Claude Code", "Cursor", "Claude Desktop", "Codex CLI", "Gemini CLI", "Cline", "Windsurf", "VS Code"]
    works = '<p class="mono" style="color:var(--text-faint);font-size:var(--fs-sm)"><b>Works with:</b> ' + esc(", ".join(clients)) + '</p>'
    links = []
    if c.get("npm_pkg"): links.append('<a class="link" href="https://www.npmjs.com/package/' + esc(c["npm_pkg"]) + '">npm ↗</a>')
    if c.get("source_repo"): links.append('<a class="link" href="https://github.com/' + esc(c["source_repo"]) + '">source ↗</a>')
    if c.get("homepage"): links.append('<a class="link" href="' + esc(c["homepage"]) + '" rel="noopener">homepage ↗</a>')
    # the flywheel edge: every capability points at its category hub, which points back at its siblings.
    # Without this the hubs are orphans that only the sitemap knows about.
    cat = ('<p class="mono" style="font-size:var(--fs-sm)"><b>Category:</b> <a class="link" href="/category/'
           + esc(c["category"]) + '.html">' + esc(CAT.get(c["category"], c["category"]))
           + " — see all ranked &rsaquo;</a></p>") if c.get("category") else ""
    # Same edge for the task axis: what WORK is this for. Category says what it touches; this says what
    # you would be doing when you reach for it, and it is the link that keeps /task/ hubs out of orphan
    # status. Only published tasks are linked — TASKS_PUBLISHED holds the ones that cleared gen_hubs'
    # population floor, so a dossier can never point at a page that was never written.
    tsk = [t["t"] for t in (c.get("tasks") or []) if t["t"] in TASKS_PUBLISHED]
    task = ('<p class="mono" style="font-size:var(--fs-sm)"><b>Work:</b> '
            + " · ".join('<a class="link" href="/task/' + esc(s) + '.html">'
                         + esc(TASK_LABEL.get(s, s)) + "</a>" for s in tsk[:4])
            + "</p>") if tsk else ""
    # every dossier offers the next action: check whether YOU are running this, and what else you run.
    # without it a capability page is a dead end — the reader learns about one thing and leaves.
    audit = ('<p class="mono" style="font-size:var(--fs-sm);margin-top:var(--sp-6)"><b>Already running this?</b> '
             '<code>npx tashan-cli doctor</code> checks your whole config against the Index — '
             '<a class="link" href="/start.html">how it works &rsaquo;</a></p>')
    # THE ONE PLACE THE PAID FEATURE IS ACTUALLY WANTED. 266 of these pages describe something
    # archived, deprecated or abandoned, and on every one of them the reader's next thought is "so
    # what do I use instead". Offering the answer there is not an upsell bolted onto a page; it is the
    # question the page just raised. Everywhere else Pro stays out of the way — no banner, no modal,
    # nothing on the 5,521 pages where the reader has no problem to solve.
    dying = (c.get("gh_archived") or c.get("npm_deprecated")
             or c.get("registry_status") in ("deprecated", "deleted") or c.get("vitality") == "abandoned")
    swap = ('<div class="callout" style="margin-top:var(--sp-6)"><b>Looking for a replacement?</b> '
            '<code>npx tashan-cli doctor</code> is free and tells you everything above about your whole '
            'config. <a class="link" href="/pricing.html">tashan Pro</a> names the replacement — which '
            'one, and how it measures. $6/mo.</div>') if dying else ""
    return ('<div class="cap-hd"><a class="back" href="/">&lsaquo; The Index</a>'
            '<h1>' + esc(n) + '</h1>'
            '<div class="cid">' + esc(c["id"]) + ' · <span class="tag">' + esc(c.get("kind") or "") + '</span>' +
            (' <span class="official">✓ ' + esc(official_org(c)) + ' · official</span>' if official_org(c) else '') + '</div>'
            + ('<p class="cap-desc">' + esc(c["description"]) + '</p>' if c.get("description") else '') + '</div>'
            + works + cat + task + install + verdict + swap +
            ('<ul class="prose" style="max-width:none">' + "".join(rows) + '</ul>' if rows else '') +
            ('<p class="mono">' + " &nbsp;·&nbsp; ".join(links) + '</p>' if links else '') + audit)

def compact(n):
    n = n or 0
    if n >= 1e6: return ("%.0f" if n >= 1e7 else "%.1f") % (n / 1e6) + "M"
    if n >= 1e3: return ("%.0f" if n >= 1e4 else "%.1f") % (n / 1e3) + "k"
    return str(n)
def fmt(n): return "{:,}".format(n) if isinstance(n, (int, float)) else n

def page(c, gen):
    n = pretty(c["name"]); url = BASE + "/capability/" + c["slug"] + ".html"
    title = n + " — tashan score " + (str(c["tashan_score"]) if c.get("tashan_score") is not None else "—") + " · tashan"
    d = esc(desc_for(c))
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n"
        '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>" + esc(title) + "</title>\n"
        '<meta name="description" content="' + d + '">\n'
        '<meta name="cap-id" content="' + esc(c["id"]) + '">\n'
        '<meta name="theme-color" content="#0b0b0a">\n'
        '<link rel="canonical" href="' + url + '">\n'
        '<meta property="og:type" content="website">\n'
        '<meta property="og:title" content="' + esc(title) + '">\n'
        '<meta property="og:description" content="' + d + '">\n'
        '<meta property="og:url" content="' + url + '">\n'
        '<meta property="og:image" content="https://tashan.sh/assets/og.png">\n'
        '<meta property="og:image:width" content="1200">\n'
        '<meta property="og:image:height" content="630">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        '<meta name="twitter:image" content="https://tashan.sh/assets/og.png">\n'
        '<meta name="twitter:title" content="' + esc(title) + '">\n'
        '<meta name="twitter:description" content="' + d + '">\n'
        '<link rel="icon" href="/assets/favicon.svg">\n'
        '<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">\n'
        '<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/SpaceGrotesk-Variable.woff2" crossorigin>\n'
        '<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/Geist-Variable.woff2" crossorigin>\n'
        '<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/GeistMono-Variable.woff2" crossorigin>\n'
        '<link rel="stylesheet" href="/css/site.css?v=' + AV + '">\n'
        + jsonld(c) + "\n</head>\n<body>\n" + NAV +
        '<main class="wrap" id="cap">' + summary(c) + "</main>\n" + FOOT +
        inline_data(c, gen) +                                    # this cap's full data, inline — no 1.2 MB fetch
        '<script src="/js/terminal.js?v=' + AV + '" defer></script>\n<script src="/js/site.js?v=' + AV + '" defer></script>\n'
        '<script src="/js/capability.js?v=' + AV + '" defer></script>\n</body>\n</html>\n')

def inline_data(c, gen):
    # a non-executable JSON island the detail page reads directly (CSP-safe). Escape </ so no early </script>.
    payload = json.dumps({"c": c, "at": gen}, ensure_ascii=False).replace("</", "<\\/")
    return '<script type="application/json" id="cap-data">' + payload + "</script>\n"

def bake_hero(caps, total):
    """Write the real counts into index.html's hero, so it is not em-dashes before JS runs.

    The hero is the first thing a visitor reads and it said "— capabilities measured / of — tracked /
    measuring…" until index.js fetched and filled it. On a site whose whole claim is that it has
    measured the field, opening with a dash undersells at exactly the moment it matters, and on a
    failed fetch it never resolves at all. JS still overwrites these with the live values; this only
    changes what is true before it does. Regenerated every run, so it cannot go stale the way a
    hand-typed number would.
    """
    idx = os.path.join(ROOT, "web", "index.html")
    html = open(idx, encoding="utf-8").read()
    when = datetime.now(timezone.utc).strftime("%b %-d")
    for pat, val in ((r'(<b class="k" id="sCaps">)[^<]*(</b>)', f"{len(caps):,}"),
                     (r'(<b id="sRepos">)[^<]*(</b>)', f"{total:,}"),
                     (r'(<span class="dim" id="sDate">)[^<]*(</span>)', when)):
        html = re.sub(pat, lambda m: m.group(1) + val + m.group(2), html, count=1)
    open(idx, "w", encoding="utf-8").write(html)
    print(f"hero: baked {len(caps):,} measured / {total:,} tracked / {when}")


def sitemap(caps):
    # Every hand-written page that is linked and indexable. terms/privacy/refunds/support were added
    # to the footer of all ~5,800 pages and never to this list, so the four pages a buyer looks for
    # before paying were the only ones a crawler could not find. welcome.html stays OUT deliberately —
    # it is the post-checkout page and carries noindex.
    urls = ["/", "/start.html", "/methodology.html", "/about.html", "/pricing.html", "/requests.html",
            "/terms.html", "/privacy.html", "/refunds.html", "/support.html", "/for-hosts.html",
            "/browse.html"]
    static = "".join("  <url><loc>" + BASE + u + "</loc></url>\n" for u in urls)
    caps_x = "".join('  <url><loc>' + BASE + "/capability/" + c["slug"] + '.html</loc>'
                     '<changefreq>weekly</changefreq></url>\n' for c in caps)
    # generated hubs + learn/agents pages if present. These are real indexable pages; leaving them out
    # of the sitemap is how a whole content tier stays invisible to crawlers.
    extra = ""
    for sub in ("learn", "agents", "category", "skills", "task"):
        d = os.path.join(ROOT, "web", sub)
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith(".html"):
                    extra += "  <url><loc>" + BASE + "/" + sub + "/" + f + "</loc></url>\n"
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + static + caps_x + extra + "</urlset>\n")
    open(os.path.join(ROOT, "web", "sitemap.xml"), "w").write(xml)

def main():
    d = json.load(open(DATA))
    gen = d.get("generated_at", "")
    caps = [c for c in d["capabilities"] if c.get("id", "").split(":", 1)[0] != "key"]
    for c in caps:
        c.setdefault("slug", slugify(c["id"]))
    have = {c["slug"] for c in caps}  # only these have prerendered pages
    for c in caps:
        if c.get("co_used"):  # drop co-use links to caps we didn't prerender (would 404 / hit the slow legacy path)
            c["co_used"] = [x for x in c["co_used"] if slugify(x["id"]) in have]
    for c in caps:
        open(os.path.join(OUT, c["slug"] + ".html"), "w").write(page(c, gen))
    # Remove pages for capabilities that dropped out of the export (junk-filtered, deprecated, renamed).
    # Without this they linger as orphans: still crawlable, in no sitemap, linked from nothing, and
    # frozen at whatever asset version last wrote them.
    stale = [f for f in os.listdir(OUT) if f.endswith(".html") and f[:-5] not in have]
    for f in stale:
        os.remove(os.path.join(OUT, f))
    if stale:
        print("removed %d orphaned page(s) no longer in the export" % len(stale))
    sitemap(caps)
    bake_hero(caps, d.get("total_capabilities") or len(caps))
    print("prerendered %d capability pages -> %s" % (len(caps), OUT))
    print("sitemap: %d capability URLs + core pages" % len(caps))

if __name__ == "__main__":
    main()
