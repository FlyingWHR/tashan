#!/usr/bin/env python3
"""A published grade must not contradict itself.

The expertise grade is one of two things we sell depth on, and it is graded by a model against a
rubric with five named bands. Nothing checked that the verdict and the number agreed, so four rows
shipped saying things like:

    @modelcontextprotocol/server-filesystem   thin    62      (62 is the "solid" band)
    obsidian-mcp-server                       solid   83      (83 is "deep")
    openttt-pot                               deep    78      (78 is "solid")

One of those is rank 3 on the board. A reader who knows the rubric sees a contradiction; a reader who
does not is simply misinformed. Neither number can be trusted when the grader disagreed with itself,
so the fix is to clear the row back to "not graded yet" — an honest absence — never to repair one
value to match the other, which would be us inventing the verdict.

Run: python3 tests/test_expertise.py
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
from merge_expertise import BANDS, validate

fail = 0


def ok(name, cond):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name)


# ---- the validator ------------------------------------------------------------------------------
known = {"pkg:x"}
ok("a coherent grade passes",
   not validate({"id": "pkg:x", "verdict": "deep", "expertise": 90, "note": "4 tool docs"}, "t", known))
ok("deep with a thin score is rejected",
   validate({"id": "pkg:x", "verdict": "deep", "expertise": 30}, "t", known))
ok("a verdict outside the rubric is rejected",
   validate({"id": "pkg:x", "verdict": "excellent", "expertise": 90}, "t", known))
ok("a score that is a string is rejected",
   validate({"id": "pkg:x", "verdict": "solid", "expertise": "72"}, "t", known))
ok("True is not an integer score",
   validate({"id": "pkg:x", "verdict": "solid", "expertise": True}, "t", known))
ok("a record with no id is rejected", validate({"verdict": "solid", "expertise": 72}, "t", known))
ok("an id we do not track is rejected — grades cannot invent capabilities",
   validate({"id": "pkg:never-heard-of-it", "verdict": "solid", "expertise": 72}, "t", known))
ok("an overlong note is rejected",
   validate({"id": "pkg:x", "verdict": "thin", "expertise": 40, "note": "z" * 500}, "t", known))
# the bands overlap deliberately: a thin wrapper is both, so membership is "inside your own band"
ok("wrapper at 40 is valid even though thin also spans 40",
   not validate({"id": "pkg:x", "verdict": "wrapper", "expertise": 40}, "t", known))

# ---- the shipped export -------------------------------------------------------------------------
path = os.path.join(ROOT, "web", "data", "capabilities.json")
if os.path.exists(path):
    caps = json.load(open(path, encoding="utf-8"))["capabilities"]
    bad = []
    for c in caps:
        v, e = c.get("expertise_verdict"), c.get("expertise")
        if not v:
            continue
        if v not in BANDS:
            bad.append(f"{c['name']}: verdict {v!r} is not in the rubric")
        elif e is None:
            bad.append(f"{c['name']}: verdict {v!r} with no score")
        elif not BANDS[v][0] <= e <= BANDS[v][1]:
            bad.append(f"{c['name']}: {v} with {e} (band {BANDS[v][0]}-{BANDS[v][1]})")
    ok(f"no shipped grade contradicts itself" + (": " + "; ".join(bad[:3]) if bad else ""), not bad)
    # A JUDGMENT MAY NOT REST ON SOMEONE ELSE'S DOCUMENT. 87 published NEGATIVE verdicts were read
    # off a README the capability shares with other packages, or one that never names it — worst,
    # @modelcontextprotocol/server-filesystem (Anthropic's own, 482k downloads a week) graded `thin`
    # for being a list entry in a monorepo index shared with three siblings. doc_signals.py already
    # capped these at `thin` so a grade could not borrow CREDIT from another project's document; it
    # must not borrow BLAME either, and `thin` is a criticism, not a neutral floor.
    borrowed = [c for c in caps
                if (c.get("doc_shared_with") or 0) > 0
                or (c.get("doc_names_self") is not None and c["doc_names_self"] == 0)]
    judged = [c for c in borrowed if c.get("expertise_verdict")]
    ok(f"no capability is judged on a document about something else ({len(borrowed)} such rows)"
       + ("" if not judged else f" — {len(judged)} still judged, e.g. "
          + str([(c["name"], c["expertise_verdict"]) for c in judged[:3]])),
       not judged)
    # …and the fact replaces it. Silence would read as "not looked at yet" when we HAVE looked and
    # found the documentation belongs to something else, which is the more useful thing to say.
    stated = [c for c in borrowed if c.get("doc_status")]
    ok(f"each states why instead of going quiet ({len(stated)}/{len(borrowed)} carry doc_status)",
       len(stated) == len(borrowed))

    graded = sum(1 for c in caps if c.get("expertise_verdict"))
    print(f"        {graded:,} of {len(caps):,} capabilities graded "
          f"({100 * graded / max(len(caps), 1):.1f}%)")

print("EXPERTISE FAILED" if fail else "ok — expertise grades are internally consistent")
sys.exit(fail)

