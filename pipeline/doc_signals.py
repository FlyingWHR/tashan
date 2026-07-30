#!/usr/bin/env python3
"""Measure whether a capability's documentation is actually ABOUT that capability.

    python3 pipeline/doc_signals.py

Found while grading: 79 of 836 staged capabilities share a README byte-for-byte with at least one
other, and in the worst clusters not one of them is ever named in it. Eleven `nigeria-*` servers
inherit one family README; seven more inherit an org README that never mentions the server. A grader
reading that text sees competent documentation and scores it "solid" — for a capability the document
does not describe.

Two columns, both plain facts:

  doc_shared_with   how many OTHER capabilities ship this exact README (0 = it is its own)
  doc_names_self    whether the text mentions the capability's own name at all

Together they identify a specific, checkable failure: the only documentation this thing has is
someone else's. That is not an accusation of bad faith — a monorepo with one README is a normal way
to ship — but it does mean the capability is undocumented, and the expertise grade must not be
allowed to borrow credit from a document about something else.
"""
import hashlib, json, os, re, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "data", "readmes", "manifest.json")


def leaf(name):
    return str(name or "").split("/")[-1].lower()


def names_self(item):
    """Does the README mention this capability by name? Generous on purpose — any of the obvious
    spellings counts, so a false 'no' means the text really never refers to it."""
    txt = (item.get("readme") or "").lower()
    if not txt:
        return 0
    # The FULL scoped package name first. Leafing "@czagents/dd" down to "dd" and then dropping it for
    # being under three characters made the capability unmatchable — a grader was told its README
    # never named it, while that README carries a "### @czagents/dd (12 tools)" section. A scoped name
    # is distinctive enough to match on directly, so the length guard must not apply to it.
    full = str(item.get("npm_pkg") or "").lower()
    if full and len(full) > 3 and full in txt:
        return 1
    cands = {leaf(item.get("name")), leaf(item.get("npm_pkg")),
             leaf(item.get("id", "").split(":", 1)[-1])}
    for c in list(cands):
        if c:
            cands.add(c.replace("-", " "))
            cands.add(c.replace("-mcp", "").replace("mcp-", ""))
    # The >2 guard stops a two-letter name matching by accident anywhere in the prose. It stays, but
    # a short name is now reachable via the scoped form above rather than being unmatchable outright.
    return 1 if any(c and len(c) > 2 and c in txt for c in cands) else 0


def main():
    if not os.path.exists(MANIFEST):
        print("  no manifest — run pipeline/fetch_readmes.py first")
        return 0
    import build
    con = build.db()
    d = json.load(open(MANIFEST, encoding="utf-8"))
    items = d["items"] if isinstance(d, dict) else d

    by_hash = defaultdict(list)
    for i in items:
        r = (i.get("readme") or "").strip()
        if len(r) > 200:                      # a stub is not evidence of sharing
            by_hash[hashlib.sha256(r.encode()).hexdigest()].append(i)

    shared_rows = orphan_rows = 0
    for group in by_hash.values():
        others = len(group) - 1
        for i in group:
            self_named = names_self(i)
            con.execute("UPDATE capabilities SET doc_shared_with=?, doc_names_self=? WHERE id=?",
                        (others, self_named, i["id"]))
            if others:
                shared_rows += 1
                if not self_named:
                    orphan_rows += 1
    con.commit()
    print(f"  {len(items)} staged · {shared_rows} share a README with another capability · "
          f"{orphan_rows} are never named in the only documentation they have")
    return 0


if __name__ == "__main__":
    sys.exit(main())
