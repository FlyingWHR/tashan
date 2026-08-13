#!/usr/bin/env python3
"""tashan — keep data/tashan.db in Cloudflare R2 instead of in git.

    python3 pipeline/db_store.py pull       # fetch the cache before a run
    python3 pipeline/db_store.py push       # store it after a run
    python3 pipeline/db_store.py --selftest # no network, no credentials

WHY THE DATABASE LEFT GIT. It reached 98.8 MiB against GitHub's hard 100 MiB blob limit, and the
daily workflow commits it every night — so the failure would have arrived at `git push`, AFTER the
pipeline had done its work, and a rejected push means the day's history shard never lands. That is
the one loss the whole daily workflow exists to prevent. It had also grown to 255 MB of the pack
across 588 blobs, all of it a cache being re-derived every night.

IT IS NOT A DATABASE PROBLEM, so the answer is not a database. Nothing serves a request from
SQLite: the site is static JSON, the CLI reads an exported index, and the Pages Functions read KV.
Twenty-one pipeline scripts use it and they run one at a time, once a night, on one machine. There
is no concurrency to solve and no query to serve, so Postgres or D1 would add a network round trip
and a non-stdlib dependency to fix a problem that does not exist. What is actually needed is
somewhere other than git to keep a large binary that changes daily.

WHY R2 AND NOT LFS. LFS retains every version, so a 98 MiB nightly commit accrues ~2.9 GiB a month
against a 10 GB allowance — free for about three months, then a bill that only grows. R2 stores one
object that is overwritten: ~0.1 GB of a 10 GB free tier, 30 writes and 30 reads a month against
1M/10M free, and zero egress. The credentials are already in the daily workflow for the Pages
deploy.

WHAT IS LOST IF THE BUCKET IS. Not the moat. `signal_history` — the only un-backfillable asset — is
committed to git as `data/history/*.csv.gz` and `snapshot_history.restore()` rebuilds it on every
run. Losing the object costs one night of `change_events` (it emits nothing without a previous
state, by construction), a full registry re-walk instead of an incremental one, and a slow re-fetch
of `capability_text`. Each of those is a bad night, not a lost record. That is exactly why the
series is sharded as text and the cache is not.
"""
import os, re, subprocess, sqlite3, sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "tashan.db")
BUCKET = os.environ.get("TASHAN_DB_BUCKET", "tashan-state")
KEY = os.environ.get("TASHAN_DB_KEY", "tashan.db")
# A tiny sidecar object holding the generation of whatever is in the bucket, plus the local memory
# of which generation we last saw. Optimistic concurrency, and it exists because of a real incident:
# see push().
STAMP_KEY = KEY + ".stamp"
STAMP_LOCAL = os.path.join(ROOT, "data", ".db_store_stamp")
WRANGLER = ["npx", "--yes", "wrangler@3"]


def _run(args):
    """wrangler, with the proxy stripped.

    HTTPS_PROXY set in the environment makes wrangler's TLS connection reset — diagnosed once
    already in this repo and worth not re-diagnosing. The daily runner has no proxy; a laptop
    usually does.
    """
    # ALL_PROXY too, and that omission is why this is a list rather than two names: wrangler reads
    # every one of them, announces "Proxy environment variables detected", and then dies with a bare
    # `fetch failed` that reads exactly like R2 being switched off. The daily runner has no proxy, so
    # this only ever breaks on a laptop — the machine where you are trying to diagnose it.
    env = {k: v for k, v in os.environ.items()
           if k.lower() not in ("all_proxy", "https_proxy", "http_proxy")}
    # ONE RETRY, because a push failure is fatal by design and a blip should not be. Observed once:
    # a push died with a bare `fetch failed` and the identical command succeeded seconds later, with
    # no proxy involved (they are stripped above) — just the network. Losing a push means every
    # later run starts from a stale object, which is a whole day of enrichment, so paying two
    # seconds to rule out a transient is obviously worth it. Not a loop: if it fails twice it is not
    # transient, and quietly retrying a real outage only delays the error that has to be read.
    out = subprocess.run(WRANGLER + args, cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=900)
    if out.returncode != 0:
        time.sleep(2)
        out = subprocess.run(WRANGLER + args, cwd=ROOT, env=env,
                             capture_output=True, text=True, timeout=900)
    return out


def usable(path=DB):
    """Is this file actually a readable SQLite database with our data in it?

    A truncated download is a real failure mode and a silent one: the pipeline would open the
    fragment, find no rows, and re-derive everything from scratch as though it were a first run —
    which is how change_events would emit a full corpus of fabricated 'new capability' events.
    """
    if not os.path.exists(path) or os.path.getsize(path) < 4096:
        return False
    try:
        con = sqlite3.connect(path)
        n = con.execute("SELECT count(*) FROM capabilities").fetchone()[0]
        con.close()
        return n > 0
    except sqlite3.Error:
        return False


def _reason(r):
    """The line that explains the failure, not the last line printed.

    wrangler ends every failed command with the path to its log file, so taking the tail reported
    `Logs were written to ...` as the cause — true, useless, and exactly the kind of message that
    makes an operator open a log to learn something the tool already knew.
    """
    NOISE = ("Logs were written", "update to the latest version", "npm notice", "wrangler@",
             "If you think this is a bug", "🪵", "▲")
    lines = [re.sub(r"\x1b\[[0-9;]*m", "", l).strip()
             for l in ((r.stderr or "") + "\n" + (r.stdout or "")).splitlines()]
    lines = [l for l in lines if l and not any(n in l for n in NOISE)]
    # Cloudflare puts a machine-readable code on the line that actually says what went wrong.
    for want in ("[code:", "Please enable", "does not exist", "not found", "Unauthorized", "ERROR"):
        for l in lines:
            if want in l:
                return l.lstrip("✘ ")[:120]
    return (lines[0][:120] if lines else "no output")


def _remote_stamp():
    """The generation string currently in the bucket, or None if there is none / it cannot be read."""
    tmp = STAMP_LOCAL + ".remote"
    r = _run(["r2", "object", "get", f"{BUCKET}/{STAMP_KEY}", "--file", tmp])
    try:
        return open(tmp, encoding="utf-8").read().strip() if r.returncode == 0 else None
    except OSError:
        return None
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _write_stamp(value):
    with open(STAMP_LOCAL, "w", encoding="utf-8") as f:
        f.write(value)


def pull():
    """Fetch the cache. Never fatal: a missing object is a first run, and a failed fetch on a
    machine that already has a database is a reason to warn, not to stop measuring."""
    had = usable()
    tmp = DB + ".pull"
    r = _run(["r2", "object", "get", f"{BUCKET}/{KEY}", "--file", tmp])
    if r.returncode != 0 or not usable(tmp):
        if os.path.exists(tmp):
            os.remove(tmp)
        detail = [_reason(r)]
        if had:
            print(f"  db_store: keeping the local database — R2 fetch failed ({detail[0][:90]})")
            return 0
        print(f"  db_store: no cache in R2 and none on disk — this run rebuilds from the sources "
              f"and from data/history ({detail[0][:90]})")
        return 0
    os.replace(tmp, DB)
    # Remember which generation we started from, so push() can tell whether anyone moved it since.
    _write_stamp(_remote_stamp() or "")
    print(f"  db_store: pulled {os.path.getsize(DB) / 1048576:.1f} MiB from r2://{BUCKET}/{KEY}")
    return 0


def push():
    """Store the cache, plus a rolling dated copy. FATAL on failure, unlike pull: silently not
    saving means every later run starts from a stale object and the incremental cursors quietly
    stop advancing.

    ONE MUTABLE OBJECT IS NOT A BACKUP. `tashan.db` is overwritten in place every night, so a run
    that corrupts the database — or a bug in this file — replaces the only copy that exists now
    that it is out of git. The rolling weekday slot costs nothing extra in the free tier (7 x 99 MiB
    against 10 GB) and needs no bucket listing to prune, because tomorrow's run overwrites the slot
    from a week ago. `usable()` already refuses to upload a database with no rows, so a truncated
    local file cannot poison either copy.
    """
    if not usable():
        print("  db_store: refusing to push — data/tashan.db is missing or has no rows")
        return 1
    # REFUSE TO OVERWRITE SOMEONE ELSE'S NEWER STATE.
    #
    # On 9 Aug 2026 the nightly run finished at 17:59:10, pushed its database, and 41 seconds later
    # a laptop pushed a copy from earlier in the day straight over the top of it. One mutable object
    # and no check: the newer state was simply gone, and the only reason nothing was lost is that
    # data/security_cache.json and data/history/*.csv.gz are committed to git, so the database could
    # be rebuilt from them. That is a backup working by accident, not a design.
    #
    # So the bucket carries a generation stamp, pull() records which one it saw, and push() refuses
    # when the bucket has moved on since. TASHAN_DB_FORCE=1 overrides for the case where the local
    # copy really is the one you want.
    seen = open(STAMP_LOCAL, encoding="utf-8").read().strip() if os.path.exists(STAMP_LOCAL) else None
    remote = _remote_stamp()
    if remote and seen is not None and remote != seen and os.environ.get("TASHAN_DB_FORCE") != "1":
        print(f"  db_store: REFUSING to push — the bucket moved since this copy was pulled")
        print(f"            bucket is at {remote}, this machine last saw {seen or '(never pulled)'}")
        print(f"            run `db_store.py pull` first, or TASHAN_DB_FORCE=1 to overwrite it")
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "-" + str(os.getpid())
    mib = os.path.getsize(DB) / 1048576
    for key in (KEY, f"backup/{datetime.now(timezone.utc).strftime('%a').lower()}.db"):
        r = _run(["r2", "object", "put", f"{BUCKET}/{key}", "--file", DB,
                  "--content-type", "application/vnd.sqlite3"])
        if r.returncode != 0:
            if key != KEY:
                print(f"  db_store: pushed the live object; the dated copy failed ({_reason(r)})")
                return 0                       # the working copy landed; a missing backup is not fatal
            print("  db_store: PUSH FAILED — the next run will start from a stale cache")
            print("           " + _reason(r))
            return 1
        print(f"  db_store: pushed {mib:.1f} MiB to r2://{BUCKET}/{key}")
    # Stamp last: a reader that sees the new generation is guaranteed the object behind it landed.
    with open(STAMP_LOCAL + ".out", "w", encoding="utf-8") as f:
        f.write(stamp)
    if _run(["r2", "object", "put", f"{BUCKET}/{STAMP_KEY}", "--file", STAMP_LOCAL + ".out",
             "--content-type", "text/plain"]).returncode == 0:
        _write_stamp(stamp)
    os.remove(STAMP_LOCAL + ".out")
    return 0


def _selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        good, empty, junk = (os.path.join(d, n) for n in ("g.db", "e.db", "j.db"))
        con = sqlite3.connect(good)
        con.execute("CREATE TABLE capabilities (id TEXT)")
        con.execute("INSERT INTO capabilities VALUES ('pkg:x')")
        con.commit(); con.close()
        assert usable(good), "a real database with rows must be usable"

        con = sqlite3.connect(empty)
        con.execute("CREATE TABLE capabilities (id TEXT)"); con.commit(); con.close()
        assert not usable(empty), "an empty corpus must not pass — it would look like a first run"

        open(junk, "wb").write(b"SQLite format 3\x00" + b"\x00" * 8000)
        assert not usable(junk), "a truncated download must not pass as a database"
        assert not usable(os.path.join(d, "absent.db"))
    print("ok — db_store rejects a truncated or empty cache before it can be mistaken for a run")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit(_selftest() if "--selftest" in sys.argv else
             pull() if cmd == "pull" else
             push() if cmd == "push" else
             (print(__doc__.strip().split("\n\n")[1]) or 2))
