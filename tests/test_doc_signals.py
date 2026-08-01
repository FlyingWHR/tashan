#!/usr/bin/env python3
"""The self-declared-unmaintained detector, which is allowed to cost a capability 70% of its
maintenance score — so a false positive here is us calling a live project dead on its own page.

It exists because wooyun-legacy sat at #1 on the security shelf with vitality "active", upkeep 79 and
a README opening "# 不维护决定 … 我们决定不维护了" (we have decided not to maintain this). Every signal the
scorer could read said healthy: pushed 18 days ago, 1,741 stars, 1 open issue, GitHub's Archive box
unticked. The scorer already discounts maintenance by 0.7 for npm's deprecated flag, the registry's
deprecated status and that Archive box — three PLATFORM flags — and had no way to hear the author say
it in prose. Our own expertise grader had already read the line and filed it as prose in
expertise_note, where nothing could act on it.

The two guards below are what the first run needed, and both are here as cases because both were
real misses on the real corpus:

  position   "the legacy API is no longer supported by upstream vendors" is a sentence about someone
             else's API. Presence anywhere in a README is not a status announcement.
  subject    @artymclabin/gmail-mcp opens "The ORIGINAL repository has been unmaintained since August
             2025" — that is a FORK explaining why it exists. Flagging it inverts the truth.

Run: python3 tests/test_doc_signals.py
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import doc_signals as ds

fail = 0


def ok(name, cond, detail=""):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  — " + detail) if detail and not cond else ""))


HIT = [
    ("a Chinese heading announcing the decision (wooyun-legacy)",
     "# 不维护决定\n随着ai的发展越来越厉害，其实skill没什么太多作用了。我们决定不维护了\n\n# WooYun Legacy\n"),
    ("a plain first-line statement",
     "This project is deprecated in favour of the hosted version.\n"),
    ("a bold callout below the fold (@jetbrains/mcp-proxy)",
     "# Proxy\n" + "x" * 400 + "\n> **This repository is no longer maintained.** Use the IDE.\n"),
]

MISS = [
    ("a project deprecating its own FLAG, not itself",
     "# Tool\n\nWe deprecated the --old flag in v2. Use --new instead.\n"),
    ("prose about a THIRD PARTY's API, below the fold",
     "# Tool\n" + "x" * 400 + "\nNote: the legacy API is no longer supported by upstream vendors.\n"),
    ("a fork explaining its upstream died (@artymclabin/gmail-mcp)",
     "The original repository has been unmaintained since August 2025 - 7+ months.\n"),
    ("a repo that PIVOTED rather than stopped (qmt-skills)",
     "本仓库曾是 xtquant 的 MCP 服务器实现，现已全面转型为 skill 仓库。旧 MCP 代码保留在 legacy-mcp。\n"),
    ("an empty document", ""),
]

for name, txt in HIT:
    ok("flags " + name, ds.declared_dead(txt) is not None)
for name, txt in MISS:
    got = ds.declared_dead(txt)
    ok("ignores " + name, got is None, f"flagged it as {got!r}")

# The quote is the product, not a boolean — the site has to be able to answer "says who?" with the
# author's own sentence, so an empty or markdown-littered capture is a failure even when the row flags.
q = ds.declared_dead(HIT[0][1])
ok("captures the author's own words as evidence", q and "不维护" in q and not q.startswith("#"), repr(q))

# ---- against the real corpus ---------------------------------------------------------------------
# Every hit here is hand-checked. If this count moves, LOOK AT THE NEW ROW before changing the number:
# the whole point of the guards is that a wrong hit is worse than a missed one.
items = ds.staged_items()
if items:
    hits = [(i["id"], ds.declared_dead(i.get("readme"))) for i in items]
    hits = [h for h in hits if h[1]]
    ok(f"reads both README stores ({len(items)} docs, manifest and batches are disjoint)",
       len(items) > 1500, f"only {len(items)} — is staged_items() reading batches/?")
    ok("flags a small, hand-checked set rather than a swathe", len(hits) <= 10,
       f"{len(hits)} flagged: " + ", ".join(h[0] for h in hits[:12]))
    known = {"plugin:tanweai/wooyun-legacy/wooyun-legacy"}
    ok("still catches the case this was built for", known <= {h[0] for h in hits},
       "wooyun-legacy no longer flagged")
else:
    ok("staged READMEs exist to scan", False, "run pipeline/fetch_readmes.py")

print("DOC SIGNALS FAILED" if fail else "ok — doc signals (self-declared unmaintained)")
sys.exit(fail)
