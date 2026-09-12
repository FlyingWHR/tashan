#!/usr/bin/env python3
"""Retired names must not survive in user-visible copy, and sorts must read fields that exist.

pipeline/build.py has a RENAMES table: `trust` -> `tashan_score`, `maintenance` -> `upkeep`. Both
renames were applied to the SCHEMA and to nothing else. Months later:

  - Nine pages still said "maintenance" while three said "upkeep", in the same sentence position.
  - The Index's board description still opened "Trust is a transparent composite…" — the single
    line most visitors read, naming the score by a name we had retired twice over.
  - The sort menu offered "Upkeep", and its comparator read `b.maintenance`, a column that no
    longer exists in the export. num(undefined) - num(undefined) is 0 for every pair, so choosing
    it silently did nothing at all.

That last one is why this test checks behaviour and not only spelling: a rename that misses the
prose looks sloppy, and a rename that misses a field reference ships a dead feature.

Run: python3 tests/test_terminology.py
"""
import json, os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Retired name -> what it is called now. Matched only in text a visitor can read.
RETIRED = {
    r"\bTrust\b(?!ed|worthy)": "tashan score",
    r"\bmaintenance\b": "upkeep",
    r"\bVitality\b": "Health",
    # THE EXPERTISE SCALE LOST TWO BANDS AND THE COPY KEPT BOTH. `wrapper` and `slop` were removed
    # because neither was a measurement — "a thin wrapper" is a KIND of artifact rather than a lower
    # grade, and "likely AI-slop" is a claim that reading a README cannot establish. The scale has
    # been deep/solid/thin ever since, and the homepage still told every reader we grade for
    # "a thin wrapper or AI-slop", the homepage FAQ's JSON-LD still published a five-band scale to
    # every answer engine, and about.html still described the read as "deep work vs. thin wrapper
    # vs. slop". A retracted claim is worse than a stale word: it is a judgment about somebody
    # else's work that we said we could not support.
    #
    # Deliberately narrow. A capability may legitimately be DESCRIBED as a thin wrapper by its own
    # author — shim_note quotes exactly that — so only the band-list forms are caught.
    r"\bAI[-\s]?slop\b": "the three bands the rubric actually has: deep, solid, thin",
    r"thin\s*/\s*wrapper|wrapper\s*/\s*slop|wrapper vs\.? slop|vs\.? slop\b":
        "the three bands the rubric actually has: deep, solid, thin",
    # The capital-T rule missed every lowercase use, and those are the ones that shipped: the ticker
    # in terminal.js said "LIVE ▸ ranked by trust" on EVERY page, llms.txt headed its list "Top
    # capabilities by measured trust", and the task hubs' ItemList JSON-LD said "ranked by trust" on
    # 53 pages. methodology.html devotes a callout to why this number is NOT called a trust score
    # ("we do not audit it… calling that 'trust' claimed something the arithmetic does not support"),
    # so the one word the page walks back was still the word the rest of the site used. Matched as a
    # phrase, not as a bare lowercase word, so ordinary English ("a rater you can trust") is fine.
    r"\btrust score\b": "tashan score",
    r"\b(?:ranked|sorted|ordered) by trust\b": "ranked by the tashan score",
    r"\bmeasured trust\b": "the tashan score",
    r"\btrust[-\s]ranked\b": "tashan-score-ranked",
}

# Places where the old word is legitimate English about something else, not our score component.
EXEMPT = [
    re.compile(r"no further maintenance is expected"),      # a plain fact about an archived repo
    re.compile(r"maintenance/adoption read"),               # historical, inside code comments only
    # methodology.html's callout NAMES the retired term in order to disown it ("Why it is called the
    # tashan score, not a trust score"). That paragraph is the reason the rule exists; it must be
    # allowed to say the word once, in the one place that explains it.
    re.compile(r"not a trust score"),
]


def visible_text(html):
    # A QUOTED NAME IS NOT OUR COPY. This rule exists to catch OUR retired vocabulary, and the
    # docstring above already says the ~12,000 generated pages are excluded because a capability
    # really is called "remote-system-maintenance". Two hand-written pages now embed generated rows
    # — index.html bakes the top of the board, /paid.html ranks by settled receipts — and one of
    # those rows is a third-party server literally named "X402 Trust". Flagging a publisher's own
    # product name teaches you to skip the guard, which is the failure this file is about. The
    # capability-name cell is dropped; every word we wrote around it is still scanned.
    html = re.sub(r'<a class="cap__link"[^>]*>.*?</a>', " ", html, flags=re.S)
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def js_strings(src):
    """String literals a visitor could end up reading.

    Code comments carry the history and must keep the old names — that is where the reasoning for a
    rename lives. Three more things in the Python sources are not prose either, and flagging them is
    how a guard trains you to ignore it: the RENAMES table, whose whole job is to hold the retired
    name next to the new one; SQL DDL, where the column really is called what it is called; and
    print() output, which is a developer looking at a terminal, not a visitor reading a page.
    """
    src = re.sub(r"^\s*//.*$", "", src, flags=re.M)
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"^\s*#.*$", "", src, flags=re.M)
    src = re.sub(r"^RENAMES\s*=.*$", "", src, flags=re.M)
    src = re.sub(r"print\(.*?\)", "", src, flags=re.S)
    src = re.sub(r"(?is)\b(CREATE|ALTER|SELECT|INSERT|UPDATE)\b[^\"\']*", " ", src)
    return " ".join(m.group(2) for m in re.finditer(r"(['\"])((?:\\.|(?!\1).)*)\1", src))


def main():
    fail = []

    # Only sources we author. The ~5,800 generated pages embed third-party names and descriptions —
    # a capability really is called "remote-system-maintenance", and another really does describe
    # itself as a "Trust layer for agent payments". Flagging those is noise that teaches you to skip
    # the guard. Every template that produces a generated page IS scanned, which is what caught
    # prerender.py printing "Vitality:" onto all 5,788 capability pages.
    targets = [(f, visible_text) for f in glob.glob(os.path.join(ROOT, "web", "*.html"))]
    targets += [(f, js_strings) for f in glob.glob(os.path.join(ROOT, "web", "js", "*.js"))]
    targets += [(f, js_strings) for f in glob.glob(os.path.join(ROOT, "pipeline", "*.py"))]

    for path, extract in targets:
        text = extract(open(path, encoding="utf-8").read())
        for e in EXEMPT:
            text = e.sub(" ", text)
        for pat, now in RETIRED.items():
            for m in re.finditer(pat, text):
                ctx = re.sub(r"\s+", " ", text[max(0, m.start() - 45):m.end() + 45]).strip()
                fail.append(f"{os.path.relpath(path, ROOT)}  \u201c\u2026{ctx}\u2026\u201d  -> say {now!r}")

    # ---- headings must not gloss themselves ------------------------------------------------------
    # "Tags — what you're doing" over a list of tags, "Categories — what it touches" over categories:
    # the gloss restates the noun and costs a line in the most-scanned part of the page. Contrast that
    # earns its place ("Request a grade, not a placement") is a clause, not an em-dash appendix.
    HEAD = re.compile(r"<(h[1-3])[^>]*>([^<]{3,70})</\1>")
    LABEL = re.compile(r'class="(?:catrail__h|trole__h|kicker|plan__name|job__k)[^"]*"[^>]*>([^<]{3,70})<')
    for path in glob.glob(os.path.join(ROOT, "web", "*.html")) + \
            [os.path.join(ROOT, "pipeline", "gen_hubs.py")]:
        src = open(path, encoding="utf-8").read()
        for rx, grp in ((HEAD, 2), (LABEL, 1)):
            for m in rx.finditer(src):
                txt = m.group(grp).strip()
                if " — " in txt or " – " in txt:
                    fail.append(f"{os.path.relpath(path, ROOT)}  heading glosses itself: {txt!r} "
                                f"— cut the gloss or make it a clause")

    # ---- behaviour: every sort comparator must read a field the export actually has -------------
    idx = os.path.join(ROOT, "web", "data", "index.json")
    if os.path.exists(idx):
        rows = json.load(open(idx, encoding="utf-8"))
        rows = rows["capabilities"] if isinstance(rows, dict) else rows
        fields = set().union(*(set(r) for r in rows[:400])) if rows else set()
        src = open(os.path.join(ROOT, "web", "js", "index.js"), encoding="utf-8").read()
        for m in re.finditer(r'case "(\w+)": return num\(b\.(\w+)\)', src):
            key, field = m.group(1), m.group(2)
            if field not in fields:
                fail.append(f"web/js/index.js  sort {key!r} reads b.{field}, which is not in the "
                            f"export — the option is in the menu and does nothing")

    if fail:
        print(f"  FAIL  {len(fail)} terminology/behaviour problem(s):")
        for f in fail[:20]:
            print("        " + f)
        if len(fail) > 20:
            print(f"        … and {len(fail) - 20} more")
        return 1
    print("  ok    no retired name in user-visible copy; every sort reads a live field")
    return 0


if __name__ == "__main__":
    sys.exit(main())
