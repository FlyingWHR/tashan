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
import glob, hashlib, json, os, re, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "data", "readmes", "manifest.json")
BATCHES = os.path.join(ROOT, "data", "readmes", "batches", "*.json")


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


# A maintainer announcing the project is over. Deliberately narrow: it must be a STATEMENT ABOUT THIS
# PROJECT, not the word "deprecated" appearing anywhere — READMEs discuss deprecated APIs, migration
# notes and changelog entries constantly, and every one of those would be a false abandonment.
DECLARED_DEAD = re.compile(
    r"(no longer (being )?(actively )?(maintain|support|develop)\w*"
    r"|not (being )?(actively )?maintained"
    r"|un-?maintained"
    r"|is (now )?(deprecated|archived|discontinued|abandoned|end[- ]of[- ]life)"
    r"|this (project|repo\w*|package|plugin|skill|server) is (deprecated|archived|no longer)"
    r"|(project|repo\w*) (has been |is )?archived"
    # CJK and JP: the corpus is not English-only, and the case that exposed this gap was Chinese
    r"|不再维护|不维护|停止维护|已归档|已废弃|已停止维护"
    r"|メンテナンスされ(てい)?ません|開発を終了)", re.I)

HEAD = 1500      # a status banner lives at the top of the file; a match 40 KB down is changelog noise

# A DESCRIPTION IS NOT PROSE. The README rule above is careful because a README discusses deprecated
# flags, migrated APIs and changelog entries constantly, so it demands a full sentence ("this project
# is deprecated") sitting in a banner position. A capability's one-line description is the opposite:
# it is the summary its author wrote to say what this IS, right now. A status token at the front of
# it is an announcement, and it needs neither the position test nor the 1,500-char window.
#
# This is the gap that let pkg:docfork rank. Its own description reads "Up-to-date docs for AI.
# DEPRECATED: Use io.github.docfork/docfork instead." and our own grader wrote "shut down 2026-06-14,
# endpoints offline, keys dead, setup fails" — and the page still showed Health: active, a score of
# 55, rank 19 in its category and a working install command. The README rule never fired because a
# bare "DEPRECATED:" is not the sentence "this project is deprecated", and because docfork's README
# was never staged. We had the evidence in our own two fields and shipped the opposite.
_DEAD_WORD = (r"deprecated|discontinued|archived|unmaintained|obsolete|sunset|retired"
              r"|no longer maintained|end[- ]of[- ]life|eol")
# Leading the description: "[DEPRECATED] Go-based terminal UI…", "DEPRECATED — use X instead."
DESC_DEAD = re.compile(r"^\W{0,4}(" + _DEAD_WORD + r")\b[\s:.,\u2014\-\]\)]", re.I)
# Or announced after a sentence break: docfork's reads "Up-to-date docs for AI. DEPRECATED: Use
# io.github.docfork/docfork instead." — the notice is the SECOND sentence, so an anchored rule misses
# it. Announcement punctuation is required (a colon or dash) so that ordinary prose about deprecated
# fields — "Supports X. Deprecated columns are ignored." — does not read as an obituary.
DESC_DEAD_MID = re.compile(r"(?:[.!?)\]]\s+|\n|\|\s*)\W{0,3}(" + _DEAD_WORD + r")\s*[:\u2013\u2014-]", re.I)


def declared_dead_desc(text):
    """The author's own status token in their one-line description, or None."""
    d = re.sub(r"\s+", " ", (text or "")).strip()
    if not d:
        return None
    if not (DESC_DEAD.match(d) or DESC_DEAD_MID.search(d) or DECLARED_DEAD.search(d)):
        return None
    if NOT_US.search(d):          # "superseded the legacy fork" is about somebody else
        return None
    return d[:200]


BANNER = re.compile(r"^\s*(#{1,4}\s|>\s|\*\*|__|!\[|\[!|[-*]\s*\*\*)")   # heading, quote, bold, badge

# "…is unmaintained" is only OUR problem when the subject is US. Both false positives in the first
# run were this: @artymclabin/gmail-mcp is a fork whose README opens "The ORIGINAL repository has been
# unmaintained since August 2025" — the sentence is the reason this package EXISTS, and reading it as
# self-abandonment would penalise the maintained fork for the dead upstream. qmt-skills says 本仓库曾是
# xtquant 的 MCP 服务器实现 ("this repo USED TO BE an MCP server, old code kept in legacy-mcp") — a
# pivot notice, not an obituary. A distancing subject anywhere on the line disqualifies the match.
# NB "deprecated in favour of X" does NOT belong here — deprecating yourself in favour of a successor
# is the most explicit self-declaration there is, not a statement about someone else.
NOT_US = re.compile(r"\b(original|legacy|previous|former|old|upstream|"
                    r"predecessor|forked from|superseded)\b|旧|原仓库|原项目|曾是|前身", re.I)


def declared_dead(text):
    """The author's own sentence saying they stopped, or None.

    Two guards, because a match here costs the capability 70% of its maintenance score and a false
    positive is us calling a live project dead.

    POSITION, not just presence. Scanning a whole README marks every project that ever deprecated one
    of its own flags as abandoned. Even the head of the file is not enough on its own: "the legacy API
    is no longer supported by upstream vendors" is a sentence about somebody else's API, and it read as
    an abandonment notice. So the statement must sit where a project announces its own status — a
    heading, a blockquote, a bold callout, a badge — or in the first 300 characters, above the fold.
    A claim buried in ordinary prose is about something, and we cannot tell what."""
    head = (text or "")[:HEAD]
    m = DECLARED_DEAD.search(head)
    if not m:
        return None
    pos = m.start()
    line_start = head.rfind("\n", 0, pos) + 1
    line = head[line_start:head.find("\n", pos) if head.find("\n", pos) > 0 else len(head)]
    if pos > 300 and not BANNER.match(line):
        return None
    if NOT_US.search(line):
        return None
    # ponytail: line-level subject test, 5/5 on the corpus that exists. It cannot parse "X is dead but
    # this fork is fine" split across two sentences — if the corpus grows a case like that, the upgrade
    # is to test the sentence containing the match rather than the whole line.
    return re.sub(r"^[#>*\-\s]+", "", line).strip()[:200] or m.group(0)


def staged_items():
    """Every capability whose documentation we have on disk.

    manifest.json and batches/ are DISJOINT — 812 and 836 rows, zero overlap — so reading only the
    manifest, as this stage did, measured half the corpus it already had. The batches are what the
    expertise graders were fed; the manifest is what fetch_readmes.py last wrote."""
    seen, out = set(), []
    paths = ([MANIFEST] if os.path.exists(MANIFEST) else []) + sorted(glob.glob(BATCHES))
    for p in paths:
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        for i in (d["items"] if isinstance(d, dict) and "items" in d else d):
            if isinstance(i, dict) and i.get("id") and i["id"] not in seen:
                seen.add(i["id"])
                out.append(i)
    return out


def main():
    items = staged_items()
    if not items:
        print("  no staged READMEs — run pipeline/fetch_readmes.py first")
        return 0
    import build
    con = build.db()

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

    # Does the document say the project is over? Cleared as well as set, so retracting the banner (or
    # tightening the pattern) un-flags the row on the next run instead of leaving a permanent mark.
    dead = 0
    staged = set()
    for i in items:
        quote = declared_dead(i.get("readme"))
        con.execute("UPDATE capabilities SET self_unmaintained=? WHERE id=?", (quote, i["id"]))
        if quote:
            staged.add(i["id"])     # answered by the README; the description pass must not clear it
            dead += 1
    # SECOND PASS, over the whole corpus. The README pass can only see the capabilities whose README
    # was staged; the description is a field we hold for every row. Written for rows the README pass
    # did not already answer, and written unconditionally (None included) so retracting a notice
    # un-flags the row on the next run rather than leaving a permanent mark.
    from_desc = 0
    for cid, desc in con.execute(
            "SELECT id, description FROM capabilities WHERE description IS NOT NULL").fetchall():
        if cid in staged:
            continue        # a README notice already answered this row, and it is the richer quote
        quote = declared_dead_desc(desc)
        con.execute("UPDATE capabilities SET self_unmaintained=? WHERE id=?", (quote, cid))
        if quote:
            from_desc += 1
    dead += from_desc
    con.commit()
    print(f"  {len(items)} staged · {shared_rows} share a README with another capability · "
          f"{orphan_rows} are never named in the only documentation they have · "
          f"{dead} declare themselves unmaintained ({from_desc} from the description alone)")
    return 0


def _selfcheck():
    """A notice must be an announcement, never a mention. Both directions cost something: a miss
    ranks a dead server (docfork scored 55 with a live install command), a false positive calls a
    working project dead and takes 70% of its maintenance score."""
    dead = [
        "Up-to-date docs for AI. DEPRECATED: Use io.github.docfork/docfork instead.",  # mid-sentence
        "[DEPRECATED] Go-based terminal UI for managing agents",                       # bracketed
        "DEPRECATED — use com.traderwai/traderwai instead.",                           # em-dash
        "DISCONTINUED 2026-05-23. Anti-bot retooling required.",
        "(deprecated) use the hosted service",
    ]
    alive = [
        "Query Postgres. Supports X. Deprecated columns are ignored.",   # a mention, not a notice
        "Migrate off the deprecated v1 endpoint automatically",
        "A wrapper around the legacy API, no longer supported by upstream vendors",  # somebody else
        "Fast search for docs",
    ]
    for t in dead:
        assert declared_dead_desc(t), "missed a notice: " + t
    for t in alive:
        assert not declared_dead_desc(t), "called a live project dead: " + t


if __name__ == "__main__":
    _selfcheck()
    sys.exit(main())
