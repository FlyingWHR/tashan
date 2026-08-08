#!/usr/bin/env python3
"""Merge LLM expertise grades (data/readmes/scores_*.json) into the DB, then re-export the site JSON.

    python3 pipeline/merge_expertise.py            # merge, reject anything malformed
    python3 pipeline/merge_expertise.py --dry-run  # validate only, touch nothing

This used to write whatever it was handed. That is fine when one person grades two dozen READMEs by
hand and reads back what they wrote; it is not fine when a fleet of graders produces hundreds of rows
that get published and sold. A verdict of "deep" carrying an expertise of 30 is not a grade, it is a
corrupted row, and on the board it would look exactly like a real one.

Every record is validated before it is written, and a bad one is REPORTED AND SKIPPED rather than
coerced — coercing it would invent a grade nobody assigned, which is the failure this whole project
exists to avoid.
"""
import json, os, glob, sys
import build  # reuse db(), export()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The bands from the shipped rubric. They overlap on purpose (wrapper 20-44 sits inside thin 35-59)
# because a thin wrapper is genuinely both, so the check is "inside your own band", not "in one band".
BANDS = {"deep": (80, 100), "solid": (60, 79), "thin": (35, 59),
         }
NOTE_MAX = 200


def validate(rec, source, known_ids):
    """Return the reasons this record must not be written. Empty list means it is good."""
    cid = rec.get("id")
    if not cid or not isinstance(cid, str):
        return [f"{source}: record with no usable id: {str(rec)[:80]}"]
    bad, v, e = [], rec.get("verdict"), rec.get("expertise")
    if v not in BANDS:
        bad.append(f"{cid}: verdict {v!r} is not one of {sorted(BANDS)}")
    if not isinstance(e, int) or isinstance(e, bool):
        bad.append(f"{cid}: expertise {e!r} is not an integer")
    elif v in BANDS:
        lo, hi = BANDS[v]
        if not lo <= e <= hi:
            bad.append(f"{cid}: verdict {v!r} with expertise {e} — outside its band {lo}-{hi}")
    note = rec.get("note")
    if note is not None and (not isinstance(note, str) or len(note) > NOTE_MAX):
        bad.append(f"{cid}: note is not a string under {NOTE_MAX} chars")
    if known_ids is not None and cid not in known_ids:
        bad.append(f"{cid}: not a capability we track — the id was altered or invented")
    return bad


def main():
    dry = "--dry-run" in sys.argv
    con = build.db()
    known = {r[0] for r in con.execute("SELECT id FROM capabilities")}

    files = sorted(glob.glob(os.path.join(ROOT, "data", "readmes", "scores_*.json")))
    good, rejected, seen = [], [], {}
    for f in files:
        src = os.path.basename(f)
        try:
            recs = json.load(open(f, encoding="utf-8"))
        except (ValueError, OSError) as e:
            rejected.append(f"{src}: unreadable ({e})")
            continue
        if not isinstance(recs, list):
            rejected.append(f"{src}: not a JSON array")
            continue
        for rec in recs:
            if not isinstance(rec, dict):
                rejected.append(f"{src}: non-object entry")
                continue
            problems = validate(rec, src, known)
            if problems:
                rejected.extend(problems)
                continue
            # The same capability graded twice with different results is a real disagreement between
            # graders, not a merge conflict to settle quietly. Keep the first and say so.
            key = (rec.get("verdict"), rec.get("expertise"))
            if rec["id"] in seen and seen[rec["id"]] != key:
                rejected.append(f"{rec['id']}: graded twice and differently "
                                f"({seen[rec['id']]} vs {key}) — kept the first")
                continue
            seen[rec["id"]] = key
            good.append(rec)

    print(f"  {len(files)} score file(s): {len(good)} valid, {len(rejected)} rejected")
    for r in rejected[:15]:
        print(f"    reject: {r}")
    if len(rejected) > 15:
        print(f"    … and {len(rejected) - 15} more")

    if dry:
        print("  --dry-run: nothing written")
        return 0

    for s in good:
        con.execute("UPDATE capabilities SET expertise=?, expertise_verdict=?, expertise_note=? WHERE id=?",
                    (s["expertise"], s["verdict"], s.get("note"), s["id"]))
    con.commit()
    graded = con.execute("SELECT COUNT(*) FROM capabilities WHERE expertise_verdict IS NOT NULL").fetchone()[0]
    total = con.execute("SELECT COUNT(*) FROM capabilities WHERE tashan_score IS NOT NULL").fetchone()[0]
    print(f"  merged {len(good)} grades -> {graded:,} of {total:,} scored capabilities graded "
          f"({100 * graded / max(total, 1):.1f}%)")
    build.export(con)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
