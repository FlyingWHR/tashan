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
}

# Places where the old word is legitimate English about something else, not our score component.
EXEMPT = [
    re.compile(r"no further maintenance is expected"),      # a plain fact about an archived repo
    re.compile(r"maintenance/adoption read"),               # historical, inside code comments only
]


def visible_text(html):
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
