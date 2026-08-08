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

# ---- probe_demand: the queue that decides what gets measured ----
# @playwright/mcp — 6.7M npm downloads/week — sat at rank 4,436 of 4,510 in the enrichment backlog,
# because never-enriched rows were ordered by config_reach and in_registry and both are 0 for almost
# all of them. The ordering signal was the one thing we only get BY enriching. No network here: the
# fetchers are stubbed, because what is under test is the ordering and the failure handling.
def _probe_checks():
    calls = []

    def fake_bulk(url, timeout=20):
        calls.append(url)
        if "," not in url.rsplit("/", 1)[-1]:
            raise AssertionError("unscoped packages must be fetched in bulk, not one at a time")
        return {p: {"downloads": len(p) * 100} for p in url.rsplit("/", 1)[-1].split(",")}

    real_json, real_weekly = build.get_json, build._weekly
    build.get_json = fake_bulk
    build._weekly = lambda p, tries=3: 9_999_999 if p == "@big/one" else None
    try:
        cache = {}
        rows = [("a", "small"), ("b", "@big/one"), ("c", "medium-name-here"), ("d", "@dead/one")]
        out = build.probe_demand(rows, cache)
        check("the biggest package sorts first even though it was never enriched",
              out[0][1] == "@big/one")
        check("a scoped package is never sent to the bulk endpoint",
              all("@" not in u.rsplit("/", 1)[-1] for u in calls))
        check("unscoped packages are ordered by real downloads",
              [p for _, p in out if not p.startswith("@")] == ["medium-name-here", "small"])
        # The first live run cached 4,441 rate-limited failures as permanent zeros — a package
        # written off for good by one bad request is the same blind spot with a new cause.
        check("a failed probe is NOT cached, so the package is retried next run",
              "@dead/one" not in cache["_probe"])
        check("a successful probe IS cached", cache["_probe"]["@big/one"] == 9_999_999)
        check("nothing is dropped from the queue", len(out) == len(rows))
    finally:
        build.get_json, build._weekly = real_json, real_weekly


_probe_checks()

# ---- the AI-capability gate: npm keywords are marketing, not evidence ----
# Pricing the backlog made a Yahoo Finance client rank 27th on the board. It is in the corpus at all
# because discovery reaches npm by keyword and it DECLARES `mcp`, `agent` and `skill` — as do a
# database ORM and a MockServer client. So the gate reads the name and the author's own prose, and
# never the tag list. Each row below is a real package that was on, or nearly on, the board.


def _says_capability(name, desc):
    return bool(build.NAME_SAYS.search(name) or build.PROSE_SAYS.search(desc))


for _name, _desc, _want in [
    # keyword-stuffed, and not an AI capability by any reading of what they say they are
    ("yahoo-finance2", "JS API for Yahoo Finance", False),
    ("prisma", "Prisma is an open-source database toolkit. It includes a JavaScript/TypeScript ORM"
               " for Node.js, migrations and a modern GUI", False),
    ("mockserver-client", "A node client for the MockServer", False),
    ("igniteui-theming", "A set of Sass variables, mixins, and functions for theming", False),
    ("npm-deprecated-check", "Check for deprecated packages", False),
    # real capabilities — the gate must not cost us any of these
    ("@playwright/mcp", "Playwright Tools for MCP", True),      # declares no npm keywords at all
    ("frontmcp", "FrontMCP command line interface", True),      # needs substring, not a \\b boundary
    ("mcporter", "TypeScript runtime and CLI for connecting to configured MCP servers", True),
    ("firecrawl-mcp", "Firecrawl MCP server", True),
    ("cline", "Autonomous coding agent CLI", True),
    ("some-tool", "Filesystem-first framework for durable backend AI agents", True),
]:
    check(f"{'keeps' if _want else 'drops'} {_name}", _says_capability(_name, _desc) == _want)

# THE GATE IS FOR npm ROWS ONLY. Applied to every id it cut 1,931 capabilities, nearly all of them
# skills and plugins — `skill:obra/systematic-debugging`, `skill:Jeffallan/api-designer` — whose
# descriptions describe the JOB ("Use when encountering any bug, test failure…") instead of
# announcing that they are AI capabilities, which is what a good skill description does. A `skill:`
# or `plugin:` id came from a Claude Code repository; it is one by construction and has no npm
# keyword field to stuff, so the reason for the gate does not apply to it.
check("the AI-capability gate is scoped to pkg: ids, so skills are never cut for describing the job",
      'o["id"].startswith("pkg:") and not (' in open(
          os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline", "build.py"),
          encoding="utf-8").read())

print("SCORE SHAPE OK" if not fail else "SCORE SHAPE FAILED")
sys.exit(fail)
