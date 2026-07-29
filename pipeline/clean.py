#!/usr/bin/env python3
"""tashan — delete rows that are not capabilities at all.

Scraping public agent configs picks up whatever people put in a `command` field, and some of that is a
local path or a shell fragment rather than a capability: "C:\\Users\\david\\OneDrive - Qolcom\\...",
"/home/blyons/finances/main.ledger", "cd cmd/mcp-server && go run .", "packages/yandex-search-mcp/src/
index.mjs". These are not published software; they are someone's machine leaking into a public config.

They were already excluded from the site by `junk()` at export, but only because they carry no trust
score — one enrichment pass away from appearing on the board. Filtering at the edge while keeping them
in the store also means every count we publish ("N capabilities tracked") is inflated by rows we would
never show. Deleting is the honest fix: the denominator should mean something.

    python3 pipeline/clean.py --dry-run     # report what would go, change nothing
    python3 pipeline/clean.py               # delete, then re-export

Conservative by construction: each rule targets a shape that cannot be a package name, and --dry-run
prints every match so the list can be eyeballed before anything is removed.
"""
import os, re, sys, collections
import build

RULES = [
    ("absolute path",     re.compile(r"^[A-Za-z]:[\\/]|^/(home|Users|etc|opt|var|tmp|mnt)/|^~[/\\]|\\\\")),
    ("repo subpath",      re.compile(r"^(packages|tools|src|apps|cmd|dist|lib|bin|scripts)/")),
    ("shell fragment",    re.compile(r"^(cd|source|export|sudo|bash|sh|zsh|python3?|node|go|uv|uvx|deno)\s"
                                     r"|&&|\|\||^\./|^\.\./|\$\{")),
    ("script/file",       re.compile(r"\.(jar|exe|dll|bat|cmd|ps1|ledger|log|txt)$", re.I)),
    ("bare url",          re.compile(r"^https?://")),
    ("placeholder path",  re.compile(r"/path/to/|your[-_]?(project|path|dir|username|name|org|repo)"
                                     r"|xxxx|<[^>]+>", re.I)),
    # A one-character name is never a published artifact. These were Windows drive letters: a volume
    # mount (`-v C:/Users/me/data:/data`) parsed as the image, leaving `docker:C` and `docker:D` in the
    # store. The parser no longer produces them (see scraper/scrape.py + tests/test_scrape.py); this
    # sweeps the ones already written.
    ("single character",  re.compile(r"^.$")),
]


def offenders(con):
    rows = con.execute("SELECT id, name, npm_pkg, kind FROM capabilities").fetchall()
    hits = []
    for cid, name, pkg, kind in rows:
        subject = name or pkg or ""
        for label, rx in RULES:
            if rx.search(subject):
                hits.append((cid, subject, kind, label))
                break
    return hits


def main():
    dry = "--dry-run" in sys.argv
    con = build.db()
    hits = offenders(con)
    by = collections.Counter(h[3] for h in hits)
    total = con.execute("SELECT COUNT(*) FROM capabilities").fetchone()[0]

    print(f"{len(hits)} of {total} rows are not capabilities ({100*len(hits)/max(1,total):.1f}%)")
    for label, n in by.most_common():
        ex = next(h[1] for h in hits if h[3] == label)
        print(f"  {label:18} {n:4}   e.g. {ex[:64]}")

    # Never silently delete something that reached the public export.
    exported = set()
    try:
        import json
        d = json.load(open(os.path.join(build.ROOT, "web", "data", "capabilities.json")))
        exported = {c["id"] for c in d["capabilities"]}
    except Exception:
        pass
    live = [h for h in hits if h[0] in exported]
    if live:
        print(f"\n  WARNING: {len(live)} of these are currently PUBLISHED — review before deleting:")
        for h in live[:10]:
            print(f"    {h[1][:70]}")

    if dry:
        print("\ndry run — nothing deleted")
        con.close(); return 0

    con.executemany("DELETE FROM capabilities WHERE id=?", [(h[0],) for h in hits])
    # signal_history is the un-backfillable series; drop only the rows for capabilities that no longer exist
    con.executemany("DELETE FROM signal_history WHERE cap_id=?", [(h[0],) for h in hits])
    con.commit()
    left = con.execute("SELECT COUNT(*) FROM capabilities").fetchone()[0]
    print(f"\ndeleted {len(hits)}; {left} capabilities remain")
    build.export(con)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
