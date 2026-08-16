#!/usr/bin/env python3
"""Every number in docs/OUTREACH.md must still be true of the database.

WHY. That file is the one thing in this repo whose content leaves the building — the drafts are meant
to be pasted into a real email to a real stranger. Its opening claim is that each message leads with
"a fact about the recipient's own users, measured, with the query behind it", and it says in its own
words: *a stale number in an outreach email is the same sin the product exists to point at.*

Within four hours of being written it was already wrong. One security pass moved the scanned corpus
2,282 -> 2,771, the provenance gap 77% -> 75%, install scripts 172 -> 199 and abandoned rows 366 ->
409. Nobody would have noticed until after the email was sent.

This checks the facts table against live SQL. It is deliberately tolerant of ±1 percentage point on
the derived rate (rounding), and exact on counts.

Run: python3 tests/test_outreach_numbers.py
"""
import json, os, re, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "OUTREACH.md")
fail = 0


def ok(name, cond, detail=""):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  — " + detail) if detail and not cond else ""))


if not os.path.exists(DOC):
    print("  -- docs/OUTREACH.md absent, nothing to check")
    sys.exit(0)

con = sqlite3.connect(os.path.join(ROOT, "data", "tashan.db"))
q = lambda s: con.execute(s).fetchone()[0]

# IS THIS DATABASE THE ONE THE NUMBERS CAME FROM? This test predates data/tashan.db leaving git for
# R2. It compares COMMITTED docs — regenerated nightly from the R2 copy — against the LOCAL database,
# which on any machine without R2 credentials is however stale it happens to be. Mine was 32 hours
# behind and every count came out "wrong", blaming the drafts for the difference:
#
#     FAIL scanned for advisories: doc says 8,044, database says 7,862
#
# That is a false failure, it blocks every commit, and worst of all it says "re-run the query and
# update the drafts" — which would make somebody overwrite CORRECT numbers with stale ones.
#
# Compared by DATE, not timestamp: within a nightly run the sources sync before the export is
# written, so last_synced is legitimately a little older than generated_at. A different DAY means a
# different run. A run that straddles midnight skips this check for one night, which costs a
# re-check and never a wrong assertion.
_synced = (q("SELECT MAX(last_synced) FROM sync_state") or "")[:10]
try:
    _exported = json.load(open(os.path.join(ROOT, "web", "data", "capabilities.json"),
                               encoding="utf-8")).get("generated_at", "")[:10]
except Exception:
    _exported = ""
if _synced and _exported and _synced < _exported:
    print(f"  -- SKIPPED: this database was last synced {_synced}, but the committed numbers were "
          f"exported {_exported}.\n     The docs are not stale, the local database is. "
          f"`python3 pipeline/db_store.py pull` to compare against the real thing.")
    sys.exit(0)
scanned = q("SELECT count(*) FROM capabilities WHERE sec_scanned_at IS NOT NULL")
attested = q("SELECT count(*) FROM capabilities WHERE sec_provenance=1")

# label fragment -> (live value, exact?)
WANT = {
    "scanned for advisories": (scanned, True),
    "no build provenance": (round(100 * (scanned - attested) / scanned) if scanned else 0, False),
    "install-time script": (
        q("SELECT count(*) FROM capabilities WHERE sec_install_script IS NOT NULL AND sec_install_script!=''"), True),
    "Confirmed-malicious": (q("SELECT count(*) FROM capabilities WHERE sec_max_severity='MALICIOUS'"), True),
    "maintainer has **stopped**": (
        q("SELECT count(*) FROM capabilities WHERE tashan_score IS NOT NULL AND vitality='abandoned'"), True),
    "can't be launched": (q("SELECT count(*) FROM capabilities WHERE npm_runnable=0"), True),
}

src = open(DOC, encoding="utf-8").read()
rows = re.findall(r"^\|\s*([^|]+?)\s*\|\s*\*{0,2}([\d,]+)%?\*{0,2}[^|]*\|", src, re.M)
ok(f"the facts table parses ({len(rows)} rows)", len(rows) >= len(WANT),
   "the table shape changed — fix this test, do not delete it")

print()
for frag, (live, exact) in WANT.items():
    got = next((int(v.replace(",", "")) for lab, v in rows if frag in lab), None)
    if got is None:
        ok(f"the table still states {frag!r}", False, "row missing")
        continue
    good = got == live if exact else abs(got - live) <= 1
    ok(f"{frag}: doc says {got:,}, database says {live:,}", good,
       "re-run the query in the table and update the drafts that quote it")

print()
# The drafts repeat the headline figure in prose; a table that agrees with the DB while the email
# body quotes last week's number is the same defect one layer down.
pct = round(100 * (scanned - attested) / scanned) if scanned else 0
stale = sorted({int(m) for m in re.findall(r"(?:~|about )(\d\d)% (?:ship with no|of scanned|don't)", src)}
               | {int(m) for m in re.findall(r"and (\d\d)% have no build provenance", src)})
ok(f"every prose mention of the provenance gap says {pct}%",
   all(abs(v - pct) <= 1 for v in stale), f"found {stale} in the drafts")

print()
print("OUTREACH NUMBERS OK" if not fail else "OUTREACH NUMBERS STALE")
sys.exit(fail)
