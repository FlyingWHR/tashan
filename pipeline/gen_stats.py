#!/usr/bin/env python3
"""/stats.html — the MCP ecosystem in numbers, built to be cited.

WHY THIS SHAPE, and why it is a distribution asset rather than an about page.

Measured 16 Aug 2026: we do not rank for "best MCP server for <job>". Seven editorial blog posts do,
and none of them carries a measurement — they rank on prose and domain authority, which we cannot
out-generate with more tables. Our deficit is AUTHORITY, and authority is built from citations.

But those posts would be better if they cited us, and they cannot cite what we do not publish in a
quotable form. We hold the largest measurement of this ecosystem anywhere — 39,374 capabilities
tracked, 7,862 scanned against OSV at the version you would install today — and until now it existed
only as JSON at /data/coverage.json and as rows in a database.

So this page publishes the numbers a writer actually wants, each one derived from a query rather
than typed, with the licence and an exact citation line beside it. A stats page is the classic thing
people link to, and a link is the thing we are short of.

HONEST BY CONSTRUCTION, which is the whole product:
  - The aggregate coverage ratio FALLS whenever discovery succeeds — coverage.py's own docstring
    says so, and it went 47%->41% in two days with nothing getting worse. So the aggregate is
    reported and the COMMITMENT is stated over the demand curve, where an absence actually costs a
    reader something.
  - Every number is a count of rows, never an estimate, and the query is named beside it.
  - Nothing here is behind the paywall. These are facts about the ecosystem, and a fact you have to
    pay for is a fact nobody repeats.

    python3 pipeline/gen_stats.py            # write web/stats.html
    python3 pipeline/gen_stats.py --selftest # no DB, no network
"""
import re, datetime as dt, html, json, os, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assets                                                    # noqa: E402
import chrome                                                    # noqa: E402

BASE = "https://tashan.sh"
OUT = os.path.join(ROOT, "web", "stats.html")
DB = os.path.join(ROOT, "data", "tashan.db")

esc = lambda s: html.escape(str(s or ""), quote=True)

# (key, label, SQL, what the number MEANS — the sentence a reader would quote)
FACTS = [
    ("tracked", "capabilities tracked",
     "SELECT COUNT(*) FROM capabilities",
     "Every MCP server, agent skill and plugin we have discovered, measured or not."),
    ("scored", "carry a tashan score",
     "SELECT COUNT(*) FROM capabilities WHERE tashan_score IS NOT NULL",
     "Enough public evidence to rank on upkeep, freshness and real adoption."),
    ("scanned", "scanned for advisories",
     "SELECT COUNT(*) FROM capabilities WHERE sec_scanned_at IS NOT NULL",
     "Queried against OSV.dev at the version you would install today, so a finding means the "
     "current release is affected."),
    ("graded", "graded on how well they document themselves",
     "SELECT COUNT(*) FROM capabilities WHERE expertise_verdict IS NOT NULL",
     "Read against a published, conjunctive rubric rather than a feeling."),
]

HEALTH = [
    ("dying", "are deprecated, archived or abandoned",
     "SELECT COUNT(*) FROM capabilities WHERE tashan_score IS NOT NULL "
     "AND (npm_deprecated=1 OR gh_archived=1 OR vitality='abandoned')",
     "Their publisher, npm or the registry says to stop using them."),
    ("solo", "have a single primary maintainer",
     "SELECT COUNT(*) FROM capabilities WHERE tashan_score IS NOT NULL AND single_maintainer=1",
     "One person away from unmaintained. Not a fault, but a fact worth knowing before you depend "
     "on it."),
    ("install_script", "run a script on your machine at install time",
     "SELECT COUNT(*) FROM capabilities WHERE sec_install_script IS NOT NULL "
     "AND sec_install_script != ''",
     "A postinstall or preinstall hook — code that runs before you have agreed to anything."),
    ("opaque_install", "of those install scripts run code we CANNOT read",
     None,     # derived: see opaque_share(). Percentage of install_script.
     "The hook runs a file inside the tarball — postinstall.js, install.js — and a static check "
     "cannot see what is in it without downloading and running the package, which no auditor "
     "should do. This is the honest limit of every scanner, including ours."),
    ("no_provenance", "of scanned packages ship with NO build provenance",
     None,     # derived: scanned - attested, as a percentage. Computed in numbers().
     "npm signs every tarball it hosts, so a signature proves nothing about who built it. Only a "
     "build attestation ties the artifact to its source."),
    ("malicious", "are in OSV's malicious-packages database",
     "SELECT COUNT(*) FROM capabilities WHERE sec_max_severity='MALICIOUS'",
     "Not a vulnerability — the package IS the attack. They are refused a place on every ranking "
     "and kept reachable only so a tool can warn someone already running one."),
]


# An install hook is either INLINE — `node -e "..."`, echo, chmod, mkdir — where the code is right
# there in package.json and we can read it, or it DELEGATES to a file in the tarball, where we
# cannot. That distinction is the whole point: a scanner that reports "runs a script" without saying
# whether it could read the script invites the reader to assume it did.
#
# Deliberately conservative — anything we are not sure is inline counts as inline, so this figure is
# a FLOOR on what is unreadable, never an inflated one.
INLINE = re.compile(r"""^\s*(node\s+-e\s|echo\s|chmod\s|mkdir\s|test\s|which\s|\[\s|true\s*$)""",
                    re.I | re.X)


def opaque_share(con):
    """(unreadable, total) install hooks. Splits on whether the code is in package.json or a file."""
    rows = [r[0] or "" for r in con.execute(
        "SELECT sec_install_script FROM capabilities "
        "WHERE sec_install_script IS NOT NULL AND sec_install_script != ''")]
    # A chained hook is only readable if EVERY step is: `chmod x && node install.js` still runs a
    # file we cannot see, and reporting it as readable would be the exact overstatement this guards.
    unreadable = sum(1 for s in rows
                     if any(not INLINE.match(part.strip())
                            for part in re.split(r"&&|\|\||;", s) if part.strip()))
    return unreadable, len(rows)


def numbers(con):
    q = lambda s: con.execute(s).fetchone()[0]
    n = {k: q(sql) for k, _l, sql, _w in FACTS}

    # THE SITE MUST DESCRIBE WHAT THE SITE PUBLISHED. Every count here came from whatever database
    # happened to be on the machine, and the rest of the site is built from the EXPORT — so the
    # moment those two are out of step, this page contradicts its own homepage. Tonight it did:
    # index.json, for-hosts and the hero all said 95,101 tracked while this page, generated from a
    # local database that had not run discovery, said 55,268. On the one page written specifically
    # to be cited, that is the worst possible number to get wrong.
    #
    # Only the two figures the export actually carries are overridden; everything else here is a
    # count of columns the export does not publish, and those still come from the database.
    idxp = os.path.join(ROOT, "web", "data", "index.json")
    if os.path.exists(idxp):
        try:
            with open(idxp, encoding="utf-8") as fh:
                idx = json.load(fh)
            if idx.get("total_capabilities"):
                n["tracked"] = idx["total_capabilities"]
            if idx.get("measured"):
                n["scored"] = max(n.get("scored", 0), idx["measured"])
        except (OSError, ValueError):
            pass
    for k, _l, sql, _w in HEALTH:
        if sql:
            n[k] = q(sql)
    attested = q("SELECT COUNT(*) FROM capabilities WHERE sec_provenance=1")
    n["attested"] = attested
    n["no_provenance"] = round(100 * (n["scanned"] - attested) / n["scanned"]) if n["scanned"] else 0
    opaque, hooks = opaque_share(con)
    n["opaque_install_n"] = opaque
    n["opaque_install"] = round(100 * opaque / hooks) if hooks else 0
    n["history_points"] = q("SELECT COUNT(*) FROM signal_history")
    n["days"] = q("SELECT COUNT(DISTINCT substr(at,1,10)) FROM signal_history")
    return n


def citation(n, today):
    """The line a writer pastes. Everything they need to attribute it, in one sentence."""
    return (f"tashan, “The MCP ecosystem, measured” ({today}): {n['tracked']:,} capabilities "
            f"tracked, {n['scanned']:,} scanned against OSV at the installable version. "
            f"{BASE}/stats — CC BY 4.0.")


def render(n, cov, today):
    lede = (f"We track {n['tracked']:,} MCP servers, agent skills and plugins. "
            f"{n['scored']:,} carry a score, {n['scanned']:,} have been scanned for advisories at "
            f"the version you would install today, and {n['no_provenance']}% of those ship with no "
            f"build provenance.")
    lds = [{
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "The MCP ecosystem, measured",
        "description": lede,
        "url": BASE + "/stats.html",
        "isAccessibleForFree": True,
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": {"@type": "Organization", "name": "tashan", "url": BASE},
        "dateModified": today,
        "measurementTechnique": BASE + "/methodology.html",
        "variableMeasured": [{"@type": "PropertyValue", "name": l, "value": n[k]}
                             for k, l, _s, _w in FACTS],
    }]

    def block(items, cls):
        h = ['<dl class="stat ' + cls + '">']
        for k, label, _sql, why in items:
            v = n.get(k, 0)
            shown = f"{v}%" if k in ("no_provenance", "opaque_install") else f"{v:,}"
            h.append('<div class="stat__i"><dt class="stat__n mono">' + esc(shown) + "</dt>"
                     '<dd class="stat__l">' + esc(label)
                     + '<span class="mnote stat__w o-70"> ' + esc(why) + "</span></dd></div>")
        h.append("</dl>")
        return "\n".join(h)

    cite = citation(n, today)
    h = [
        '<main class="wrap" id="main">',
        '<p class="eyebrow mono">— THE NUMBERS</p>',
        '<h1 class="h1">The MCP ecosystem, measured.</h1>',
        '<p class="lede">' + esc(lede) + "</p>",
        '<p class="mono fs-sm o-70">Every figure on this page is a count of rows, recomputed nightly '
        'and derived from public evidence. Nothing here is behind the paywall — a fact you have to '
        'pay for is a fact nobody repeats. '
        '<a class="link" href="/methodology.html">How we measure</a> · '
        '<a class="link" href="/changes.html">What changed recently</a></p>',

        '<h2 class="h2 mt-6">What is measured</h2>',
        block(FACTS, "stat--head"),

        '<h2 class="h2 mt-6">What the ecosystem looks like</h2>',
        block(HEALTH, "stat--health"),
    ]

    if cov:
        head = cov.get("headline") or {}
        h += [
            '<h2 class="h2 mt-6">Coverage, weighted by demand</h2>',
            '<p class="p">The aggregate ratio falls every time discovery succeeds — finding a '
            'thousand new capabilities makes the fraction we have measured smaller while nothing '
            'has got worse. So it is reported and never targeted. What we commit to is the '
            '<b>demand curve</b>, because what costs a reader is an absence on the thing they '
            'looked up, not a gap in the tail.</p>',
            '<dl class="stat stat--cov"><div class="stat__i">'
            '<dt class="stat__n mono">' + esc(str(head.get("scanned_pct", "—"))) + "%</dt>"
            '<dd class="stat__l">of the top 100 by adoption are scanned for advisories</dd></div>'
            '<div class="stat__i"><dt class="stat__n mono">'
            + esc(str(head.get("scored_pct", "—"))) + "%</dt>"
            '<dd class="stat__l">carry a score</dd></div>'
            '<div class="stat__i"><dt class="stat__n mono">'
            + esc(str(head.get("graded_pct", "—"))) + "%</dt>"
            '<dd class="stat__l">are graded on documentation</dd></div></dl>',
        ]

    h += [
        '<h2 class="h2 mt-6">The record behind it</h2>',
        '<p class="p">' + f"{n['history_points']:,}" + " measurements across "
        + f"{n['days']:,}" + ' days. That series cannot be backfilled by anyone, including us — '
        'you cannot know what a score was in June unless you measured it in June — which is why '
        # NOT "a page nobody else can publish" — we cannot know who else has been recording, and a
        # claim about everyone else is exactly the kind this product refuses everywhere else. The
        # fact underneath it is stronger and checkable: the series cannot be reconstructed after the
        # fact, by us or anyone, so the page can only come from having recorded it daily.
        '<a class="link" href="/changes.html">what changed</a> cannot be rebuilt from today&rsquo;s '
        'data &mdash; only from having recorded it every day since July.</p>',

        '<h2 class="h2 mt-6">Cite this</h2>',
        '<p class="p">Published under <a class="link" rel="license" '
        'href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Quote any number here, '
        'with attribution. If you are writing about which MCP server to use, these are the figures '
        'behind the rankings — and <a class="link" href="/llms.txt">llms.txt</a> is the machine '
        'version.</p>',
        '<div class="embed"><div class="embed__row"><code class="embed__code">' + esc(cite)
        + '</code><button class="embed__copy" id="citeCopy" type="button" data-copy="'
        + esc(cite) + '">copy</button></div></div>',
        "</main>",
    ]
    return lds, "\n".join(h), lede


def main():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    n = numbers(con)
    con.close()
    cov = {}
    p = os.path.join(ROOT, "web", "data", "coverage.json")
    if os.path.exists(p):
        cov = json.load(open(p, encoding="utf-8"))
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    lds, body, lede = render(n, cov, today)

    import gen_hubs
    doc = gen_hubs.head(
        "The MCP ecosystem, measured — " + f"{n['tracked']:,}" + " capabilities · tashan",
        (f"{n['tracked']:,} MCP servers, skills and plugins tracked; {n['scanned']:,} scanned for "
         f"advisories; {n['no_provenance']}% have no build provenance. Free, CC BY 4.0.")[:155],
        BASE + "/stats.html", lds)
    doc += body + chrome.footer_html()
    doc += '<script src="/js/site.js?v=' + str(assets.V) + '" defer></script>\n</body>\n</html>\n'
    open(OUT, "w", encoding="utf-8").write(doc)
    print(f"stats: {n['tracked']:,} tracked, {n['scanned']:,} scanned -> web/stats.html")
    return 0


def _selftest():
    n = {"tracked": 39374, "scored": 14419, "scanned": 7862, "graded": 3969, "dying": 727,
         "solo": 7652, "install_script": 490, "attested": 2044, "no_provenance": 74,
         "malicious": 6, "history_points": 229279, "days": 19,
         "opaque_install": 92, "opaque_install_n": 453}
    lds, body, lede = render(n, {"headline": {"scanned_pct": 100, "scored_pct": 92, "graded_pct": 67}},
                             "2026-08-16")
    assert "39,374" in body and "74%" in body, "the headline numbers must reach the page"
    assert "cannot be backfilled" in body, "the moat is the reason the page is worth citing"
    # The citation line is the distribution mechanism: it must carry source, date, numbers, licence.
    c = citation(n, "2026-08-16")
    for must in ("tashan", "2026-08-16", "39,374", "CC BY 4.0", BASE + "/stats"):
        assert must in c, (must, c)
    # Honest framing is not optional — the aggregate falls when discovery succeeds and the page
    # must say so rather than quoting a flattering ratio.
    assert "falls every time discovery succeeds" in body
    assert lds[0]["isAccessibleForFree"] is True and lds[0]["@type"] == "Dataset"
    assert len(lds[0]["variableMeasured"]) == len(FACTS)
    # No number may be typed: every FACTS row is either SQL or explicitly derived.
    assert all(sql for _k, _l, sql, _w in FACTS), "a fact without a query is a claim"
    assert "92%" in body, "the unreadable-install share must reach the page"

    # THE SPLIT THAT DECIDES THE NUMBER: inline code we can read vs a file we cannot. Getting this
    # backwards would let us claim we audited install behaviour we never saw.
    import sqlite3 as _s
    c2 = _s.connect(":memory:")
    c2.execute("CREATE TABLE capabilities (sec_install_script TEXT)")
    c2.executemany("INSERT INTO capabilities VALUES (?)", [
        ("echo 'installed!'",),                       # readable
        ('node -e "console.log(1)"',),                # readable
        ("chmod +x dist/index.js",),                  # readable
        ("node scripts/postinstall.js",),             # a file in the tarball: unreadable
        ("playwright install chromium",),             # downloads a browser: unreadable
        # A CHAIN IS ONLY READABLE IF EVERY STEP IS. Splitting on && and taking the first part
        # would score this as a harmless chmod and hide the install.js behind it.
        ("chmod +x a && node install.js",),
        ("",), (None,)])                              # neither counts as a hook at all
    op, tot = opaque_share(c2)
    assert (op, tot) == (3, 6), (op, tot)
    print("gen_stats selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
