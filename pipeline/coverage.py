#!/usr/bin/env python3
"""Coverage, weighted by demand instead of by row count.

    python3 pipeline/coverage.py            # measure, write web/data/coverage.json
    python3 pipeline/coverage.py --selftest # pure-logic checks, no DB

THE NUMBER WE WERE REPORTING WAS THE WRONG NUMBER. Aggregate coverage — measured rows over tracked
rows — went 47% -> 41% in two days, and read as decline. Nothing got worse: ingestion grew the
denominator 44% while measurement grew 25%. That ratio falls every time discovery does its job, so
optimising it means discovering less, which is the opposite of what a coverage metric is for.

The failure that actually costs us is not a low ratio. It is an absence on something someone asks
about. Measured 5 Aug on the top 20 by weekly downloads: 2/20 fully measured, 18/20 with no expertise
grade, 20/20 with no task mapping — while the headline said 41%. An agent that hits absences on
popular packages stops querying; it never sees the long tail we were counting.

So the denominator is demand. `top100` and `top1000` are the capabilities ranked by the adoption
evidence we hold, and those tiers are what we commit to. The whole corpus is still reported, plainly,
because hiding it would be the same sin in the other direction — it is just not the target.

TIERS ARE CUMULATIVE AND ORDERED BY EVIDENCE, NOT BY SCORE. Score is the wrong proxy for what someone
will ask about: a badly-kept package with two million downloads a week is asked about constantly and
scores 43.
"""
import json, os, re, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "tashan.db")
OUT = os.path.join(ROOT, "web", "data", "coverage.json")

# The tiers we publish a commitment against. Everything else is reported, not promised.
TIERS = [("top100", 100), ("top1000", 1000)]
# How much of the measurement queue to publish on /requests.html. Enough to show the shape of the
# backlog, short enough that the page stays a page.
QUEUE_N = int(os.environ.get("QUEUE_N", "40"))

# Each axis: (key, label, what an absence costs the reader).
AXES = [
    ("score",  "tashan score",     "no ranking, no badge, no comparison"),
    ("scan",   "security scan",    "we cannot say whether an advisory affects the version you would install"),
    ("grade",  "expertise grade",  "no read of whether the capability documents itself"),
    ("task",   "task mapping",     "invisible to every job and role page, and to 'what should I install for X'"),
]


def demand(r):
    """Rank by the adoption evidence we actually hold, best channel first.

    npm downloads dominate where they exist because they are a direct usage count. Everything else
    falls back to the blended adoption axis, which is what a plugin or a registry-only server has.
    Ties break on id so the ordering is stable run to run — an unstable tier boundary would make
    coverage jitter for reasons that have nothing to do with measurement.
    """
    return (-(r["npm_downloads"] or 0), -(r["adoption"] or 0), r["id"])


def measured(r, tagged):
    return {
        "score": r["tashan_score"] is not None,
        "scan": bool(r["sec_scanned_at"]),
        "grade": bool(r["expertise_verdict"]),
        "task": r["id"] in tagged,
    }


def tally(pool, tagged):
    out = {"n": len(pool)}
    for key, _, _ in AXES:
        out[key] = sum(1 for r in pool if measured(r, tagged)[key])
    out["full"] = sum(1 for r in pool if all(measured(r, tagged).values()))
    return out


OUTREACH = os.path.join(ROOT, "docs", "OUTREACH.md")


def bake_outreach(con):
    """Rewrite the numbers in docs/OUTREACH.md from the database.

    THIS IS A BUG FIX, AND THE BUG WAS A TEST. The facts table was hand-written and
    tests/test_outreach_numbers.py checked it against live SQL — which sounds right and is not: the
    numbers move every time the pipeline runs, so the check went red every night BY CONSTRUCTION and
    blocked the nightly publish. It had already drifted 2,771 -> 3,564 scanned and 75% -> 78%
    provenance within one run. A gate that fails on a schedule is worse than no gate; it teaches
    everyone to ignore a red suite.

    So the numbers are generated, like every other number on this site — the methodology page, the
    hero counts, the product tree. The test stays, and now catches the thing worth catching: someone
    hand-editing a figure, or the bake not having run before the drafts were sent.
    """
    if not os.path.exists(OUTREACH):
        return
    q = lambda s: con.execute(s).fetchone()[0]
    scanned = q("SELECT count(*) FROM capabilities WHERE sec_scanned_at IS NOT NULL")
    attested = q("SELECT count(*) FROM capabilities WHERE sec_provenance=1")
    gap = scanned - attested
    pct = round(100.0 * gap / scanned) if scanned else 0
    # The row label fragment -> the query behind it. Kept as plain strings rather than inlined into
    # f-strings: the first version fought the quoting of `!= ''` and came out unreadable, which is
    # the wrong trade in a function whose entire job is that a number is checkable.
    SQL = {
        "install-time script":
            "SELECT count(*) FROM capabilities "
            "WHERE sec_install_script IS NOT NULL AND sec_install_script != ''",
        "Confirmed-malicious":
            "SELECT count(*) FROM capabilities WHERE sec_max_severity = 'MALICIOUS'",
        "maintainer has **stopped**":
            "SELECT count(*) FROM capabilities "
            "WHERE tashan_score IS NOT NULL AND vitality = 'abandoned'",
        "can't be launched":
            "SELECT count(*) FROM capabilities WHERE npm_runnable = 0",
    }
    vals = {
        "scanned for advisories": f"{scanned:,}",
        "no build provenance": f"**{pct}%** ({gap:,})",
    }
    for frag, sql in SQL.items():
        vals[frag] = f"{q(sql):,}"
    src = open(OUTREACH, encoding="utf-8").read()
    out, hits = [], 0
    for line in src.split("\n"):
        m = re.match(r"^\|\s*(.+?)\s*\|\s*[^|]*\|\s*(.*)\|\s*$", line)
        if m and not line.startswith("| Fact") and not set(line) <= set("|- "):
            for frag, v in vals.items():
                if frag in m.group(1):
                    out.append(f"| {m.group(1)} | {v} | {m.group(2)}|")
                    hits += 1
                    break
            else:
                out.append(line)
        else:
            out.append(line)
    s = "\n".join(out)
    # The drafts quote the headline figure in prose too. A table that agrees with the database while
    # the email body carries last week's number is the same defect one layer down.
    s, n1 = re.subn(r"(~|about )\d\d(% (?:ship with no|of scanned packages have))", rf"\g<1>{pct}\g<2>", s)
    s, n2 = re.subn(r"(build provenance \(~)\d\d(% don't\))", rf"\g<1>{pct}\g<2>", s)
    s, n3 = re.subn(r"(and )\d\d(% have no build provenance)", rf"\g<1>{pct}\g<2>", s)
    s, n4 = re.subn(r"(The )\d\d(% is the strongest single line)", rf"\g<1>{pct}\g<2>", s)
    if hits < len(vals):
        raise SystemExit(f"outreach bake matched {hits}/{len(vals)} table rows — the table shape "
                         f"changed. Fix docs/OUTREACH.md, do not let stale numbers ship to strangers.")
    open(OUTREACH, "w", encoding="utf-8").write(s)
    print(f"outreach: baked {hits} facts + {n1 + n2 + n3 + n4} prose mentions ({pct}% no provenance)")


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    # Only things that are capabilities. A library you build servers with is not one we owe coverage
    # on, and publishing it as "next in the queue" would contradict the gate that keeps it off the
    # board: @modelcontextprotocol/sdk led this queue on 53M weekly downloads until this line existed.
    # ponytail: two of build.export()'s junk() rules, not all of them — junk() is a closure and the
    # rest (DEMO, CANARY, PATHY, generic leaf names) do not reach the top of a demand ranking. If a
    # third rule ever changes what the board contains at the top, lift junk() out and share it.
    rows = [dict(r) for r in con.execute(
        "SELECT id, name, kind, npm_downloads, adoption, tashan_score, expertise_verdict, "
        "sec_scanned_at FROM capabilities "
        "WHERE (npm_runnable IS NULL OR npm_runnable=1) "
        "AND (sec_max_severity IS NULL OR sec_max_severity!='MALICIOUS')")]
    tagged = {r[0] for r in con.execute("SELECT DISTINCT cap_id FROM capability_tags")}
    ranked = sorted(rows, key=demand)

    # THE QUEUE, PUBLISHED. /requests.html was a demand board with nothing on it — "empty by design"
    # is true and reads as no demand. The honest thing to put there is not a fabricated wishlist but
    # what the pipeline is actually going to measure next, in the order it will do it. That order is
    # this same demand ranking, so the page cannot claim a queue the pipeline does not run.
    queue = []
    for r in ranked:
        got = measured(r, tagged)
        missing = [k for k, _, _ in AXES if not got[k]]
        if not missing:
            continue
        queue.append({
            "id": r["id"], "name": r["name"], "kind": r["kind"],
            "downloads": r["npm_downloads"], "missing": missing,
        })
        if len(queue) >= QUEUE_N:
            break

    payload = {
        "_why": "Coverage weighted by demand. The aggregate ratio falls whenever discovery succeeds, "
                "so it is reported but never targeted; the tiers are what we commit to.",
        "tiers": {name: tally(ranked[:n], tagged) for name, n in TIERS},
        "all": tally(ranked, tagged),
        "axes": [{"key": k, "label": lab, "absence_costs": why} for k, lab, why in AXES],
        "queue": queue,
    }
    # The single number the commitment is written against, so the page and the test read one field
    # rather than each recomputing a percentage and disagreeing in the rounding.
    t = payload["tiers"]["top1000"]
    payload["headline"] = {
        "tier": "top1000",
        "scored_pct": round(100.0 * t["score"] / t["n"]),
        "scanned_pct": round(100.0 * t["scan"] / t["n"]),
        "graded_pct": round(100.0 * t["grade"] / t["n"]),
        "tasked_pct": round(100.0 * t["task"] / t["n"]),
    }
    bake_outreach(con)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
        f.write("\n")

    w = max(len(k) for k, _ in TIERS + [("all", 0)])
    print(f"  {'tier':<{w}}  {'n':>6}  " + "  ".join(f"{k:>7}" for k, _, _ in AXES) + "     full")
    for name in [k for k, _ in TIERS] + ["all"]:
        d = payload["tiers"].get(name) or payload["all"]
        cells = "  ".join(f"{100.0 * d[k] / d['n']:6.0f}%" for k, _, _ in AXES)
        print(f"  {name:<{w}}  {d['n']:>6}  {cells}  {100.0 * d['full'] / d['n']:6.0f}%")
    print(f"coverage -> {os.path.relpath(OUT, ROOT)}")
    return 0


def _selftest():
    tagged = {"a"}
    pool = [
        {"id": "a", "npm_downloads": 5, "adoption": 1, "tashan_score": 1, "expertise_verdict": "deep",
         "sec_scanned_at": "x"},
        {"id": "b", "npm_downloads": 9, "adoption": 1, "tashan_score": None, "expertise_verdict": None,
         "sec_scanned_at": None},
    ]
    assert [r["id"] for r in sorted(pool, key=demand)] == ["b", "a"], "demand must rank downloads first"
    t = tally(pool, tagged)
    assert t == {"n": 2, "score": 1, "scan": 1, "grade": 1, "task": 1, "full": 1}, t
    # A row measured on three axes out of four is NOT full coverage. This is the whole point of the
    # metric: partial measurement on a popular capability is the case that reads as an absence.
    pool[0]["expertise_verdict"] = None
    assert tally(pool, tagged)["full"] == 0
    # Ties must not depend on dict ordering, or the tier boundary moves between runs on its own.
    same = [{"id": x, "npm_downloads": 0, "adoption": 0, "tashan_score": None,
             "expertise_verdict": None, "sec_scanned_at": None} for x in ("z", "m", "a")]
    assert [r["id"] for r in sorted(same, key=demand)] == ["a", "m", "z"]
    print("coverage selftest ok")


if __name__ == "__main__":
    sys.exit(_selftest() or 0 if "--selftest" in sys.argv else main())
