#!/usr/bin/env python3
"""Merge LLM category assignments (data/classify/cat_*.json) into the DB, then re-export."""
import json, os, glob
import build  # reuse db(), export()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALID = {"browser","search","database","devtools","cloud","files","data","docs",
         "comms","design","ai","finance","productivity","security","other"}

con = build.db()
n, bad = 0, 0
for f in sorted(glob.glob(os.path.join(ROOT, "data", "classify", "cat_*.json"))):
    for s in json.load(open(f)):
        cat = (s.get("category") or "other").strip().lower()
        if cat not in VALID:
            cat = "other"; bad += 1
        con.execute("UPDATE capabilities SET category=? WHERE id=?", (cat, s["id"]))
        n += 1
con.commit()
print(f"merged {n} category assignments ({bad} coerced to 'other')")
# tally
for cat, c in con.execute("SELECT category, COUNT(*) FROM capabilities WHERE category IS NOT NULL GROUP BY category ORDER BY COUNT(*) DESC"):
    print(f"  {cat:14} {c}")
build.export(con)
con.close()
