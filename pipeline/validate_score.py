#!/usr/bin/env python3
"""Does the tashan score predict anything? Asked of our own product, answered with the series.

    python3 pipeline/validate_score.py            # the analysis, against the live database
    python3 pipeline/validate_score.py --selftest # the arithmetic, no database

WHY ASK. The score is the product, and until now the only defence of it was that its inputs are
public and its weights are written down. That is a defence of TRANSPARENCY, not of VALIDITY: a
transparent number can still predict nothing. The retention series finally makes the question
answerable — we have a score recorded on a date, and events recorded after it.

CIRCULARITY IS THE WHOLE METHODOLOGICAL PROBLEM, so the outcome set is chosen to avoid it.
`deprecated`, `abandoned`, `archived` and `score_moved` are all downstream of scorer inputs
(npm_deprecated, vitality, freshness) — "the score predicts abandonment" would be arithmetic, not a
finding. Security is different: CLAUDE.md states security columns are deliberately NOT inputs to
tashan_score, and tests/test_firewall.py enforces it. So a security event after the baseline is a
genuinely independent outcome.

WHAT IT FOUND (first run, 17 Aug 2026, 23 days of series, 15,795 capabilities):

  Raw association looked dramatic and was mostly an artefact.

      score 0-39    0.06% had a security event      score 70-84   14.09%
                                                    — a 235x spread

  But a dormant package cannot add an install script, because it never ships. Conditioning on
  having published a release — everyone who actually had the OPPORTUNITY — the effect collapses:

      0-39  0.0%    40-54  1.4%    55-69  1.2%    70-84  6.6%    85+  0.0%      (10 events, 573 shippers)

  What the score DOES predict, strongly, is liveness — which is what it claims to measure:

      shipped a release: 0.3% (score 0-39) -> 24.0% (55-69) -> 28.6% (85+)      (~80x)

TWO CONCLUSIONS, and the second is the one a reader needs:

  1. The score is doing its stated job. It is a measure of upkeep and freshness gated by adoption,
     and it separates capabilities that are alive from ones that are not by roughly eighty-fold.
  2. A LOW SCORE DOES NOT MEAN SAFE. It usually means nothing is happening — including nothing
     being observed. The apparent "high scores are riskier" finding is detection bias: risk is
     visible where there is change, and change is what a high score measures.

We cannot yet say whether the score predicts security risk once activity is held constant. Ten
events across 573 shippers is not enough to say anything, and this file says so rather than
rounding a null into a headline. Re-run it as the series grows.
"""
import os, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "tashan.db")

# Outcomes that are NOT scorer inputs. Anything derived from npm_deprecated, vitality, freshness or
# the score itself is excluded — predicting those from the score is arithmetic, not evidence.
INDEPENDENT = ("install_script_added", "install_script_changed", "advisory_new", "severity_raised")
EXPOSURE = ("version_published",)      # you can only change what you ship
BANDS = [(0, 40), (40, 55), (55, 70), (70, 85), (85, 101)]
MIN_EVENTS = 30                        # below this, a rate is a rumour


def baselines(con):
    """Each capability's earliest recorded score, with the date. That date is the dividing line:
    only events AFTER it can be an outcome, or we are reading the future into the past."""
    return {cid: (at[:10], val) for cid, at, val in con.execute(
        "SELECT cap_id, MIN(at), value FROM signal_history WHERE metric='tashan_score' "
        "GROUP BY cap_id")}


def events_after(con, base, kinds):
    got = set()
    q = "SELECT cap_id, at FROM change_events WHERE kind IN (%s)" % ",".join("?" * len(kinds))
    for cid, at in con.execute(q, kinds):
        b = base.get(cid)
        if b and at[:10] > b[0]:
            got.add(cid)
    return got


def rates(base, subject, universe=None):
    """(band, n, events, rate) per score band. `universe` restricts the denominator."""
    out = []
    for lo, hi in BANDS:
        ids = [i for i, (d, v) in base.items()
               if v is not None and lo <= v < hi and (universe is None or i in universe)]
        n = len(ids)
        e = sum(1 for i in ids if i in subject)
        out.append((f"{lo}-{hi - 1}", n, e, (e / n) if n else 0.0))
    return out


def spread(rows):
    """Ratio between the highest and lowest non-zero rate over bands with a usable n."""
    r = [x[3] for x in rows if x[1] >= 50 and x[3] > 0]
    return (max(r) / min(r)) if len(r) > 1 else None


def table(title, rows, note=""):
    print(f"\n  {title}")
    print(f"  {'band':10} {'n':>9} {'events':>9} {'rate':>8}")
    for band, n, e, r in rows:
        print(f"  {band:10} {n:9,} {e:9,} {100 * r:7.2f}%")
    tot_n, tot_e = sum(x[1] for x in rows), sum(x[2] for x in rows)
    print(f"  {'ALL':10} {tot_n:9,} {tot_e:9,} {100 * tot_e / max(tot_n, 1):7.2f}%")
    if note:
        print(f"  {note}")
    return tot_e


def main():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    base = baselines(con)
    if not base:
        print("  no series yet — nothing to validate")
        return 0
    sec = events_after(con, base, INDEPENDENT)
    shipped = events_after(con, base, EXPOSURE)
    con.close()

    span = (min(d for d, _ in base.values()), max(d for d, _ in base.values()))
    print(f"\n  baseline scores for {len(base):,} capabilities, first recorded {span[0]}")
    print(f"  outcome window: everything after each capability's own baseline date")

    n_sec = table("RAW — security event after baseline, by score band", rates(base, sec),
                  "security events are NOT scorer inputs, so this is not circular")
    sp = spread(rates(base, sec))
    if sp:
        print(f"  spread across bands: {sp:.0f}x")

    table("EXPOSURE — did it ship a release at all?", rates(base, shipped),
          "this is the score doing its stated job: separating alive from dormant")

    cond = rates(base, sec, universe=shipped)
    n_cond = table("CONDITIONED — security events among capabilities that DID ship", cond,
                   "everyone here had the opportunity; the raw effect above largely collapses")

    print("\n  READING:")
    print("  - The score predicts LIVENESS strongly, which is what it claims to measure.")
    print("  - A LOW SCORE DOES NOT MEAN SAFE. It usually means nothing is happening — including")
    print("    nothing being observed. Risk is visible where there is change.")
    if n_cond < MIN_EVENTS:
        print(f"  - UNDERPOWERED: {n_cond} events among shippers, below the {MIN_EVENTS} this file")
        print("    treats as a floor. No claim is made about whether the score predicts security")
        print("    risk once activity is held constant. Re-run as the series grows.")
    else:
        print(f"  - {n_cond} events among shippers: enough to read the conditioned table above.")
    return 0


def _selftest():
    b = {f"c{i}": ("2026-07-23", float(i % 100)) for i in range(1000)}
    subj = {f"c{i}" for i in range(0, 1000, 10)}
    rs = rates(b, subj)
    assert sum(x[1] for x in rs) == 1000, rs
    assert sum(x[2] for x in rs) == len(subj), rs
    # A restricted universe must shrink BOTH the denominator and the numerator.
    uni = {f"c{i}" for i in range(500)}
    ru = rates(b, subj, universe=uni)
    assert sum(x[1] for x in ru) == 500
    assert sum(x[2] for x in ru) == len(subj & uni)
    # spread() must ignore bands too small to mean anything, and never divide by zero.
    assert spread([("a", 10, 1, 0.1), ("b", 10, 0, 0.0)]) is None, "tiny bands must not produce a ratio"
    assert spread([("a", 100, 1, 0.01), ("b", 100, 10, 0.10)]) == 10.0
    assert spread([]) is None
    # The circularity exclusion is the method. If someone adds a scorer-derived outcome here, the
    # whole result becomes arithmetic — so the list is asserted, not just commented.
    for banned in ("deprecated", "abandoned", "archived", "score_moved", "version_published"):
        assert banned not in INDEPENDENT, banned
    print("validate_score selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
