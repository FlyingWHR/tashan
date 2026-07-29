#!/usr/bin/env python3
"""Dump ranked capabilities (metadata only) for LLM category classification.
Writes data/classify/manifest.json = [{id,name,description,npm_pkg,source_repo,co_used}]."""
import json, os, sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "tashan.db")
OUT = os.path.join(ROOT, "data", "classify")
os.makedirs(OUT, exist_ok=True)

con = sqlite3.connect(DB)
rows = con.execute("SELECT id,name,kind,title,description,npm_pkg,source_repo,co_used FROM capabilities "
                   "WHERE tashan_score IS NOT NULL ORDER BY tashan_score DESC").fetchall()
man = []
for cid, name, kind, title, desc, pkg, repo, co in rows:
    cou = []
    try:
        cou = [x.get("id", "").split(":", 1)[-1] for x in (json.loads(co) if co else [])][:4]
    except Exception:
        pass
    man.append({"id": cid, "name": name, "kind": kind,
                "description": (title or "") + (" — " + desc if desc else "") if (title or desc) else "",
                "npm_pkg": pkg, "source_repo": repo, "co_used": cou})
json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"), indent=2)
print(f"{len(man)} capabilities -> {OUT}/manifest.json")
