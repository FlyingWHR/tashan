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
import json, gzip
import shutil
import os, re, subprocess, sqlite3, sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "tashan.db")
BUCKET = os.environ.get("TASHAN_DB_BUCKET", "tashan-state")
KEY = os.environ.get("TASHAN_DB_KEY", "tashan.db")
# GZIPPED, BECAUSE WRANGLER REFUSES ANYTHING OVER 300 MiB. The database passed 284 MiB on 14 Aug and
# CI died with "Wrangler only supports uploading files up to 300 MiB in size" — so every run since
# had been starting from a stale object with its incremental cursors frozen, silently, because push
# failures are reported at the end of a long job. SQLite compresses to about 21% of its size
# (284 MiB -> ~61 MiB), which buys years rather than weeks and costs a few seconds each way.
GZKEY = KEY + ".gz"

# THE SAME PROBLEM, A SECOND FILE. data/skills_cache.json is a blob-SHA-keyed cache of SKILL.md
# content that makes re-ingestion nearly free. It reached 127 MB in CI on 14 Aug and GitHub refused
# the push — "File data/skills_cache.json is 127.09 MB; this exceeds GitHub's file size limit of
# 100.00 MB" — so the nightly could not commit the day's retention shard, and the deploy that
# depends on that commit was skipped. Exactly what moved the database out of git in the first place.
#
# Gzipping it and keeping it in git would be WORSE than the database case: a fresh binary blob every
# night defeats delta compression entirely, so a ~20 MB compressed cache would add ~7 GB of pack a
# year. It rides to R2 beside the database instead, on the same credentials and the same free tier.
AUX = [("data/skills_cache.json", "skills_cache.json.gz")]

# THE TEXT CACHE TRAVELS SEPARATELY, and this is what keeps the object under wrangler's ceiling.
# capability_text is README and SKILL.md text — 49% of the database on this machine, and the single
# reason the push started refusing: 1,485.9 MiB compressed to 297.1 MiB against a 300 MiB limit, so
# the R2 object stopped advancing on 11 September and every run since has started from an older
# cursor. It is also the most re-derivable thing in the file: losing it costs a slow re-fetch, never
# a wrong answer. Splitting it out halves the object that MUST land and gives the rest years of room.
#
# NOT signal_history, which is the other obvious candidate and would be a bug. It is sharded to git
# and snapshot_history.restore() rebuilds it — but that runs in the ENRICH phase, after build.py has
# already scored, and scoring is what reads the series. Emptying it here would hand the scorer an
# empty history on every run.
TEXTKEY = KEY + ".text.gz"
TEXT_TABLE = "capability_text"
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
    # Prefer the compressed object; fall back to the legacy uncompressed one so a bucket written by
    # an older revision still restores. The fallback can be deleted once a gzipped object exists.
    gz = tmp + ".gz"
    used = GZKEY
    r = _run(["r2", "object", "get", f"{BUCKET}/{GZKEY}", "--file", gz])
    if r.returncode == 0 and os.path.exists(gz) and os.path.getsize(gz) > 0:
        try:
            with gzip.open(gz, "rb") as fin, open(tmp, "wb") as fout:
                shutil.copyfileobj(fin, fout, 1024 * 1024)
        except OSError as e:
            print(f"  db_store: compressed object would not decompress ({e}) — trying the legacy key")
        finally:
            os.remove(gz)
    if not usable(tmp):
        used = KEY
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
    # THE TEXT CACHE, back into the file it came out of. Best-effort by design: an object that is
    # missing (a bucket written before the split) or unreadable leaves capability_text empty, which
    # costs a slow re-fetch of README text and nothing else. The cursors, the scores and the change
    # history all travelled in the core object that has already landed.
    tgz = DB + ".text.gz"
    rt = _run(["r2", "object", "get", f"{BUCKET}/{TEXTKEY}", "--file", tgz])
    if rt.returncode == 0 and os.path.exists(tgz) and os.path.getsize(tgz) > 0:
        tpath = DB + ".text"
        try:
            with gzip.open(tgz, "rb") as fin, open(tpath, "wb") as fout:
                shutil.copyfileobj(fin, fout, 1024 * 1024)
            n = _merge_text(DB, tpath)
            print(f"  db_store: merged {n:,} cached document(s) back from {TEXTKEY}")
        except OSError as e:
            print(f"  db_store: {TEXTKEY} would not restore ({e}) — README text will re-fetch")
        finally:
            for p_ in (tgz, tpath):
                if os.path.exists(p_):
                    os.remove(p_)
    else:
        print(f"  db_store: no {TEXTKEY} in R2 — README text will re-fetch as it goes")
        if os.path.exists(tgz):
            os.remove(tgz)
    _pull_aux()
    # Remember which generation we started from, so push() can tell whether anyone moved it since.
    _write_stamp(_remote_stamp() or "")
    print(f"  db_store: pulled {os.path.getsize(DB) / 1048576:.1f} MiB from r2://{BUCKET}/{used}")
    return 0


def _aux_paths(rel):
    return os.path.join(ROOT, rel)


def _pull_aux():
    """Auxiliary caches. Never fatal: a missing one costs a slower run, never a wrong one."""
    for rel, key in AUX:
        dest = _aux_paths(rel)
        gz = dest + ".gz"
        r = _run(["r2", "object", "get", f"{BUCKET}/{key}", "--file", gz])
        if r.returncode != 0 or not os.path.exists(gz) or os.path.getsize(gz) == 0:
            print(f"  db_store: no {key} in R2 — {rel} will rebuild as it goes")
            if os.path.exists(gz):
                os.remove(gz)
            continue
        try:
            with gzip.open(gz, "rb") as fin, open(dest + ".tmp", "wb") as fout:
                shutil.copyfileobj(fin, fout, 1024 * 1024)
            json.load(open(dest + ".tmp", encoding="utf-8"))   # refuse a truncated cache outright
            os.replace(dest + ".tmp", dest)
            print(f"  db_store: pulled {os.path.getsize(dest) / 1048576:.1f} MiB {rel}")
        except (OSError, ValueError) as e:
            print(f"  db_store: {key} would not restore ({e}) — {rel} will rebuild")
            if os.path.exists(dest + ".tmp"):
                os.remove(dest + ".tmp")
        finally:
            os.remove(gz)


def _push_aux():
    for rel, key in AUX:
        src = _aux_paths(rel)
        if not os.path.exists(src):
            continue
        gz = src + ".gz"
        with open(src, "rb") as fin, gzip.open(gz, "wb", compresslevel=6) as fout:
            shutil.copyfileobj(fin, fout, 1024 * 1024)
        r = _run(["r2", "object", "put", f"{BUCKET}/{key}", "--file", gz,
                  "--content-type", "application/gzip"])
        size = os.path.getsize(gz) / 1048576
        os.remove(gz)
        # NOT fatal. The database is the state that must survive; this is a speed cache, and losing
        # it costs one slow re-ingest rather than a wrong answer.
        print(f"  db_store: {'pushed' if r.returncode == 0 else 'FAILED to push'} "
              f"{size:.1f} MiB {key}" + ("" if r.returncode == 0 else f" ({_reason(r)})"))


def _split(src):
    """(core, text): the database with capability_text lifted into its own file.

    VACUUM INTO for the core rather than a file copy, so the pages the DELETE frees are actually
    reclaimed — deleting rows from SQLite without vacuuming leaves the file exactly as large, which
    would make this whole exercise a no-op that looks like it worked.
    """
    core, text = src + ".core", src + ".text"
    for p in (core, text):
        if os.path.exists(p):
            os.remove(p)
    con = sqlite3.connect(src)
    try:
        has_text = bool(con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TEXT_TABLE,)).fetchone())
        con.execute("VACUUM INTO ?", (core,))
    finally:
        con.close()
    if not has_text:
        return core, None
    c = sqlite3.connect(core)
    try:
        c.execute("ATTACH ? AS side", (text,))
        c.execute(f"CREATE TABLE side.{TEXT_TABLE} AS SELECT * FROM {TEXT_TABLE}")
        c.commit()
        c.execute("DETACH side")
        c.execute(f"DELETE FROM {TEXT_TABLE}")
        c.commit()
        c.execute("VACUUM")                      # reclaim, or the split saved nothing
    finally:
        c.close()
    return core, text


def _merge_text(dbpath, textpath):
    """Put the text cache back. Missing or unreadable is survivable — it re-fetches."""
    if not (textpath and os.path.exists(textpath)):
        return 0
    con = sqlite3.connect(dbpath)
    try:
        con.execute("ATTACH ? AS side", (textpath,))
        if not con.execute("SELECT 1 FROM side.sqlite_master WHERE type='table' AND name=?",
                           (TEXT_TABLE,)).fetchone():
            return 0
        n = con.execute(f"SELECT count(*) FROM side.{TEXT_TABLE}").fetchone()[0]
        con.execute(f"INSERT OR REPLACE INTO {TEXT_TABLE} SELECT * FROM side.{TEXT_TABLE}")
        con.commit()
        con.execute("DETACH side")
        return n
    except sqlite3.Error as e:
        print(f"  db_store: the text cache would not merge ({e}) — it will re-fetch")
        return 0
    finally:
        con.close()


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
    raw_mib = os.path.getsize(DB) / 1048576
    core, text = _split(DB)
    blob = DB + ".gz"
    with open(core, "rb") as fin, gzip.open(blob, "wb", compresslevel=6) as fout:
        shutil.copyfileobj(fin, fout, 1024 * 1024)
    mib = os.path.getsize(blob) / 1048576
    print(f"  db_store: {raw_mib:.1f} MiB -> core {os.path.getsize(core) / 1048576:.1f} MiB "
          f"-> {mib:.1f} MiB gzipped, text cache split out")
    if mib > 290:
        print("  db_store: REFUSING to push — even split and compressed this is near wrangler's "
              "300 MiB ceiling. The next thing to lift out is cap_state, or move to the S3 API.")
        for p_ in (blob, core, text):
            if p_ and os.path.exists(p_):
                os.remove(p_)
        return 1
    for key in (GZKEY, f"backup/{datetime.now(timezone.utc).strftime('%a').lower()}.db.gz"):
        r = _run(["r2", "object", "put", f"{BUCKET}/{key}", "--file", blob,
                  "--content-type", "application/gzip"])
        if r.returncode != 0:
            if key != GZKEY:
                print(f"  db_store: pushed the live object; the dated copy failed ({_reason(r)})")
                return 0                       # the working copy landed; a missing backup is not fatal
            print("  db_store: PUSH FAILED — the next run will start from a stale cache")
            print("           " + _reason(r))
            return 1
        print(f"  db_store: pushed {mib:.1f} MiB to r2://{BUCKET}/{key}")
    os.remove(blob)
    os.remove(core)
    # The text cache, as its own object. NOT fatal — same posture as the aux caches: losing it costs
    # a slow re-fetch of README text, never a wrong answer, and the object that carries the cursors
    # has already landed by the time we get here.
    if text and os.path.exists(text):
        tgz = text + ".gz"
        with open(text, "rb") as fin, gzip.open(tgz, "wb", compresslevel=6) as fout:
            shutil.copyfileobj(fin, fout, 1024 * 1024)
        tmib = os.path.getsize(tgz) / 1048576
        r = _run(["r2", "object", "put", f"{BUCKET}/{TEXTKEY}", "--file", tgz,
                  "--content-type", "application/gzip"])
        print(f"  db_store: {'pushed' if r.returncode == 0 else 'FAILED to push'} {tmib:.1f} MiB "
              f"{TEXTKEY}" + ("" if r.returncode == 0 else f" ({_reason(r)}) — it will re-fetch"))
        os.remove(tgz)
        os.remove(text)
    _push_aux()
    # Stamp last: a reader that sees the new generation is guaranteed the object behind it landed.
    with open(STAMP_LOCAL + ".out", "w", encoding="utf-8") as f:
        f.write(stamp)
    if _run(["r2", "object", "put", f"{BUCKET}/{STAMP_KEY}", "--file", STAMP_LOCAL + ".out",
             "--content-type", "text/plain"]).returncode == 0:
        _write_stamp(stamp)
    os.remove(STAMP_LOCAL + ".out")
    return 0


def _selftest_split():
    """The split must round-trip exactly, and must actually make the file smaller.

    Both halves matter. If the core is not smaller the whole exercise is a no-op that still prints
    a success line — deleting rows from SQLite without vacuuming leaves the file byte-for-byte the
    size it was. If the merge is not exact the pipeline silently re-fetches documents it already
    had, or worse, grades against a truncated one.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "t.db")
        con = sqlite3.connect(src)
        con.execute("CREATE TABLE capabilities (id TEXT PRIMARY KEY)")
        con.execute(f"CREATE TABLE {TEXT_TABLE} (cap_id TEXT PRIMARY KEY, body TEXT)")
        con.executemany("INSERT INTO capabilities VALUES (?)", [(f"pkg:{i}",) for i in range(200)])
        # Big enough that reclaiming pages is measurable rather than rounding.
        con.executemany(f"INSERT INTO {TEXT_TABLE} VALUES (?, ?)",
                        [(f"pkg:{i}", "x" * 20000) for i in range(200)])
        con.commit(); con.close()
        before = os.path.getsize(src)

        core, text = _split(src)
        assert usable(core), "the core must still be a usable database — it carries the cursors"
        c = sqlite3.connect(core)
        assert c.execute("SELECT count(*) FROM capabilities").fetchone()[0] == 200
        assert c.execute(f"SELECT count(*) FROM {TEXT_TABLE}").fetchone()[0] == 0, \
            "the text table must be empty in the core, or nothing was saved"
        c.close()
        assert os.path.getsize(core) < before * 0.5, (
            f"the core must actually shrink: {os.path.getsize(core)} vs {before} — a DELETE without "
            f"VACUUM leaves the file exactly as large and this whole split does nothing")
        t = sqlite3.connect(text)
        assert t.execute(f"SELECT count(*) FROM {TEXT_TABLE}").fetchone()[0] == 200
        t.close()

        assert _merge_text(core, text) == 200, "every document must come back"
        c = sqlite3.connect(core)
        assert c.execute(f"SELECT count(*) FROM {TEXT_TABLE}").fetchone()[0] == 200
        assert c.execute(f"SELECT body FROM {TEXT_TABLE} WHERE cap_id='pkg:7'").fetchone()[0] \
            == "x" * 20000, "a merged document must be the one that went in, not a truncation"
        c.close()
        print("  ok — the text cache splits out, the core shrinks by half, and it all comes back")

        # A bucket written before the split has no text object. That must cost a re-fetch, not a run.
        assert _merge_text(core, os.path.join(d, "nope.db")) == 0
        assert _merge_text(core, None) == 0
        print("  ok — a missing text object is survivable: README text simply re-fetches")


def _selftest():
    _selftest_split()
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
