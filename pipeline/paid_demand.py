#!/usr/bin/env python3
"""tashan — PAID DEMAND: which agent services have actually been paid, from the chain.

WHY THIS IS A NEW KIND OF SIGNAL. Every number tashan already carries is an upstream claim measured
from the outside: npm downloads, publish cadence, GitHub activity, how often a server turns up in a
public config. Each is a proxy for "is anyone using this". None of them is money.

x402 changed that. A service answers HTTP 402 with a price, the caller signs a USDC transfer, and
the receipt settles on chain — so for the slice of the field that has adopted it there is now a
public, unforgeable record of demand. Coinbase's Bazaar publishes the DIRECTORY of those services,
14,536 of them, and no evidence about any: not one number saying whether a listed endpoint has ever
been paid once. That gap is the whole reason this file exists.

WHERE THE DATA COMES FROM. A subgraph (see ../subgraph) indexes USDC transfers on Base whose
recipient is an address a service published as its payTo. This stage reads it and writes two things:

    data/paid_demand.json      per receiver: settled calls, volume, distinct payers, first/last seen
    web/data/demand.json       the site's export, joined to capabilities where the host is one we know

THE JOIN IS DELIBERATELY NARROW. A receiver address maps to the hosts that published it, and a host
maps to a capability only when we already hold that exact host as the capability's homepage or
repository. Anything looser — fuzzy name matching, registrable-domain guessing — would attach real
money to the wrong project, which is the one error an evidence product cannot make. Unmatched
receivers are still published; they are simply reported as economy-level facts with no capability
attached.

    python3 pipeline/paid_demand.py              # query, store, export
    python3 pipeline/paid_demand.py --selftest   # no network, no credentials
"""
import json, os, sys, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECEIVERS = os.path.join(ROOT, "subgraph", "receivers.json")
OUT = os.path.join(ROOT, "data", "paid_demand.json")
SITE = os.path.join(ROOT, "web", "data", "demand.json")

# Set once the subgraph is published. Until then this stage is a no-op that says so rather than
# inventing numbers — an empty file is honest, a fabricated one is not.
ENDPOINT = os.environ.get("TASHAN_SUBGRAPH_URL", "")

USDC = 10 ** 6          # 6 decimals, so atomic units are not dollars and must never be printed raw

QUERY = """
{
  receivers(first: 1000, orderBy: totalPaid, orderDirection: desc) {
    id totalPaid payments payers firstPaymentAt lastPaymentAt
  }
  economy(id: "x402") { totalPaid payments receiversPaid lastBlock }
}
"""


def query(endpoint, body=QUERY, timeout=30):
    """Ask the subgraph. Raises on transport failure; the caller decides whether that is fatal."""
    req = urllib.request.Request(
        endpoint,
        data=json.dumps({"query": body}).encode(),
        headers={"content-type": "application/json", "user-agent": "tashan/paid-demand (+https://tashan.sh)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        doc = json.load(r)
    if doc.get("errors"):
        raise RuntimeError(f"subgraph: {doc['errors'][0].get('message', 'query failed')}")
    return doc.get("data") or {}


def usd(atomic):
    """Atomic USDC to dollars. Kept in one place so no caller ever prints 6-decimal units as money."""
    try:
        return round(int(atomic) / USDC, 4)
    except (TypeError, ValueError):
        return 0.0


def hosts_for(receivers_file=RECEIVERS):
    """address -> the hosts that published it as their payTo."""
    try:
        with open(receivers_file) as f:
            doc = json.load(f)
    except (OSError, ValueError):
        return {}
    return {a.lower(): (v.get("hosts") or []) for a, v in (doc.get("receivers") or {}).items()}


def join(rows, addr_hosts, host_to_cap):
    """Attach a capability to a receiver only when a host it published is one we already hold.

    Returns (records, matched, unmatched). A receiver with several hosts attaches to each capability
    it can be proven to belong to; money is never split or guessed, it is reported per receiver and
    the reader is told how many services share the address.
    """
    out, matched, unmatched = [], 0, 0
    for r in rows:
        addr = str(r.get("id", "")).lower()
        hosts = addr_hosts.get(addr, [])
        caps = sorted({host_to_cap[h] for h in hosts if h in host_to_cap})
        if caps:
            matched += 1
        else:
            unmatched += 1
        out.append({
            "address": addr,
            "hosts": hosts,
            "capabilities": caps,
            "shared": len(hosts) > 1,
            "paid_usd": usd(r.get("totalPaid", 0)),
            "calls": int(r.get("payments", 0) or 0),
            "payers": int(r.get("payers", 0) or 0),
            "first": int(r.get("firstPaymentAt", 0) or 0),
            "last": int(r.get("lastPaymentAt", 0) or 0),
        })
    out.sort(key=lambda x: (-x["paid_usd"], -x["calls"], x["address"]))
    return out, matched, unmatched


def hostname(url):
    """The host of a URL, lowercased, with one leading www. removed.

    NOT `.lstrip("www.")`: lstrip takes a SET of characters, so it eats every leading w, dot and
    space it finds — "wwe.tv" becomes "e.tv" and "wow.dev" becomes "dev". A stripped host that is
    still a valid-looking host is the worst kind of wrong here, because it silently joins one
    project's money to another project's page.
    """
    host = str(url).split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0].lower()
    return host[4:] if host.startswith("www.") else host


def host_index(con):
    """host -> capability id, built only from hosts we already store. Exact match, nothing inferred."""
    idx = {}
    try:
        cur = con.execute("SELECT id, homepage, gh_homepage, source_repo FROM capabilities "
                          "WHERE homepage IS NOT NULL OR gh_homepage IS NOT NULL "
                          "OR source_repo IS NOT NULL")
    except Exception:
        return idx
    for cap_id, homepage, gh_homepage, source_repo in cur:
        # A source repo is where the code lives, not where the service answers, so it is the weakest
        # of the three — but a project that publishes an x402 endpoint on its own domain usually
        # lists that domain as its homepage, and an exact host match is an exact host match.
        for url in (homepage, gh_homepage, source_repo):
            if not url or "://" not in str(url):
                continue
            idx.setdefault(hostname(url), cap_id)
    return idx


def main():
    if not ENDPOINT:
        print("  paid-demand: TASHAN_SUBGRAPH_URL is unset — the subgraph is not published yet.")
        print("  Nothing written. This stage reports the chain or it reports nothing.")
        return 0
    try:
        data = query(ENDPOINT)
    except (urllib.error.URLError, RuntimeError, TimeoutError) as e:
        print(f"  paid-demand: subgraph unreachable ({e}) — leaving the last good file in place.")
        return 0

    rows = data.get("receivers") or []
    eco = data.get("economy") or {}
    addr_hosts = hosts_for()

    host_to_cap = {}
    try:
        import build
        host_to_cap = host_index(build.db())
    except Exception:
        pass    # without the DB we still publish the economy; the join is the enrichment, not the point

    records, matched, unmatched = join(rows, addr_hosts, host_to_cap)
    doc = {
        "source": ENDPOINT,
        "economy": {
            "paid_usd": usd(eco.get("totalPaid", 0)),
            "calls": int(eco.get("payments", 0) or 0),
            "receivers_paid": int(eco.get("receiversPaid", 0) or 0),
            "last_block": int(eco.get("lastBlock", 0) or 0),
        },
        "receivers_indexed": len(addr_hosts),
        "receivers_paid": len(records),
        "matched_to_capability": matched,
        "unmatched": unmatched,
        "records": records,
    }
    for path in (OUT, SITE):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(doc, f, indent=2 if path == OUT else None)
            f.write("\n")
    paid = doc["economy"]["paid_usd"]
    print(f"  paid-demand: {len(records)} of {len(addr_hosts)} indexed receivers have been paid · "
          f"${paid:,.2f} across {doc['economy']['calls']} calls · {matched} matched to a capability")
    return 0


def _selftest():
    assert usd(10000) == 0.01, "a cent must not print as 10000"
    assert usd(1_000_000) == 1.0
    assert usd(None) == 0.0 and usd("x") == 0.0, "a missing amount is zero, never a crash"

    addr_hosts = {"0xaaa": ["api.example.com", "alt.example.com"], "0xbbb": ["nobody.example"]}
    host_to_cap = {"api.example.com": "pkg:example-mcp"}
    rows = [
        {"id": "0xAAA", "totalPaid": "2500000", "payments": "12", "payers": "5", "firstPaymentAt": "1", "lastPaymentAt": "9"},
        {"id": "0xbbb", "totalPaid": "10000", "payments": "1", "payers": "1", "firstPaymentAt": "2", "lastPaymentAt": "2"},
        {"id": "0xccc", "totalPaid": "0", "payments": "0", "payers": "0"},
    ]
    recs, matched, unmatched = join(rows, addr_hosts, host_to_cap)

    # The address is the identity; its spelling is not.
    assert recs[0]["address"] == "0xaaa", "a checksummed address must join to its lowercase record"
    assert recs[0]["paid_usd"] == 2.5 and recs[0]["calls"] == 12
    assert recs[0]["capabilities"] == ["pkg:example-mcp"], "an exact host match must attach"
    assert recs[0]["shared"] is True, "an address behind two hosts must say so before money is read off it"

    # THE ERROR THIS PRODUCT CANNOT MAKE: attaching real money to the wrong project.
    b = next(r for r in recs if r["address"] == "0xbbb")
    assert b["capabilities"] == [], "an unknown host must attach to nothing, not to a near match"
    assert matched == 1 and unmatched == 2, f"join accounting is wrong: {matched}/{unmatched}"

    # Biggest first, and a receiver with no payments is still listed rather than silently dropped.
    assert [r["address"] for r in recs][0] == "0xaaa"
    assert any(r["address"] == "0xccc" and r["paid_usd"] == 0.0 for r in recs), \
        "a listed service that has never been paid is the finding, not an omission"

    assert hosts_for("/nonexistent/receivers.json") == {}, "a missing harvest is empty, not fatal"

    # The prefix strip that is not a character strip.
    assert hostname("https://www.example.com/x") == "example.com"
    assert hostname("https://wwe.tv") == "wwe.tv", "lstrip('www.') would have left 'e.tv'"
    assert hostname("https://wow.dev/a") == "wow.dev", "and 'dev'"
    assert hostname("http://api.example.com:8080/p") == "api.example.com"
    print("ok   atomic USDC is never printed as dollars")
    print("ok   money attaches only to a host we already hold, never to a near match")
    print("ok   a service that has never been paid is reported, not hidden")
    print("ok   www. is removed as a prefix, not as a set of characters")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
