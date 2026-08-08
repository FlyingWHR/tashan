#!/usr/bin/env python3
"""tashan — write signal_history to committed daily shards.

THE ONLY ASSET THAT CANNOT BE REBUILT. `signal_history` records one trust/adoption reading per
capability per day; "was added, then went quiet, then was removed" is a verdict you can only
ACCUMULATE. Miss a day and it is gone — not slow to recompute, gone.

It lived in exactly one place: an UNTRACKED 37 MB `data/tashan.db` on one laptop. The daily workflow
was supposed to be the backup and had never once succeeded, so the series was one disk failure from
zero. This stage is the fix, and it is deliberately the dumbest thing that works.

ONE GZIPPED CSV PER DAY, written once and never rewritten:

    data/history/2026-08-01.csv.gz

Shards, not one rolling file, because git stores a new blob every time a tracked file changes. A
single 3 MB CSV rewritten daily costs ~1 GB of objects a year; a write-once ~150 KB shard costs what
it says. Past days are skipped if present — only the newest day is re-written, since a same-day
re-run may have added rows to it.

These shards ARE the durable record; `data/tashan.db` is a cache of them. (An earlier version of this
docstring said the DB "stays out of git" — it is tracked, and has been for 116 commits. Verify with
`git ls-files data/tashan.db` before repeating either claim.)

THE RESTORE RUNS FIRST, EVERY TIME, and it is not a disaster-recovery path — it is routine
reconciliation. The daily workflow commits `data/history` on a red suite but withholds everything
else, the DB included. So a red night writes a shard and throws away the database rows behind it,
and the two records drift apart silently and permanently. On 8 Aug 2026 the shards held twelve days
and the committed DB held ten: 08-04 and 08-06 existed on disk as durable record while
`signal_history` had never heard of them.

That is not a cosmetic gap. `trend()` and the exported `retention` column read the DB, so the site
and the CLI were both understating the series against evidence sitting in the same repository —
`trend()` needs three points under one scorer and believed it had two. The paid endpoint was fine,
because push_history.py reads the shards directly, which is exactly why nobody noticed.

Stdlib only. Idempotent. Runs in the daily loop, right after scoring, so a crash in a later stage
can never cost a day.

    python3 pipeline/snapshot_history.py             # reconcile from shards, then write today
    python3 pipeline/snapshot_history.py --selftest  # round-trip check, no DB needed
"""
import csv, gzip, io, os, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "tashan.db")
OUT = os.path.join(ROOT, "data", "history")
COLS = ("cap_id", "metric", "value", "at", "scorer")


def write_day(con, day, out_dir):
    """Write one day's rows to <out_dir>/<day>.csv.gz. Returns the row count."""
    rows = con.execute(
        "SELECT cap_id, metric, value, at, scorer FROM signal_history "
        "WHERE substr(at,1,10)=? ORDER BY cap_id, metric", (day,)).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(COLS)
    w.writerows(rows)
    # mtime=0 so an unchanged day produces a byte-identical file — git sees no diff, no churn commit
    with gzip.GzipFile(os.path.join(out_dir, day + ".csv.gz"), "wb", mtime=0) as f:
        f.write(buf.getvalue().encode())
    return len(rows)


def load(out_dir=OUT):
    """Read every shard back as (cap_id, metric, value, at, scorer) tuples — the restore path."""
    out = []
    for fn in sorted(os.listdir(out_dir)):
        if not fn.endswith(".csv.gz"):
            continue
        with gzip.open(os.path.join(out_dir, fn), "rt") as f:
            for r in csv.DictReader(f):
                out.append((r["cap_id"], r["metric"], float(r["value"]), r["at"], r["scorer"]))
    return out


def restore(con, out_dir=OUT):
    """Put back any shard row the database is missing. Returns rows restored.

    Idempotent by (cap_id, metric, at): signal_history has no unique index, so this compares against
    what is already there rather than relying on the storage to refuse a duplicate. Re-running it
    inserts nothing.
    """
    if not os.path.isdir(out_dir):
        return 0
    have = {(r[0], r[1], r[2]) for r in
            con.execute("SELECT cap_id, metric, at FROM signal_history")}
    missing = [r for r in load(out_dir) if (r[0], r[1], r[3]) not in have]
    if missing:
        con.executemany("INSERT INTO signal_history (cap_id, metric, value, at, scorer) "
                        "VALUES (?,?,?,?,?)", missing)
        con.commit()
    return len(missing)


def main():
    if not os.path.exists(DB):
        print("no data/tashan.db — nothing to snapshot"); return 0
    os.makedirs(OUT, exist_ok=True)
    con = sqlite3.connect(DB)
    # RECONCILE BEFORE WRITING. A red-suite night commits the shard and discards the DB, so the
    # cache falls behind the record it is caching — and every reader except the paid endpoint goes
    # through the cache.
    back = restore(con)
    if back:
        print(f"  restored {back:,} row(s) the DB was missing from the shards")
    days = [r[0] for r in con.execute(
        "SELECT DISTINCT substr(at,1,10) FROM signal_history ORDER BY 1")]
    if not days:
        print("signal_history is empty — nothing to snapshot"); return 0
    newest = days[-1]
    wrote = skipped = 0
    for day in days:
        path = os.path.join(OUT, day + ".csv.gz")
        # past days are final; only the newest can still be growing within the same day
        if os.path.exists(path) and day != newest:
            skipped += 1
            continue
        n = write_day(con, day, OUT)
        wrote += 1
        print(f"  {day}  {n:>6} rows")
    print(f"history: {wrote} shard(s) written, {skipped} already final "
          f"-> data/history ({len(days)} days total)")
    return 0


def selftest():
    import tempfile
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE signal_history (cap_id TEXT, metric TEXT, value REAL, at TEXT, scorer TEXT)")
    src = [("pkg:a", "tashan_score", 92.0, "2026-08-01", "s4"),
           ("pkg:a", "adoption", 71.5, "2026-08-01", "s4"),
           ("pkg:b,quoted \"name\"", "tashan_score", 0.0, "2026-08-02", "s4")]
    con.executemany("INSERT INTO signal_history VALUES (?,?,?,?,?)", src)

    with tempfile.TemporaryDirectory() as d:
        for day in ("2026-08-01", "2026-08-02"):
            write_day(con, day, d)
        back = load(d)
        assert sorted(back) == sorted(src), f"round-trip lost or mangled rows:\n{back}\n{src}"

        # byte-stability: re-writing an unchanged day must not produce a new git blob
        p = os.path.join(d, "2026-08-01.csv.gz")
        first = open(p, "rb").read()
        write_day(con, "2026-08-01", d)
        assert open(p, "rb").read() == first, "re-write changed the bytes — every run would commit noise"

        # a day with no rows is a valid, empty shard, not a crash — and adds nothing on read-back
        assert write_day(con, "1999-01-01", d) == 0
        assert sorted(load(d)) == sorted(src)

        # restore(): a DB that lost a red-suite night gets it back from the shard, exactly once
        gap = sqlite3.connect(":memory:")
        gap.execute("CREATE TABLE signal_history "
                    "(cap_id TEXT, metric TEXT, value REAL, at TEXT, scorer TEXT)")
        gap.executemany("INSERT INTO signal_history VALUES (?,?,?,?,?)", src[:1])
        assert restore(gap, d) == 2, "the two rows the DB never saw must come back"
        assert restore(gap, d) == 0, "a second run must insert nothing — this runs every night"
        got = sorted(gap.execute("SELECT cap_id, metric, value, at, scorer FROM signal_history"))
        assert got == sorted(src), f"restore did not reproduce the record:\n{got}"
    print("ok — signal_history shards round-trip, are byte-stable, and tolerate empty days")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
