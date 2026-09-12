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

    python3 tests/test_identity.py            # fail if divergence grows past the recorded baseline
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
    diverging = [g for g in multi if g[4] is not None and g[4] >= SPREAD]
    return {
        "duplicated_identities": len(rows),
        "spanning_kinds": len(multi),
        "diverging": len(diverging),
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

    ceiling = int(was.get("diverging", 0) * SLACK) + 5
    bad = now["diverging"] > ceiling
    print(f"  {'FAIL' if bad else 'ok  '}  {now['diverging']:,} identities score themselves two ways "
          f"(was {was.get('diverging', 0):,}, ceiling {ceiling:,}, worst spread {now['worst']:.0f})")
    if bad:
        print("        A change has made the index disagree with itself more often than it did.")
        print("        python3 tests/test_identity.py --report   to see which, then fix or --accept.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
