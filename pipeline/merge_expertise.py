#!/usr/bin/env python3
"""Merge LLM expertise grades (data/readmes/scores_*.json) into the DB, then re-export the site JSON."""
import json, os, glob, sqlite3
import build  # reuse db(), export()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
con = build.db()
n = 0
for f in sorted(glob.glob(os.path.join(ROOT, "data", "readmes", "scores_*.json"))):
    for s in json.load(open(f)):
        con.execute("UPDATE capabilities SET expertise=?, expertise_verdict=?, expertise_note=? WHERE id=?",
                    (s.get("expertise"), s.get("verdict"), s.get("note"), s["id"]))
        n += 1
con.commit()
print(f"merged {n} expertise grades")
build.export(con)
con.close()
