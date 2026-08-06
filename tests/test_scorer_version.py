#!/usr/bin/env python3
"""SCORER_VERSION must change whenever the scoring changes.

signal_history stores which scorer measured each point, and trend() only compares points sharing a
version. That is the only thing standing between a customer and being told our own recalibration was
their capability declining — which is exactly what happened before the column existed:
pkg:3dstreet-mcp read 43,43,43,43,42,40 and every step down was a scorer rewrite.

The protection depends on a human remembering to bump a string. This makes forgetting fail loudly
instead of silently, the same way pipeline/bump_assets.py --check does for the ?v= asset version.

    python3 tests/test_scorer_version.py            # verify
    python3 tests/test_scorer_version.py --accept   # record the current scoring as the new baseline

Run --accept ONLY together with a SCORER_VERSION bump. Accepting without bumping is precisely the
mistake this exists to catch.
"""
import datetime, hashlib, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
BASELINE = os.path.join(ROOT, "pipeline", "scorer.lock")
# How long a scorer version is promised to hold. 90 days is a quarter — long enough that a Pro
# customer's trend line is worth buying, short enough that a real calibration error is not frozen in
# for a year. It is published on methodology.html; changing it here without changing it there is the
# kind of drift tests/test_claims.py exists to catch.
WINDOW_DAYS = 90


def today():
    return datetime.date.today().isoformat()


def days_left(until):
    if not until:
        return None
    try:
        return (datetime.date.fromisoformat(until) - datetime.date.today()).days
    except ValueError:
        return None

# Every knob and every line of arithmetic that can move a published score.
CONSTANTS = ["COVERAGE_W", "ADOPT_W", "STAR_W", "GATE_FLOOR", "DL_FULL", "REACH_FULL", "STAR_FULL",
             "CAL_KNEES"]


def fingerprint():
    """Derived from the SOURCE TEXT, never from an import.

    The first version imported build and read the constants off the module. A stale __pycache__ then
    reported GATE_FLOOR=0.45 while build.py plainly said 0.30, so the guard both fired on a clean tree
    and would have stayed silent on a real change if the bytecode lagged the other way. A checker that
    can disagree with the file it is checking is worse than no checker.
    """
    src = open(os.path.join(ROOT, "pipeline", "build.py"), encoding="utf-8").read()
    parts = []
    for n in CONSTANTS:
        m = re.search(rf"^{n}\s*=\s*(.+)$", src, re.M)
        if not m:
            raise SystemExit(f"could not find constant {n} in build.py — update this test, do not delete it")
        parts.append(f"{n}={m.group(1).strip()}")
    for fn in ("compute_scores", "_calibrate", "_adopt_axis"):
        m = re.search(rf"\ndef {fn}\(.*?(?=\ndef |\Z)", src, re.S)
        if not m:
            raise SystemExit(f"could not locate {fn}() in build.py — update this test, do not delete it")
        # comments carry the reasoning and change constantly; only the code decides a score
        body = "\n".join(l for l in m.group(0).split("\n")
                         if l.strip() and not l.strip().startswith("#"))
        parts.append(body)
    mv = re.search(r"^SCORER_VERSION\s*=\s*.*?\"([^\"]+)\"\)?\s*$", src, re.M)
    if not mv:
        raise SystemExit("could not find SCORER_VERSION in build.py")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16], mv.group(1)


def read_baseline():
    """`<version> <fingerprint> [effective] [stable_until]`.

    The last two are the stability commitment and were added later, so a two-field lock still parses
    — an old lock means "no window declared", not a crash.
    """
    parts = open(BASELINE).read().split()
    return (parts + [None, None])[:4]


def main():
    fp, version = fingerprint()
    if "--accept" in sys.argv:
        _, _, eff, until = read_baseline() if os.path.exists(BASELINE) else (None, None, None, None)
        eff = today()
        until = (datetime.date.fromisoformat(eff) + datetime.timedelta(days=WINDOW_DAYS)).isoformat()
        with open(BASELINE, "w") as f:
            f.write(f"{version} {fp} {eff} {until}\n")
        print(f"recorded baseline: SCORER_VERSION={version} fingerprint={fp}")
        print(f"stability window: {eff} -> {until} ({WINDOW_DAYS} days). Publish it on methodology.html.")
        return 0

    if not os.path.exists(BASELINE):
        print(f"  FAIL  no {os.path.relpath(BASELINE, ROOT)} — run with --accept to record the baseline")
        return 1

    want_version, want_fp, eff, until = read_baseline()
    if fp == want_fp and version == want_version:
        left = days_left(until)
        note = f", stable through {until}" + (f" ({left}d left)" if left is not None else "") if until else ""
        print(f"  ok    scoring unchanged (SCORER_VERSION={version}{note})")
        return 0

    # THE STABILITY COMMITMENT. Pro sells score history, and history only accrues while the ruler
    # holds still: every version boundary restarts trend() from zero, so a scorer rewritten four
    # times in a week sells a series that is never more than two days long. The technical guard
    # below already stops us mislabelling a change; it does nothing to stop us MAKING one. This is
    # the part that costs something — inside the published window a scoring change is refused, and
    # shipping one anyway requires writing down why, in a variable, where a reviewer sees it.
    left = days_left(until)
    if fp != want_fp and left and left > 0 and not os.environ.get("TASHAN_SCORER_BREAK_GLASS"):
        print(f"  FAIL  the scoring changed inside the declared stability window.")
        print(f"        {want_version} is published as stable through {until} — {left} days left.")
        print("        Every capability's trend restarts at the boundary, and a customer paying for")
        print("        score history gets a series that begins the day we changed our minds.")
        print("        A correctness fix can still ship. Say so, so it is on the record:")
        print("            TASHAN_SCORER_BREAK_GLASS='malicious-severity fix' python3 tests/run.sh")
        return 1
    if fp != want_fp and version == want_version:
        print(f"  FAIL  the scoring changed but SCORER_VERSION is still {version!r}.")
        print("        Every stored history point claims to be comparable to the new ones, and trend()")
        print("        will compare across two different rulers — reporting OUR change as a capability")
        print("        declining, to someone paying for the number.")
        print(f"        Bump SCORER_VERSION in pipeline/build.py, then: python3 {os.path.relpath(__file__, ROOT)} --accept")
        return 1
    if fp == want_fp and version != want_version:
        print(f"  FAIL  SCORER_VERSION moved {want_version!r} -> {version!r} but the scoring is identical.")
        print("        That splits the history for nothing: trend() will refuse to compare across the")
        print("        boundary and every capability loses its usable series. Revert, or --accept if")
        print("        the break is deliberate.")
        return 1
    print(f"  ok    scoring changed AND SCORER_VERSION bumped {want_version!r} -> {version!r}")
    print(f"        run: python3 {os.path.relpath(__file__, ROOT)} --accept   to record it")
    return 1


if __name__ == "__main__":
    sys.exit(main())
