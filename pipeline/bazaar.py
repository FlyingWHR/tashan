#!/usr/bin/env python3
"""The x402 market, measured — and whether tashan is in it yet.

    python3 pipeline/bazaar.py              # the market, and our listing status
    python3 pipeline/bazaar.py --selftest   # no network

WHY THIS EXISTS. Every number we had about per-call pricing was a guess. The CDP Bazaar publishes
its whole index — public, keyless, no account — including a `quality` block per resource carrying
`l30DaysTotalCalls` and `l30DaysUniquePayers`. That is the only real demand data in this market, and
it was sitting behind a GET the entire time we were reasoning about price from first principles.

WHAT IT SAID, 18 Aug 2026, and why our prices changed the same day:

    15,089 resources listed · 324,462 calls / 30d · 41,671 unique payers · ~$9.8k GMV / 30d
    That is $0.65 per listed seller per month. The single best-earning resource in the entire
    ecosystem takes ~$362/mo (Chainlink); the best independent one ~$355 (a Twitter search).
    83% of ALL calls happen at or below $0.01. Our kit was $0.25 — a band holding 1.4%.

    MEASURE, DO NOT TRUST THE FIRST NUMBER. The first pass read 1,700 resources and $12.4k GMV.
    Both were wrong: the fetch stopped at a 2,000-row cap, and the GMV included listings whose
    price parses to $3.5e14 (a units error in somebody else's row). The corrected index is 9x
    larger and the corrected GMV is 21% smaller. Neither error changed the conclusion, which is
    the only reason it is safe to say so — a truncated sample that happens to agree is still luck.

TWO CONCLUSIONS, and the second matters more than the first:

  1. Price for VOLUME. Repriced kit $0.25 -> $0.05 and audit $0.05 -> $0.01, because a listing is
     created BY a settle and records what it settled at (see below) — the price had to be right
     before the first one, not after.
  2. x402 IS NOT A REVENUE LINE. A ~$9.8k/month total market split across 15,089 sellers cannot
     fund anything, and no amount of our execution changes that. It is a DISCOVERY channel —
     41,671 agents that demonstrably pay for things — and a credibility surface. Optimising it
     for margin would be optimising a rounding error at the cost of the only thing it is good
     for. Revenue is Pro's job. If this file ever reports a market an order of magnitude larger,
     that conclusion is the first one to revisit.

HOW A LISTING IS EARNED, which is the operational finding: every listed resource has at least one
paid call and none is missing its quality block. Nothing is listed by asking. The Bazaar indexes a
seller after a settle CONFIRMS through the CDP facilitator — so tashan appears the moment one real
payment clears, and not before. That is the whole bootstrap: one $0.01 call.
"""
import json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources"
BANDS = ((0.01, "<= $0.01"), (0.05, "$0.01-0.05"), (0.10, "$0.05-0.10"),
         (0.25, "$0.10-0.25"), (float("inf"), "> $0.25"))


def fetch(limit=100, cap=20000, get=None):
    """Every listed resource. Paginated; the index was 1,700 rows and growing when written."""
    get = get or (lambda u: json.load(urllib.request.urlopen(
        urllib.request.Request(u, headers={"user-agent": "tashan-selfcheck/bazaar"}), timeout=45)))
    out, off = [], 0
    while off < cap:
        got = (get(f"{INDEX}?limit={limit}&offset={off}") or {}).get("items") or []
        out += got
        if len(got) < limit:
            break
        off += limit
    return out


def price_of(item):
    """The USD price of the first offer, or None. Amounts are atomic strings at 6 decimals (USDC)."""
    for a in item.get("accepts") or []:
        raw = a.get("amount") or a.get("maxAmountRequired")
        try:
            p = int(raw) / 1e6
        except (TypeError, ValueError):
            continue
        # A price beyond any plausible per-call fee is a testnet artifact or a units mistake in
        # somebody else's listing; including it moved the market max to $3.5e14 and would poison
        # every aggregate computed here.
        if 0 <= p < 100:
            return p
    return None


def summarise(items):
    rows = [(price_of(i), ((i.get("quality") or {}).get("l30DaysTotalCalls") or 0), i)
            for i in items]
    priced = [(p, c, i) for p, c, i in rows if p is not None]
    calls = sum(c for _, c, _ in rows)
    payers = sum(((i.get("quality") or {}).get("l30DaysUniquePayers") or 0) for _, _, i in rows)
    gmv = sum(p * c for p, c, _ in priced)
    bands, lo = [], -1.0
    for hi, label in BANDS:
        sel = [c for p, c, _ in priced if lo < p <= hi]
        bands.append((label, len(sel), sum(sel)))
        lo = hi
    return {"n": len(items), "calls": calls, "payers": payers, "gmv": gmv, "bands": bands,
            "top": sorted(priced, key=lambda r: -r[1])[:10],
            "listed": [i for _, _, i in rows if "tashan" in str(i.get("resource", "")).lower()]}


def report(s):
    L = ["x402 BAZAAR — the whole public index", "",
         f"  resources listed      {s['n']:,}",
         f"  calls, last 30d       {s['calls']:,}",
         f"  unique payers         {s['payers']:,}",
         f"  GMV, last 30d         ${s['gmv']:,.0f}", ""]
    if s["calls"]:
        L.append("  price band     listings   calls/30d   share")
        for label, n, c in s["bands"]:
            L.append(f"    {label:<12} {n:>7}   {c:>9,}   {100.0 * c / s['calls']:>5.1f}%")
        L.append("")
        L.append("  best earners (what agents actually pay for):")
        for p, c, i in s["top"][:6]:
            L.append(f"    {c:>7,} calls x ${p:<7.4f} = ${p * c:>8,.0f}/30d  "
                     f"{str(i.get('resource', ''))[:46]}")
        L.append("")
    # OUR OWN STATUS — the reason to run this rather than read the docstring.
    if s["listed"]:
        L.append(f"  TASHAN: LISTED ({len(s['listed'])} resource(s)) — agents can discover us here.")
        for i in s["listed"]:
            q = i.get("quality") or {}
            L.append(f"    {i.get('resource','')}  {q.get('l30DaysTotalCalls', 0)} calls, "
                     f"{q.get('l30DaysUniquePayers', 0)} payers")
    else:
        L.append("  TASHAN: NOT LISTED. Every listed resource has >=1 settled call and none is")
        L.append("  missing its quality block, so a listing is earned by a settle, never requested.")
        L.append("  One confirmed payment through the CDP facilitator puts us in front of the")
        L.append(f"  {s['payers']:,} agents that demonstrably pay for things. Cheapest door: $0.01.")
    return "\n".join(L)


def _selftest():
    fake = {"items": [
        {"resource": "https://a.example/x", "accepts": [{"amount": "10000"}],
         "quality": {"l30DaysTotalCalls": 100, "l30DaysUniquePayers": 9}},
        {"resource": "https://b.example/y", "accepts": [{"maxAmountRequired": "250000"}],
         "quality": {"l30DaysTotalCalls": 4, "l30DaysUniquePayers": 1}},
        # A listing with an absurd price — real, and it moved the market max to $3.5e14.
        {"resource": "https://c.example/z", "accepts": [{"amount": "350000000000000000000"}],
         "quality": {"l30DaysTotalCalls": 1, "l30DaysUniquePayers": 1}}]}
    assert price_of(fake["items"][0]) == 0.01
    assert price_of(fake["items"][1]) == 0.25, "v1 spelling maxAmountRequired must still be read"
    assert price_of(fake["items"][2]) is None, "an implausible price must not enter the aggregates"

    # A PAGE SHORTER THAN THE LIMIT ENDS PAGINATION. Written with limit=3 against a 3-item fake,
    # this looped until the cap: len(got) < limit was never true. The live index would have been
    # fetched 20 times over for the same 1,700 rows.
    got = fetch(limit=5, get=lambda u: fake)
    assert len(got) == 3, "a short page must end pagination, not loop to the cap"
    calls_made = []
    fetch(limit=3, get=lambda u: (calls_made.append(u), {"items": fake["items"][:3]})[1], cap=9)
    assert len(calls_made) == 3, "a FULL page must keep paging: %d" % len(calls_made)
    s = summarise(got)
    assert s["calls"] == 105 and s["payers"] == 11, s
    assert abs(s["gmv"] - (0.01 * 100 + 0.25 * 4)) < 1e-9, s["gmv"]
    r = report(s)
    assert "NOT LISTED" in r and "earned by a settle" in r, r
    # ...and it must SAY so when we are listed, or the whole point of running it is lost.
    s2 = summarise(got + [{"resource": "https://tashan.sh/v0.1/kit", "accepts": [{"amount": "50000"}],
                           "quality": {"l30DaysTotalCalls": 2, "l30DaysUniquePayers": 2}}])
    assert "TASHAN: LISTED" in report(s2)
    print("bazaar selftest ok")
    return 0


def main():
    try:
        items = fetch()
    except Exception as e:
        # Never fail a pipeline over a market report about somebody else's index.
        print("bazaar: index unreachable (%s)" % e)
        return 0
    s = summarise(items)
    print(report(s))
    out = os.path.join(ROOT, "data", "bazaar.json")
    json.dump({"n": s["n"], "calls": s["calls"], "payers": s["payers"], "gmv": round(s["gmv"], 2),
               "bands": s["bands"], "listed": len(s["listed"])}, open(out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
