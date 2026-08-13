#!/usr/bin/env python3
"""The money funnel, read out loud — views -> offer clicks -> checkout.

WHY THIS EXISTS. Every page on this site now fires a countable event: a pageview, an install-snippet
copy, an outbound click, and (since the CTA fix) a `cta` event carrying which offer was clicked.
That data has been landing in Cloudflare Analytics Engine since 9 Aug and NOBODY HAS EVER READ IT.
docs/ANALYTICS.md documents the SQL; it does not run any. A number nobody looks at is the same as a
number nobody collected — this codebase just spent a round learning that lesson from seven nightly
runs that failed loudly into an empty room.

So this runs in the daily workflow, where CLOUDFLARE_API_TOKEN already exists, and writes the answer
into the GitHub step summary. No dashboard to remember, no SQL to re-derive, no tab to keep open:
the run that measures the corpus also says what the corpus earned.

WHAT IT REFUSES TO DO. If the token lacks `Account Analytics: Read` it says exactly that and exits 0
— a missing report must never fail the pipeline that publishes the site. And it never invents a
denominator: a funnel with no traffic yet prints zeros and says so, because a conversion rate over
three sessions is noise wearing a percentage sign.

Run:  CLOUDFLARE_ACCOUNT_ID=… CLOUDFLARE_API_TOKEN=… python3 pipeline/funnel.py [--days 7]
      python3 pipeline/funnel.py --selftest      # no network, no credentials
"""
import json, os, sys, urllib.error, urllib.request

ACCOUNT = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
DATASET = os.environ.get("TASHAN_AE_DATASET", "tashan_events")
API = "https://api.cloudflare.com/client/v4/accounts/{}/analytics_engine/sql"

# blob1 event · blob2 path · blob3 referrer host · blob4 context key · blob5 value
# · blob6 viewport · blob7 country · blob8 session   (see functions/api/e.js and docs/ANALYTICS.md)
EV, PATH, REF, KEY = "blob1", "blob2", "blob3", "blob4"


def sql(q):
    """One query. Returns rows, or raises RuntimeError with a message meant for a human."""
    req = urllib.request.Request(
        API.format(ACCOUNT), data=q.encode("utf-8"),
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "text/plain"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8")).get("data") or []
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        if e.code in (401, 403):
            raise RuntimeError(
                "Cloudflare refused the query (HTTP %d). The token needs the "
                "'Account Analytics: Read' permission — the deploy token usually does not have it. "
                "Add it at Cloudflare > My Profile > API Tokens.\n  %s" % (e.code, body))
        raise RuntimeError("Analytics Engine returned HTTP %d: %s" % (e.code, body))
    except urllib.error.URLError as e:
        raise RuntimeError("Could not reach the Analytics Engine API: %s" % e.reason)


def n(row, k, default=0):
    v = row.get(k, default)
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def collect(days):
    """Every number in one place, so the report cannot cite a metric it did not fetch."""
    since = "timestamp > NOW() - INTERVAL '%d' DAY" % days
    tot = sql("SELECT %s AS ev, SUM(_sample_interval) AS c FROM %s WHERE %s GROUP BY ev"
              % (EV, DATASET, since))
    totals = {r.get("ev", ""): n(r, "c") for r in tot}

    offers = sql("SELECT %s AS k, SUM(_sample_interval) AS c FROM %s WHERE %s='cta' AND %s "
                 "GROUP BY k ORDER BY c DESC LIMIT 20" % (KEY, DATASET, EV, since))
    checkout = sql("SELECT %s AS host, SUM(_sample_interval) AS c FROM %s WHERE %s='outbound' "
                   "AND %s LIKE '%%polar%%' AND %s GROUP BY host ORDER BY c DESC LIMIT 5"
                   % (KEY, DATASET, EV, KEY, since))
    pages = sql("SELECT %s AS path, SUM(_sample_interval) AS c FROM %s WHERE %s='pageview' AND %s "
                "GROUP BY path ORDER BY c DESC LIMIT 12" % (PATH, DATASET, EV, since))
    refs = sql("SELECT %s AS ref, SUM(_sample_interval) AS c FROM %s WHERE %s='pageview' "
               "AND %s != '' AND %s GROUP BY ref ORDER BY c DESC LIMIT 10"
               % (REF, DATASET, EV, REF, since))
    return {"totals": totals, "offers": offers, "checkout": checkout, "pages": pages, "refs": refs}


def rate(num, den):
    """A percentage, or an honest dash. Never a rate over a denominator too small to mean anything."""
    if den < 100:
        return "—"
    return "%.2f%%" % (100.0 * num / den)


def report(d, days):
    t = d["totals"]
    views = t.get("pageview", 0)
    ctas = t.get("cta", 0)
    buys = sum(n(r, "c") for r in d["checkout"])
    L = []
    L.append("## Funnel — last %d days" % days)
    L.append("")
    L.append("| stage | count | of views |")
    L.append("|---|---:|---:|")
    L.append("| pageviews | %s | — |" % f"{views:,}")
    L.append("| offer clicks (`cta`) | %s | %s |" % (f"{ctas:,}", rate(ctas, views)))
    L.append("| reached Polar checkout | %s | %s |" % (f"{buys:,}", rate(buys, views)))
    L.append("")
    if views < 100:
        L.append("_Too little traffic to read a rate yet (%d views). Counts only._" % views)
        L.append("")
    if d["offers"]:
        L.append("### Which offer gets clicked")
        L.append("")
        L.append("| placement | clicks |")
        L.append("|---|---:|")
        for r in d["offers"]:
            L.append("| `%s` | %s |" % (r.get("k") or "—", f"{n(r,'c'):,}"))
        L.append("")
    else:
        L.append("_No `cta` events yet. Every generated page carries a `data-k=\"pro-*\"` button, so "
                 "zero here means no clicks — not missing instrumentation._")
        L.append("")
    for title, rows, col in (("Top pages", d["pages"], "path"), ("Referrers", d["refs"], "ref")):
        if not rows:
            continue
        L.append("### " + title)
        L.append("")
        for r in rows:
            L.append("- `%s` — %s" % (r.get(col) or "—", f"{n(r,'c'):,}"))
        L.append("")
    other = {k: v for k, v in t.items() if k not in ("pageview", "cta")}
    if other:
        L.append("### Other events")
        L.append("")
        L.append(", ".join("`%s` %s" % (k, f"{v:,}") for k, v in sorted(other.items(), key=lambda x: -x[1])))
        L.append("")
    return "\n".join(L)


def _selftest():
    assert rate(5, 1000) == "0.50%"
    assert rate(5, 20) == "—", "a rate over 20 sessions is noise, not a rate"
    assert n({"c": "12.0"}, "c") == 12 and n({}, "c") == 0
    d = {"totals": {"pageview": 1000, "cta": 20, "copy": 4},
         "offers": [{"k": "pro-dossier", "c": "18"}], "checkout": [{"host": "buy.polar.sh", "c": "3"}],
         "pages": [{"path": "/", "c": "500"}], "refs": []}
    out = report(d, 7)
    assert "0.30%" in out and "pro-dossier" in out and "| 1,000 |" in out, out
    empty = report({"totals": {}, "offers": [], "checkout": [], "pages": [], "refs": []}, 7)
    assert "Too little traffic" in empty and "not missing instrumentation" in empty
    print("funnel selftest ok")
    return 0


def main(argv):
    days = int(argv[argv.index("--days") + 1]) if "--days" in argv else 7
    if not ACCOUNT or not TOKEN:
        print("funnel: CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN not set — skipping.\n"
              "        This is expected locally; the daily workflow has both.")
        return 0
    try:
        out = report(collect(days), days)
    except RuntimeError as e:
        # NEVER fail the pipeline over a report. The site publishing matters more than the numbers
        # about it, and a broken token must not become a reason the board goes stale.
        print("funnel: %s" % e)
        return 0
    print(out)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main(sys.argv[1:]))
