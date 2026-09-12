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
# Printed as the source when nothing has been read yet, so the file never claims a source.
SSE_NOTE = "not read yet — set GRAPH_API_KEY to read via The Graph's Subgraph MCP"

# THE X402 INDEX WE READ, and why it is not ours. `../subgraph` indexes USDC transfers to the payTo
# addresses we harvested; this one indexes the x402 settlement events themselves (EIP-3009
# AuthorizationUsed and Permit2), which is the better index of the two — it separates batch
# settlements from single payments and escrow legs from direct ones, and it is already published on
# The Graph Network where anyone can re-run our queries. Using it instead of waiting for ours is not
# a shortcut: the whole argument for publishing measurements over a standard interface is that you
# can then READ over one, and a second independent index of the same economy is a cross-check rather
# than a duplicate. Ours stays, and disagreement between them is a finding, not an error.
X402_SUBGRAPH = os.environ.get("X402_SUBGRAPH_ID", "Cb56epg3EvQ6JRpPfknbkM54QxpzTvLa7mwKNQQfUyoj")
BATCH = 150               # addresses per query; the gateway is fine with more, this keeps URLs sane

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


def fetch():
    """Read the subgraph, preferring The Graph's own Subgraph MCP server over a bespoke HTTP call.

    TWO GRAPH PRODUCTS, COMPOSED — and the reason is not the prize. Published to Subgraph Studio and
    served by The Graph Network, then READ through https://subgraphs.mcp.thegraph.com/sse with the
    same tool call any agent would make. A number about payments that anyone can re-fetch over the
    public standard interface is worth more than the same number from our private exporter, and the
    site says which path produced it.

    Returns (data, via). `via` is published, so a reader is never left guessing whether the figure
    came over the composed path or the fallback.
    """
    if os.environ.get("GRAPH_API_KEY") and os.environ.get("TASHAN_SUBGRAPH_ID"):
        import subgraph_mcp
        return subgraph_mcp.query(QUERY), "subgraph-mcp"
    if ENDPOINT:
        return query(ENDPOINT), "gateway"
    return None, None


def receipts(addrs, subgraph_id=X402_SUBGRAPH):
    """Settled x402 payments for exactly the addresses we asked about, through Subgraph MCP.

    ASKED BY ADDRESS, NOT BY LEADERBOARD. Ordering by volume and taking the top 1,000 answers "who
    earns most", which is a different question and the one that flatters the economy: it cannot tell
    you that 592 of the services a directory lists have earned under a dollar, because those are
    exactly the rows a top-N query drops. Every listed receiver is asked about, in batches, and a
    receiver the chain does not know is reported as never paid rather than omitted.
    """
    import subgraph_mcp
    found = {}
    with subgraph_mcp.Session() as s:
        for i in range(0, len(addrs), BATCH):
            batch = addrs[i:i + BATCH]
            q = ("{ x402AddressSummaries(first: 1000, where: {role: RECIPIENT, address_in: ["
                 + ",".join('"%s"' % a for a in batch)
                 + "]}) { address totalPayments totalVolume firstPaymentTimestamp"
                   " lastPaymentTimestamp } }")
            out = s.call_tool("execute_query_by_subgraph_id",
                              {"subgraph_id": subgraph_id, "query": q})
            if not isinstance(out, dict):
                raise RuntimeError(f"unexpected payload: {str(out)[:160]}")
            if out.get("errors"):
                raise RuntimeError(f"subgraph: {out['errors'][0].get('message', 'query failed')}")
            for r in (out.get("data") or {}).get("x402AddressSummaries") or []:
                found[str(r["address"]).lower()] = r
    return found


def distribution(paid_usd):
    """What a total hides. A sum is the one statistic a concentrated economy can always pass.

    $247,247 settled sounds like a market. Two thirds of it is ONE receiver, 89% is five, and the
    median service has earned 51 cents in its life. Publishing the total alone would be the same
    mistake as ranking by stars: technically true, and it would tell a reader the opposite of what
    is happening. So the page gets the shape, not the headline — and these are the numbers that
    make the shape checkable.
    """
    v = sorted(x for x in paid_usd if x is not None)
    total = round(sum(v), 4)
    if not v:
        return {"total_usd": 0.0, "receivers": 0}
    mid = len(v) // 2
    median = v[mid] if len(v) % 2 else round((v[mid - 1] + v[mid]) / 2, 4)
    return {
        "total_usd": total,
        "receivers": len(v),
        "median_usd": median,
        "top1_share": round(v[-1] / total, 4) if total else 0.0,
        "top5_share": round(sum(v[-5:]) / total, 4) if total else 0.0,
        "under_1_usd": sum(1 for x in v if x < 1),
        "under_10_usd": sum(1 for x in v if x < 10),
        "over_1000_usd": sum(1 for x in v if x >= 1000),
    }


def attributable(record):
    """Whether this receiver's money may be printed against a capability.

    THE ONE RULE THAT KEEPS THIS HONEST. Volume is a property of an ADDRESS. An address that
    published one host belongs to one service and the money is that service's; an address shared by
    several hosts cannot be split by anything on chain, so attaching its total to one capability
    would invent a number. blockrun.ai is the real case both ways: one address publishing only
    blockrun.ai has settled $166,658 across 8.7M calls, and a SECOND address publishing both
    blockrun.ai and api.aidress.ai has settled $130 that belongs to neither in particular.
    Shared receivers are still published — as an address-level fact, with the sharing stated.
    """
    return bool(record.get("capabilities")) and not record.get("shared")


def charging(addr_hosts, host_to_cap):
    """Which capabilities PUBLISH a price, before anyone has been paid — the half that needs no chain.

    Charging is not being paid and must never be printed as if it were, but it is a fact about the
    field that nothing else publishes: of 1,079 x402 receiver addresses harvested from the Bazaar,
    these are the ones whose host we already hold as a capability's own homepage or repository. It
    comes from a file in the repo and the database, so it is publishable tonight, with the payment
    columns explicitly unmeasured rather than zero — a zero here would read as "nobody has ever paid
    for this", which is a claim about the world and not about our coverage.
    """
    out = []
    for addr, hosts in sorted(addr_hosts.items()):
        caps = sorted({host_to_cap[h] for h in hosts if h in host_to_cap})
        if not caps:
            continue
        out.append({"address": addr, "hosts": hosts, "capabilities": caps,
                    "shared": len(hosts) > 1, "paid_measured": False,
                    "paid_usd": None, "calls": None, "payers": None, "first": None, "last": None})
    return out


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


def build_records(addr_hosts, host_to_cap, found):
    """One row per LISTED receiver — paid or not. The unpaid rows are the finding.

    A directory of 14,536 x402 services publishes no evidence about any of them. The interesting
    output of asking the chain about every one is not the leaderboard; it is that 82 of the 1,079 we
    could check have never been paid at all and 592 of the rest have earned under a dollar. Dropping
    those rows would turn a measurement into an advertisement.
    """
    out = []
    for addr in sorted(addr_hosts):
        hosts = addr_hosts[addr]
        caps = sorted({host_to_cap[h] for h in hosts if h in host_to_cap})
        r = found.get(addr)
        rec = {
            "address": addr,
            "hosts": hosts,
            "capabilities": caps,
            "shared": len(hosts) > 1,
            "paid_measured": True,
            "paid_usd": usd(r["totalVolume"]) if r else 0.0,
            "calls": int(r["totalPayments"]) if r else 0,
            "payers": None,          # the settlement index aggregates by recipient, not by payer
            "first": int(r["firstPaymentTimestamp"]) if r else None,
            "last": int(r["lastPaymentTimestamp"]) if r else None,
        }
        rec["attributable"] = attributable(rec)
        out.append(rec)
    out.sort(key=lambda x: (-x["paid_usd"], -x["calls"], x["address"]))
    return out


def per_capability(records):
    """Sum a capability's attributable addresses. A project may publish more than one payTo.

    Three of ours do. Writing one row per address made the same capability appear twice with
    different numbers and its real total appear nowhere — the "one thing ranked twice at two
    different numbers" defect this repo already has a test for, arriving through a new door. Money
    adds, the first payment is the earliest and the last is the latest, and every address is kept so
    the page can say how many there were rather than implying a single one.
    """
    agg = {}
    for r in records:
        if not r.get("attributable"):
            continue
        for cap in r["capabilities"]:
            a = agg.setdefault(cap, {"paid_usd": 0.0, "calls": 0, "addresses": [],
                                     "first": None, "last": None})
            a["paid_usd"] = round(a["paid_usd"] + (r["paid_usd"] or 0.0), 6)
            a["calls"] += r["calls"] or 0
            a["addresses"].append(r["address"])
            for k, pick in (("first", min), ("last", max)):
                if r.get(k) is not None:
                    a[k] = r[k] if a[k] is None else pick(a[k], r[k])
    for a in agg.values():
        a["addresses"].sort()
    return agg


def store(records):
    """Write the per-capability money facts to the DB, so every surface reads one source.

    Only attributable rows, by construction — see attributable(). The columns live beside every other
    signal because that is how the export, the dossiers, the hubs, the badges and the CLI all pick a
    field up for free; a JSON file read by one page would have been a second source of truth, and
    this repo has paid for that mistake before.
    """
    try:
        import build
    except Exception:
        return 0
    con = build.db()
    n = 0
    for cap, a in per_capability(records).items():
        cur = con.execute(
            "UPDATE capabilities SET paid_usd=?, paid_calls=?, paid_address=?, "
            "paid_first=?, paid_last=?, paid_seen_at=datetime('now') WHERE id=?",
            (a["paid_usd"], a["calls"], ",".join(a["addresses"]), a["first"], a["last"], cap))
        n += cur.rowcount or 0      # rowcount, not total_changes: the latter is cumulative
    con.commit()
    return n


def main():
    addr_hosts = hosts_for()
    host_to_cap = {}
    try:
        import build
        host_to_cap = host_index(build.db())
    except Exception:
        pass    # without the DB we still publish the economy; the join is the enrichment, not the point

    # THE STAGE USED TO WRITE NOTHING WITHOUT A PUBLISHED SUBGRAPH, and that was a mistake of
    # sequencing rather than of honesty: the half that says WHO CHARGES needs no chain at all, and
    # withholding it meant the whole signal was invisible until a wallet had been connected.
    charges = charging(addr_hosts, host_to_cap)
    found, via = {}, None
    if os.environ.get("GRAPH_API_KEY"):
        try:
            found = receipts(sorted(addr_hosts))
            via = "subgraph-mcp"
        except Exception as e:
            print(f"  paid-demand: Subgraph MCP unreachable ({e}) — publishing who charges only.")
    elif ENDPOINT:
        try:
            data = query(ENDPOINT)
            found = {str(r["id"]).lower(): {"address": r["id"], "totalVolume": r.get("totalPaid", 0),
                                            "totalPayments": r.get("payments", 0),
                                            "firstPaymentTimestamp": r.get("firstPaymentAt", 0),
                                            "lastPaymentTimestamp": r.get("lastPaymentAt", 0)}
                     for r in (data.get("receivers") or [])}
            via = "gateway"
        except Exception as e:
            print(f"  paid-demand: gateway unreachable ({e}) — publishing who charges only.")

    if via:
        records = build_records(addr_hosts, host_to_cap, found)
        dist = distribution([r["paid_usd"] for r in records if r["paid_usd"]])
        paid_rows = [r for r in records if r["paid_usd"] or r["calls"]]
        economy = {
            "paid_usd": dist["total_usd"],
            "calls": sum(r["calls"] for r in records),
            "receivers_paid": len(paid_rows),
            "receivers_never_paid": len(records) - len(paid_rows),
            "mean_payment_usd": round(dist["total_usd"] / max(sum(r["calls"] for r in records), 1), 6),
            **{k: v for k, v in dist.items() if k != "total_usd"},
        }
        stored = store(records)
    else:
        records, economy, stored = charges, None, 0

    attributed = [r for r in records if r.get("attributable")]
    doc = {
        "source": (f"subgraph {X402_SUBGRAPH} via subgraphs.mcp.thegraph.com" if via == "subgraph-mcp"
                   else ENDPOINT or SSE_NOTE),
        "via": via,
        "paid_measured": bool(via),
        "economy": economy,
        "receivers_indexed": len(addr_hosts),
        "receivers_paid": economy["receivers_paid"] if economy else 0,
        "charging_capabilities": len({c for r in charges for c in r["capabilities"]}),
        "paid_capabilities": len({c for r in attributed for c in r["capabilities"]}),
        "matched_to_capability": len([r for r in records if r["capabilities"]]),
        "unmatched": len([r for r in records if not r["capabilities"]]),
        "records": records,
    }
    # NEVER REPLACE A CHAIN READ WITH A GUESS. Without a gateway key this stage can still publish
    # who CHARGES, and that is worth publishing — but it is strictly less than what is already on
    # disk if a previous run read the chain. A nightly running without the key would otherwise
    # silently blank every settled figure on /paid.html and leave the page saying nobody has been
    # paid, which is a claim about the world made out of a missing environment variable.
    if not via and os.path.exists(SITE):
        try:
            with open(SITE) as f:
                prev = json.load(f)
        except (OSError, ValueError):
            prev = {}
        if prev.get("paid_measured"):
            print("  paid-demand: no key this run — KEEPING the last chain read "
                  f"({prev.get('receivers_paid', 0)} paid receivers, source: {prev.get('source')}). "
                  "Set GRAPH_API_KEY to refresh it.")
            return 0

    for path in (OUT, SITE):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(doc, f, indent=2 if path == OUT else None)
            f.write("\n")
    if economy:
        print(f"  paid-demand: via {via} · {economy['receivers_paid']} of {len(addr_hosts)} listed "
              f"receivers have been paid, {economy['receivers_never_paid']} never · "
              f"${economy['paid_usd']:,.2f} across {economy['calls']:,} payments · median receiver "
              f"${economy.get('median_usd', 0):,.2f} · top receiver {economy.get('top1_share', 0):.0%} "
              f"of all volume · {doc['paid_capabilities']} capabilities attributable ({stored} stored)")
    else:
        print(f"  paid-demand: no chain read (set GRAPH_API_KEY) — published "
              f"{doc['charging_capabilities']} capabilities that CHARGE, of {len(addr_hosts)} "
              f"listed receivers, with payment columns unmeasured")
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
