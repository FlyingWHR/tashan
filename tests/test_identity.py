#!/usr/bin/env python3
"""One thing must not be ranked twice at two different numbers.

WHAT THIS CATCHES. A project that ships an npm package, a Claude plugin and a skill from the same
repository is ingested three times, once per source, and scored three times from whatever evidence
that particular channel carries. The rows are real — they are genuinely different install paths —
but they are not different CAPABILITIES, and the board treats them as if they were:

    pkg:skylight-mcp                              npm      60
    plugin:chrischall/skylight-mcp/skylight-mcp   plugin   45
    skill:chrischall/skylight-mcp                 skill    —

Same repository, same name, same software, two scores fifteen points apart and one blank. A reader
searching for it sees the same thing recommended and not-recommended at once. On a site whose only
asset is being right about numbers, that is the same defect as the four different capability counts
the pages used to print, one layer down in the data.

WHY THIS IS A TEST AND NOT A MERGE. Merging them is a product decision with real consequences — which
row owns the URL, which score survives, what happens to the two dossiers already indexed by Google —
and it cannot be made correctly at 2am against a deadline. What can be done now is refuse to let the
number grow: the disagreement is measured, recorded, and the suite fails if a pipeline change starts
manufacturing more of it. A known defect with a ceiling is a different thing from an unknown one.

    python3 tests/test_identity.py            # fail if the divergence RATE grows past the baseline
    python3 tests/test_identity.py --report   # list the worst offenders
"""
import json, os, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "tashan.db")
BASELINE = os.path.join(ROOT, "data", "identity_baseline.json")

# A capability whose channels disagree by less than this is noise: the npm row genuinely knows more
# than the skill row, and a few points of difference is that knowledge, not a contradiction.
SPREAD = 15

# Room for the corpus to grow without a false alarm. Ratcheting is the point: the baseline is
# rewritten only by a human running --accept, so a change that doubles the divergence fails here.
SLACK = 1.15


def groups(con):
    """Every (repo, name) that exists as more than one row, with the spread of its scores."""
    return con.execute(
        """SELECT LOWER(source_repo) AS repo, LOWER(name) AS name, COUNT(*) AS rows,
                  COUNT(DISTINCT kind) AS kinds,
                  MAX(tashan_score) - MIN(tashan_score) AS spread,
                  COUNT(tashan_score) AS scored
             FROM capabilities
            WHERE source_repo IS NOT NULL AND source_repo <> ''
              AND name IS NOT NULL AND name <> ''
         GROUP BY repo, name
           HAVING rows > 1"""
    ).fetchall()


def measure(con):
    rows = groups(con)
    multi = [g for g in rows if g[3] > 1]
    # THE DENOMINATOR, and the reason this test failed for the wrong reason. An identity can only
    # CONTRADICT itself if at least two of its channels carry a score; one score and three blanks is
    # incomplete, not inconsistent. So the population at risk is not "every multi-kind identity", it
    # is "every multi-kind identity we have scored twice" — and that population grows every time
    # scoring succeeds.
    at_risk = [g for g in multi if g[5] >= 2]
    diverging = [g for g in multi if g[4] is not None and g[4] >= SPREAD]
    return {
        "duplicated_identities": len(rows),
        "spanning_kinds": len(multi),
        "at_risk": len(at_risk),
        "diverging": len(diverging),
        "rate": round(len(diverging) / max(len(at_risk), 1), 4),
        "worst": max((g[4] for g in diverging), default=0),
    }, diverging


def main():
    if not os.path.exists(DB):
        print("  skip  no database")
        return 0
    con = sqlite3.connect(DB)
    now, diverging = measure(con)

    if "--report" in sys.argv:
        for repo, name, rows, kinds, spread, scored in sorted(diverging, key=lambda g: -g[4])[:25]:
            channels = con.execute(
                "SELECT kind, tashan_score FROM capabilities "
                "WHERE LOWER(source_repo)=? AND LOWER(name)=? ORDER BY tashan_score DESC",
                (repo, name)).fetchall()
            shown = " · ".join(f"{k}={'—' if s is None else round(s)}" for k, s in channels)
            print(f"  {spread:>3.0f}  {name[:34]:<34} {shown}   {repo[:44]}")
        return 0

    if "--accept" in sys.argv:
        with open(BASELINE, "w") as f:
            json.dump(now, f, indent=2)
            f.write("\n")
        print(f"  baseline recorded: {json.dumps(now)}")
        return 0

    try:
        with open(BASELINE) as f:
            was = json.load(f)
    except (OSError, ValueError):
        with open(BASELINE, "w") as f:
            json.dump(now, f, indent=2)
            f.write("\n")
        print(f"  ok    baseline established: {now['diverging']:,} identities score themselves two ways")
        return 0

    # RATCHET THE RATE, NOT THE COUNT. The first version of this gate compared the raw number of
    # diverging identities, and it went red on its second night: 65 -> 172 against a ceiling of 79 —
    # which withheld the whole site. Nothing had got worse. The pipeline had not completed a run
    # since 25 August, so that night it cleared eighteen days of enrichment backlog and scored
    # thousands of rows for the first time; every newly-scored second channel moved an identity into
    # the population that CAN disagree. The tell was in the numbers: the count nearly tripled while
    # the worst spread went DOWN, 49 to 46. A defect getting worse does not improve its extreme.
    #
    # This is the same shape as the coverage ratio in CLAUDE.md, which falls every time discovery
    # succeeds and is therefore reported and never targeted: a ratchet on an absolute count punishes
    # measuring more. The rate is the defect; the count is coverage times the defect. Both are
    # printed, with the denominator, so the next failure can be read without re-running the pipeline
    # — the CI line that cost a day said "172 (was 65)" and nothing about how many were at risk.
    was_rate = was.get("rate")
    if was_rate is None:                      # baseline predates the rate — derive it if we can
        was_rate = was.get("diverging", 0) / max(was.get("at_risk") or 0, 1) if was.get("at_risk") else None
    ceiling = round(was_rate * SLACK, 4) if was_rate else None
    worst_ceiling = max(was.get("worst", 0), SPREAD)
    bad_rate = ceiling is not None and now["rate"] > ceiling
    bad_worst = now["worst"] > worst_ceiling
    bad = bad_rate or bad_worst
    print(f"  {'FAIL' if bad else 'ok  '}  {now['diverging']:,} of {now['at_risk']:,} twice-scored "
          f"identities disagree with themselves — {now['rate']:.1%}"
          + (f" (was {was_rate:.1%}, ceiling {ceiling:.1%})" if was_rate else " (no baseline rate)")
          + f", worst spread {now['worst']:.0f} of {worst_ceiling:.0f} allowed")
    if bad:
        if bad_rate:
            print("        A change has made the index disagree with itself MORE OFTEN, per identity")
            print("        it has scored twice. That is not discovery — that is a regression.")
        if bad_worst:
            print(f"        And the worst single contradiction has grown past {worst_ceiling:.0f} points.")
        print("        python3 tests/test_identity.py --report   to see which, then fix or --accept.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
