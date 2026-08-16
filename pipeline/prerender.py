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
import skill_doc
AV = str(assets.V)   # single source of truth for cache-busting
SCORER = ""          # which ruler produced these numbers; read from the export in main()
GEN_DATE = ""        # the day these numbers were measured — a citation signal, same source
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
        # int, not float. Every description read "tashan score 34.0/100" — the score is stored as a
        # REAL and printed raw, so a trailing .0 shipped in the one string a search result quotes.
        _s = c["tashan_score"]
        claim = "tashan score " + (str(int(_s)) if float(_s) == int(_s) else str(_s)) + "/100"
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
        assert out.endswith("tashan score 37/100."), (n, out[-40:])
        assert len(out) <= MAX_DESC, (n, len(out))
        assert ".…" not in out and "…." not in out and ".." not in out, (n, out[-40:])
    # a description that already ends in an ellipsis must not collect a second full stop
    pre = desc_for({"description": "Already cut short…", "tashan_score": 5.0, "name": "x", "label": "X"})
    assert pre == "Already cut short… tashan score 5/100.", pre
    assert desc_for({"description": "Short.", "tashan_score": 12.0, "name": "x", "label": "X"}) \
        == "Short. tashan score 12/100."
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
        # WHEN we measured it. An answer engine weighs recency when it decides whether to quote a
        # claim, and a rating with no date is a rating it has to treat as undated — the markdown twin
        # has carried "Measured <date> … Scorer s5" from the start and the structured data did not.
        if SCORER:
            app["review"]["reviewAspect"] += f" (scorer {SCORER})"
        if GEN_DATE:
            app["review"]["datePublished"] = GEN_DATE
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

SEV_RANK = {"high": 0, "medium": 1, "low": 2}


def changed_block(c):
    """What moved recently, dated, in the author's-eye-view the pipeline already writes.

    change_events has run nightly since it was built and appeared on NO surface — 404 rows, each
    with a written what / why / action, exported nowhere. It is the only thing here that cannot be
    recomputed later: a change is observable exactly once, on the day it happens.

    FREE, deliberately and in full. The existence of a risk is never behind the paywall (PROJECT.md
    §12), and this is the clearest demonstration of what the product does — a reader who sees "this
    server started running an install script on 5 Aug" understands the offer without being pitched.
    What Pro sells is not this text; it is being told on the day it happens about the servers YOU
    run, which is `tashan doctor` and the alert, not a page you would have to remember to revisit.
    """
    ch = c.get("changes") or []
    if not ch:
        return ""
    ch = sorted(ch, key=lambda x: (SEV_RANK.get(x.get("sev"), 3), x.get("at") or ""))[:3]
    items = ""
    for x in ch:
        sev = x.get("sev") or "low"
        items += ('<li class="chg chg--' + esc(sev) + '">'
                  + '<span class="chg__at mono">' + esc(x.get("at") or "") + '</span> '
                  + '<b>' + esc(x.get("what") or "") + '</b>'
                  + ('<span class="chg__why"> ' + esc(x.get("why") or "") + '</span>' if x.get("why") else "")
                  + '</li>')
    # The Pro line is CONCRETE and names what it would have done for this row, rather than
    # advertising a feature in the abstract. It is also honest that the page is not the product:
    # nobody reloads a dossier to find out their stack moved.
    pitch = ('<p class="chg__pro mono fs-sm">You are reading this because you came looking. '
             '<a class="link" href="/pricing.html">tashan Pro</a> gives <code>tashan doctor</code> the '
             'history behind it, so a run over your own config says which of YOURS moved.</p>')
    return ('<section class="changed"><h2 class="sec-h">What changed recently</h2>'
            '<ul class="chg-list">' + items + '</ul>' + pitch + '</section>')


def embed_block(c):
    """The badge, offered on the page a publisher actually visits.

    THE ONLY DISTRIBUTION LOOP THIS PRODUCT HAS THAT COMPOUNDS. A maintainer who puts the badge in
    their README gives us a permanent backlink and an impression to everyone who reads it — and
    they do it because it shows THEIR score, not as a favour. It is opt-in, it is honest, and it is
    the opposite of the mass-messaging that would end an independent rater's credibility overnight.

    It existed only in capability.js. The client REPLACES the server render, so the badge offer was
    invisible to every crawler, to anyone with JS off, and — most expensively — it was absent from
    the static HTML that answer engines read. The one asset designed to spread was the one asset
    only a browser could see. That is the fourth time this file and capability.js have disagreed.

    Shown only where there is a score: a badge for an unrated row would advertise an empty number.
    """
    if c.get("tashan_score") is None:
        return ""
    slug = c["slug"]
    url = BASE + "/badge/" + slug + ".svg"
    page = BASE + "/capability/" + slug + ".html"
    md = "[![tashan](" + url + ")](" + page + ")"
    return ('<div class="embed"><h2 class="embed__h">Show your score</h2>'
            '<p class="embed__p">Measured this well? Put the live badge in your README &mdash; it '
            'updates as the score does.</p>'
            '<img class="embed__badge" src="/badge/' + esc(slug) + '.svg" alt="tashan badge for '
            + esc(disp(c)) + '" width="132" height="20" loading="lazy">'
            '<div class="embed__code"><code id="embedCode">' + esc(md) + '</code>'
            '<button class="embed__copy" id="embedCopy" type="button" data-copy="' + esc(md)
            + '">copy</button></div></div>')


def doctor_cta(c):
    """The free action, given to somebody who arrived from a search.

    MEASURED, NOT ASSUMED. With analytics finally live, the only organic arrivals in the first
    72 hours were Google landing on capability pages — including pkg-agentutility-mcp-web-probe,
    which is about as long-tail as this corpus gets. Package-name search is the traffic this site
    gets, and a dossier is where it lands.

    What that reader was offered was one button: "Start a 7-day trial". Asking a stranger for money
    before giving them anything is the wrong first move, and it is worse than doing nothing here,
    because the free thing we have is the strongest thing we have. `doctor` reads the config already
    on their machine and names what is wrong in it, for nothing, with no account.

    It is also the only path to a subscription: everything Pro delivers arrives through doctor. So
    the free command is the primary action and the trial is secondary — the order the funnel
    actually runs in, rather than the order we would like it to.
    """
    return ('<section class="dcta">'
            '<p class="dcta__lbl mono">You searched for one. Check the rest of your stack:</p>'
            '<pre class="install__snip"><button class="install__copy install__copy--pre" type="button" '
            'data-copy="npx tashan-cli doctor">copy</button><code>npx tashan-cli doctor</code></pre>'
            '<p class="dcta__sub">Reads the config already on your machine and names what is dead, '
            'deprecated or running code at install time. No account, nothing uploaded.</p>'
            "</section>")


def skill_doc_block(c):
    """What a skill's own SKILL.md contains — facts, deliberately not a grade.

    A skill cannot be graded by the expertise rubric: its first criterion is per-tool documentation
    and a skill has no tools, which lands skills at 2.7% `deep` against servers' 16-20% and measures
    the mismatch rather than the writing (docs/GRADING-RUBRIC.md has the numbers). So the page states
    checkable facts about the document instead. Facts need no shared vocabulary, so nothing here can
    be misread as comparable to a server's verdict.

    It is also the only measured thing most of these pages have. 2,775 skill dossiers were noindexed
    as thin because a description was their single signal.
    """
    raw = c.get("skill_doc")
    if not raw:
        return ""
    try:
        m = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return ""
    if not isinstance(m, dict) or not m:
        return ""
    return ('<section class="sec"><h2>Its own instructions</h2>'
            '<p class="prose">' + esc(skill_doc.sentence(m)) + "</p>"
            '<p class="muted">Read from the capability&rsquo;s own SKILL.md. This is not a grade '
            'and does not compare to the instruction-depth verdict on an MCP server &mdash; a skill '
            'has no tools to document, so that rubric does not apply to it.</p></section>')


def pro_panel(c):
    """The one commercial surface on a dossier, and the only place a price appears.

    WHY IT IS A PANEL AND NOT A SENTENCE. Every page carried a pricing link, and a sample of 3,000
    dossiers found 3,000 plain text links inside a closing paragraph and ZERO buttons. That is not a
    commercial surface, it is a footnote — a reader scanning a measurement page has no reason to stop
    at the last line of prose, and nothing about it looked like an offer.

    TWO STATES, ONE ELEMENT. What ships here is the SIGNED-OUT state, because it is the one a crawler
    and an answer engine read, and it must stand alone. capability.js replaces it with the Pro state
    once /api/account confirms an active licence — same pattern as the security detail, and the same
    rule: it starts as the free state and only ever upgrades, so no page flashes a wrong entitlement
    and an unreachable API leaves the honest offer on screen.

    The offer is specific to THIS capability rather than generic, because a generic upsell on 9,638
    pages is banner blindness by the second page. It names the row's own numbers.

    NO ACCENT COLOUR. brand/BRAND.md reserves jade for measured data; an offer is not a measurement.
    The panel earns its separation from a hairline and a tint, which is also why it does not compete
    with the score sitting a few centimetres above it.
    """
    name = esc(c.get("label") or c.get("name") or "this capability")
    score = c.get("tashan_score")
    n_ch = len(c.get("changes") or [])
    # Concrete, and true for this row: what Pro would have told them about THIS package.
    if n_ch:
        line = ("We recorded <b>" + str(n_ch) + (" change" if n_ch == 1 else " changes")
                + "</b> to " + name + " in the last 45 days. Pro tells you on the day — for the "
                "servers in your own config, not the ones you thought to look up.")
    elif score is not None:
        line = (name + " scores <b>" + str(int(score)) + "</b> today. Pro keeps the series, so you "
                "can see whether that is a project getting better or one on its way down — and "
                "tells you the day it moves.")
    else:
        line = ("Pro adds the history to <code>tashan doctor</code>, so a run over your own config "
                "says which of yours gained an advisory, started running an install script, or "
                "lost its last maintainer &mdash; and what to move to.")
    # ONE DEFINITION: the markup lives in chrome.pro_panel now, because the hubs and the
    # /learn/ pages need the identical panel and a second copy is how surfaces drift.
    return chrome.pro_panel(line, "pro-dossier", pid="pro")


ACTIVATION = re.compile(
    r'\btrigger(?:s|ed)?\s+(?:whenever|when)\b'
    r'|\bactivat(?:e|es|ed)\s+(?:whenever|when)\s+the\s+user\b'
    r'|\bthe\s+user\s+says\s*["\u201c]'
    r'|\bYou\s+MUST\b'
    r'|\b(?:ALWAYS|NEVER)\s+use\s+this\b'
    r'|^\s*Use\s+(?:this\s+skill|PROACTIVELY)\b', re.I | re.M)


def desc_block(c):
    """The author's description — captioned when it is not one.

    283 capabilities, almost all skills, publish activation text where a description belongs:
    "Trigger whenever the user says 'compile the discovery doc'", "You MUST use this before any
    creative work". That is a prompt addressed to a model, and we render it as the opening
    paragraph under the title, which makes a page we generated from real evidence read like
    scraped slop.

    We do not rewrite it — inventing prose about a capability is exactly the claim this project
    refuses to make. We say what it is. Six words of caption turn a confusing paragraph into a
    fact about the source, and a reader who was about to bounce learns something instead.
    """
    d = c.get("description")
    if not d:
        return ""
    cap = ('<p class="muted">Author\u2019s activation text, quoted as published</p>'
           if ACTIVATION.search(d) else "")
    return cap + '<p class="cap-desc">' + esc(clip_desc(d)) + "</p>"


DESC_SHOWN = 700


def clip_desc(t):
    """The author's description, bounded — for reading first, weight second.

    Sixteen exported rows run past 1,200 characters and one reaches 1,647, rendered as a single
    unbroken paragraph directly under the title. That is the wall-of-text problem this codebase
    already fixed everywhere else, and it also multiplies: the description appears three times per
    page — visible, in the inline payload the client re-renders from, and in the structured data —
    so a long one is the difference between a 16 KB page and a 30 KB one. The nightly went red twice
    on exactly that.

    Cut on a sentence end where there is one, otherwise a word boundary; never mid-word. The FULL
    text is untouched in the export, in the .md twin and on the source page, so nothing is lost for
    an agent or for anyone who wants all of it — only the first screen is protected.
    """
    t = (t or "").strip()
    if len(t) <= DESC_SHOWN:
        return t
    cut = t.rfind(". ", 0, DESC_SHOWN)
    if cut < DESC_SHOWN * 0.5:
        cut = t.rfind(" ", 0, DESC_SHOWN)
    if cut <= 0:  # no boundary at all (one long token) — cut flat, never grow
        cut = DESC_SHOWN
    return t[:cut].rstrip(" ,;:—-") + ("" if t[cut - 1:cut] == "." else ".") + " …"


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
    # A NAMED JUDGMENT NEEDS A ROUTE TO CONTEST IT. We publish a verdict on someone's documentation
    # under their project's name, and until now the only thing on the page was requests.html — which
    # is for asking us to MEASURE something, not for telling us we got it wrong. An independent rater
    # that cannot be corrected is just an opinion with better typography, and we have already had to
    # withdraw 87 judgments read off the wrong document. The link carries the id and the verdict, so
    # a reply costs the author one click and no explaining of which page they mean.
    contest = ("" if not c.get("expertise_verdict") else
               '<a class="expert-read__fix link" href="'
               + esc("https://github.com/FlyingWHR/tashan/issues/new?labels=grade-correction&title="
                     + quote("Grade correction: " + (c.get("name") or c["id"]))
                     + "&body=" + quote(
                         "Capability: " + c["id"] + "\n"
                         "Current grade: " + str(c.get("expertise_verdict")) + "\n"
                         "Our note: " + (c.get("expertise_note") or "") + "\n\n"
                         "What the grade got wrong (a link to the docs we should have read is the "
                         "most useful thing you can give us):\n"))
               + '" rel="noopener">This grade is wrong &rsaquo;</a>')
    verdict = ('<div class="expert-read">' + chrome.verdict_chip(c.get("expertise_verdict"))
               + '<p>&ldquo;' + esc(c["expertise_note"]) + '&rdquo;</p>'
               + contest + '</div>') if c.get("expertise_note") else ""
    # …and where a verdict was WITHHELD because the documentation is about something else, say so.
    # Silence there reads as "not looked at yet" when we have looked and found the docs belong to a
    # different project — which is the more useful thing for a reader deciding whether to adopt it.
    if not verdict and c.get("doc_status"):
        # The "another project's document" clause explains the BORROWED-DOC case and only that one.
        # Appended to every reason it became a non-sequitur: "no documentation was published with
        # it. A grade read off another project's document would borrow its credit, or its blame."
        why = c["doc_status"]
        because = (" A grade read off another project&rsquo;s document would borrow its credit, "
                   "or its blame." if "documentation with" in why or "never names it" in why else "")
        verdict = ('<div class="expert-read"><p class="mono fs-sm">Not graded: '
                   + esc(why) + '.' + because + '</p></div>')
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
           + " — see all ranked &rsaquo;</a></p>") if c.get("category_basis") else ""
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
            + desc_block(c) + '</div>'
            # ORDER IS AN ARGUMENT, and four sections were added to this page in a week without
            # anyone re-reading it top to bottom. The badge ask — which is a request to the
            # PUBLISHER — and the Pro panel had ended up above the security audit, so a reader who
            # arrived to find out whether a package is safe met a marketing block first and the
            # answer last.
            #
            # The order a visitor actually needs: what it is, what we measured, what it can do to
            # your machine, what changed, what YOU can do for free, what a licence adds, and only
            # then the one thing we want from them. Anything else is asking before giving.
            + works + cat + task + job + install + verdict + swap +
            ('<ul class="prose prose--wide">' + "".join(rows) + '</ul>' if rows else '') +
            security_block(c) + skill_doc_block(c) + changed_block(c) + doctor_cta(c) + pro_panel(c) + embed_block(c)
            + ('<p class="mono">' + " &nbsp;·&nbsp; ".join(links) + '</p>' if links else '')
            # ONE HONEST CLOSING LINE, ON EVERY DOSSIER. 8,648 of 9,638 capability pages made no
            # case for the product at all — only the 990 that happen to carry a change block or a
            # finding did — so a reader could read the deepest page we publish about a package and
            # leave without learning that anything watches it.
            #
            # Suppressed where changed_block already pitched, because saying it twice on one page is
            # how a measured page starts to read like a landing page. Nothing here is gated and
            # nothing is withheld: the line names what the PAGE cannot do, which is know what is in
            # your config. That is the only honest thing left to sell once every finding is free.
            + ("" if (c.get("changes") or []) else
               '<p class="chg__pro mono fs-sm">Everything on this page is public evidence and free. '
               'What it cannot know is whether <em>you</em> run this — '
               '<code>npx tashan-cli doctor</code> reads your own config and names what is wrong in '
               'it, also free. <a class="link" href="/pricing.html">tashan Pro</a> tells you the day '
               'any of it changes.</p>') + audit
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
        # SAY WHAT WAS CHECKED, not just against what version. OSV is queried by PACKAGE NAME, so
        # this is a statement about this package and not about its dependency tree — a server whose
        # dependency carries a CVE still reads "clear" here. Verified 15 Aug against live OSV: all
        # 18 of the most-installed scanned rows agree exactly with what we publish, so the finding
        # is correct; it is the SCOPE that a reader could over-read. The same rule the permission
        # surface already follows: an empty result means "nothing found where we looked", never
        # "nothing there".
        rows.append(sec_row("No known advisories", '<span class="sev sev--none">clear</span>',
                            '<span class="secrow__ok">checked against OSV for '
                            + esc(c.get("npm_latest_version") or "the current release")
                            + " &mdash; this package, not its dependency tree</span>"))

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


# HOW MUCH THIS PAGE CAN ACTUALLY SAY. Counted so the thin tail can be kept off the index without
# being deleted: a dossier with a name and one sentence is still the right answer for `doctor` when
# somebody runs that obscure server, and still belongs in the agent tier — it just should not be
# submitted to a search engine as a page worth ranking.
def skill_doc_found(c):
    """True when a skill's own SKILL.md documented at least one of the five things we look for."""
    raw = c.get("skill_doc")
    if not raw:
        return False
    try:
        m = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return False
    return isinstance(m, dict) and any(m.values())


def signal_count(c):
    return sum(1 for x in (
        c.get("tashan_score") is not None,
        bool((c.get("description") or "").strip()),
        bool(c.get("sec_scanned_at")),
        bool(c.get("expertise_verdict")),
        bool(c.get("changes")),
        bool(c.get("tasks")),
        # A measured SKILL.md is a real signal — the one axis a skill can be measured on at all —
        # but ONLY when the reading found something. 337 of 3,368 SKILL.md files say none of the
        # five things, and "we read it and it documents nothing" is an honest sentence to print and
        # a poor reason to ask a search engine to index the page. The block still renders on those;
        # a negative result is a result. It just does not count as content.
        skill_doc_found(c),
    ) if x)


THIN_SIGNALS = 1          # a name and, at most, one measured thing


def thin(c):
    return signal_count(c) <= THIN_SIGNALS


def page(c, gen):
    n = disp(c); url = BASE + chrome.canon("/capability/" + c["slug"] + ".html")
    # THE TITLE MUST CONTAIN THE STRING PEOPLE TYPE. Search Console's first query report is almost
    # entirely identifier lookups — `registry.npmjs.org/kordoc`, `ussumant/llm-wiki-compiler`,
    # `contextd` — people checking what an unknown package IS. That is exactly what a dossier
    # answers, and the one query that visibly worked did so because the repo path is literally on
    # the page.
    #
    # 3,328 titles did not contain their own package identifier: the title said "Supabase" while the
    # query is `@supabase/mcp-server-supabase`, "Context7" against `@upstash/context7-mcp`,
    # "Firecrawl" against `firecrawl-mcp`. The friendly label is better to read and worse to find,
    # so the identifier goes in parentheses after it — kept out of the lead so the human name is
    # still what a person sees first.
    #
    # Dropped when it does not fit: tests/test_site.py caps a title at 62 characters, and a title
    # truncated by Google helps nobody. The identifier is also in the description and in the body,
    # so a long scoped name is findable either way.
    sc = c.get("tashan_score")
    # int, not float: every one of 8,416 titles read "tashan score 75.0", and a trailing .0 in a
    # search result is the kind of detail that makes a measurement look unconsidered.
    score = (str(int(sc)) if sc is not None and float(sc) == int(sc) else str(sc)) if sc is not None else "—"
    pkg = c.get("npm_pkg") or ""
    ident = (" (" + pkg + ")") if pkg and pkg.lower() != n.lower() else ""
    title = n + ident + " — tashan score " + score + " · tashan"
    # 90, NOT 62. The 62-character rule is about what Google DISPLAYS, and it applies to the
    # handful of hand-written pages where the whole title is a headline. Here the title's first job
    # is to CONTAIN the string somebody typed: the query report is identifier lookups, and
    # `@supabase/mcp-server-supabase` alone is 28 characters. A title Google truncates in the SERP
    # still matches on every word it holds — dropping the identifier to look tidy loses the match
    # itself, which is the only reason the page ranks at all.
    if len(title) > 90:
        title = n + " — tashan score " + score + " · tashan"
    # NOT TRUNCATED FURTHER. Cutting the label to fit produced "0nMCP — Universal AI API…" and
    # tests/test_consistency.py caught it on 105 pages: a title that no longer contains the
    # capability's name is a worse failure than a long one, because the page stops being findable
    # by the thing it is about. Google truncates in the SERP either way, and it truncates at the
    # pixel — the string still has to name the row.
    d = esc(desc_for(c))
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n"
        '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>" + esc(title) + "</title>\n"
        '<meta name="description" content="' + d + '">\n'
        '<meta name="cap-id" content="' + esc(c["id"]) + '">\n'
        '<meta name="theme-color" content="#0b0b0a">\n'
        # NOINDEX FOR THE THIN TAIL. 770 of 9,638 dossiers are a name and a sentence — nothing
        # measured, nothing scanned, nothing graded — and all 10,244 URLs were being submitted to
        # search. Quality signals are evaluated site-wide, not per page, so a large thin tail drags
        # on everything above it. `follow` is deliberate: the links out of these pages still pass
        # value to the hubs and to the capabilities that DO have something to say.
        + ('<meta name="robots" content="noindex,follow">\n' if thin(c) else "")
        + '<link rel="canonical" href="' + url + '">\n'
        '<link rel="alternate" type="application/atom+xml" title="tashan — what changed" '
        'href="' + BASE + '/changes.xml">\n'
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
    html = bake_board(html, caps)
    open(idx, "w", encoding="utf-8").write(html)
    print(f"hero: baked {len(caps):,} measured / {total:,} tracked / {when} "
          f"+ top {min(BOARD_BAKE_N, len(caps))} rows and an ItemList")


BOARD_BAKE_N = int(os.environ.get("BOARD_BAKE_N", "25"))
# Mirrors KIND_LABEL in web/js/index.js. Two copies of a display map is a smell, but the alternative
# is shipping it in the export and paying for it on every board row; the pre-JS table is replaced by
# the client anyway, so a drift here shows for one paint and never contradicts the live board.
KIND_LABEL = {"npm": "npm", "pkg": "npm-pkg", "docker": "docker", "python": "python",
              "remote": "remote", "skill": "skill", "plugin": "plugin"}


def bake_board(html, caps):
    """Put the top of the Index into index.html as HTML, for readers that do not run JavaScript.

    THE SITE'S MOST-CRAWLED URL PUBLISHED NO MEASUREMENTS. `<tbody id="rows">` shipped a "Loading
    measured data…" spinner and index.js filled it on boot, so a crawler, an answer engine or an
    agent fetching https://tashan.sh/ saw 3,137 characters of navigation, hero copy and footer — and
    not one capability, score or rank. Every category and task hub was server-rendered; the board
    itself, the thing the whole product is, was the one page that needed a browser.

    Deliberately SIMPLER than index.js's row: rank, name, score, evidence, health. No verdict chips,
    no security flags, no category tags. This is the pre-JS state of a table the client fully
    replaces on its first render (`rowsEl.innerHTML = …`), so the two cannot drift into disagreement
    the way prerender and capability.js did — there is no merge, only a replacement. Keeping it thin
    is the point: it must stay obviously subordinate to the live board rather than become a second
    implementation of it.
    """
    rows, items = [], []
    for i, c in enumerate(caps[:BOARD_BAKE_N], 1):
        t = c.get("tashan_score")
        href = "/capability/" + (c.get("slug") or slugify(c["id"])) + ".html"
        name, kind = disp(c), KIND_LABEL.get(c.get("kind"), c.get("kind") or "")
        score = f'<span class="sig__val">{int(round(t))}</span>' if t is not None else \
            '<span class="unrated">not scored yet</span>'
        vit = c.get("vitality") or "—"
        rows.append(
            f'<tr><td class="rank">{i}</td>'
            f'<td><div class="cap__name"><a class="cap__link" href="{esc(href)}">{esc(name)}</a>'
            f' <span class="tag">{esc(kind)}</span></div></td>'
            f'<td><div class="sig">{score}</div></td>'
            f'<td class="num">{esc(board_evidence(c))}</td>'
            f'<td><span class="fresh">{esc(vit)}</span></td></tr>')
        # The part an answer engine actually parses. Category hubs have carried an ItemList since
        # they were built; the Index never did, so the ranked list we exist to publish was the one
        # ranked list with no structured form.
        item = {"@type": "ListItem", "position": i, "url": BASE + href, "name": name}
        if t is not None:
            # A Review, NOT an aggregateRating — the same call jsonld() makes, and for the same
            # reason. aggregateRating means "the mean of ratings left by reviewers"; one with
            # ratingCount:1 claims a crowd that does not exist, and it was deliberately removed from
            # 6,586 capability pages for exactly that. The tashan score is ONE named party's
            # measurement, so it is modelled as one named party's review: attributed and dated.
            # Writing it the other way here would have quietly reinstated the pattern on the most
            # crawled page on the site.
            item["item"] = {"@type": "SoftwareApplication", "name": name,
                            "applicationCategory": "DeveloperApplication",
                            "url": BASE + href,
                            "review": {"@type": "Review",
                                       "author": {"@type": "Organization", "name": "tashan",
                                                  "url": BASE + "/"},
                                       "reviewRating": {"@type": "Rating", "ratingValue": round(t),
                                                        "bestRating": 100, "worstRating": 0},
                                       "reviewAspect": "tashan score — upkeep and freshness, "
                                                       "gated by adoption"}}
        items.append(item)

    body = "\n".join(rows)
    new, n = re.subn(r'(<tbody id="rows">)[\s\S]*?(</tbody>)',
                     lambda m: m.group(1) + "\n" + body + "\n            " + m.group(2), html, count=1)
    if n != 1:
        raise SystemExit("index.html has no <tbody id=\"rows\"> to bake into — the board markup moved.")

    # On `new`, not `html`: the tbody substitution above already forked the string, so writing back
    # to `html` here edits a copy this function then throws away. It printed success and changed
    # nothing — caught only because the assertion after it read the file rather than the return value.
    new = bake_dataset(new)
    ld = {"@context": "https://schema.org", "@type": "ItemList",
          "name": "The tashan Index — AI capabilities ranked on public evidence",
          "description": f"The {len(items)} highest-scoring MCP servers and agent skills by the "
                         "tashan score: upkeep and freshness, gated by real adoption. Public "
                         "evidence only; nothing paid can change a rank.",
          "url": BASE + "/", "numberOfItems": len(items), "itemListOrder": "Descending",
          "itemListElement": items}
    tag = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + "</script>"
    # Replace our own previous block rather than appending one per run, or the head grows every night.
    marked = '<!--BOARD-LD-->'
    if marked in new:
        new = re.sub(re.escape(marked) + r"[\s\S]*?" + re.escape('<!--/BOARD-LD-->'),
                     marked + tag + '<!--/BOARD-LD-->', new, count=1)
    else:
        new = new.replace("</head>", "  " + marked + tag + "<!--/BOARD-LD-->\n</head>", 1)
    return new


def bake_dataset(html):
    """Keep the homepage's Dataset block current, in the two ways it was not.

    The block itself was already the strongest structured data on the site — measurementTechnique,
    a variableMeasured per axis, a distribution listing the bulk feeds. Two things were missing and
    both matter specifically to a machine reader:

    `dateModified` — a dataset with no date is one an answer engine has to treat as undated, and
    "measured today" is most of why anyone would prefer our number to a directory's. It was the only
    date on the page a human could see (the hero says "measured Aug 6") and the only one a parser
    could not.

    The per-question endpoints — `distribution` listed only the multi-hundred-KB and multi-MB bulk files and nothing
    else, so a crawler that correctly understood this as a dataset was pointed only at the expensive
    way to read it.

    Rewritten in place from the live values rather than hand-edited, so it cannot drift the way the
    scorer version did.
    """
    # WHITESPACE-TOLERANT, and the write-back below is compact — because the first version of this
    # was neither, and broke its own idempotency on the very next run. It matched the hand-written
    # compact JSON, rewrote it with json.dumps' default `", "` separators, and could then never match
    # again: one successful bake, then `pages` failed every night. The raise is what caught it, which
    # is the argument for raising rather than skipping quietly.
    m = re.search(r'<script type="application/ld\+json">(\{\s*"@context"\s*:\s*"https://schema\.org"\s*,'
                  r'\s*"@type"\s*:\s*"Dataset".*?)</script>', html, re.S)
    if not m:
        raise SystemExit("index.html has no Dataset JSON-LD to bake — the block moved or was removed.")
    d = json.loads(m.group(1))
    d["dateModified"] = GEN_DATE or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dist = [x for x in (d.get("distribution") or [])
            if "/v0.1/lookup" not in x.get("contentUrl", "") and "/v0.1/search" not in x.get("contentUrl", "")]
    # Listed FIRST, because the order is the recommendation: a reader answering one question should
    # not be pointed at 5.6 MB because it happened to be declared earlier.
    d["distribution"] = [
        {"@type": "DataDownload", "encodingFormat": "application/json",
         "name": "One measurement by name — the cheapest complete answer",
         "contentUrl": BASE + "/v0.1/lookup?name={package}"},
        {"@type": "DataDownload", "encodingFormat": "application/json",
         "name": "Ranked search across the measured corpus",
         "contentUrl": BASE + "/v0.1/search?q={query}"},
    ] + dist
    # Compact separators: the same shape every other JSON-LD block on the page uses, so a re-run
    # reads back exactly what it wrote and the file does not churn on formatting alone.
    return (html[:m.start(1)]
            + json.dumps(d, ensure_ascii=False, separators=(",", ":"))
            + html[m.end(1):])


def board_evidence(c):
    """The raw public signal, worded exactly as the board's own Evidence column words it."""
    if c.get("npm_downloads") is not None:
        return compact(c["npm_downloads"]) + "/wk"
    if c.get("gh_stars") is not None:
        return compact(c["gh_stars"]) + " ★"
    if c.get("config_reach"):
        return fmt(c["config_reach"]) + (" marketplaces" if c.get("kind") == "plugin" else " repos")
    return "—"


def bake_pricing():
    """Render the price block on pricing.html from data/entitlements.json.

    THE ANNUAL BUTTON ONCE CHARGED MONTHLY. Two CTAs offering different cadences pointed at the same
    Polar checkout, so anyone choosing annual was billed $6/month and the funnel recorded it as an
    annual conversion — neither the customer nor the dashboard could see the mismatch. It was removed
    rather than left lying (f8628ff41f), and tests/test_claims.py now fails the build if two cadences
    ever share one price link again.

    This is how it comes back safely: the toggle renders ONLY when `tiers.pro.annual.url` is set to a
    real, DIFFERENT Polar link. Until then the page shows the monthly price and says plainly that
    annual is not available — which is what it says today. One config edit turns it on; no HTML
    changes, and no way to ship a toggle whose second option bills the first option's price.
    """
    pg = os.path.join(ROOT, "web", "pricing.html")
    ent = os.path.join(ROOT, "data", "entitlements.json")
    if not (os.path.exists(pg) and os.path.exists(ent)):
        return
    pro = json.load(open(ent, encoding="utf-8"))["tiers"]["pro"]
    ann = pro.get("annual") or None
    monthly_url, price = pro.get("checkout", ""), pro.get("price", "")

    # THE BUTTON GOES THROUGH US NOW, and the Polar links below stay the canonical record of what
    # is being sold. /api/buy 302s to exactly these URLs — but on the way it verifies the one field
    # that decides whether a paying customer can be identified afterwards (`success_url`), and
    # repairs it if it is wrong. That field lives in Polar's dashboard, it was wrong for weeks, and
    # nothing we owned could see it. See functions/api/buy.js.
    #
    # The validation below is UNCHANGED and still runs against the real Polar URLs, because those
    # are what /api/buy redirects to — routing through our origin must not become a way to stop
    # checking that the destination is a real checkout link.
    buy_href = {"monthly": "/api/buy?plan=monthly", "annual": "/api/buy?plan=annual"}

    # A PRODUCT ID IS NOT A CHECKOUT LINK. buy.polar.sh/<product-uuid> answers 302 -> polar.sh/ —
    # Polar's own marketing homepage, with a 200 at the end of the redirect. So a pasted product id
    # produces a working-looking "Annual" button that lands the buyer on someone else's landing page
    # and sells nothing: the same shape as the bug that billed annual buyers monthly, where the
    # control looked right and the money went wrong. Only accept the checkout-link form.
    if ann and ann.get("url") and not re.match(r"^https://buy\.polar\.sh/polar_cl_[A-Za-z0-9]+$", ann["url"]):
        raise SystemExit(
            f"pricing: tiers.pro.annual.url is {ann['url']!r}, which is not a Polar checkout link.\n"
            f"  Expected https://buy.polar.sh/polar_cl_...  — a product UUID redirects to polar.sh/\n"
            f"  and sells nothing. Create a Checkout Link on the annual product and paste that.")
    if ann and ann.get("url") and ann["url"] != monthly_url:
        # Savings stated as a number, computed, never typed: "save 30%" that does not match the two
        # prices on the same page is the kind of arithmetic a buyer checks.
        try:
            m = float(str(price).lstrip("$")) * 12
            a = float(str(ann["price"]).lstrip("$"))
            save = f" · save {round(100 * (m - a) / m)}%" if m > a else ""
        except (TypeError, ValueError):
            save = ""
        toggle = (
            '<div class="ptoggle" role="group" aria-label="Billing period">'
            '<button type="button" class="ptoggle__b is-on" data-cad="month" aria-pressed="true">Monthly</button>'
            f'<button type="button" class="ptoggle__b" data-cad="year" aria-pressed="false">Annual{esc(save)}</button>'
            "</div>")
        data = (f' data-monthly-url="{esc(buy_href["monthly"])}" data-monthly-label="{esc(price)} monthly"'
                f' data-annual-url="{esc(buy_href["annual"])}" data-annual-label="{esc(ann["price"])} annually"'
                # THE HEADLINE PRICE HAS TO MOVE TOO. Without this the card read "$6 /mo" while the
                # button under it read "$50 annually" — two prices for one plan, on the page whose
                # entire job is that the number you see is the number you are charged.
                f' data-monthly-price="{esc(price)}" data-monthly-cad="/mo"'
                f' data-annual-price="{esc(ann["price"])}" data-annual-cad="/yr"')
        note = ""
    else:
        toggle, data = "", ""
        note = "annual billing is not available yet &mdash; monthly only"

    out, n = re.subn(r"<!--PRICE-TOGGLE-->[\s\S]*?<!--/PRICE-TOGGLE-->",
                     "<!--PRICE-TOGGLE-->" + toggle + "<!--/PRICE-TOGGLE-->",
                     open(pg, encoding="utf-8").read(), count=1)
    if n != 1:
        raise SystemExit("pricing.html has no <!--PRICE-TOGGLE--> slot — the block moved or was edited away.")
    days = pro.get("trial_days") or 0
    cancel = "cancel any time in <a class=\"link\" href=\"/account.html\">your account</a>"
    # BOTH CADENCES, because this line moves with the toggle. A first draft hardcoded "/mo" here, so
    # switching to Annual left "7 days free, then $6/mo" under a $50/yr button — the same defect as
    # the headline price that did not move, on the same page, in the same hour.
    def terms_for(amount, per):
        return (f"{int(days)} days free, then {esc(amount)}/{per} &middot; " + cancel) if days else cancel
    terms = terms_for(price, "mo")
    if days:
        # Built outside the f-string: the nested double quotes in terms_for(price, "mo") inside an
        # f' ... ' literal is exactly the quoting that produced an unterminated string a moment ago.
        m_terms = esc(terms_for(price, "mo"))
        data += ' data-monthly-terms="' + m_terms + '"'
        if ann and ann.get("url"):
            data += ' data-annual-terms="' + esc(terms_for(ann["price"], "yr")) + '"'

    out = re.sub(r'(<a class="btn btn--primary plan__cta" id="proCta")[^>]*?(\s+rel="noopener">)([^<]*)(</a>)',
                 lambda m: (m.group(1) + f' data-src="pricing-pro-monthly" href="{buy_href["monthly"]}"' + data
                            + m.group(2) + f"{price} monthly &rsaquo;" + m.group(4)), out, count=1)
    # The secondary "Annual: $50/yr" link was hand-written in the page and pointed straight at
    # Polar, so it would have been the one route that skipped the repair — and it is the link for
    # the more valuable subscription. Baked from the same source as the button.
    if ann and ann.get("url"):
        out, n_ann = re.subn(r'(<a class="link" href=")[^"]*(" data-src="pricing-pro-annual")',
                             lambda m: m.group(1) + buy_href["annual"] + m.group(2), out, count=1)
        if n_ann != 1:
            raise SystemExit("pricing.html has no data-src=\"pricing-pro-annual\" link to bake — "
                             "it moved or was edited away, and an un-baked one goes straight to "
                             "Polar without the success_url repair.")
    out = re.sub(r'(<span class="plan__note mono" id="proCadence">)[^<]*(</span>)',
                 lambda m: m.group(1) + note + m.group(2), out, count=1)

    # THE TRIAL, IF THERE IS ONE. "7-day refund" was the reassurance under the buy button, and a
    # refund is a weak thing to lead with: it asks someone to pay, be disappointed, and then chase
    # their money. A trial is the same reassurance without any of that. But it is only true if Polar
    # is configured for it — advertising a free period the checkout then charges for is the annual
    # button billing monthly again, so this renders from `trial_days` and 0 renders nothing.
    # The refund policy itself is unchanged and still linked from the footer, where it belongs.
    out2, n2 = re.subn(r'(<p class="plan__note mono" id="proTerms">)[\s\S]*?(</p>)',
                       lambda m: m.group(1) + terms + m.group(2), out, count=1)
    if n2 != 1:
        raise SystemExit("pricing.html has no #proTerms line to bake — it moved or was edited away.")
    out = out2
    open(pg, "w", encoding="utf-8").write(out)
    print(f"pricing: {'monthly + annual toggle' if toggle else 'monthly only (no annual price configured)'}")


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
    # The freeze date is the lock file's, not a typed one. A published stability promise that
    # disagrees with the guard enforcing it is worse than no promise: the page would keep claiming a
    # window the build had already let go of.
    stable = "—"
    try:
        parts = open(os.path.join(ROOT, "pipeline", "scorer.lock"), encoding="utf-8").read().split()
        stable = parts[3] if len(parts) > 3 else "—"
    except OSError:
        pass
    # RAISE rather than degrade. Without this the page renders "top 0 … tashan score —%" — a
    # coverage section, on the methodology page, made of placeholders. Same rule as the marker guard
    # below: for a document whose only job is to be checkable, publishing a blank is worse than
    # failing the build. pipeline/run.py runs `coverage` immediately before `pages` for this reason.
    covp = os.path.join(ROOT, "web", "data", "coverage.json")
    try:
        cov = json.load(open(covp, encoding="utf-8"))
        t, a = cov["tiers"]["top1000"], cov["all"]
        if not (t.get("n") and a.get("n")):
            raise ValueError("empty tiers")
    except (OSError, ValueError, KeyError) as e:
        raise SystemExit(f"methodology bake needs {os.path.relpath(covp, ROOT)} ({e}). "
                         f"Run: python3 pipeline/coverage.py")

    def cpct(d, k):
        return str(round(100.0 * d[k] / d["n"]))

    targets = [
        (r'(<span class="mono" id="mScorer">)[^<]*(</span>)', SCORER or "?"),
        (r'(<span class="mono" id="mScorer2">)[^<]*(</span>)', SCORER or "?"),
        (r'(<span id="mScorerDate">)[^<]*(</span>)', when),
        (r'(<span id="mScorerStable">)[^<]*(</span>)', stable),
        (r'(<span class="mono" id="cvTierN">)[^<]*(</span>)', f"{t.get('n', 0):,}"),
        (r'(<span class="mono" id="cvAll">)[^<]*(</span>)', f"{a.get('n', 0):,}"),
        (r'(<span id="cvAll2">)[^<]*(</span>)', f"{a.get('n', 0):,}"),
        (r'(<span id="cvScore">)[^<]*(</span>)', cpct(t, "score")),
        (r'(<span id="cvScan">)[^<]*(</span>)', cpct(t, "scan")),
        (r'(<span id="cvGrade">)[^<]*(</span>)', cpct(t, "grade")),
        (r'(<span id="cvTask">)[^<]*(</span>)', cpct(t, "task")),
        (r'(<span id="cvFull">)[^<]*(</span>)', cpct(t, "full")),
        (r'(<span id="cvAllFull">)[^<]*(</span>)', cpct(a, "full")),
    ]
    subs = 0
    for pat, val in targets:
        html, n = re.subn(pat, lambda m: m.group(1) + val + m.group(2), html, count=1)
        subs += n

    # STRUCTURED DATA ON THE PAGE MOST WORTH CITING. methodology.html carried none — zero JSON-LD on
    # the one document that answers "how does tashan score anything", which is precisely the question
    # an answer engine needs sourced before it will quote a number. Every hub had an ItemList and
    # every dossier a Review; the explanation behind all of them was unstructured.
    #
    # TechArticle rather than Article: it is documentation of a method, and `about` points at the
    # Dataset those numbers live in so the two are linked rather than merely adjacent. The dates are
    # the export's, not today's — the method is described as of the run that produced the numbers.
    lda = {"@context": "https://schema.org", "@type": "TechArticle",
           "headline": "How the tashan score is derived",
           "description": "The exact arithmetic behind the tashan score, the evidence each input "
                          "comes from, how much of the corpus is measured, and what the score "
                          "deliberately does not claim.",
           "url": BASE + "/methodology.html",
           "mainEntityOfPage": BASE + "/methodology.html",
           "author": {"@type": "Organization", "name": "tashan", "url": BASE + "/"},
           "publisher": {"@type": "Organization", "name": "tashan", "url": BASE + "/"},
           "datePublished": when, "dateModified": when,
           "inLanguage": "en",
           "about": {"@type": "Dataset", "name": "The tashan Index — measured AI capabilities",
                     "url": BASE + "/"},
           # The version and the window it is promised to hold. A method article that does not say
           # which ruler it describes is one a reader cannot check a stored number against.
           "version": SCORER or "unversioned",
           "creativeWorkStatus": f"Scorer {SCORER} frozen through {stable}" if stable != "—" else "Active",
           "license": BASE + "/terms.html"}
    tag = '<script type="application/ld+json">' + json.dumps(lda, ensure_ascii=False,
                                                             separators=(",", ":")) + "</script>"
    mark, endmark = "<!--METHOD-LD-->", "<!--/METHOD-LD-->"
    if mark in html:
        html = re.sub(re.escape(mark) + r"[\s\S]*?" + re.escape(endmark), mark + tag + endmark,
                      html, count=1)
    elif "</head>" in html:
        html = html.replace("</head>", "  " + mark + tag + endmark + "\n</head>", 1)
    else:
        raise SystemExit("methodology.html has no </head> to attach structured data to.")
    # A baker that silently matches nothing is worse than no baker: it prints success while the page
    # keeps whatever a human last typed, which is exactly how "s2" survived two scorer bumps.
    if subs != len(targets):
        raise SystemExit(f"methodology bake matched {subs}/{len(targets)} targets — the markers moved "
                         f"or were edited away. Fix web/methodology.html, do not let this pass silently.")
    open(p, "w", encoding="utf-8").write(html)
    print(f"methodology: baked scorer {SCORER} (stable to {stable}) / {when} / coverage top1000 "
          f"{cpct(t, 'full')}% full")


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
            "/browse.html", "/compare.html",
            # The freshest page on the site, and the only one competitors cannot reproduce — it is
            # built from a series that cannot be backfilled. `changefreq` says daily below.
            "/changes.html"]
    def _static_url(u):
        # /changes.html is rewritten every night from change_events; saying so is the whole point of
        # having it in here. Everything else changes when the site is rebuilt, which is not daily.
        freq = "<changefreq>daily</changefreq>" if u == "/changes.html" else ""
        return "  <url><loc>" + BASE + chrome.canon(u) + "</loc>" + freq + "</url>\n"

    static = "".join(_static_url(u) for u in urls)
    # A SITEMAP IS A REQUEST TO INDEX, so it must agree with the robots tag on the page. Submitting
    # a URL that answers `noindex` wastes crawl budget and sends a contradictory signal about a site
    # whose entire distribution strategy is being readable by crawlers and answer engines.
    caps_x = "".join('  <url><loc>' + BASE + chrome.canon("/capability/" + c["slug"] + ".html")
                     + '</loc>' + lastmod(c) + '<changefreq>weekly</changefreq></url>\n'
                     for c in caps if not thin(c))
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

MD_SHARDS = 64
MD_DIR = os.path.join(ROOT, "web", "data", "md")


def md_shard(slug, n=MD_SHARDS):
    """Which shard a slug's markdown lives in.

    MUST stay identical to shard() in functions/capability/[[path]].js — the Function computes this
    to know which file to fetch, so a divergence 404s every dossier at once. tests/test_agent_surface
    checks a sample of real slugs against the JS. Slugs are [a-z0-9-] by construction (slugify), so
    per-character iteration is ASCII-safe on both sides.
    """
    h = 0
    for ch in slug:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h % n


def write_md_shards(by_slug):
    """The markdown dossiers, as sharded data instead of one file each.

    CLOUDFLARE PAGES REFUSES ANY DEPLOYMENT OVER 20,000 FILES. Not degrades — refuses. Writing one
    .md beside each .html made every capability cost two files, and the corpus went 7,365 -> 9,013 in
    a single run: at 18,759 files there were 620 capabilities of runway left and the next full run
    would have taken the site past the point where it could be published at all. It has happened
    before, when one .svg per capability hit 21,782 and badges had to move behind a Function.

    So the dossiers become 64 data files and a Function, which is the same move badges made. What
    they do NOT become is a second renderer: the markdown is still produced by markdown() above, in
    Python, at build time — the Function only looks a string up and returns it. That matters more
    than the file count here, because a JS reimplementation of the dossier is exactly the "one
    concept, many implementations" defect this codebase has paid for six times.

    64 shards keeps each one around 150 KB, small enough that a Worker parses it in milliseconds and
    the edge cache holds all of them comfortably.
    """
    os.makedirs(MD_DIR, exist_ok=True)
    shards = [{} for _ in range(MD_SHARDS)]
    for slug, text in by_slug.items():
        shards[md_shard(slug)][slug] = text
    for i, s in enumerate(shards):
        with open(os.path.join(MD_DIR, f"{i:02d}.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, separators=(",", ":"))
    # A shard that vanished from the map would silently 404 its slugs, so every index is written even
    # when empty rather than skipped.
    for f in os.listdir(MD_DIR):
        if f.endswith(".json") and not (f[:-5].isdigit() and int(f[:-5]) < MD_SHARDS):
            os.remove(os.path.join(MD_DIR, f))
    sizes = [os.path.getsize(os.path.join(MD_DIR, f"{i:02d}.json")) for i in range(MD_SHARDS)]
    print(f"markdown dossiers: {len(by_slug):,} in {MD_SHARDS} shards "
          f"(largest {max(sizes) // 1024} KB) -> web/data/md/")


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
    global SCORER, GEN_DATE
    SCORER = d.get("scorer", "")
    GEN_DATE = (gen or "")[:10]
    caps = [c for c in d["capabilities"] if c.get("id", "").split(":", 1)[0] != "key"]
    for c in caps:
        c.setdefault("slug", slugify(c["id"]))
    have = {c["slug"] for c in caps}  # only these have prerendered pages
    for c in caps:
        if c.get("co_used"):  # drop co-use links to caps we didn't prerender (would 404 / hit the slow legacy path)
            c["co_used"] = [x for x in c["co_used"] if slugify(x["id"]) in have]
    for c in caps:
        open(os.path.join(OUT, c["slug"] + ".html"), "w").write(page(c, gen))
    write_md_shards({c["slug"]: markdown(c, gen) for c in caps})
    # Remove pages for capabilities that dropped out of the export (junk-filtered, deprecated, renamed).
    # Without this they linger as orphans: still crawlable, in no sitemap, linked from nothing, and
    # frozen at whatever asset version last wrote them. `.md` is included because 9,013 of them were
    # files until the shard move below, and a tree that has been through both must end up clean.
    stale = [f for f in os.listdir(OUT)
             if (f.endswith(".html") and f[:-5] not in have) or f.endswith(".md")]
    for f in stale:
        os.remove(os.path.join(OUT, f))
    if stale:
        print("removed %d orphaned/superseded page file(s)" % len(stale))
    sitemap(caps)
    bake_hero(caps, d.get("total_capabilities") or len(caps))
    bake_methodology(gen)
    bake_pricing()
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
