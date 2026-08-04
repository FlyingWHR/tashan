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
from urllib.parse import quote
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assets
import chrome
AV = str(assets.V)   # single source of truth for cache-busting
SCORER = ""          # which ruler produced these numbers; read from the export in main()
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


def _published_roles():
    import glob as _g
    have = {os.path.basename(p)[:-5] for p in _g.glob(os.path.join(ROOT, "web", "role", "*.html"))}
    labels, t2r = {}, {}
    try:
        d = json.load(open(os.path.join(ROOT, "web", "data", "tasks.json")))
        labels = {r["id"]: r["label"] for r in d.get("roles", [])}
        t2r = {t["slug"]: (t.get("roles") or []) for t in d["tasks"]}
    except Exception:
        pass
    return have, labels, t2r

ROLES_PUBLISHED, ROLE_LABEL, TASK_ROLES = _published_roles()

CAT = {"browser":"Browser & Web","search":"Search","database":"Database","devtools":"Dev Tools & CI",
       "cloud":"Cloud & Infra","files":"Files & Memory","data":"Data & Analytics","docs":"Docs & Knowledge",
       "comms":"Communication","design":"Design","ai":"AI & Agents","finance":"Finance & Crypto",
       "productivity":"Productivity","security":"Security","other":"Other"}

def slugify(cid): return re.sub(r"[^a-z0-9]+", "-", cid.lower()).strip("-")
def esc(s): return html.escape(str(s), quote=True)
def pretty(name):
    return re.sub(r"^mcp-", "", re.sub(r"^mcp-server-", "", re.sub(r"-mcp$", "",
        re.sub(r"^@modelcontextprotocol/server-", "", str(name)))))

def disp(c):
    """The human label, computed once in build.py's apply_labels over the whole corpus and shipped in
    the export. pretty() stays below for the one place that needs an IDENTIFIER — the `claude mcp add`
    server name — where a space or a "·" would be wrong."""
    return c.get("label") or pretty(c.get("name") or "")


def official_org(c):
    """READ the export's answer; never re-derive it.

    This function used to carry its own copy of the rule, and it was the OLD one: a bare substring
    match that badged @atomicmail/mcp-modelcontextprotocol as Anthropic. build.py's official_of was
    fixed to anchor on the namespace (165 badges -> 137) and index.js was switched to read the
    exported field, but this copy and capability.js were missed — so 88 canonical, indexed dossiers
    were still claiming "✓ Anthropic · official" for packages the board itself showed as unaffiliated.
    The same page, contradicting the board, about a real company's endorsement.

    An endorsement claim gets exactly one definition. It lives in build.py::official_of, it is
    resolved once at export time, and every surface reads the answer."""
    return c.get("official") or None

MAX_DESC = 300


def _clip(d, limit):
    """Trim to `limit` on a word boundary, ending in a single ellipsis. Never mid-word: the no-score
    path used a bare slice and shipped "...split view with current sl"."""
    cut = d[:limit - 1]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > limit * 0.6 else cut).rstrip(" ,;:.-") + "…"


def desc_for(c):
    """The meta description. TRUNCATE THE PROSE, NEVER THE CLAIM.

    This used to append the score and then cut the whole string at 300 characters, so any capability
    with a long description had its own score chopped in half: six pages shipped `…tashan score 3"`
    for a capability scoring 37. That string is what a search result and an answer engine quote,
    which makes a truncated number worse than none — it is a wrong measurement published in the one
    place we cannot correct after the fact.

    Build the claim first, fit the prose around it, and join on a word boundary with exactly one
    piece of punctuation.
    """
    n = disp(c)
    d = (c.get("description")
         or n + " — an AI capability (" + (c.get("kind") or "server")
         + ") tracked and scored by tashan on public evidence.")
    d = re.sub(r"\s+", " ", d).strip()
    # build.py's 500-char cap leaves some descriptions ending ".…" already; carrying that through
    # renders "issue management.… tashan score 34.0/100." Normalise before anything else appends.
    d = re.sub(r"[.,;:\-]+…", "…", d)

    claim = ""
    if c.get("tashan_score") is not None:
        claim = "tashan score " + str(c["tashan_score"]) + "/100"
        if c.get("expertise_verdict"):
            claim += " · expertise: " + c["expertise_verdict"]
        claim += "."
    if not claim:
        return d if len(d) <= MAX_DESC else _clip(d, MAX_DESC)

    room = MAX_DESC - len(claim) - 1               # -1 for the single separating space
    d = d.rstrip(" .")
    if len(d) > room:
        d = _clip(d, room)
    elif d and d[-1] not in ".!?…":
        # Many descriptions arrive ALREADY truncated with an ellipsis by build.py's 500-char cap, and
        # appending a full stop to those produced "issue management.…. tashan score 34.0/100." on 84
        # pages. Only punctuate a sentence that has not punctuated itself.
        d += "."
    return d + " " + claim


def _selfcheck_markdown():
    """The .md dossier must never imply safety it has not established, and must agree with the HTML.

    An answer engine reads these instead of the page. The two failure modes that matter: printing an
    install command for something discontinued, and OMITTING the security section when nothing was
    scanned — an absent line reads as "fine" to a summariser, which is the one thing this site must
    never imply. Both are asserted here rather than eyeballed.
    """
    base = {"id": "pkg:x", "slug": "pkg-x", "name": "x", "label": "X", "kind": "npm",
            "npm_pkg": "x", "tashan_score": 50.0, "coverage": 1.0}
    md = markdown(dict(base), "2026-08-04T00:00:00Z")
    assert "claude mcp add x -- npx -y x" in md, md
    assert "Not scanned." in md, "an unscanned capability must SAY so, not omit the section"
    assert "not yet graded" in md, "an ungraded capability must say so rather than drop the line"

    # discontinued: no install command anywhere in the document
    gone = markdown(dict(base, discontinued=True), "2026-08-04T00:00:00Z")
    assert "npx -y" not in gone and "## Install" not in gone, gone

    # a plugin prints the two-step form, and it must match install_cmd() used by the HTML
    plug = dict(base, kind="plugin", npm_pkg=None, plugin_market_repo="o/r", title="mkt", name="p")
    assert "/plugin marketplace add o/r" in markdown(plug, "") and "/plugin install p@mkt" in markdown(plug, "")

    # permissions are a JSON STRING in the export — joining it raw spells them one letter at a time
    perm = markdown(dict(base, sec_advisory_count=0, sec_permissions='["credentials", "network"]'), "")
    assert "credentials, network" in perm, perm
    print("ok — markdown dossier: install matches install_cmd, unknowns stated, permissions parsed")


def _selfcheck():
    """One runnable check: the score survives intact at every description length."""
    for n in (0, 50, 240, 299, 300, 500):
        out = desc_for({"description": "word " * (n // 5) or None, "tashan_score": 37.0,
                        "name": "x", "label": "X"})
        assert out.endswith("tashan score 37.0/100."), (n, out[-40:])
        assert len(out) <= MAX_DESC, (n, len(out))
        assert ".…" not in out and "…." not in out and ".." not in out, (n, out[-40:])
    # a description that already ends in an ellipsis must not collect a second full stop
    pre = desc_for({"description": "Already cut short…", "tashan_score": 5.0, "name": "x", "label": "X"})
    assert pre == "Already cut short… tashan score 5.0/100.", pre
    assert desc_for({"description": "Short.", "tashan_score": 12.0, "name": "x", "label": "X"}) \
        == "Short. tashan score 12.0/100."
    return True


def faq(c):
    n = disp(c); qa = []
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
    # The structured answer must agree with the page. This shipped "In Claude Code: run `claude mcp
    # add docfork …`" inside the FAQPage JSON-LD of a dossier whose body said DISCONTINUED — DO NOT
    # INSTALL, which is the worst possible split: the human sees the warning and the answer engine
    # quoting us reads the install command.
    if c.get("discontinued"):
        inst = ("Don't. This capability has been discontinued by its author or publisher and is not "
                "scored or recommended. If you are already running it, `npx tashan-cli doctor` will "
                "flag it and name what to move to.")
    elif c.get("kind") == "skill":
        inst = "Drop the skill folder into ~/.claude/skills/ (user scope) or .claude/skills/ (project scope)."
    elif c.get("npm_pkg"):
        inst = "In Claude Code: run `claude mcp add " + chrome.alias(c["name"]) + " -- npx -y " + c["npm_pkg"] + "`. In Cursor / Claude Desktop, add it to mcp.json / claude_desktop_config.json."
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
    n = disp(c); url = BASE + chrome.canon("/capability/" + c["slug"] + ".html")
    app = {"@context":"https://schema.org","@type":"SoftwareApplication","name": n,
           "description": desc_for(c), "applicationCategory":"DeveloperApplication",
           "operatingSystem":"Cross-platform","url": url}
    if c.get("source_repo"): app["codeRepository"] = "https://github.com/" + c["source_repo"]
    if c.get("gh_license"): app["license"] = c["gh_license"]
    if c.get("tashan_score") is not None:
        # A Review, NOT an aggregateRating. aggregateRating means "the mean of ratings left by
        # reviewers"; we had one with ratingCount:1 on 6,586 pages, which claims a crowd that does not
        # exist and is the exact self-serving-rating pattern Google's structured-data policy rejects.
        # The tashan score is one named party's measurement, so it is modelled as one named party's
        # review — attributed, dated, and traceable to its sources. Same number, honest shape.
        app["review"] = {"@type":"Review",
            "author": {"@type":"Organization","name":"tashan","url": BASE + "/"},
            "reviewRating": {"@type":"Rating","ratingValue": c["tashan_score"],
                             "bestRating": 100, "worstRating": 0},
            "reviewAspect":"tashan score — upkeep and freshness, gated by adoption",
            "reviewBody": desc_for(c), "url": url}
    if c.get("npm_pkg"):
        app["offers"] = {"@type":"Offer","price":"0","priceCurrency":"USD"}
    crumbs = {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":"The Index","item": BASE + "/"},
        {"@type":"ListItem","position":2,"name": n, "item": url}]}
    faqld = {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
        {"@type":"Question","name": q, "acceptedAnswer":{"@type":"Answer","text": a}} for q, a in faq(c)]}
    return "\n".join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False) + "</script>"
                     for x in (app, crumbs, faqld))

NAV = chrome.nav_html()
FOOT = chrome.footer_html()

def summary(c, gen=""):
    """Server-rendered content crawlers see with JS off (capability.js replaces it for humans)."""
    n = disp(c); rows = []
    def kv(k, v): rows.append("<li><b>" + esc(k) + ":</b> " + esc(v) + "</li>") if v not in (None, "", "—") else None
    kv("tashan score", c.get("tashan_score"))
    kv(chrome.FIELD_LABEL,
       (str(c["expertise"]) + " (" + chrome.VERDICT_LABEL.get(c["expertise_verdict"], c["expertise_verdict"])
        + " — " + chrome.VERDICT_BLURB.get(c["expertise_verdict"], "") + ")")
       if c.get("expertise") is not None and c.get("expertise_verdict") else c.get("expertise"))
    kv("Adoption", (compact(c["npm_downloads"]) + "/wk") if c.get("npm_downloads") is not None else (str(c.get("config_reach")) + " repos" if c.get("config_reach") else None))
    # EVERY INPUT TO THE SCORE, on the page, in the STATIC tier. methodology.html promises "every
    # input is shown on the capability page" and this render carried the result and two of its
    # inputs. capability.js showed Upkeep and Freshness, so a human with JS saw them and every
    # crawler and answer engine — the readers this tier exists for — saw a bare number with no
    # working. Coverage is here too, and it is the one that most needed showing: it discounts the
    # score by up to 30% for thin evidence, and it was computed and discarded without ever being
    # persisted, so no surface could have displayed it.
    kv("Upkeep", c.get("upkeep"))
    kv("Freshness", c.get("freshness"))
    kv("Evidence coverage", (str(int(round(c["coverage"] * 100))) + "% of the inputs this score can use"
                             + ("" if c["coverage"] >= 1 else " — the rest are unknown, and the score is "
                                "discounted for it")) if c.get("coverage") is not None else None)
    kv("Health", c.get("vitality"))
    kv("GitHub stars", fmt(c.get("gh_stars")) if c.get("gh_stars") is not None else None)
    kv("Contributors", c.get("gh_contributors"))
    kv("License", c.get("gh_license"))
    install = ""     # remote/registry rows reach neither branch below and must still be defined
    # DISCONTINUED: say so, loudly, and offer no way to install it. This page exists so an indexed
    # URL keeps answering and so someone already running the thing finds out — not to help anyone
    # start. The notice is the author's own words, quoted rather than paraphrased.
    if c.get("discontinued"):
        note = c.get("self_unmaintained") or c.get("description") or ""
        gone = ('<div class="callout callout--stop"><b>Discontinued — do not install.</b> '
                + ("The author's own notice: &ldquo;" + esc(clip_notice(note)) + "&rdquo; "
                   if note else "")
                + "It stays listed so anyone already running it can find this page, and so "
                  "<code>npx tashan-cli doctor</code> can warn about it. It is not scored and does "
                  "not appear in any ranking.</div>")
        install = gone
    # Same omission as the plugin branch below, found by the same guard: capability.js offers skill
    # readers `cp -r …` and this render offered nothing, so the command was invisible to anything that
    # does not run JS. alias() is the shared derivation both sides already use.
    elif c.get("kind") == "skill":
        install = ('<p class="install__lbl mono">Install (Claude Code):</p><pre class="install__snip"><code>'
                   'cp -r ' + esc(chrome.alias(c["name"])) + ' ~/.claude/skills/</code></pre>')
    elif c.get("npm_pkg"):
        install = '<p class="install__lbl mono">Install (Claude Code):</p><pre class="install__snip"><code>claude mcp add ' + \
            esc(chrome.alias(c["name"])) + ' -- npx -y ' + esc(c["npm_pkg"]) + '</code></pre>'
    # A PLUGIN IS NOT A REMOTE SERVER. There was no branch here at all, so the crawled HTML of 3,624
    # plugin pages carried no install path — while capability.js, which replaces this render, fell
    # through to its npm-less catch-all and told the reader to "configure it from its source" as if it
    # were a hosted endpoint. Answer engines largely do not run JS, so the single most useful line on
    # the page was missing from the document they actually read. Mirrors capability.js::installBlock.
    elif c.get("kind") == "plugin" and c.get("plugin_market_repo") and c.get("title"):
        install = ('<p class="install__lbl mono">Install (Claude Code):</p><pre class="install__snip"><code>'
                   '/plugin marketplace add ' + esc(c["plugin_market_repo"]) + '\n'
                   '/plugin install ' + esc(c["name"]) + '@' + esc(c["title"]) + '</code></pre>')
    # The graded read, using the one chip definition — this site was missed when the others moved to
    # chrome.verdict_chip, so two dossiers still rendered a bare "slop" while every other surface
    # said "low-quality".
    verdict = ('<div class="expert-read">' + chrome.verdict_chip(c.get("expertise_verdict"))
               + '<p>&ldquo;' + esc(c["expertise_note"]) + '&rdquo;</p></div>') if c.get("expertise_note") else ""
    # COMPATIBILITY, WITH ITS LEVEL AND ITS BASIS. This printed a flat list of client names derived
    # from `kind` alone, so every npm-backed capability in the corpus claimed the same eight clients
    # and "Works with VS Code" shipped on thousands of pages nobody had checked. A level says what is
    # actually being claimed; the basis says who is promising it. Mirrors capability.js::worksWith —
    # the client REPLACES this render, so the two must say the same thing.
    kind = c.get("kind")
    if kind == "plugin":
        groups = [("native", ["Claude Code"])]
    elif kind == "skill":
        groups = [("native", ["Claude Code"]), ("manual", ["Cursor", "Codex CLI"])]
    elif kind == "remote":
        groups = [("installable", ["Claude Code", "Cursor", "Claude Desktop", "Codex CLI",
                                   "Gemini CLI", "ChatGPT"])]
    else:
        groups = [("installable", ["Claude Code", "Cursor", "Claude Desktop", "Codex CLI",
                                   "Gemini CLI", "Cline", "Windsurf", "VS Code"])]
    works = ('<p class="mono fs-sm faint"><b>Works with:</b> '
             + " &nbsp;·&nbsp; ".join(esc(", ".join(names)) + " <i>(" + lvl + ")</i>"
                                      for lvl, names in groups)
             + '<br><span class="o-50">'
             + ("native: this artifact type is that client's own format"
                if kind in ("plugin", "skill") else
                "installable: each client documents how to load an MCP server of this type — "
                "that is the client's promise, not a claim verified against this capability")
             + "</span></p>")
    links = []
    if c.get("npm_pkg"): links.append('<a class="link" href="https://www.npmjs.com/package/' + esc(c["npm_pkg"]) + '">npm ↗</a>')
    if c.get("source_repo"): links.append('<a class="link" href="https://github.com/' + esc(c["source_repo"]) + '">source ↗</a>')
    if c.get("homepage"): links.append('<a class="link" href="' + esc(c["homepage"]) + '" rel="noopener">homepage ↗</a>')
    links.append('<span class="capid" title="the id the CLI and API use">' + esc(c["id"]) + '</span>')
    # the flywheel edge: every capability points at its category hub, which points back at its siblings.
    # Without this the hubs are orphans that only the sitemap knows about.
    cat = ('<p class="mono fs-sm"><b>Category:</b> <a class="link" href="/category/'
           + esc(c["category"]) + '.html">' + esc(CAT.get(c["category"], c["category"]))
           + " — see all ranked &rsaquo;</a></p>") if c.get("category") else ""
    # Same edge for the task axis: what WORK is this for. Category says what it touches; this says what
    # you would be doing when you reach for it, and it is the link that keeps /task/ hubs out of orphan
    # status. Only published tasks are linked — TASKS_PUBLISHED holds the ones that cleared gen_hubs'
    # population floor, so a dossier can never point at a page that was never written.
    tsk = [t["t"] for t in (c.get("tasks") or []) if t["t"] in TASKS_PUBLISHED]
    task = ('<p class="mono fs-sm"><b>Work:</b> '
            + " · ".join('<a class="link" href="/task/' + esc(s) + '.html">'
                         + esc(TASK_LABEL.get(s, s)) + "</a>" for s in tsk[:4])
            + "</p>") if tsk else ""
    roles_for = []
    for t in (c.get("tasks") or []):
        for rid in TASK_ROLES.get(t["t"], []):
            if rid in ROLES_PUBLISHED and rid not in roles_for:
                roles_for.append(rid)
    job = ('<p class="mono fs-sm"><b>Who it is for:</b> '
           + " · ".join('<a class="link" href="/role/' + esc(r) + '.html">'
                        + esc(ROLE_LABEL.get(r, r)) + "</a>" for r in roles_for[:3])
           + "</p>") if roles_for else ""
    # every dossier offers the next action: check whether YOU are running this, and what else you run.
    # without it a capability page is a dead end — the reader learns about one thing and leaves.
    audit = ('<p class="mono fs-sm mt-6"><b>Already running this?</b> '
             '<code>npx tashan-cli doctor</code> checks your whole config against the Index — '
             '<a class="link" href="/start.html">how it works &rsaquo;</a></p>')
    # THE ONE PLACE THE PAID FEATURE IS ACTUALLY WANTED. 266 of these pages describe something
    # archived, deprecated or abandoned, and on every one of them the reader's next thought is "so
    # what do I use instead". Offering the answer there is not an upsell bolted onto a page; it is the
    # question the page just raised. Everywhere else Pro stays out of the way — no banner, no modal,
    # nothing on the 5,521 pages where the reader has no problem to solve.
    dying = (c.get("gh_archived") or c.get("npm_deprecated")
             or c.get("registry_status") in ("deprecated", "deleted") or c.get("vitality") == "abandoned")
    swap = ('<div class="callout mt-6"><b>Looking for a replacement?</b> '
            '<code>npx tashan-cli doctor</code> is free and tells you everything above about your whole '
            'config. <a class="link" href="/pricing.html">tashan Pro</a> names the replacement — which '
            'one, and how it measures. $6/mo.</div>') if dying else ""
    return ('<div class="cap-hd"><a class="back" href="/">&lsaquo; The Index</a>'
            '<h1>' + esc(n) + '</h1>'
            # The id used to lead this line, one long restatement of the <h1> right above it —
            # "sequential-thinking" followed by "pkg:@modelcontextprotocol/server-sequential-thinking",
            # with the same string a third time in the install command below. It is a machine key, so
            # it moved down to the links row where someone reaching for it is already looking.
            '<div class="cid"><span class="tag">' + esc(c.get("kind") or "") + '</span>' +
            (' <span class="official">✓ ' + esc(official_org(c)) + ' · official</span>' if official_org(c) else '') + '</div>'
            + ('<p class="cap-desc">' + esc(c["description"]) + '</p>' if c.get("description") else '') + '</div>'
            + works + cat + task + job + install + verdict + swap +
            ('<ul class="prose prose--wide">' + "".join(rows) + '</ul>' if rows else '') +
            # The security audit goes BEFORE the CTA and the link row: it is the measurement the
            # page exists to publish, and it was previously absent from this tier entirely.
            security_block(c)
            + ('<p class="mono">' + " &nbsp;·&nbsp; ".join(links) + '</p>' if links else '') + audit
            # WHEN THIS WAS MEASURED, in the static file. capability.js prints it in its closing
            # callout, but that is client-side only — so every crawler and answer engine we court in
            # llms.txt read 5,788 pages of measurements with no date attached to any of them. A
            # measurement without an as-of date is not a measurement, it is an assertion.
            + ('<p class="mono fs-sm faint">Measured ' + esc(gen[:10]) + ' &nbsp;·&nbsp; scorer '
               + esc(SCORER) + ' &nbsp;·&nbsp; '
               '<a class="link" href="/methodology.html">how</a> &nbsp;·&nbsp; '
               '<a class="link" href="/support.html?ref=' + quote(c["id"], safe="") + '#corrections">'
               'something wrong here?</a></p>' if gen else ''))

def clip_notice(t):
    """One line of the author's notice — enough to be quoted, not a wall of README."""
    t = re.sub(r"\s+", " ", str(t or "")).strip()
    return t if len(t) <= 200 else t[:199].rsplit(" ", 1)[0] + "\u2026"


def compact(n):
    n = n or 0
    if n >= 1e6: return ("%.0f" if n >= 1e7 else "%.1f") % (n / 1e6) + "M"
    if n >= 1e3: return ("%.0f" if n >= 1e4 else "%.1f") % (n / 1e3) + "k"
    return str(n)
def fmt(n): return "{:,}".format(n) if isinstance(n, (int, float)) else n

PERM_LABEL = {
    "filesystem": "Reads and writes files", "shell": "Runs shell commands",
    "network": "Makes network requests", "browser": "Drives a browser",
    "database": "Connects to databases", "credentials": "Handles credentials or secrets",
    "cloud": "Talks to cloud provider APIs",
}
SEV_CLS = {"MALICIOUS": "sev--mal", "CRITICAL": "sev--crit", "HIGH": "sev--high",
           "MODERATE": "sev--mod", "MEDIUM": "sev--mod", "LOW": "sev--low"}


def security_block(c):
    """The security audit, ON THE CANONICAL PAGE.

    It existed only in capability.js, which rewrites the dossier client-side — so a person saw it and
    a crawler did not. The prerendered tier exists precisely so answer engines and search can read
    what we measure, and the one measurement nobody else publishes was the one thing missing from it.
    A reader with JS off saw nothing either.

    Mirrors capability.js::securityBlock row for row, including the free/paid line: the EXISTENCE of
    every finding is stated in full and only the detail needed to act is gated. Hiding the existence
    of a vulnerability behind a paywall would be indefensible for a product whose claim is that it
    tells you the truth about what you run.
    """
    def sec_row(label, value="", detail="", cls=""):
        return ('<div class="secrow' + ((" " + cls) if cls else "") + '">'
                '<span class="secrow__l">' + label + "</span>"
                '<span class="secrow__v mono">' + value + "</span>"
                '<span class="secrow__d">' + detail + "</span></div>")

    def advisory_detail(cap):
        """Name every advisory: its id, and the version that fixes it. Free.

        This was an "unlock detail" link to /pricing.html. Telling a reader that their package has a
        known vulnerability and then charging them to learn WHICH one is the one thing an independent
        rater cannot do — see build.py::redact_paid."""
        try:
            adv = json.loads(cap["sec_advisories"]) if cap.get("sec_advisories") else []
        except (ValueError, TypeError):
            adv = []
        if not adv:
            return '<span class="secrow__ok">see the advisory database for detail</span>'
        out = []
        for a in adv[:6]:
            fixed = a.get("fixed")
            out.append('<code>' + esc(a.get("id") or "?") + "</code> "
                       + ("fixed in " + esc(fixed) if fixed else "no fix published"))
        return '<span class="secrow__ok">' + " · ".join(out) + "</span>"

    def sec(title, body, sub, aside=""):
        return ('<section class="capsec"><div class="capsec__hd"><h2>' + title + "</h2>"
                + ('<span class="capsec__aside">' + esc(aside) + "</span>" if aside else "")
                + "</div>"
                + ('<p class="capsec__sub">' + sub + "</p>" if sub else "") + body + "</section>")

    if not c.get("sec_scanned_at"):
        # NEVER imply an audit happened. Say plainly that it did not, and why.
        return sec("Security audit",
                   '<p class="hubnote">Not scanned yet. We audit npm-published capabilities for known '
                   "advisories, install-time scripts and permission surface; this one has no npm "
                   "package we can resolve, or has not reached the queue.</p>", "")

    try:
        perms = json.loads(c["sec_permissions"]) if c.get("sec_permissions") else []
    except Exception:
        perms = []

    rows = []
    n = c.get("sec_advisory_count") or 0
    if n:
        sv = c.get("sec_max_severity") or "UNKNOWN"
        rows.append(sec_row(
            "<b>" + str(n) + " known advisor" + ("y" if n == 1 else "ies") + "</b>",
            '<span class="sev ' + SEV_CLS.get(sv, "") + '">' + esc(sv.lower()) + "</span>",
            advisory_detail(c),
            "secrow--alert"))
    else:
        rows.append(sec_row("No known advisories", '<span class="sev sev--none">clear</span>',
                            '<span class="secrow__ok">checked against OSV for '
                            + esc(c.get("npm_latest_version") or "the current release") + "</span>"))

    if c.get("sec_install_script"):
        scr = c.get("sec_install_script")
        rows.append(sec_row("<b>Runs a script at install time</b>",
                            '<span class="sev sev--high">code</span>',
                            ('<code class="secrow__cmd">' + esc(scr) + "</code>"
                             if isinstance(scr, str) else
                             '<span class="secrow__ok">a script runs on install</span>'),
                            "secrow--alert"))

    if perms:
        # only the first permission is exported now (the full list is the paid detail), so the total
        # comes from sec_perm_n — see build.py::redact_paid.
        # every permission, free — see build.py::redact_paid for why this is not gated
        rows.append(sec_row(
            esc(" · ".join(PERM_LABEL.get(x, x) for x in perms)), "",
            '<span class="secrow__ok">from declared dependencies</span>'))
    else:
        # "No permission surface detected" was reassurance dressed as a measurement. This layer
        # reads DECLARED DEPENDENCIES and nothing else — a server can shell out with Node built-ins
        # and declare nothing at all — so an empty result means we found no declaration, never that
        # the capability cannot reach anything. The official Supabase server, whose entire purpose is
        # talking to a remote Supabase project, renders this row: technically correct about its
        # dependency graph, and read by a person as "this is sandboxed".
        rows.append(sec_row("No access inferred from declared dependencies", "",
                            '<span class="secrow__ok">nothing it depends on reaches files, shell or '
                            "network. This reads declarations only — built-in APIs are invisible to "
                            "it, so absence of a declaration is not absence of access</span>"))

    if c.get("sec_remote_content"):
        rows.append(sec_row("Can carry remote content into your agent", "",
                            '<span class="secrow__ok">it can pull third-party text into the model\'s '
                            "context — treat what it returns as untrusted input</span>"))

    rows.append(sec_row(
        "Signed build provenance" if c.get("sec_provenance") else "No build provenance", "",
        '<span class="secrow__ok">' + ("published from public CI with an attestation"
                                       if c.get("sec_provenance") else
                                       "no attestation — the published artifact cannot be traced to "
                                       "its source") + "</span>",
        "" if c.get("sec_provenance") else "secrow--warn"))

    # NOTHING HERE IS GATED, so there is no offer and no "unlock" link anywhere in this section.
    #
    # What stood here counted the findings whose detail was paid and pitched $6/mo against them —
    # which made the pitch loudest exactly where the reader was most exposed. Telling someone their
    # package has a known vulnerability and charging them to learn WHICH one is the single move an
    # independent rater does not get to make. Pro sells TIME (history, and being told when this
    # CHANGES); a section describing the CURRENT state therefore has nothing to advertise.
    # See build.py::redact_paid.
    sub = ("Every finding is shown in full — which advisory, the version that fixes it, and the exact "
           "command run at install time. Nothing in this audit is behind a licence.")

    return sec("Security audit", '<div class="sec">' + "".join(rows) + "</div>", sub,
               "scanned " + (c.get("sec_scanned_at") or "")[:10])


def page(c, gen):
    n = disp(c); url = BASE + chrome.canon("/capability/" + c["slug"] + ".html")
    title = n + " — tashan score " + (str(c["tashan_score"]) if c.get("tashan_score") is not None else "—") + " · tashan"
    d = esc(desc_for(c))
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n"
        '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>" + esc(title) + "</title>\n"
        '<meta name="description" content="' + d + '">\n'
        '<meta name="cap-id" content="' + esc(c["id"]) + '">\n'
        '<meta name="theme-color" content="#0b0b0a">\n'
        '<link rel="canonical" href="' + url + '">\n'
        '<link rel="alternate" type="text/markdown" href="'
        + BASE + '/capability/' + c["slug"] + '.md" title="Plain-markdown dossier">\n'
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
        '<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/Geist-Variable.woff2" crossorigin>\n'
        '<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/GeistMono-Variable.woff2" crossorigin>\n'
        '<link rel="stylesheet" href="/css/site.css?v=' + AV + '">\n'
        + jsonld(c) + "\n</head>\n<body>\n" + NAV +
        '<main class="wrap" id="main" tabindex="-1">' + summary(c, gen) + "</main>\n" + FOOT +
        inline_data(c, gen) +                                    # this cap's full data, inline — no 1.2 MB fetch
        '<script src="/js/terminal.js?v=' + AV + '" defer></script>\n<script src="/js/site.js?v=' + AV + '" defer></script>\n'
        '<script src="/js/capability.js?v=' + AV + '" defer></script>\n</body>\n</html>\n')

def inline_data(c, gen):
    # a non-executable JSON island the detail page reads directly (CSP-safe). Escape </ so no early </script>.
    # `sv` is the scorer version. Without it in the island, capability.js could not print the ruler
    # the static page prints, and the two halves would disagree about which scorer produced the
    # number on the very line that states it.
    payload = json.dumps({"c": c, "at": gen, "sv": SCORER}, ensure_ascii=False).replace("</", "<\\/")
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


def bake_methodology(gen):
    """Write the LIVE scorer version into methodology.html.

    It was typed by hand and read "s2, from 30 July 2026" while production served s5 — two bumps had
    shipped without anyone editing the prose. For a site whose product is measurement, a methodology
    page describing a scorer that has not run in weeks is not a stale docs page; it is the one
    document a sceptical reader opens to check whether the numbers mean anything, and it was wrong.
    Baked from the same export the scores come from, so it cannot drift again.
    """
    p = os.path.join(ROOT, "web", "methodology.html")
    if not os.path.exists(p):
        return
    html = open(p, encoding="utf-8").read()
    when = (gen or "")[:10] or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    subs = 0
    for pat, val in ((r'(<span class="mono" id="mScorer">)[^<]*(</span>)', SCORER or "?"),
                     (r'(<span id="mScorerDate">)[^<]*(</span>)', when)):
        html, n = re.subn(pat, lambda m: m.group(1) + val + m.group(2), html, count=1)
        subs += n
    # A baker that silently matches nothing is worse than no baker: it prints success while the page
    # keeps whatever a human last typed, which is exactly how "s2" survived two scorer bumps.
    if subs != 2:
        raise SystemExit(f"methodology bake matched {subs}/2 targets — the markers moved or were "
                         f"edited away. Fix web/methodology.html, do not let this pass silently.")
    open(p, "w", encoding="utf-8").write(html)
    print(f"methodology: baked scorer {SCORER} / {when}")


def lastmod(c):
    """<lastmod> from the date the described artifact actually last changed — or nothing.

    The dossier is re-derived nightly, so stamping every one of 5,788 URLs with today's date would be
    both true and useless: a sitemap where everything changed every day carries no priority signal at
    all, and Google states plainly that it ignores lastmod it finds to be inaccurate. The real signal
    is upstream — a page's content moves when the package is republished or the repo is pushed. That
    is a lower bound (a score can drift on downloads alone), and a lower bound is the safe direction:
    it under-claims freshness rather than over-claiming it. Unknown stays absent, never guessed.
    """
    d = max((x[:10] for x in (c.get("gh_pushed"), c.get("npm_last_publish")) if x), default=None)
    return "<lastmod>" + d + "</lastmod>" if d and re.fullmatch(r"\d{4}-\d\d-\d\d", d) else ""


def sitemap(caps):
    # Every hand-written page that is linked and indexable. terms/privacy/refunds/support were added
    # to the footer of all ~5,800 pages and never to this list, so the four pages a buyer looks for
    # before paying were the only ones a crawler could not find. welcome.html stays OUT deliberately —
    # it is the post-checkout page and carries noindex.
    urls = ["/", "/start.html", "/methodology.html", "/about.html", "/pricing.html", "/requests.html",
            "/terms.html", "/privacy.html", "/refunds.html", "/support.html", "/for-hosts.html",
            "/browse.html"]
    static = "".join("  <url><loc>" + BASE + chrome.canon(u) + "</loc></url>\n" for u in urls)
    caps_x = "".join('  <url><loc>' + BASE + chrome.canon("/capability/" + c["slug"] + ".html")
                     + '</loc>' + lastmod(c) + '<changefreq>weekly</changefreq></url>\n' for c in caps)
    # generated hubs + learn/agents pages if present. These are real indexable pages; leaving them out
    # of the sitemap is how a whole content tier stays invisible to crawlers.
    extra = ""
    for sub in ("learn", "agents", "category", "skills", "task", "role", "compare"):
        d = os.path.join(ROOT, "web", sub)
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith(".html"):
                    extra += "  <url><loc>" + BASE + chrome.canon("/" + sub + "/" + f) + "</loc></url>\n"
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + static + caps_x + extra + "</urlset>\n")
    open(os.path.join(ROOT, "web", "sitemap.xml"), "w").write(xml)

def markdown(c, gen):
    """The same dossier as plain markdown, at <slug>.md.

    WHY THIS EXISTS. An answer engine that will not run JS gets our HTML, parses around the chrome, and
    hopes. A competing directory ships a .md per listing and it is markedly easier to read — that is a
    real advantage and it costs almost nothing to match. Structure is deliberate: one labelled Facts
    block so the numbers are extractable without a parser, the install command exactly as the HTML
    prints it, and every unknown stated as unknown rather than omitted (an absent line reads as "fine"
    to a summariser, which is the one thing this site must never imply).

    Derived from the SAME export row as page(), so the two cannot disagree about a number.
    """
    L = []
    L.append("# " + disp(c))
    if c.get("description"):
        L.append("\n> " + " ".join(str(c["description"]).split()))
    L.append("\n## Facts")
    def fact(k, v):
        L.append(f"- {k}: {v}")
    fact("Page", BASE + chrome.canon("/capability/" + c["slug"] + ".html"))
    fact("tashan id", c["id"])
    if c.get("source_repo"): fact("Source", "https://github.com/" + c["source_repo"])
    if c.get("npm_pkg"):     fact("npm", "https://www.npmjs.com/package/" + c["npm_pkg"])
    fact("Type", c.get("kind") or "unknown")
    fact("Category", c.get("category") or "uncategorised")
    # The headline, then what it is made of — and "not measured" wherever that is the truth.
    fact("tashan score", f'{c["tashan_score"]} / 100' if c.get("tashan_score") is not None
                         else "not scored (catalogued only — too little public evidence)")
    for label, key in (("Adoption", "adoption"), ("Upkeep", "upkeep"), ("Freshness", "freshness")):
        fact(label, c.get(key) if c.get(key) is not None else "not measured")
    fact("Evidence coverage", f'{round(100 * c["coverage"])}% of the inputs this score can use'
                              if c.get("coverage") is not None else "not measured")
    fact("Health", c.get("vitality") or "not measured")
    fact("Instruction depth", c.get("expertise_verdict") or "not yet graded")
    if c.get("gh_stars") is not None:   fact("GitHub stars", f'{c["gh_stars"]:,}')
    if c.get("npm_downloads") is not None: fact("npm downloads", f'{c["npm_downloads"]:,}/week')
    if c.get("gh_license"):             fact("License", c["gh_license"])
    fact("Official", "yes" if c.get("official") else "no")

    cmd = install_cmd(c)
    if cmd:
        L.append("\n## Install\n\n```sh\n" + cmd + "\n```")

    L.append("\n## Security audit")
    if c.get("sec_scanned_at") or c.get("sec_advisory_count") is not None:
        n = c.get("sec_advisory_count") or 0
        L.append(f"- Known advisories: {n}" + (f" (max severity {c['sec_max_severity']})" if n else ""))
        L.append("- Install-time script: " + (f"`{c['sec_install_script']}`" if c.get("sec_install_script") else "none declared"))
        L.append("- Build provenance: " + ("attested" if c.get("sec_provenance") else "not attested"))
        # JSON string in the export, not a list — joining it directly spells the permission surface
        # one character at a time. The other two readers in this file already json.loads it.
        perms = json.loads(c.get("sec_permissions") or "[]")
        if perms:
            L.append("- Declared permission surface: " + ", ".join(perms))
        L.append("\nPermissions are read from DECLARED dependencies only. Nothing is executed, so an "
                 "empty result means \"nothing declared\", never \"nothing possible\".")
    else:
        L.append("Not scanned. We audit npm-published capabilities; this one has no npm package we can "
                 "resolve, or has not reached the queue. This is not a clean bill of health.")
    L.append(f"\n---\nMeasured {gen[:10]} by tashan ({BASE}) from public evidence. Scorer {SCORER}.")
    return "\n".join(L) + "\n"


def install_cmd(c):
    """The install line, ONE definition, shared by page() and markdown(). See capability.js::installBlock."""
    if c.get("discontinued"):
        return None
    if c.get("kind") == "skill":
        return "cp -r " + chrome.alias(c["name"]) + " ~/.claude/skills/"
    if c.get("kind") == "plugin" and c.get("plugin_market_repo") and c.get("title"):
        return ("/plugin marketplace add " + c["plugin_market_repo"]
                + "\n/plugin install " + c["name"] + "@" + c["title"])
    if c.get("npm_pkg"):
        return "claude mcp add " + chrome.alias(c["name"]) + " -- npx -y " + c["npm_pkg"]
    return None


def main():
    d = json.load(open(DATA))
    gen = d.get("generated_at", "")
    global SCORER
    SCORER = d.get("scorer", "")
    caps = [c for c in d["capabilities"] if c.get("id", "").split(":", 1)[0] != "key"]
    for c in caps:
        c.setdefault("slug", slugify(c["id"]))
    have = {c["slug"] for c in caps}  # only these have prerendered pages
    for c in caps:
        if c.get("co_used"):  # drop co-use links to caps we didn't prerender (would 404 / hit the slow legacy path)
            c["co_used"] = [x for x in c["co_used"] if slugify(x["id"]) in have]
    for c in caps:
        open(os.path.join(OUT, c["slug"] + ".html"), "w").write(page(c, gen))
        open(os.path.join(OUT, c["slug"] + ".md"), "w").write(markdown(c, gen))
    # Remove pages for capabilities that dropped out of the export (junk-filtered, deprecated, renamed).
    # Without this they linger as orphans: still crawlable, in no sitemap, linked from nothing, and
    # frozen at whatever asset version last wrote them.
    stale = [f for f in os.listdir(OUT)
             if (f.endswith(".html") and f[:-5] not in have) or (f.endswith(".md") and f[:-3] not in have)]
    for f in stale:
        os.remove(os.path.join(OUT, f))
    if stale:
        print("removed %d orphaned page(s) no longer in the export" % len(stale))
    sitemap(caps)
    bake_hero(caps, d.get("total_capabilities") or len(caps))
    bake_methodology(gen)
    print("prerendered %d capability pages -> %s" % (len(caps), OUT))
    print("sitemap: %d capability URLs + core pages" % len(caps))

if __name__ == "__main__":
    # --selftest runs the pure-logic checks (description clipping + the markdown dossier) with no
    # filesystem or export needed. _selfcheck() existed for weeks and was called from NOWHERE — a
    # check that never runs is not a check. tests/run.sh invokes this.
    if "--selftest" in sys.argv:
        _selfcheck(); _selfcheck_markdown()
    else:
        main()
