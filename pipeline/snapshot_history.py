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

The DB stays out of git (see .gitignore). These shards ARE the durable record: to rebuild the series
on a fresh machine, read them back with load() below.

Stdlib only. Idempotent. Runs in the daily loop, right after scoring, so a crash in a later stage
can never cost a day.

    python3 pipeline/snapshot_history.py             # write any missing shards
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


def main():
    if not os.path.exists(DB):
        print("no data/tashan.db — nothing to snapshot"); return 0
    os.makedirs(OUT, exist_ok=True)
    con = sqlite3.connect(DB)
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
    print("ok — signal_history shards round-trip, are byte-stable, and tolerate empty days")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
