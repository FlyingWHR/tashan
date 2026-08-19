#!/usr/bin/env python3
"""/changes.html — what changed in the MCP ecosystem, published daily.

WHY THIS IS THE DISTRIBUTION ASSET, and not another hub page.

Measured 16 Aug 2026: we do not rank for the queries our 12,000 generated pages were built to win.
"best MCP server for web scraping ranked" returns seven editorial blog posts and no tashan; the same
for a head-to-head query where we publish a dedicated compare page. Those posts win because they
answer in prose and carry domain authority, and more of the same shape will not change that.

But look at what the answer engine said when asked which of two servers is better maintained:

    "the search results don't provide detailed information about the relative maintenance
     intensity, release frequency, or issue resolution speed"

That is the question, unanswered, in public. It is also exactly what `signal_history` and
`change_events` hold and nobody else does — the series cannot be backfilled, so a competitor
starting today cannot produce this page at any price. Four rival scorers exist (mcp-scorecard.ai at
4,484 servers, MCP Radar, trusted-mcp.org at 102, mcp-trust-radar) and not one publishes a dated
record of what moved.

So this page is the opposite of the hubs: not a bigger table, but the one thing only we can say —
dated, specific, and fresh every night, which is the signal a static catalogue can never send.

WHAT IT MUST NOT DO. `version_published` is 830 of 3,721 events and says nothing worth reading; a
page that leads with it is a changelog nobody finishes. Consequence leads, routine is counted and
collapsed. Every line is an event we recorded on a date, never a projection, and every claim on the
page is a count of rows in the database.

    python3 pipeline/gen_changes.py            # write web/changes.html
    python3 pipeline/gen_changes.py --selftest # no DB, no network
"""
import datetime as dt, html, json, os, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assets                                                    # noqa: E402
from prerender import slugify                                    # noqa: E402
import chrome                                                    # noqa: E402

BASE = "https://tashan.sh"
OUT = os.path.join(ROOT, "web", "changes.html")
DB = os.path.join(ROOT, "data", "tashan.db")
DAYS = 30
MAX_ROWS = 260          # the page is read, not exported; the feed and the API carry the whole set

esc = lambda s: html.escape(str(s or ""), quote=True)

# What a reader needs to act on, loudest first. `version_published` is deliberately absent: it is
# the bulk of the corpus and none of the signal.
CONSEQUENTIAL = ["advisory_new", "severity_raised", "ownership_changed", "install_script_added",
                 "install_script_changed", "delisted", "deprecated", "abandoned", "archived",
                 "maintainers_dropped", "permissions_widened", "score_moved"]

HEADLINE = {
    "advisory_new": "gained a security advisory",
    "severity_raised": "had an advisory get worse",
    "ownership_changed": "changed hands",
    "install_script_added": "started running a script at install time",
    "install_script_changed": "changed what it runs at install time",
    "deprecated": "was deprecated by its publisher",
    "abandoned": "stopped being maintained",
    "archived": "had its repository archived",
    "delisted": "was removed from the registry",
    "maintainers_dropped": "lost maintainers",
    "permissions_widened": "widened what it can reach",
    "score_moved": "moved on the score",
}


# THE SECURITY SWEEP'S OWN SHADOW. Until 18 Aug the state snapshot did not record whether the L1-L4
# scan had ever run for a capability, so the first time the scan reached a package its NULL install
# script became "node install.js" and the diff called that an ADDITION. This page told the public
# that 301 packages "started running a script at install time" in 30 days, against 490 that have one
# at all — 143 of them on a single day, which is the shape of a scanner walking a corpus, not of the
# world changing.
#
# change_events.py now requires a prior observation before any security transition (see SEC_FIELDS).
# That fixes every future event and NOTHING already written: no historical snapshot recorded the
# flag, so a pre-cutoff security event cannot be told apart from a first look. They are therefore
# not shown. They are not deleted either — a handful are real, and deleting a record because it is
# inconveniently ambiguous is how an archive stops being one. They simply stop being published as
# fact, which is the claim we could not stand behind.
SEC_KINDS = ("advisory_new", "severity_raised", "install_script_added", "install_script_changed",
             "permissions_widened")
# THE DATE THE GUARD FIRST RAN, NOT THE DATE IT WAS WRITTEN. This said 2026-08-18 — when the fix
# was committed — while the nightly kept running the previous commit for two more days because the
# fix sat unpushed. The 19 Aug run therefore emitted first-observation events that this cutoff
# happily published as fact. A trust boundary has to key on deployment; code that exists on a laptop
# has never protected anything.
SEC_TRUSTED_FROM = "2026-08-20"


def rows(con, days=DAYS):
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%d")
    # `slug` is DERIVED, not stored — prerender.slugify() is the one definition and the dossier
    # filenames follow it. Selecting c.slug looked obvious and does not exist.
    q = ("SELECT e.cap_id, e.at, e.kind, e.severity, e.what, e.why, e.action, "
         "       c.name, c.tashan_score "
         "FROM change_events e LEFT JOIN capabilities c ON c.id = e.cap_id "
         "WHERE substr(e.at,1,10) >= ? AND e.kind IN (%s) "
         "  AND (e.kind NOT IN (%s) OR substr(e.at,1,10) >= ?) "
         "ORDER BY e.at DESC, "
         "  CASE e.severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, e.cap_id"
         % (",".join("?" * len(CONSEQUENTIAL)), ",".join("?" * len(SEC_KINDS))))
    return con.execute(q, [since] + list(CONSEQUENTIAL) + list(SEC_KINDS)
                       + [SEC_TRUSTED_FROM]).fetchall()


def tally(con, days=DAYS):
    """Counts a reader (or an answer engine) can quote. Every one is a row count, not an estimate."""
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%d")
    out = {}
    # The SAME withholding as rows(). This tally feeds the JSON-LD description, the meta
    # description and the citation line — the three places a number gets quoted BY SOMEONE ELSE.
    # Filtering the visible list but not the counts is worse than not filtering at all: the page
    # would show 12 install-script events above a sentence advertising 301, and the sentence is the
    # part an answer engine repeats.
    for kind, n in con.execute(
            "SELECT kind, COUNT(DISTINCT cap_id) FROM change_events "
            "WHERE substr(at,1,10) >= ? AND (kind NOT IN (%s) OR substr(at,1,10) >= ?) "
            "GROUP BY kind" % ",".join("?" * len(SEC_KINDS)),
            [since] + list(SEC_KINDS) + [SEC_TRUSTED_FROM]):
        out[kind] = n
    return out


def meta_description(t, days=DAYS):
    """<=155 characters, because this is the line that appears in a search result. The full
    sentence() runs to 218 on a busy month and gets truncated mid-clause by the engine."""
    parts = []
    for k, short in (("deprecated", "deprecated"), ("abandoned", "abandoned"),
                     ("install_script_added", "added install scripts"),
                     ("advisory_new", "new advisories")):
        if t.get(k):
            parts.append(f"{t[k]:,} {short}")
    if not parts:
        return f"Dated record of what changed across the MCP ecosystem, updated daily."
    return ("What changed in the MCP ecosystem, dated: "
            + ", ".join(parts[:3]) + f" in {days} days. Updated daily.")[:155]


def sentence(t, days=DAYS):
    """The quotable line. Only facts with a non-zero count appear — a sentence padded with zeroes
    reads as a template, and an answer engine will lift the whole thing."""
    bits = []
    order = [("deprecated", "were deprecated by their publishers"),
             ("abandoned", "stopped being maintained"),
             ("install_script_added", "started running a script at install time"),
             ("advisory_new", "gained a security advisory"),
             ("ownership_changed", "changed hands"),
             ("permissions_widened", "widened what they can reach")]
    for k, phrase in order:
        if t.get(k):
            bits.append(f"{t[k]:,} {phrase}")
    if not bits:
        return f"No consequential changes recorded in the last {days} days."
    head = "In the last %d days, tashan recorded: " % days
    return head + "; ".join(bits) + "."


def published_slugs():
    """Slugs that actually have a dossier on disk.

    NOT every capability with a change event has a page: junk() drops some from the export, thin
    rows are never written, and a delisted one is deliberately absent. Linking every event to
    /capability/<slug>.html produced dozens of 404s on the first run — caught by tests/test_links.py,
    which walks this page like any other. A dead link on the page whose job is to be crawled is
    worse than no link at all.
    """
    d = os.path.join(ROOT, "web", "capability")
    if not os.path.isdir(d):
        return set()
    return {f[:-5] for f in os.listdir(d) if f.endswith(".html")}


def render(evs, t, generated, live=None):
    total = sum(t.values())
    lede = sentence(t)
    lds = [{
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "What changed in the MCP ecosystem",
        "description": lede,
        "url": BASE + "/changes.html",
        "isAccessibleForFree": True,
        "creator": {"@type": "Organization", "name": "tashan", "url": BASE},
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "temporalCoverage": f"{generated[:10]}/P{DAYS}D",
        "measurementTechnique": BASE + "/methodology.html",
        "distribution": [{"@type": "DataDownload", "encodingFormat": "application/atom+xml",
                          "contentUrl": BASE + "/changes.xml"}],
    }]
    parts = [chrome.__dict__.get("_noop", "")] if False else []
    h = [
        '<main class="wrap">',
        '<p class="eyebrow mono">— WHAT CHANGED</p>',
        '<h1 class="h1">The MCP ecosystem, dated.</h1>',
        '<p class="lede">' + esc(lede) + "</p>",
        '<p class="mono fs-sm o-70">Every line below is something we observed on the date shown, '
        'across ' + f"{total:,}" + ' capabilities. Routine releases are excluded — this is what '
        'would change a decision. <a class="link" href="/changes.xml">Atom feed</a> · '
        '<a class="link" href="/methodology.html">how we measure</a></p>',
    ]

    by_day = {}
    for r in evs[:MAX_ROWS]:
        by_day.setdefault(str(r[1])[:10], []).append(r)

    for day in sorted(by_day, reverse=True):
        h.append('<h2 class="h2 mt-6">' + esc(day) + "</h2>")
        h.append('<ul class="chg">')
        for cap_id, at, kind, sev, what, why, action, name, score in by_day[day]:
            slug = slugify(cap_id)
            label = name or (cap_id.split(":", 1)[-1])
            href = ("/capability/" + slug + ".html") if (live is None or slug in live) else None
            title = ('<a class="link" href="' + esc(href) + '">' + esc(label) + "</a>") if href \
                else esc(label)
            h.append(
                '<li class="chg__i chg__i--' + esc(sev or "info") + '">'
                + '<span class="chg__k mono">' + esc(HEADLINE.get(kind, kind.replace("_", " "))) + "</span> "
                + "<b>" + title + "</b>"
                + ('<span class="chg__s mono o-70"> · ' + str(int(score)) + "</span>" if score else "")
                + '<p class="chg__w">' + esc(what) + "</p>"
                + ('<p class="mnote chg__y o-70">' + esc(why) + "</p>" if why else "")
                + ('<p class="mnote chg__a mono fs-sm">' + esc(action) + "</p>" if action else "")
                + "</li>")
        h.append("</ul>")

    if len(evs) > MAX_ROWS:
        h.append('<p class="mono fs-sm o-70 mt-4">Showing the ' + f"{MAX_ROWS:,}"
                 + " most recent of " + f"{len(evs):,}"
                 + ' consequential changes. The <a class="link" href="/changes.xml">feed</a> '
                   "carries the rest.</p>")
    h.append("</main>")
    return lds, "\n".join(h)


def main():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    evs = rows(con)
    t = tally(con)
    con.close()
    generated = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    lds, body = render(evs, t, generated, published_slugs())

    import gen_hubs                                              # reuse the exact site chrome
    doc = gen_hubs.head(
        "What changed in the MCP ecosystem — dated · tashan",
        meta_description(t),
        BASE + "/changes.html", lds,
        extra='<link rel="alternate" type="application/atom+xml" title="tashan changes" '
              'href="/changes.xml">\n')
    doc += body + chrome.footer_html()
    doc += '<script src="/js/site.js?v=' + str(assets.V) + '" defer></script>\n</body>\n</html>\n'
    open(OUT, "w", encoding="utf-8").write(doc)
    print(f"changes: {min(len(evs), MAX_ROWS):,} of {len(evs):,} consequential events -> web/changes.html")
    return 0


def _sec_withholding_check():
    """rows() and tally() must withhold the SAME events, or the page contradicts its own summary."""
    import sqlite3
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE change_events (cap_id TEXT, at TEXT, kind TEXT, severity TEXT, "
              "what TEXT, why TEXT, action TEXT)")
    c.execute("CREATE TABLE capabilities (id TEXT, name TEXT, tashan_score REAL)")
    c.execute("INSERT INTO capabilities VALUES ('pkg:x','x',70)")
    old, new = "2026-08-11T00:00:00Z", SEC_TRUSTED_FROM + "T00:00:00Z"
    c.executemany("INSERT INTO change_events VALUES (?,?,?,?,?,?,?)", [
        ("pkg:x", old, "install_script_added", "high", "w", "y", "a"),   # first-scan shadow
        ("pkg:x", old, "permissions_widened", "high", "w", "y", "a"),    # same shadow
        ("pkg:x", old, "deprecated", "high", "w", "y", "a"),             # NOT security: keep
        ("pkg:x", new, "install_script_added", "high", "w", "y", "a"),   # trustworthy: keep
    ])
    got = {r[2] for r in rows(c, days=3650)}
    assert got == {"deprecated", "install_script_added"}, got
    t = tally(c, days=3650)
    # One install_script_added survives, and it is the post-cutoff one.
    assert t.get("install_script_added") == 1, t
    assert "permissions_widened" not in t, t
    assert t.get("deprecated") == 1, t
    # THE SUMMARY MUST NOT OUTRUN THE LIST. This is the failure that would put "301" in a sentence
    # above twelve rows, and the sentence is what gets quoted.
    assert sum(t.values()) == len({(r[0], r[1], r[2]) for r in rows(c, days=3650)}), (t, got)


def _selftest():
    _sec_withholding_check()
    t = {"deprecated": 52, "abandoned": 111, "install_script_added": 301, "advisory_new": 5}
    s = sentence(t)
    assert "52 were deprecated" in s and "301 started running a script" in s, s
    assert s.endswith("."), s
    # A count of zero must not appear at all — "0 gained a security advisory" reads as a template.
    s2 = sentence({"deprecated": 3})
    # Check for a zero-COUNT clause, not the digit — "In the last 30 days" contains "0 " and the
    # first version of this assertion failed on its own header.
    assert "3 were deprecated" in s2, s2
    assert not any(c.strip().startswith("0 ") for c in s2.split(": ", 1)[-1].split("; ")), s2
    assert "No consequential changes" in sentence({}), sentence({})
    # The meta description is a search result, and an engine truncates it mid-clause past ~155.
    d = meta_description(t)
    assert len(d) <= 155, f"{len(d)}: {d}"
    assert "52 deprecated" in d, d
    assert len(meta_description({})) <= 155
    # Routine releases are the bulk of the corpus and must never be a headline.
    assert "version_published" not in CONSEQUENTIAL
    assert all(k in HEADLINE for k in CONSEQUENTIAL), \
        [k for k in CONSEQUENTIAL if k not in HEADLINE]
    # Rendering must survive a row with no slug, no score and no why — those are real rows.
    row = ("pkg:x", "2026-08-14T00:00:00+00:00", "deprecated", "high",
           "x was deprecated", None, None, None, None)
    lds, body = render([row], t, "2026-08-16")
    assert "x was deprecated" in body and "<li" in body
    # A capability with no published dossier must render as TEXT, never as a link to a 404 — the
    # first version linked every event and shipped dozens of dead links onto the page whose entire
    # purpose is being crawled.
    linked = render([row], t, "2026-08-16", live={"pkg-x"})[1]
    assert 'href="/capability/pkg-x.html"' in linked, linked[:400]
    unlinked = render([row], t, "2026-08-16", live=set())[1]
    assert "/capability/" not in unlinked, unlinked[:400]
    assert lds[0]["@type"] == "Dataset" and lds[0]["isAccessibleForFree"] is True
    print("gen_changes selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
