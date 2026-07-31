#!/usr/bin/env python3
"""Push the security audit's DETAIL into Cloudflare KV, where /api/security serves it to licence holders.

    CF_ACCOUNT_ID=... CF_KV_NAMESPACE_ID=... CF_API_TOKEN=... python3 pipeline/push_security.py
    python3 pipeline/push_security.py --dry-run      # build the shards, print sizes, send nothing

WHY THIS EXISTS. The detail is the paid half of the audit, and it had no delivery path at all: the
pricing page sold "which CVE or GHSA … and the version that fixes it", the capability page offered
"unlock detail", and no endpoint, CLI path or client fetch ever produced any of it. The values were
instead sitting in the public /data/capabilities.json, so a stranger could read what a customer could
not get. build.py::redact_paid removed them from every public payload; this is how they reach the
people who paid.

WHAT IS PUSHED, AND WHAT IS NOT. Only the three things the copy sells:

    a  the advisory list — id, severity, summary, the version that fixes it
    s  the literal command run at install time
    (permissions are NOT here: "what it can reach on your machine" is the free tier's own promise,
     and gating it sold one fact twice)

Everything a free reader sees stays in the public export and is not duplicated here. If a capability
has none of the three, it is not written at all — an id missing from KV means "nothing to add",
which /api/security returns as a 404 with a note, never as "we scanned it and it was clean".

SHARDING is identical to push_history.py, deliberately: same 64 buckets, same character-sum
arithmetic, so the two paid paths cannot drift. bucket_of() MUST stay byte-for-byte equivalent to
bucketOf() in functions/api/security.js or every lookup misses silently and paying customers see
404s — functions/api/security.test.mjs pins the JS side against vectors computed from this file.
"""
import json, os, sqlite3, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "tashan.db")
ACCOUNT = os.environ.get("CF_ACCOUNT_ID", "")
NAMESPACE = os.environ.get("CF_KV_NAMESPACE_ID", "")
TOKEN = os.environ.get("CF_API_TOKEN", "")

SHARDS = 64


def bucket_of(cap_id):
    """Mirror of bucketOf() in functions/api/security.js. Keep these two byte-for-byte equivalent."""
    return str(sum(ord(c) for c in str(cap_id)) % SHARDS)


def shards(con):
    """One dict per bucket: {cap_id: {a: [...], s: "...", p: [...], t: "..."}}.

    Short keys because this is read on every dossier view by a licence holder; the field names would
    be a third of the payload.
    """
    out = {}
    rows = con.execute(
        "SELECT id, sec_advisories, sec_install_script, sec_scanned_at "
        "FROM capabilities WHERE sec_scanned_at IS NOT NULL "
        "AND (sec_advisories IS NOT NULL OR sec_install_script IS NOT NULL)")
    for cap_id, adv, script, at in rows:
        rec = {}
        if adv:
            try:
                rec["a"] = json.loads(adv)
            except Exception:
                pass
        if script:
            rec["s"] = script
        if not rec:
            continue
        rec["t"] = at
        out.setdefault(bucket_of(cap_id), {})[cap_id] = rec
    return out


def put(bucket, payload):
    url = (f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/storage/kv/namespaces/"
           f"{NAMESPACE}/values/sec:{bucket}")
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

        python3 pipeline/push_security.py --bulk /tmp/sec.json
        npx wrangler@3 kv:bulk put /tmp/sec.json --namespace-id <id>
    """
    out = [{"key": "sec:" + b, "value": json.dumps(v, separators=(",", ":"))}
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
        # A skip, not a failure: this runs inside the nightly loop, and a missing credential must not
        # take down the whole measurement. It must be LOUD, though — silence here means paying
        # customers quietly stop receiving what they bought.
        print("SKIPPED — set CF_ACCOUNT_ID, CF_KV_NAMESPACE_ID and CF_API_TOKEN to deliver paid "
              "detail. Until then /api/security returns 503 and every 'unlock detail' link is dead.")
        return 0
    con = sqlite3.connect(DB)
    data = shards(con)
    total = sum(len(v) for v in data.values())
    n_adv = sum(1 for b in data.values() for r in b.values() if r.get("a"))
    n_scr = sum(1 for b in data.values() for r in b.values() if r.get("s"))
    con.close()
    print(f"{total:,} capabilities with paid detail -> {len(data)} shard(s)")
    print(f"  {n_adv:,} with advisories · {n_scr:,} with an install script")
    sent = 0
    for b in sorted(data, key=int):
        payload = json.dumps(data[b], separators=(",", ":"))
        kb = len(payload.encode()) / 1024
        if kb > 24000:
            print(f"  !! shard {b} is {kb/1024:.1f} MB — approaching the 25 MB KV ceiling")
        if dry:
            print(f"  {b:>3} {len(data[b]):5,} caps  {kb:8.1f} KB  (dry run)")
            continue
        if put(b, payload):
            sent += 1
        else:
            print(f"  {b:>3} FAILED")
    if not dry:
        print(f"pushed {sent}/{len(data)} shards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
