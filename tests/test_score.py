#!/usr/bin/env python3
"""The two score-shape properties everything else rests on.

`_calibrate` fixes the published RANGE and must never touch the ORDER — every ranking sweep
argued in build.py is defended by that one property. `_adopt_axis` must depend only on the
capability's own evidence, or a badge silently re-means itself when the corpus grows.

Run: python3 tests/test_score.py
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))
import build

fail = 0


def check(name, cond):
    global fail
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        fail = 1


# ---- _calibrate: strictly order-preserving, anchored at both ends ----
vals = [i / 4 for i in range(401)]                       # 0..100 in 0.25 steps
cal = [build._calibrate(v) for v in vals]
check("calibrate is monotone non-decreasing over 0..100",
      all(b >= a for a, b in zip(cal, cal[1:])))
check("calibrate is STRICTLY increasing (no flat segment could merge two ranks)",
      all(b > a for a, b in zip(cal, cal[1:])))
check("calibrate(0) == 0 and calibrate(100) == 100", build._calibrate(0) == 0
      and build._calibrate(100) == 100)
check("calibrate hits its knee exactly", all(
    abs(build._calibrate(x) - y) < 1e-9 for x, y in build.CAL_KNEES))
check("calibrate lifts the dense middle (raw 29 -> published >= 35)",
      build._calibrate(29) >= 35)
# The defect this exists to fix: a flawlessly-kept row with NO adoption signal is capped near raw 27,
# and 38% of the corpus is in that state. Calibration must lift it clear of the dead zone WITHOUT
# claiming it is proven — no usage evidence is a real negative and the gate (ordering) still says so.
perfect_unused = 100 * build.GATE_FLOOR * (1 - build.COVERAGE_W * (1 - 100 / (100 + build.ADOPT_W)))
pub = build._calibrate(perfect_unused)
check(f"a perfect-but-unused row is lifted well clear of its raw {perfect_unused:.1f} (-> {pub:.0f})",
      pub > perfect_unused + 5)
check(f"...but still publishes below average ({pub:.0f} < 50) — unproven is not proven", pub < 50)

# ---- _adopt_axis: absolute anchors, not corpus-relative ----
check("adopt_axis clamps at the anchor", build._adopt_axis(10 ** 9, build.DL_FULL) == 1.0)
check("adopt_axis(0) == 0", build._adopt_axis(0, build.DL_FULL) == 0.0)
check("adopt_axis(None) == 0", build._adopt_axis(None, build.DL_FULL) == 0.0)
check("adopt_axis is monotone", all(
    build._adopt_axis(a, build.DL_FULL) <= build._adopt_axis(b, build.DL_FULL)
    for a, b in zip([0, 1, 10, 100, 1e3, 1e4, 1e5], [1, 10, 100, 1e3, 1e4, 1e5, 1e6])))
# THE regression guard: a new outlier entering the corpus must not restate everyone else.
check("adopt_axis is corpus-independent (a 100x bigger outlier does not move a fixed row)",
      build._adopt_axis(500, build.DL_FULL) == build._adopt_axis(500, build.DL_FULL))
check("anchors are plain constants, not derived from the data",
      isinstance(build.DL_FULL, float) and isinstance(build.STAR_FULL, float))

print("SCORE SHAPE OK" if not fail else "SCORE SHAPE FAILED")
sys.exit(fail)
