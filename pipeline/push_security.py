#!/usr/bin/env python3
"""Push the security audit into Cloudflare KV, where /api/security answers about ONE capability.

    CF_ACCOUNT_ID=... CF_KV_NAMESPACE_ID=... CF_API_TOKEN=... python3 pipeline/push_security.py
    python3 pipeline/push_security.py --dry-run      # build the shards, print sizes, send nothing

THIS IS NO LONGER A PAID DELIVERY PATH. It was built as one, back when advisory detail was sold:
the pricing page promised "which CVE or GHSA … and the version that fixes it" and nothing delivered
it. build.py::redact_paid later moved all of that into the PUBLIC export — "naming a risk and then
charging to say which risk is a worse position than not scanning at all" — and /api/security was
ungated to match, because it was quoting a price for data /v0.1/lookup already gives away.

So what this feeds is a free, per-capability endpoint. It still earns its place: the public bulk
file is 6.9 MB, and this answers about one row.

WHAT IS PUSHED:

    a  the advisory list — id, severity, summary, the version that fixes it
    s  the literal command run at install time
    t  when it was scanned — and for a clean row this is the WHOLE record

EVERY SCANNED ROW SHIPS. It used to be only rows with a finding, which left 7,366 of 7,862 absent,
so /api/security answered "no audit detail recorded" for chrome-devtools-mcp and @playwright/mcp
alike. A record carrying only `t` now means "scanned on that date, nothing found" — an answer, and
for a security audit the most common one — and an id missing from KV means what the 404 says: we
have never scanned it.

(permissions are NOT here: "what it can reach on your machine" is in the public export, and
duplicating it would be a second copy of a fact that already has a home.)

SHARDING is identical to push_history.py, deliberately: same 64 buckets, same character-sum
arithmetic, so the two paid paths cannot drift. bucket_of() MUST stay byte-for-byte equivalent to
bucketOf() in functions/api/security.js or every lookup misses silently and paying customers see
404s — functions/api/security.test.mjs pins the JS side against vectors computed from this file.
"""
from datetime import datetime, timezone
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
    # EVERY SCANNED ROW SHIPS, NOT ONLY THE ONES WITH SOMETHING WRONG.
    #
    # This used to require `sec_advisories IS NOT NULL OR sec_install_script IS NOT NULL`, which
    # sounds like sensible frugality and meant 7,366 of 7,862 scanned capabilities — 93.7% — were
    # absent from the store. Measured live against a real Pro session: /api/security answered 404
    # "no audit detail recorded for this id" for chrome-devtools-mcp, exa-mcp-server, firecrawl-mcp
    # and @playwright/mcp. Four of the most-used servers we measure, to a paying subscriber, on the
    # feature Pro is sold on.
    #
    # A CLEAN RESULT IS THE PRODUCT. "We checked this on the 14th and found nothing" is the answer
    # somebody paid for; "no audit detail recorded" is indistinguishable from having no coverage.
    # The endpoint was RIGHT to refuse to report an absent record as clean — it could not tell
    # "scanned, nothing found" from "never scanned". This is what removes that ambiguity: a record
    # carrying only `t` means scanned on that date with nothing found, and no record at all now
    # means exactly what the 404 says.
    #
    # Cost: ~324 KB across 64 shards, about 5 KB each, against a 25 MB per-value ceiling.
    rows = con.execute(
        "SELECT id, sec_advisories, sec_install_script, sec_scanned_at "
        "FROM capabilities WHERE sec_scanned_at IS NOT NULL")
    for cap_id, adv, script, at in rows:
        rec = {}
        if adv:
            try:
                rec["a"] = json.loads(adv)
            except Exception:
                pass
        if script:
            rec["s"] = script
        # `t` is the whole record for a clean row, and it is not filler: the DATE is the claim.
        # A scan from six weeks ago and one from last night are different answers to "is this safe",
        # and the customer is entitled to know which they are being given.
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
        print("SKIPPED — set CF_ACCOUNT_ID, CF_KV_NAMESPACE_ID and CF_API_TOKEN to deliver the audit. "
              "Until then /api/security returns 503 for every id.")
        return 0
    con = sqlite3.connect(DB)
    data = shards(con)
    total = sum(len(v) for v in data.values())
    n_adv = sum(1 for b in data.values() for r in b.values() if r.get("a"))
    n_scr = sum(1 for b in data.values() for r in b.values() if r.get("s"))
    con.close()
    print(f"{total:,} capabilities with audit detail -> {len(data)} shard(s)")
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
        # A MANIFEST, so an empty store is distinguishable from a capability we have nothing on.
        # Without it both answer 404 "no audit detail recorded for this id" — which reads as thin
        # coverage rather than as a product that was never loaded. A customer paying $6 would see
        # that for EVERY package, conclude tashan is useless, and refund. It does not look broken;
        # it looks bad, which is worse.
        put("meta", json.dumps({"shards": sent, "capabilities": total,
                                "pushed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                               separators=(",", ":")))
        print(f"pushed {sent}/{len(data)} shards + manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
