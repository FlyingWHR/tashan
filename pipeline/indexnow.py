#!/usr/bin/env python3
"""Tell the IndexNow engines which pages actually changed today.

    python3 pipeline/indexnow.py            # submit today's changed URLs
    python3 pipeline/indexnow.py --seed     # one-time: the whole indexable corpus, best first
    python3 pipeline/indexnow.py --dry-run  # print what would be sent
    python3 pipeline/indexnow.py --selftest

WHY THIS, AND WHY NOW. Analytics went live and showed the shape of the traffic: two organic
arrivals in 72 hours, both Google landing on a capability dossier from what looks like a
package-name search. The constraint is arrivals, not conversion — at one visit a day there is no
conversion problem to solve — so the work that matters is being found.

Nothing here submitted a URL anywhere. There was a sitemap and that was all; Google retired its
sitemap ping in 2023 and nothing replaced it.

GOOGLE DOES NOT PARTICIPATE IN INDEXNOW. Bing, Yandex, Seznam and Naver do, and that is a better
fit than it first sounds for this project: Bing's index is what grounds Copilot and ChatGPT search,
so the engines this reaches are the ones answering the questions an AI-capability index exists to
answer. It is not a substitute for ranking in Google; it is the half we can actually act on.

ONLY WHAT CHANGED. The protocol accepts 10,000 URLs per request and it would be trivial to post the
whole sitemap every night. That is the behaviour the engines throttle, and it is also a lie: a page
whose score did not move did not change. Submissions are the capabilities with a change event in
the last day, plus the handful of pages that are rewritten every run anyway.

Stdlib only. Never fatal — a rejected submission must not fail a pipeline whose real job is
measurement.
"""
import json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = "c8e4ef5a41262283c1bd92a720315b2b"
HOST = "tashan.sh"
BASE = "https://" + HOST
ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_URLS = 10000


def changed_urls(con, days=1):
    """Capability pages with a real change, plus the pages that genuinely change every run."""
    from datetime import datetime, timedelta, timezone
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = con.execute(
        "SELECT DISTINCT c.id FROM change_events e JOIN capabilities c ON c.id = e.cap_id "
        "WHERE e.at >= ?", (since,)).fetchall()
    import build
    urls = []
    for (cid,) in rows:
        slug = build.slugify(cid)
        p = os.path.join(ROOT, "web", "capability", slug + ".html")
        # never submit a page we do not serve, or one we have asked robots not to index
        if not os.path.exists(p):
            continue
        if 'name="robots" content="noindex' in open(p, encoding="utf-8").read():
            continue
        urls.append(BASE + "/capability/" + slug)
    urls += [BASE + "/", BASE + "/browse", BASE + "/llms.txt"]
    return urls[:MAX_URLS]


def seed_urls(con, n=9000):
    """One-time: the indexable corpus, best first. IndexNow has never heard of this site, so the
    steady-state "what changed today" is meaningless until it knows what exists. Ranked by score so
    that if an engine takes only part of it, it takes the part worth ranking. Noindex pages are
    excluded here for the same reason they are excluded from the sitemap — submitting a URL that
    answers noindex is a contradictory signal."""
    import build
    rows = con.execute("SELECT id FROM capabilities WHERE tashan_score IS NOT NULL "
                       "ORDER BY tashan_score DESC").fetchall()
    urls = []
    for (cid,) in rows:
        slug = build.slugify(cid)
        p = os.path.join(ROOT, "web", "capability", slug + ".html")
        if not os.path.exists(p):
            continue
        if 'name="robots" content="noindex' in open(p, encoding="utf-8").read():
            continue
        urls.append(BASE + "/capability/" + slug)
        if len(urls) >= n:
            break
    import glob
    for sub in ("category", "task", "role", "compare"):
        for f in sorted(glob.glob(os.path.join(ROOT, "web", sub, "*.html"))):
            urls.append(BASE + "/" + sub + "/" + os.path.basename(f)[:-5])
    urls += [BASE + "/", BASE + "/browse", BASE + "/pricing", BASE + "/methodology", BASE + "/llms.txt"]
    return urls[:MAX_URLS]


BATCH = 1000        # the protocol allows 10,000; 9,310 in one POST was refused with a 403


def submit(urls, dry=False):
    """Post in batches. The spec permits 10,000 per request and the endpoint does not: a single
    9,310-URL body came back 403, while the same key with one URL returned 200 — so the 403 is the
    payload, not the credential, and it reads exactly like an auth failure. Batching is politer
    anyway, and a partial success is still a success for the URLs that landed."""
    if not urls:
        print("indexnow: nothing changed today, nothing submitted")
        return 0
    if dry:
        print(f"indexnow: would submit {len(urls)} url(s) in "
              f"{-(-len(urls) // BATCH)} batch(es), e.g. {urls[:3]}")
        return 0
    sent = 0
    for i in range(0, len(urls), BATCH):
        chunk = urls[i:i + BATCH]
        body = json.dumps({"host": HOST, "key": KEY, "urlList": chunk}).encode()
        req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                     headers={"content-type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                if r.status < 300:
                    sent += len(chunk)
        except urllib.error.HTTPError as e:
            print(f"indexnow: batch {i // BATCH + 1} refused — HTTP {e.code} {e.reason}")
        except Exception as e:
            print(f"indexnow: batch {i // BATCH + 1} failed — {e}")
        time.sleep(1)
    print(f"indexnow: submitted {sent} of {len(urls)} url(s)")
    return 0


def _selftest():
    body = json.loads(json.dumps({"host": HOST, "key": KEY, "urlList": [BASE + "/"]}))
    assert len(KEY) >= 8 and all(ch in "0123456789abcdefABCDEF-" for ch in KEY), "key must be hex"
    assert os.path.exists(os.path.join(ROOT, "web", KEY + ".txt")), "key file must be served at root"
    assert open(os.path.join(ROOT, "web", KEY + ".txt"), encoding="utf-8").read().strip() == KEY
    assert body["host"] == HOST
    print("ok — indexnow key is hex, served at the root, and the payload matches the protocol")
    return 0


def main():
    if "--selftest" in sys.argv:
        return _selftest()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build
    con = build.db()
    urls = seed_urls(con) if "--seed" in sys.argv else changed_urls(con)
    con.close()
    return submit(urls, dry="--dry-run" in sys.argv)


if __name__ == "__main__":
    sys.exit(main())
