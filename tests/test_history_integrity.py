#!/usr/bin/env python3
"""The paid series must contain the capability's movement, not ours.

`signal_history` is the only asset that cannot be re-derived, and it is what Pro sells. Its one
failure mode is silent: if the scorer changes without SCORER_VERSION changing, every point before and
after the change lands in the same comparable window, and `trend()` reports OUR recalibration as the
capability rising or falling. A customer is then paying to be misinformed about the one thing they
cannot check.

THIS HAPPENED. Between 28 and 29 July 2026 the scale was stretched, and both days are labelled `s1`:

      score on 28 Jul     n     median change
            10–19       111          -1.0
            20–29       955          -1.0
            30–39     1,253          -1.0
            40–49     1,490          -1.0
            50–59       511          +0.0
            60–69       128          +5.0
            70–79        17          +6.0
            80–89         7          +7.0

@supabase/mcp-server-supabase went 85 → 99 and firecrawl-mcp 75 → 93 overnight. A recalibration moves
whole bands in order; real churn does not sort itself by score. SCORER_VERSION was bumped to `s2` the
NEXT day, so the break sits inside a window the code believes is comparable.

WHY tests/test_scorer_version.py DID NOT CATCH IT. That test fingerprints compute_scores() from its
source text, so it fails when the code changes and asks a human to bump the version. It cannot see a
recalibration that arrives through data, a config value, or a changed input — and it cannot fire at
all if the suite is not run between the change and the commit. This checks the OUTPUT instead, which
is where the damage actually appears.

Run: python3 tests/test_history_integrity.py
"""
import collections, os, sqlite3, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "tashan.db")

# A recalibration shows up as band-ordered drift. Real churn is noisy across bands, so the signal is
# the SPREAD between what happened to the bottom of the distribution and the top on the same night.
SPREAD_MAX = 4.0       # points between the lowest and highest band's median change
MIN_PER_BAND = 20      # ignore bands too thin to have a meaningful median

fail = 0


def ok(name, cond, detail=""):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  — " + detail) if detail and not cond else ""))


def main():
    if not os.path.exists(DB):
        print("  --   no data/tashan.db — nothing to check")
        return 0
    con = sqlite3.connect(DB)
    try:
        scores = collections.defaultdict(dict)
        version = {}
        for cap_id, at, val, sc in con.execute(
                "SELECT cap_id, at, value, scorer FROM signal_history WHERE metric='tashan_score'"):
            scores[at][cap_id] = val
            version[at] = sc
    finally:
        con.close()

    days = sorted(scores)
    if len(days) < 2:
        print(f"  --   only {len(days)} day(s) of history — nothing to compare yet")
        return 0

    print(f"  {len(days)} days of history, {len(set(version.values()))} scorer version(s)\n")
    suspect = []
    for a, b in zip(days, days[1:]):
        if version.get(a) != version.get(b):
            print(f"  --   {a} -> {b}: scorer {version.get(a)} -> {version.get(b)}, "
                  f"correctly fenced, not compared")
            continue
        common = set(scores[a]) & set(scores[b])
        if len(common) < 200:
            continue
        bands = collections.defaultdict(list)
        for c in common:
            bands[min(int(scores[a][c] // 10) * 10, 90)].append(scores[b][c] - scores[a][c])
        meds = {k: statistics.median(v) for k, v in bands.items() if len(v) >= MIN_PER_BAND}
        if len(meds) < 3:
            continue
        spread = max(meds.values()) - min(meds.values())
        lo, hi = meds[min(meds)], meds[max(meds)]
        if spread > SPREAD_MAX:
            suspect.append((a, b, version.get(a), spread, lo, hi, len(common)))

    ok("no day-over-day shift inside one scorer version looks like a recalibration",
       not suspect,
       "; ".join(f"{a}->{b} (both '{v}'): the bottom band moved {lo:+.1f} and the top {hi:+.1f}, "
                 f"spread {sp:.1f} over {n:,} shared capabilities — bump SCORER_VERSION or explain it"
                 for a, b, v, sp, lo, hi, n in suspect))

    # And the number a customer is actually sold: how much comparable history exists right now.
    newest = version[days[-1]]
    comparable = sum(1 for d in days if version[d] == newest)
    print(f"\n  comparable history under the current scorer ({newest}): {comparable} day(s)")
    if comparable < 3:
        print(f"        trend() needs 3 and will correctly say so — but Pro's 'every score since we")
        print(f"        started measuring' currently delivers nothing. See docs/FEATURE-AUDIT.md.")

    # ---- the collector must survive its own failures --------------------------------------------
    # Four days are missing from the record — 07-26, 07-31, 08-02, 08-07 — and none of them were
    # lost to a bad measurement. The pipeline step had no continue-on-error, so a crash in any of the
    # five source stages that run BEFORE the snapshot failed the job, skipped the commit, and took
    # the day with it. The workflow had already learned this lesson for the test suite and not for
    # itself. These are text checks on purpose: the repo is stdlib-only and has no YAML parser, and
    # a grep that fails loudly beats a dependency.
    wf = open(os.path.join(ROOT, ".github", "workflows", "daily.yml"), encoding="utf-8").read()
    pipeline_step = wf.split("- name: Run the pipeline")[1].split("- name:")[0]
    ok("a crashing pipeline cannot fail the job before the day is recorded",
       "continue-on-error: true" in pipeline_step and "id: pipeline" in pipeline_step)
    ok("the snapshot runs even when everything above it failed",
       "if: always()" in wf.split("- name: Snapshot the series")[1].split("- name:")[0])
    ok("the commit runs even when everything above it failed",
       "if: always()" in wf.split("- name: Commit the day")[1].split("run:")[0])
    ok("nothing is published from a crashed pipeline",
       "steps.pipeline.outcome == 'success'" in wf.split("- name: Deploy")[1].split("run:")[0])

    # The DB is a cache of data/history and drifts from it whenever a night commits shards without
    # the DB. Reconciling must be automatic, not a thing someone remembers after noticing.
    snap = open(os.path.join(ROOT, "pipeline", "snapshot_history.py"), encoding="utf-8").read()
    ok("the DB is reconciled from the shards on every run, not just after a disaster",
       "def restore(" in snap and "restore(con)" in snap.split("def main(")[1])

    # ---- the repository must still accept the commit ------------------------------------------
    # None of the above matters if the push is refused. GitHub rejects any blob at 100 MiB and
    # data/tashan.db was 98 MiB on 8 Aug 2026, growing nightly — and a rejected push means no shard
    # lands, which is the exact loss everything else here exists to prevent. The daily workflow
    # withholds the DB near the wall so the series still gets committed; this fails the suite before
    # it comes to that, because the real fix (git-lfs, or splitting the 0.72 MB of essential state
    # out of a 98 MiB binary) is a decision, not a thing to discover from a red CI run.
    mib = os.path.getsize(DB) / 1048576 if os.path.exists(DB) else 0
    if mib >= 90:
        print(f"        data/tashan.db is {mib:.0f} MiB — GitHub refuses a blob at 100 MiB. "
              f"cap_state + sync_state gzip to 0.72 MB; the rest is cache.")
    # Fails only where the push genuinely cannot succeed. A tighter bound would block every local
    # commit through the pre-commit hook — including the commit that fixes this — which is a worse
    # outcome than the wall itself. The warning above is what does the forcing.
    ok(f"data/tashan.db ({mib:.1f} MiB) can still be pushed", mib < 99.5,
       "at 100 MiB GitHub rejects the push and the daily loop stops recording")

    print("\nHISTORY INTEGRITY FAILED" if fail else "\nok — the paid series carries the capability's movement, not ours")
    return fail


if __name__ == "__main__":
    sys.exit(main())
