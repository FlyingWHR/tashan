#!/usr/bin/env python3
"""Head-to-head comparison pages — /compare/<a>-vs-<b>.html

WHY THESE EXIST. "X vs Y" is the highest-intent question in this category and the one we are best
placed to answer, because both sides are already measured on the same public evidence by the same
scorer on the same day. Everyone else answering it is guessing or is paid by one of the two.

WHAT THEY CONTAIN. Both scores, the raw evidence each was derived from, freshness, upkeep, the
expertise grade, and a one-line roll-up of what the security audit found. The audit is now FREE IN
FULL — advisory id, severity, the version that fixes it and the literal install-time command all
ship to everyone — so the roll-up here is a summary written for a two-column table, never a
redaction. This paragraph used to read "free-tier data only … never a way around its paywall": that
was written when the audit was paid, and this file was the one place missed when it went free
(build.py::redact_paid stopped redacting, prerender.py::security_block went inline, pricing.html
stopped selling it), so 218 generated pages kept advertising a licence that no longer buys anything.

THE URL IS ALPHABETICAL AND THE CONTENT IS RANKED, deliberately and not by accident. If the slug
were ordered by score, every page would change URL the day two capabilities crossed — churning the
one asset that takes months to earn. Alphabetical is stable for the life of the pair; the ranking
lives in the body where it can move freely.

THE GATE. Same category (comparing a PDF reader to a Kubernetes client answers nobody's question),
both scored, both with real adoption. Without a floor this is 5,788² pages of doorway spam, which is
how a site earns a manual action rather than traffic.

    python3 pipeline/gen_compare.py
"""
import glob, html, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chrome
import gen_hubs as H

BASE = H.BASE
OUT = os.path.join(ROOT, "web", "compare")

TOP_PER_CAT = 8        # 8 -> 28 pairs per category; 12 -> 66. Past this the tail is not a real question.
MIN_DOWNLOADS = 1000   # a comparison nobody is choosing between is a page nobody searches for


def esc(s):
    return html.escape(str(s), quote=True)


def freshness(c):
    txt, _cls, _t = H.vitality_cell(c)
    return txt


def verdict(c):
    return c.get("expertise_verdict") or "not graded"


def findings(c):
    """Every finding this capability has, named but not expanded — one line, for a table cell.

    NOT a paywall line, though it was written as one. This used to be the free half of a free/paid
    split ("the existence is free, the detail is licensed"); the audit is free in full now, id and
    fix and install-time command included, so the only reason this stays a summary is that a
    head-to-head table has two narrow columns. The unabridged version is on each dossier, also free.
    """
    bits = []
    n = c.get("sec_advisory_count") or 0
    bits.append(f"{n} known advisor" + ("y" if n == 1 else "ies") if n else "no known advisories")
    if c.get("sec_install_script"):
        bits.append("runs an install script")
    if not c.get("sec_provenance"):
        bits.append("no build provenance")
    return ", ".join(bits)


def row(label, a, b, note=""):
    return ('<tr><th scope="row">' + esc(label) + "</th><td>" + a + "</td><td>" + b + "</td>"
            + '<td class="cmp__n">' + esc(note) + "</td></tr>")


def page(a, b, cat_label, gen):
    """`a` and `b` are ALPHABETICAL by slug — the URL order. Ranking happens inside."""
    na, nb = H.disp(a), H.disp(b)
    slug = a["slug"] + "-vs-" + b["slug"]
    url = BASE + "/compare/" + slug + ".html"
    hi, lo = (a, b) if (a.get("tashan_score") or 0) >= (b.get("tashan_score") or 0) else (b, a)
    gap = abs((a.get("tashan_score") or 0) - (b.get("tashan_score") or 0))

    title = na + " vs " + nb + " — measured side by side · tashan"
    desc = (na + " and " + nb + " compared on public evidence: tashan score, adoption, freshness, "
            "upkeep and what each one's security audit found. Both measured the same day by the "
            "same scorer.")

    # The verdict is DERIVED, never editorial. A 2-point gap is not a recommendation, and saying so
    # is the whole reason anyone would trust the pages where the gap IS decisive.
    if gap >= 10:
        lead = ("<b>" + esc(H.disp(hi)) + "</b> scores " + str(int(gap)) + " points higher on the "
                "same evidence, which is a real separation rather than noise.")
    elif gap >= 3:
        lead = ("<b>" + esc(H.disp(hi)) + "</b> scores " + str(int(gap)) + " points higher — a "
                "narrow lead. Read the evidence rows below before treating it as decisive.")
    else:
        lead = ("These two are level on the tashan score (within " + str(int(gap)) + " points), so "
                "the score does not decide it. The evidence rows below are where they differ.")

    lds = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "The Index", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": cat_label,
             "item": BASE + "/category/" + a["category"] + ".html"},
            {"@type": "ListItem", "position": 3, "name": na + " vs " + nb, "item": url}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": "Is " + na + " or " + nb + " better?",
             "acceptedAnswer": {"@type": "Answer", "text":
                (H.disp(hi) + " scores " + str(a.get("tashan_score") if hi is a else b.get("tashan_score"))
                 + " and " + H.disp(lo) + " scores "
                 + str(b.get("tashan_score") if hi is a else a.get("tashan_score"))
                 + " on the tashan score, which measures upkeep and freshness gated by real adoption. "
                   "Neither number is a security audit and neither can be bought. "
                 + ("The gap is wide enough to be decisive." if gap >= 10 else
                    "The gap is narrow, so compare the evidence rather than the headline."))}},
            {"@type": "Question", "name": "Are " + na + " and " + nb + " safe to install?",
             "acceptedAnswer": {"@type": "Answer", "text":
                (na + ": " + findings(a) + ". " + nb + ": " + findings(b) + ". Every capability tashan "
                 "measures is checked against the OSV advisory database at the version you would "
                 "install today, for install-time scripts and for build provenance. The audit reads "
                 "public evidence and never executes anything.")}},
            {"@type": "Question", "name": "How were these two compared?",
             "acceptedAnswer": {"@type": "Answer", "text":
                ("Both were measured on the same day by the same scorer, from public signal only — npm "
                 "download volume and publish cadence, repository activity, maintainer count and "
                 "registry status. Nobody can pay to change a score, a rank or a listing.")}}]},
    ]

    def cell(c, v):
        return '<span class="cmp__v">' + v + "</span>"

    def score_cell(c):
        t = c.get("tashan_score")
        return ('<span class="cmp__score">' + (str(int(round(t))) if t is not None else "—") + "</span>"
                '<span class="bar" data-w="' + str(int(round(t or 0))) + '"><i></i></span>')

    rows = "".join([
        row("tashan score", score_cell(a), score_cell(b), "upkeep + freshness, gated by adoption"),
        row("Adoption evidence", cell(a, esc(H.evidence(a) or "—")), cell(b, esc(H.evidence(b) or "—")),
            "the raw public signal the score came from"),
        row("Last release", cell(a, esc(freshness(a))), cell(b, esc(freshness(b))), "npm publish or repo push"),
        row("Upkeep", cell(a, esc(str(int(a["upkeep"])) if a.get("upkeep") is not None else "—")),
            cell(b, esc(str(int(b["upkeep"])) if b.get("upkeep") is not None else "—")),
            "cadence, maintainers, status"),
        row("Expertise grade", cell(a, esc(verdict(a))), cell(b, esc(verdict(b))),
            "an LLM read of its own documentation against a fixed rubric"),
        # This note sold a licence on all 218 pages after the audit went free — the last survivor of
        # the free/paid split. It now says why the row is short (table width) instead of implying a
        # tier gate, because the detail it points at costs nothing.
        row("Security audit", cell(a, esc(findings(a))), cell(b, esc(findings(b))),
            "a summary — the full audit, free, is on each dossier"),
        # "Licence" here is the OSS licence off GitHub (MIT, Apache-2.0, …), NOT a tashan tier.
        # Left alone deliberately: a sweep for paywall wording will hit this word, and it is the
        # one legitimate use of it in the file.
        row("Licence", cell(a, esc(a.get("gh_license") or "—")), cell(b, esc(b.get("gh_license") or "—")), ""),
        row("Maintainers", cell(a, "one primary" if a.get("single_maintainer") else "more than one"),
            cell(b, "one primary" if b.get("single_maintainer") else "more than one"), "bus-factor risk"),
    ])

    def install(c):
        if not c.get("npm_pkg"):
            return ""
        return ('<div class="cmp__inst"><p class="cmp__insth mono">' + esc(H.disp(c)) + "</p>"
                '<pre class="install__snip"><code>claude mcp add ' + esc(chrome.alias(c["name"]))
                + " -- npx -y " + esc(c["npm_pkg"]) + "</code></pre></div>")

    body = ('<main class="wrap" id="main"><article class="prose prose--wide">\n'
        '<p class="kicker"><a class="link" href="/">The Index</a> · '
        '<a class="link" href="/category/' + esc(a["category"]) + '.html">' + esc(cat_label) + "</a></p>\n"
        "<h1>" + esc(na) + " vs " + esc(nb) + "</h1>\n"
        '<p class="lede">' + lead + " Both are measured the same way, on the same day, from public "
        "evidence only — so this is a comparison of two measurements rather than two marketing pages. "
        '<a class="link" href="/methodology.html">How we measure &rsaquo;</a></p>\n'
        '<div class="cmp"><table class="cmp__t"><thead><tr><th scope="col"></th>'
        '<th scope="col"><a class="link" href="/capability/' + esc(a["slug"]) + '.html">' + esc(na) + "</a></th>"
        '<th scope="col"><a class="link" href="/capability/' + esc(b["slug"]) + '.html">' + esc(nb) + "</a></th>"
        '<th class="cmp__n" scope="col">what it means</th></tr></thead><tbody>' + rows + "</tbody></table></div>\n"
        '<h2>Install either</h2>\n<div class="cmp__insts">' + install(a) + install(b) + "</div>\n"
        # The closing note used to read "including what a licence adds" — a pitch for a tier that no
        # longer exists. What the dossier actually adds over this table is depth, not access: the
        # advisory ids, the fixed versions, the install-time command. All of it free.
        '<p class="note">Neither score is a security verdict — "well maintained" and "nothing known '
        "is wrong\" are different claims, which is why the audit is a separate row and never folded "
        "into the number. The full audit for each — the advisory ids, the version that fixes them "
        "and anything that runs at install time — is free on its own page: "
        '<a class="link" href="/capability/' + esc(a["slug"]) + '.html">' + esc(na) + "</a> · "
        '<a class="link" href="/capability/' + esc(b["slug"]) + '.html">' + esc(nb) + "</a>.</p>\n"
        '<p class="mt-12"><a class="btn btn--ghost" href="/category/' + esc(a["category"]) +
        '.html">All ranked ' + esc(cat_label) + " &rsaquo;</a></p>\n"
        # THE HIGHEST-INTENT PAGE ON THE SITE AND IT MADE NO CASE AT ALL. "X vs Y" is what somebody
        # types immediately before choosing, and all 413 of these pages ended at a category link.
        # The pitch is the honest one and it is specific to this page: a comparison is a snapshot,
        # and the thing it cannot do is tell you when the answer stops being true. Both scores stay
        # free, both audits stay free — what a licence buys is the watch on whichever one you pick.
        '<p class="note chg__pro">Both numbers above are today&rsquo;s. Whichever you choose, the '
        'question that matters next is when it changes &mdash; a new advisory, an install script '
        'that appeared, a maintainer walking away. '
        '<a class="link" href="/pricing.html">tashan Pro</a> adds the history to '
        '<code>tashan doctor</code>, so a run over your own config says which of yours moved '
        '&mdash; and what to move to.</p>\n'
        "</article></main>\n")

    return H.head(title, desc, url, lds) + body + H.FOOT + \
        '<script src="/js/terminal.js?v=' + H.AV + '" defer></script>\n' \
        '<script src="/js/site.js?v=' + H.AV + '" defer></script>\n</body>\n</html>\n'


def main():
    d = json.load(open(H.DATA))
    gen = d.get("generated_at", "")
    caps = d["capabilities"]
    for c in caps:
        c.setdefault("slug", H.slugify(c["id"]))

    by_cat = {}
    for c in caps:
        if (c.get("tashan_score") is not None and c.get("category")
                and (c.get("npm_downloads") or 0) >= MIN_DOWNLOADS):
            by_cat.setdefault(c["category"], []).append(c)

    os.makedirs(OUT, exist_ok=True)
    pairs, keep, manifest = 0, set(), {}
    for cat, rows in sorted(by_cat.items()):
        rows.sort(key=lambda x: -(x["tashan_score"] or 0))
        head = rows[:TOP_PER_CAT]
        label = H.CAT_LABEL.get(cat, cat)
        for i in range(len(head)):
            for j in range(i + 1, len(head)):
                # alphabetical by slug -> a stable URL that survives the two crossing on score
                a, b = sorted((head[i], head[j]), key=lambda x: x["slug"])
                slug = a["slug"] + "-vs-" + b["slug"]
                keep.add(slug + ".html")
                open(os.path.join(OUT, slug + ".html"), "w").write(page(a, b, label, gen))
                manifest.setdefault(cat, []).append(
                    {"slug": slug, "a": H.disp(a), "b": H.disp(b)})
                pairs += 1

    json.dump({"generated_at": gen, "by_category": manifest},
              open(os.path.join(ROOT, "web", "data", "compare.json"), "w"), ensure_ascii=False)
    stale = [f for f in os.listdir(OUT) if f.endswith(".html") and f not in keep]
    for f in stale:
        os.remove(os.path.join(OUT, f))   # a pair can fall out of the head; leave no orphan behind
    print("compare pages: %d written across %d categories (top %d each, >=%s weekly downloads)%s"
          % (pairs, len(by_cat), TOP_PER_CAT, f"{MIN_DOWNLOADS:,}",
             f", {len(stale)} stale removed" if stale else ""))


if __name__ == "__main__":
    main()
