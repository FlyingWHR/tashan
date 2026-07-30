#!/usr/bin/env python3
"""Fetch READMEs for expertise grading. Writes data/readmes/manifest.json =
[{id,name,repo,npm_pkg,description,readme(truncated)}].

TWO SAMPLING MODES, because grading serves two different jobs:

  default (top-N)   CURATION — make the most-visible rows on the board good.
  --stratified      VALIDATION — is the score right at all?

The default silently made validation impossible. Grading only ever ran top-N by score, so all 24
graded rows landed at or above the 96th percentile, and comparing verdicts against scores produced
deep+solid mean 84.6 vs thin+wrapper+slop mean 85.9 — the "bad" ones scoring HIGHER. That is not the
score failing, it is a sample with no variance in it: you cannot measure whether a score separates
good from bad using only rows the score already called good. --stratified draws an equal number from
each score band so the correlation means something.

    python3 pipeline/fetch_readmes.py --stratified          # PER_BAND=30 across 5 bands
    PER_BAND=50 python3 pipeline/fetch_readmes.py --stratified
"""
import json, os, sqlite3, sys, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "tashan.db")
OUT = os.path.join(ROOT, "data", "readmes")
os.makedirs(OUT, exist_ok=True)
TOP_N = int(os.environ.get("TOP_N", "24"))
MAXLEN = 4000

def raw(repo, path):
    for ref in ("HEAD", "main", "master"):
        url = f"https://raw.githubusercontent.com/{repo}/{ref}/{path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "tashan"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception:
            continue
    return None

con = sqlite3.connect(DB)
SEL = "SELECT id,name,source_repo,npm_pkg,description FROM capabilities"
# Already-graded rows were not excluded, so a bigger TOP_N re-fetched and re-staged the same top
# capabilities every run — the queue looked full while coverage stayed at 2.6%.
WHERE = (" WHERE tashan_score IS NOT NULL AND source_repo IS NOT NULL"
         " AND expertise_verdict IS NULL")
if "--stratified" in sys.argv:
    # Equal draw per band. Skills are excluded: every skill in a monorepo carries the SAME repo
    # signal, so they cluster on one score and would swamp whichever band they land in.
    BANDS = [(80, 101), (60, 80), (45, 60), (30, 45), (0, 30)]
    per = int(os.environ.get("PER_BAND", "30"))
    rows, seen = [], set()
    for lo, hi in BANDS:
        band = con.execute(SEL + WHERE + " AND kind!='skill' AND tashan_score >= ? AND tashan_score < ?"
                           " ORDER BY tashan_score, id", (lo, hi)).fetchall()
        # spread the draw ACROSS the band rather than taking its top, or each band re-creates in
        # miniature the very top-slice bias this mode exists to remove
        step = max(1, len(band) // per)
        pick = band[::step][:per]
        for r in pick:
            if r[0] not in seen:
                seen.add(r[0]); rows.append(r)
        print(f"  band {lo:>3}-{hi:<3} {len(band):5,} eligible -> sampled {len(pick)}")
else:
    rows = con.execute(SEL + WHERE + " ORDER BY tashan_score DESC LIMIT ?", (TOP_N,)).fetchall()
man = []
for cid, name, repo, pkg, desc in rows:
    # try common README locations
    txt = None
    for p in ("README.md", "readme.md", "Readme.md", "docs/README.md"):
        txt = raw(repo, p)
        if txt:
            break
    if not txt:
        print(f"  no README: {cid} ({repo})")
        continue
    man.append({"id": cid, "name": name, "repo": repo, "npm_pkg": pkg,
                "description": desc, "readme": txt[:MAXLEN]})
    print(f"  ok {cid}  ({len(txt)} chars)")
json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"), indent=2)
print(f"\n{len(man)} READMEs -> {OUT}/manifest.json")
