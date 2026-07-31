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
import chrome
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
        # review — attributed, dated, and re-derivable. Same number, honest shape.
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

def summary(c):
    """Server-rendered content crawlers see with JS off (capability.js replaces it for humans)."""
    n = disp(c); rows = []
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
    works = '<p class="mono fs-sm faint"><b>Works with:</b> ' + esc(", ".join(clients)) + '</p>'
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
            + ('<p class="mono">' + " &nbsp;·&nbsp; ".join(links) + '</p>' if links else '') + audit)

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

    def unlock(what):
        return ('<a class="unlock" href="/pricing.html?ref=' + esc(c["id"]) + '" title="' + esc(what)
                + '">unlock detail</a>')

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
            unlock("Which advisory, its severity, the affected range and the version that fixes it"),
            "secrow--alert"))
    else:
        rows.append(sec_row("No known advisories", '<span class="sev sev--none">clear</span>',
                            '<span class="secrow__ok">checked against OSV for '
                            + esc(c.get("npm_latest_version") or "the current release") + "</span>"))

    if c.get("sec_install_script"):
        rows.append(sec_row("<b>Runs a script at install time</b>",
                            '<span class="sev sev--high">code</span>',
                            unlock("The exact command this package executes when it is installed"),
                            "secrow--alert"))

    if perms:
        # only the first permission is exported now (the full list is the paid detail), so the total
        # comes from sec_perm_n — see build.py::redact_paid.
        # every permission, free — see build.py::redact_paid for why this is not gated
        rows.append(sec_row(
            esc(" · ".join(PERM_LABEL.get(x, x) for x in perms)), "",
            '<span class="secrow__ok">from declared dependencies</span>'))
    else:
        rows.append(sec_row("No permission surface detected", "",
                            '<span class="secrow__ok">declares no dependency that reaches files, '
                            "shell or network</span>"))

    if c.get("sec_remote_content"):
        rows.append(sec_row("Can carry remote content into your agent", "",
                            unlock("What it fetches, and why that is the injection-exposure question "
                                   "for agent tools")))

    rows.append(sec_row(
        "Signed build provenance" if c.get("sec_provenance") else "No build provenance", "",
        '<span class="secrow__ok">' + ("published from public CI with an attestation"
                                       if c.get("sec_provenance") else
                                       "no attestation — the published artifact cannot be traced to "
                                       "its source") + "</span>",
        "" if c.get("sec_provenance") else "secrow--warn"))

    # THE OFFER IS EARNED, PER PAGE, OR IT IS NOT MADE. Count only findings whose ACTIONABLE detail
    # is actually gated on this capability. A clean package has nothing to unlock, so it carries no
    # pitch at all — a standing banner on all 5,788 pages is the thing readers learn to stop seeing,
    # and pitching a fix for a package with nothing wrong is a lie about the product.
    gated = []
    if n:
        gated.append("which advisor" + ("y and the version that fixes it" if n == 1
                                        else "ies, and the versions that fix them"))
    if c.get("sec_install_script"):
        gated.append("the exact command it runs at install time")
    if c.get("sec_remote_content"):
        gated.append("what third-party content it can pull into your agent")

    sub = ("Every finding is shown in full. A licence adds the detail needed to act on it — "
           "which advisory, what the install script does, the version that fixes it."
           if gated else
           # Nothing is withheld here, so do not imply that something is.
           "Every finding is shown in full. Nothing on this page is behind a licence — there is no "
           "advisory to name and no install script to read.")

    offer = ""
    if gated:
        many = len(gated) > 1
        offer = ('<div class="secoffer">'
                 '<p class="secoffer__h"><b>' + str(len(gated)) + " finding" + ("s" if many else "") +
                 " here " + ("have" if many else "has") + " detail behind a licence.</b> "
                 "You can see " + ("they exist" if many else "it exists") +
                 " above, free, permanently — Pro tells you " + "; ".join(gated) + ".</p>"
                 '<p class="secoffer__cta">'
                 '<a class="btn btn--primary" href="/pricing.html?ref=' + esc(c["id"]) + '">'
                 "Unlock the fix &mdash; $6/mo &rsaquo;</a>"
                 '<a class="link secoffer__alt" href="/start.html">or check your whole config free '
                 "with <code>npx tashan-cli doctor</code></a></p></div>")

    return sec("Security audit", '<div class="sec">' + "".join(rows) + "</div>" + offer, sub,
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
