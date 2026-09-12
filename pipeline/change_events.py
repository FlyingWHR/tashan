#!/usr/bin/env python3
"""tashan — normalised CHANGE EVENTS: what changed about a capability, why it matters, what to do.

WHY THIS EXISTS. Everything else on this site answers "what is true today". That is a question a
reader asks once, fixes, and never pays for again — which is exactly why the subscription was weak:
it sold a static fact (the advisory detail) that has since, correctly, become free. The recurring
product is not the state, it is the DELTA. A capability you vetted in March and a capability you
vetted in March that quietly added an install script in July are different risks, and nothing on the
internet tells you the second one happened.

signal_history already accrues daily but carries only two REAL-valued metrics (tashan_score,
adoption), so it can express "the score moved" and nothing else — not a new advisory, not a widened
permission surface, not a maintainer walking away. Those are the changes worth an alert, and most of
them are strings or sets. Hence a state snapshot per capability plus a diff, rather than more rows in
a numeric time series.

    cap_state      one JSON row per capability per run — the watchable signals, as they were
    change_events  the diff between consecutive states, one row per transition

THREE FIELDS OR IT IS NOISE. A warning that says "something changed" trains people to ignore it, so
every event carries what changed, why that matters, and what to do about it. That is the difference
between a monitoring product and a diff.

FIRST RUN EMITS NOTHING, by construction: with no previous state there is no transition, and
inventing events for the initial snapshot would open the product with a wall of false alarms.

    python3 pipeline/change_events.py            # snapshot + diff + store
    python3 pipeline/change_events.py --dry-run  # show what would be emitted, write nothing
    python3 pipeline/change_events.py --report   # what changed most recently
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build

# The signals worth waking someone up for. Deliberately NOT the whole row: a description edit or a
# star count drifting by three is not an event, and every field here has to survive the "would a
# competent engineer want to be told?" test.
WATCHED = ("vitality", "npm_deprecated", "gh_archived", "self_unmaintained", "npm_latest_version",
           "npm_maintainers", "npm_maint_fp", "sec_advisory_count", "sec_max_severity", "sec_install_script",
           "sec_permissions", "tashan_score",
           # NOT a signal anyone is alerted about — it records whether the L1-L4 fields above were
           # ever LOOKED AT. Without it, an unscanned capability's NULL install script is
           # indistinguishable from an observed absence, and the first scan of a package reads as
           # the package changing. See SEC_FIELDS below.
           "sec_scanned_at")

SEV_ORDER = {None: 0, "": 0, "LOW": 1, "MODERATE": 2, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4,
             "MALICIOUS": 5}

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS cap_state (
         cap_id TEXT NOT NULL, at TEXT NOT NULL, state TEXT NOT NULL,
         PRIMARY KEY (cap_id, at))""",
    """CREATE TABLE IF NOT EXISTS change_events (
         cap_id TEXT NOT NULL, at TEXT NOT NULL, kind TEXT NOT NULL,
         severity TEXT, what TEXT, why TEXT, action TEXT,
         PRIMARY KEY (cap_id, at, kind))""",
    "CREATE INDEX IF NOT EXISTS idx_events_at ON change_events(at)",
    "CREATE INDEX IF NOT EXISTS idx_events_cap ON change_events(cap_id)",
]


def _perms(v):
    """sec_permissions ships as a JSON list or a string; compare as a set either way."""
    if not v:
        return set()
    try:
        return set(json.loads(v) if isinstance(v, str) else v)
    except (ValueError, TypeError):
        return set()


# UNKNOWN IS NOT ZERO, and this is where that cost the most.
#
# Every field the security scan writes is NULL until the scan reaches that package. The scan walks
# the corpus over days, so on the day it first reaches something, `sec_install_script` goes NULL ->
# "node install.js" and the old diff read that as THE PACKAGE ADDED AN INSTALL SCRIPT. It published
# 143 such alerts on 10 Aug, 110 on 11 Aug, 35 on 12 Aug, then 1 and 1 — the decay curve of a
# scanner sweeping a corpus, not of the world changing. /changes.html told the public that 301
# packages "started running a script at install time" when ~289 of them had simply been examined for
# the first time.
#
# That is the worst failure mode this instrument has. A false security alarm from the thing that
# exists to stop false security alarms costs more than saying nothing, and it is exactly what a
# subscriber would be paying to receive.
#
# So: a security transition requires that the PREVIOUS state was itself observed. Anything derived
# from the L1-L4 scan is withheld until we have two real observations to compare.
SEC_FIELDS = ("sec_advisory_count", "sec_max_severity", "sec_install_script", "sec_permissions")


def diff(prev, cur, name):
    """Every transition between two states, as (kind, severity, what, why, action).

    Ordered most-alarming first so a digest that truncates still leads with the thing that matters.
    """
    out = []
    g = lambda k: (prev.get(k), cur.get(k))
    # Was the security scan's output ever observed for this capability before now? A state snapshot
    # written before sec_scanned_at joined WATCHED has no key at all, which is correctly falsy — one
    # quiet run while the field backfills beats a wave of invented alerts.
    sec_known = bool(prev.get("sec_scanned_at"))

    # --- security: the reason someone subscribes -------------------------------------------------
    was, now = g("sec_advisory_count")
    if sec_known and (now or 0) > (was or 0):
        out.append(("advisory_new", "high",
                    f"{name} now has {now} known advisor{'y' if now == 1 else 'ies'}, up from {was or 0}",
                    "A published advisory means someone has demonstrated a way this can be abused.",
                    "Open the dossier for the advisory id and the version that fixes it, then upgrade."))
    elif sec_known and (was or 0) > (now or 0) and (now or 0) == 0:
        out.append(("advisory_cleared", "info",
                    f"{name} no longer has any known advisory",
                    "The finding that was open against it has been resolved upstream.",
                    "No action needed. Worth noting if you pinned an old version to avoid it."))

    was, now = g("sec_max_severity")
    if sec_known and SEV_ORDER.get(now, 0) > SEV_ORDER.get(was, 0):
        out.append(("severity_raised", "critical" if now in ("CRITICAL", "MALICIOUS") else "high",
                    f"the worst advisory against {name} is now {now}, was {was or 'none'}",
                    "The severity ceiling rose, so the worst case for this dependency got worse.",
                    "Re-check whether you still accept this risk at its new level."))

    was, now = g("sec_install_script")
    if sec_known and now and not was:
        out.append(("install_script_added", "high",
                    f"{name} now runs a script when it installs",
                    "Install-time code executes on your machine before you have used the tool once, "
                    "and it did not do this before.",
                    "Read the command on the dossier — it is free — before your next install or CI run."))
    elif sec_known and was and now and was != now:
        out.append(("install_script_changed", "high",
                    f"the command {name} runs at install time changed",
                    "The code that executes on your machine is not the code you last approved.",
                    "Compare the new command on the dossier against what you accepted."))

    gained = _perms(cur.get("sec_permissions")) - _perms(prev.get("sec_permissions"))
    if sec_known and gained:
        out.append(("permissions_widened", "high",
                    f"{name} now reaches {', '.join(sorted(gained))}",
                    "Its declared dependencies reach further into your machine than they did before.",
                    "Confirm the new reach is something this tool should have."))

    # --- the project stopping ---------------------------------------------------------------------
    if cur.get("self_unmaintained") and not prev.get("self_unmaintained"):
        out.append(("declared_unmaintained", "high",
                    f"the author of {name} has declared it unmaintained",
                    "Nobody is going to fix the next problem with this, including a security one.",
                    "Plan a replacement. The dossier links what else does this work."))
    if cur.get("npm_deprecated") and not prev.get("npm_deprecated"):
        out.append(("deprecated", "high", f"{name} was marked deprecated on npm",
                    "The publisher is telling installers to stop using it.",
                    "Move to the successor named in the deprecation notice."))
    if cur.get("gh_archived") and not prev.get("gh_archived"):
        out.append(("archived", "medium", f"the repository for {name} was archived",
                    "The source is now read-only: no fixes, no releases, no issues.",
                    "Treat it as finished. Fine if it works; risky if you need it to change."))

    was, now = g("vitality")
    if was and now and was != now and now == "abandoned":
        out.append(("abandoned", "medium", f"{name} now reads as abandoned, was {was}",
                    "Upkeep signals stopped, under enough issue pressure that it is not merely finished.",
                    "Check whether an alternative is better maintained before you depend on it further."))

    # --- who is behind it -------------------------------------------------------------------------
    # OWNERSHIP CHANGED — the same number of maintainers, different people. This is how event-stream
    # and ua-parser-js happened: nobody dropped, somebody was ADDED, and the count never moved. The
    # count-based check below cannot see it by construction.
    #
    # Only fires when both sides are known: a first sighting has nothing to compare against, and
    # reporting one as a handoff would alarm somebody about a package that simply entered the index.
    was_fp, now_fp = g("npm_maint_fp")
    if was_fp and now_fp and was_fp != now_fp:
        out.append(("ownership_changed", "high",
                    f"{name} has a different set of npm maintainers than it did",
                    "Who can publish this package changed — the classic supply-chain handoff, and "
                    "invisible to a maintainer count that did not move.",
                    "Pin the version you have audited and read the next release's diff before taking it."))

    was, now = g("npm_maintainers")
    if was and now and now < was and now <= 1:
        out.append(("maintainers_dropped", "medium",
                    f"{name} is down to {now} maintainer, from {was}",
                    "Bus factor of one: one person's availability now decides this dependency's future.",
                    "Note the risk; prefer an alternative with more hands for anything load-bearing."))

    # --- routine, still worth a line --------------------------------------------------------------
    was, now = g("npm_latest_version")
    if was and now and was != now:
        out.append(("version_published", "info", f"{name} published {now}, was {was}",
                    "A new release is available.",
                    "Upgrade at your convenience; check the advisory row first if one is open."))

    was, now = g("tashan_score")
    if was is not None and now is not None and abs(now - was) >= 5:
        d = "rose" if now > was else "fell"
        out.append(("score_moved", "info", f"the tashan score for {name} {d} to {now}, from {was}",
                    "Upkeep, freshness or adoption moved enough to change how this measures.",
                    "Informational. A sustained fall is the early shape of abandonment."))
    return out


def latest_state(con, cap_id, before):
    r = con.execute("SELECT state FROM cap_state WHERE cap_id=? AND at<? ORDER BY at DESC LIMIT 1",
                    (cap_id, before)).fetchone()
    return json.loads(r[0]) if r else None


def run(con, dry=False):
    for stmt in SCHEMA:
        con.execute(stmt)
    now = build.datetime.now(build.timezone.utc).isoformat()
    rows = con.execute("SELECT id, name, " + ", ".join(WATCHED) + " FROM capabilities").fetchall()
    events, snapped, first = [], 0, 0
    for r in rows:
        cap_id, name = r[0], r[1]
        cur = dict(zip(WATCHED, r[2:]))
        prev = latest_state(con, cap_id, now)
        if prev is None:
            first += 1
        else:
            for kind, sev, what, why, action in diff(prev, cur, name or cap_id):
                events.append((cap_id, now, kind, sev, what, why, action))
        if not dry:
            con.execute("INSERT OR REPLACE INTO cap_state VALUES (?,?,?)",
                        (cap_id, now, json.dumps(cur, sort_keys=True)))
        snapped += 1
    if not dry:
        con.executemany("INSERT OR REPLACE INTO change_events VALUES (?,?,?,?,?,?,?)", events)
        con.commit()
    by_kind = {}
    for e in events:
        by_kind[e[2]] = by_kind.get(e[2], 0) + 1
    print(f"  {snapped:,} capabilities snapshotted · {first:,} seen for the first time (no baseline "
          f"to diff, so no events) · {len(events):,} change events")
    for k, n in sorted(by_kind.items(), key=lambda kv: -kv[1]):
        print(f"    {k:24} {n}")
    return len(events)


def report(con):
    rows = con.execute(
        "SELECT at, kind, severity, what, action FROM change_events ORDER BY at DESC LIMIT 25").fetchall()
    if not rows:
        print("no change events yet — this needs two runs on different days to have a delta")
        return 0
    for at, kind, sev, what, action in rows:
        print(f"  [{sev:8}] {at[:10]}  {kind:22} {what}")
        print(f"             -> {action}")
    return 0


def _selfcheck():
    """The diff must fire on the transitions people subscribe for, and stay silent otherwise."""
    base = {"sec_advisory_count": 0, "sec_max_severity": None, "sec_install_script": None,
            "sec_permissions": None, "npm_deprecated": 0, "gh_archived": 0,
            "self_unmaintained": None, "npm_maintainers": 3, "npm_latest_version": "1.0.0",
            "vitality": "active", "tashan_score": 70,
            # base models a capability we have ALREADY scanned — the ordinary case. The
            # never-scanned case is exercised separately below, and must stay silent.
            "sec_scanned_at": "2026-08-01T00:00:00Z"}
    assert diff(base, base, "x") == [], "an unchanged capability must produce no events"

    # THE FIRST SCAN IS NOT A CHANGE. Without sec_scanned_at in the previous state, every security
    # field is unobserved, and a NULL install script must not be read as an observed absence. This
    # published 301 false "started running a script at install time" alerts before it was caught.
    # Never scanned: every security field NULL *and* no scan timestamp. Nulling the fields alone
    # would leave sec_scanned_at set and quietly test the wrong thing.
    unseen = dict(base, sec_scanned_at=None)
    unseen.update({f: None for f in SEC_FIELDS})
    first_look = dict(unseen, sec_install_script="node install.js", sec_advisory_count=2,
                      sec_max_severity="HIGH", sec_scanned_at="2026-08-10T00:00:00Z")
    assert diff(unseen, first_look, "x") == [], \
        "a package examined for the first time must emit NO security event"

    # ...but once observed, a REAL addition must still fire. Over-suppressing would silently delete
    # the alert people subscribe for, which is the same failure wearing the opposite mask.
    seen_clean = dict(unseen, sec_scanned_at="2026-08-10T00:00:00Z")
    kinds = {e[0] for e in diff(seen_clean, first_look, "x")}
    assert "install_script_added" in kinds, kinds
    assert "advisory_new" in kinds and "severity_raised" in kinds, kinds
    # A changed script, between two observed states, still fires.
    was = dict(seen_clean, sec_install_script="node a.js")
    now2 = dict(was, sec_install_script="node b.js", sec_scanned_at="2026-08-12T00:00:00Z")
    assert "install_script_changed" in {e[0] for e in diff(was, now2, "x")}
    # Non-security signals are NOT gated — deprecation does not depend on the advisory scan.
    assert "deprecated" in {e[0] for e in diff(unseen, dict(unseen, npm_deprecated=1), "x")}

    got = {e[0] for e in diff(base, dict(base, sec_advisory_count=1, sec_max_severity="HIGH"), "x")}
    assert {"advisory_new", "severity_raised"} <= got, got

    got = {e[0] for e in diff(base, dict(base, sec_install_script="node evil.js"), "x")}
    assert "install_script_added" in got, got

    got = {e[0] for e in diff(dict(base, sec_permissions='["files"]'),
                              dict(base, sec_permissions='["files","network"]'), "x")}
    assert "permissions_widened" in got, got
    # narrowing is not a risk event
    got = {e[0] for e in diff(dict(base, sec_permissions='["files","network"]'),
                              dict(base, sec_permissions='["files"]'), "x")}
    assert "permissions_widened" not in got, got

    got = {e[0] for e in diff(base, dict(base, npm_maintainers=1), "x")}
    assert "maintainers_dropped" in got, got
    # A handoff with no change in headcount must still fire — that is the whole point.
    same_count = {e[0] for e in diff(dict(base, npm_maint_fp="aaa"),
                                     dict(base, npm_maint_fp="bbb"), "x")}
    assert "ownership_changed" in same_count, same_count
    assert "maintainers_dropped" not in same_count, same_count
    # A first sighting has nothing to compare against and must not be reported as a handoff.
    first = {e[0] for e in diff(dict(base, npm_maint_fp=None),
                                dict(base, npm_maint_fp="bbb"), "x")}
    assert "ownership_changed" not in first, first
    # a drop that still leaves a team is not a bus-factor alert
    assert "maintainers_dropped" not in {e[0] for e in diff(dict(base, npm_maintainers=9),
                                                            dict(base, npm_maintainers=4), "x")}
    # score noise below the threshold stays quiet
    assert diff(base, dict(base, tashan_score=73), "x") == []
    assert {e[0] for e in diff(base, dict(base, tashan_score=61), "x")} == {"score_moved"}

    # EVERY event is well-formed, including the branches nothing above exercises.
    #
    # This check exists because `ownership_changed` shipped with four fields instead of five and
    # took the daily pipeline down for twelve days — every run from 1 September crashed on
    # `for kind, sev, what, why, action in diff(...)`, so the site went stale and signal_history,
    # the one series that cannot be backfilled, recorded retention and nothing else.
    #
    # The assertions above did not catch it because they all read e[0], the kind. The event fired
    # correctly; it was simply malformed, and a set of kinds cannot see a missing column. So this
    # reads the SOURCE rather than the output: a branch that never fires in a test still has to be
    # the right shape, and there is no state pair that exercises all fourteen.
    import ast as _ast
    _fn = next(n for n in _ast.walk(_ast.parse(open(__file__).read()))
               if isinstance(n, _ast.FunctionDef) and n.name == "diff")
    _bad = [(c.lineno, len(c.args[0].elts)) for c in _ast.walk(_fn)
            if isinstance(c, _ast.Call) and getattr(c.func, "attr", None) == "append"
            and isinstance(c.args[0], _ast.Tuple) and len(c.args[0].elts) != 5]
    assert not _bad, f"diff() appends a non-5-tuple at line(s) {_bad} — the consumer unpacks five"

    # and what the branches we CAN drive actually produce
    for _ev in diff(base, dict(base, npm_maint_fp="zzz", npm_deprecated=1, gh_archived=1,
                               npm_latest_version="9.9.9", tashan_score=20), "x"):
        assert len(_ev) == 5, f"event is not a 5-tuple: {_ev}"
        assert all(isinstance(f, str) and f.strip() for f in _ev), f"event has an empty field: {_ev}"


def main():
    _selfcheck()
    con = build.db()
    if "--report" in sys.argv:
        return report(con)
    return 0 if run(con, dry="--dry-run" in sys.argv) >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
