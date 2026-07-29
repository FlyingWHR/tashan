#!/usr/bin/env python3
"""Fetch READMEs for the top-ranked capabilities that have a source repo, for LLM expertise-eval.
Writes data/readmes/manifest.json = [{id,name,repo,npm_pkg,description,readme(truncated)}]."""
import json, os, sqlite3, urllib.request, urllib.parse

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
rows = con.execute("SELECT id,name,source_repo,npm_pkg,description FROM capabilities "
                   "WHERE tashan_score IS NOT NULL AND source_repo IS NOT NULL "
                   "ORDER BY tashan_score DESC LIMIT ?", (TOP_N,)).fetchall()
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
