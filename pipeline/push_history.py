#!/usr/bin/env python3
"""Push the signal_history series into Cloudflare KV, where /api/history serves it to licence holders.

    CF_ACCOUNT_ID=... CF_KV_NAMESPACE_ID=... CF_API_TOKEN=... python3 pipeline/push_history.py
    python3 pipeline/push_history.py --dry-run      # build the shards, print sizes, send nothing

This is the ONLY paid data path, so it is the only place the moat leaves this machine. Everything
else the site publishes is free and static.

WHY SHARDED, AND NOT BY FIRST CHARACTER. One KV value per capability is ~6,500 writes a night; one
value for everything is a 14 MB read by day 90 to answer a question about a single capability. The
obvious fix, bucketing on the first character, does not work here: every id is `<kind>:<name>`, so
`pkg:` and `plugin:` both land on "p" and 5,150 of 6,530 capabilities share one shard — 737 KB today
and ~11 MB by day 90, close to KV's 25 MB per-value ceiling. A cheap character sum spreads them
evenly instead, and is arithmetic that cannot drift between Python and JS: no overflow, no hash
library, no endianness.
The bucket function MUST stay identical to bucketOf() in functions/api/history.js, or every lookup
misses silently and paying customers see 404s. functions/api/license.test.mjs pins the JS side.
ponytail: 64 shards holds for years; raise SHARDS and re-push if one ever gets slow.
"""
import json, os, sqlite3, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "tashan.db")
ACCOUNT = os.environ.get("CF_ACCOUNT_ID", "")
NAMESPACE = os.environ.get("CF_KV_NAMESPACE_ID", "")
TOKEN = os.environ.get("CF_API_TOKEN", "")


SHARDS = 64


def bucket_of(cap_id):
    """Mirror of bucketOf() in functions/api/history.js. Keep these two byte-for-byte equivalent."""
    return str(sum(ord(c) for c in str(cap_id)) % SHARDS)


def shards(con):
    """One dict per bucket: {cap_id: {metric: {date: value}}} plus a `_scorers` date->version map.

    The scorer version is carried ONCE per date rather than per point, because snapshot_history writes
    exactly one snapshot per day under one scorer. Per-point would multiply the payload for no
    information. Without it a reader cannot tell that 43 -> 40 across 2026-07-29/30 is a recalibration
    rather than a decline, which is the whole reason the column exists.
    """
    out, scorers = {}, {}
    for cap_id, metric, value, at, scorer in con.execute(
            "SELECT cap_id, metric, value, at, COALESCE(scorer,'s1') FROM signal_history ORDER BY at"):
        out.setdefault(bucket_of(cap_id), {}).setdefault(cap_id, {}).setdefault(metric, {})[at] = value
        scorers[at] = scorer
    for b in out:
        out[b]["_scorers"] = scorers
    return out


def put(bucket, payload):
    url = (f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/storage/kv/namespaces/"
           f"{NAMESPACE}/values/hist:{bucket}")
    req = urllib.request.Request(url, data=payload.encode(), method="PUT",
                                 headers={"Authorization": "Bearer " + TOKEN,
                                          "Content-Type": "text/plain"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r).get("success", False)


def bulk(data, path):
    """Write the shards as a wrangler kv:bulk payload instead of calling the REST API.

    push via the REST API needs CF_API_TOKEN, which is a SEPARATE credential from the OAuth token
    `wrangler login` already stores. Rather than ask for a second secret just to move data we
    already have, emit the file wrangler can upload with the auth it holds:

        python3 pipeline/push_history.py --bulk /tmp/hist.json
        npx wrangler@3 kv:bulk put /tmp/hist.json --namespace-id <id>
    """
    out = [{"key": "hist:" + b, "value": json.dumps(v, separators=(",", ":"))}
           for b, v in data.items()]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    kb = os.path.getsize(path) / 1024
    print(f"  {len(out)} shard(s) -> {path}  ({kb:,.0f} KB)")
    print(f"  now: npx wrangler@3 kv:bulk put {path} --namespace-id <TASHAN_KV id>")
    return 0


def main():
    dry = "--dry-run" in sys.argv
    if "--bulk" in sys.argv:
        con = sqlite3.connect(DB)
        data = shards(con)
        con.close()
        return bulk(data, sys.argv[sys.argv.index("--bulk") + 1])
    if not dry and not (ACCOUNT and NAMESPACE and TOKEN):
        sys.exit("set CF_ACCOUNT_ID, CF_KV_NAMESPACE_ID and CF_API_TOKEN (or pass --dry-run)")
    con = sqlite3.connect(DB)
    data = shards(con)
    days = con.execute("SELECT COUNT(DISTINCT at) FROM signal_history").fetchone()[0]
    total = sum(len(v) for v in data.values())
    print(f"{total:,} capabilities over {days} day(s) -> {len(data)} shard(s)")
    sent = 0
    for b in sorted(data):
        payload = json.dumps(data[b], separators=(",", ":"))
        kb = len(payload.encode()) / 1024
        if kb > 24000:                       # KV hard limit is 25 MB per value
            print(f"  !! shard {b!r} is {kb/1024:.1f} MB — approaching the 25 MB KV ceiling, shard by month")
        if dry:
            print(f"  {b!r:5} {len(data[b]):5,} caps  {kb:8.1f} KB  (dry run)")
            continue
        if put(b, payload):
            sent += 1
            print(f"  {b!r:5} {len(data[b]):5,} caps  {kb:8.1f} KB  ok")
        else:
            print(f"  {b!r:5} FAILED")
    if not dry:
        print(f"pushed {sent}/{len(data)} shards")


if __name__ == "__main__":
    main()
