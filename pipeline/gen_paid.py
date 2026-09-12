#!/usr/bin/env python3
"""/paid.html — which AI services have actually been paid, from the chain.

THE ONE SIGNAL HERE THAT IS MONEY. Every other number this site publishes is a proxy for demand
measured from outside: npm downloads, publish cadence, stars, how often a server appears in a public
config. All of them can be produced without anyone finding the thing useful. A settled USDC payment
cannot: somebody's agent hit a 402, signed a transfer, and the receipt is on Base forever.

WHAT THIS PAGE SAYS THAT A DIRECTORY CANNOT. Coinbase's Bazaar lists 14,536 x402 services and
publishes no evidence about any of them — not one number saying whether a listed endpoint has ever
been paid once. We asked the chain about every receiver address we could resolve from those listings
and the answer is the page: 997 of 1,079 have been paid at least once, they have settled $247,247
between them, and the MEDIAN service has earned 51 cents in its entire life. Two thirds of all volume
belongs to one receiver.

That last set of facts is why this is a distribution and not a leaderboard. A total is the one
statistic a concentrated economy always passes, and "$247k settled" read on its own would tell a
visitor the opposite of what is happening.

READ OVER A PATH THE READER CAN REPRODUCE. The figures come from a subgraph on The Graph Network,
queried through The Graph's own Subgraph MCP server — the same tool call, with the same arguments,
that any agent can make. The page prints the call. An evidence product should be checkable by the
means it recommends to others, and "run this yourself" is a stronger claim than "trust our exporter".

    python3 pipeline/gen_paid.py            # write web/paid.html from web/data/demand.json
    python3 pipeline/gen_paid.py --selftest # pure render, no data, no network
"""
import datetime as dt, html, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assets                                                    # noqa: E402
import chrome                                                    # noqa: E402

BASE = "https://tashan.sh"
OUT = os.path.join(ROOT, "web", "paid.html")
DEMAND = os.path.join(ROOT, "web", "data", "demand.json")
EXPORT = os.path.join(ROOT, "web", "data", "capabilities.json")
SUBGRAPH_MCP = "https://subgraphs.mcp.thegraph.com/sse"

esc = lambda s: html.escape(str(s), quote=True)


def money(v):
    """Dollars, at the precision the number deserves. A $0.51 median must not round to $1, and
    $166,658.8173 must not print four decimals as if the cents were the point."""
    if v is None:
        return "—"
    if v == 0:
        return "$0.00"
    if v < 0.01:
        return "<$0.01"
    if v < 100:
        return f"${v:,.2f}"
    return f"${v:,.0f}"


def pct(x):
    return f"{round((x or 0) * 100)}%"


def rows_from(demand, export):
    """The capabilities with an attributable receipt, richest first.

    ATTRIBUTABLE, not merely matched — paid_demand.attributable() is the gate, and it holds that
    volume is a property of an ADDRESS. An address publishing one host belongs to one service; an
    address shared by several cannot be split by anything on chain. blockrun.ai is the case in both
    directions: one address publishing only blockrun.ai has settled $166,658, and a second address
    publishing blockrun.ai AND api.aidress.ai has settled $130 that belongs to neither in particular.
    The shared rows are counted on the page and deliberately not ranked on it.
    """
    import paid_demand
    caps = {c["id"]: c for c in (export.get("capabilities") or [])}
    hosts = {}
    for r in demand.get("records") or []:
        for cid in r.get("capabilities") or []:
            hosts.setdefault(cid, []).extend(r.get("hosts") or [])
    out = []
    # ONE ROW PER CAPABILITY, summed over its addresses. Three of ours publish two payTo addresses,
    # and a row each made the same server appear twice with different numbers and its real total
    # appear nowhere.
    for cid, a in paid_demand.per_capability(demand.get("records") or []).items():
        c = caps.get(cid)
        if not c:
            continue                         # exported catalog is the published set; skip the rest
        out.append({
            "id": cid,
            "slug": c.get("slug") or "",
            "name": c.get("label") or c.get("name") or cid,
            "kind": c.get("kind") or "",
            "score": c.get("tashan_score"),
            "paid_usd": a["paid_usd"],
            "calls": a["calls"],
            "host": (sorted(set(hosts.get(cid) or [])) or [""])[0],
            "addresses": a["addresses"],
        })
    out.sort(key=lambda x: (-x["paid_usd"], -x["calls"], x["name"].lower()))
    return out


def stat_block(items):
    h = ['<dl class="stat stat--4">']
    for value, label, why in items:
        h.append('<div class="stat__i"><dt class="stat__n mono">' + esc(value) + "</dt>"
                 '<dd class="stat__l">' + esc(label)
                 + '<span class="mnote stat__w o-70"> ' + esc(why) + "</span></dd></div>")
    h.append("</dl>")
    return "\n".join(h)


def table(rows):
    """The ranked table, structurally the same row as the board — see gen_hubs.table()'s docstring.

    Money column first, because it is why the reader is here, and the tashan score beside it because
    the interesting thing is how little they agree: the top earner scores 71, and plenty of 80s have
    never been paid a cent.
    """
    if not rows:
        return ('<p class="lede">No capability in the published catalog has an attributable '
                "receipt yet. When one does, it appears here — with the address it was paid at.</p>")
    out = ['<div class="board"><div class="board__scroll"><table class="board__t"><thead><tr>'
           '<th class="rank" scope="col">#</th><th scope="col">Capability</th>'
           '<th class="num" scope="col" title="Settled USDC received at this service\'s own payment '
           'address, all time, on Base">Settled</th>'
           '<th class="num" scope="col" title="Number of settled x402 payments">Payments</th>'
           '<th class="num" scope="col" title="Settled volume divided by payments">Per call</th>'
           '<th class="num" scope="col" title="The tashan score — upkeep, freshness and adoption. '
           'Payment is deliberately not an input to it">tashan score</th></tr></thead><tbody>']
    for i, r in enumerate(rows, 1):
        href = "/capability/" + r["slug"] + ".html"
        t = r["score"]
        score = ('<span class="unrated">not scored yet</span>' if t is None
                 else '<span class="sig__val">' + str(int(round(t))) + "</span>")
        per = (r["paid_usd"] / r["calls"]) if r["calls"] else None
        out.append(
            '<tr data-href="' + href + '">'
            '<td class="rank">' + str(i) + "</td>"
            '<td><div class="cap__name"><a class="cap__link" href="' + esc(href) + '">'
            + esc(r["name"]) + "</a>"
            ' <span class="tag">' + esc(r["kind"]) + "</span></div>"
            '<div class="mnote o-70 mono">' + esc(r["host"])
            + (esc(f' · {len(r["addresses"])} payment addresses') if len(r["addresses"]) > 1 else "")
            + "</div></td>"
            '<td class="num"><span class="ev">' + esc(money(r["paid_usd"])) + "</span></td>"
            '<td class="num">' + (f'{r["calls"]:,}' if r["calls"]
                                  else '<span class="num--dim">never paid</span>') + "</td>"
            '<td class="num">' + ('<span class="num--dim">' + esc(money(per)) + "</span>"
                                  if per is not None else '<span class="num--dim">—</span>')
            + "</td>"
            '<td class="num"><div class="sig' + ("" if t is not None else " sig--none") + '">'
            + score + '<span class="bar" data-w="' + str(int(round(t or 0))) + '"><i></i></span>'
            "</div></td></tr>")
    out.append("</tbody></table></div></div>")
    return "".join(out)


def render(demand, export, today):
    eco = demand.get("economy") or {}
    rows = rows_from(demand, export)
    listed = demand.get("receivers_indexed") or 0
    paid = eco.get("receivers_paid") or 0
    never = eco.get("receivers_never_paid") or 0
    total = eco.get("paid_usd") or 0.0
    calls = eco.get("calls") or 0
    median = eco.get("median_usd")
    shared = len([r for r in (demand.get("records") or [])
                  if r.get("capabilities") and r.get("shared")])

    lede = (f"Directories list thousands of x402 services and publish no evidence about any of them. "
            f"We asked the chain about every payment address we could resolve.")
    finding = (f"{paid:,} of {listed:,} have been paid at least once \u2014 {never} never have. "
               f"Together: {money(total)} across {calls:,} payments. The median service has earned "
               f"{money(median)}.")

    lds = [{
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "Paid demand for AI services — settled x402 payments on Base",
        "description": lede + " " + finding,
        "url": BASE + "/paid.html",
        "isAccessibleForFree": True,
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": {"@type": "Organization", "name": "tashan", "url": BASE},
        "dateModified": today,
        "measurementTechnique": BASE + "/methodology.html",
        "variableMeasured": [
            {"@type": "PropertyValue", "name": "Settled volume (USD, all time)", "value": total},
            {"@type": "PropertyValue", "name": "Settled payments", "value": calls},
            {"@type": "PropertyValue", "name": "Median receiver (USD, all time)", "value": median},
            {"@type": "PropertyValue", "name": "Listed receivers never paid", "value": never},
        ],
    }]

    h = [
        '<main class="wrap" id="main">',
        '<p class="eyebrow mono">— PAID DEMAND</p>',
        '<h1 class="h1">Which AI services have actually been paid.</h1>',
        '<p class="lede">' + esc(lede) + "</p>",
        '<p class="lede">' + esc(finding) + "</p>",
        '<p class="mono fs-sm o-70">Read from a subgraph on The Graph Network, through The '
        'Graph’s Subgraph MCP server. The call is printed below — re-run it yourself. '
        'Free, CC BY 4.0.</p>',

        '<h2 class="h2">The shape of it</h2>',
        stat_block([
            (money(total), "settled, all time", f"across {calls:,} payments"),
            (money(median), "the median service", f"{eco.get('under_1_usd', 0)} have earned under $1"),
            (pct(eco.get("top1_share")), "is one receiver", f"the top five are {pct(eco.get('top5_share'))}"),
            (f"{never}", "listed but never paid", f"of {listed:,} addresses we asked about"),
        ]),
        '<p class="mnote o-70">A sum is the one statistic a concentrated economy always passes. '
        'Here is the distribution instead.</p>',
        '<p class="mnote o-70">Mean payment: ' + esc(money(eco.get("mean_payment_usd")))
        + '. Fractions of a cent, at enormous volume.</p>',
        '<div class="board"><div class="board__scroll"><table class="board__t"><thead><tr>'
        '<th scope="col">All-time earnings</th><th class="num" scope="col">Receivers</th>'
        '<th scope="col">Share of the paid set</th></tr></thead><tbody>',
    ]
    bands = [("under $1", eco.get("under_1_usd", 0)),
             ("under $10", eco.get("under_10_usd", 0)),
             ("$1,000 or more", eco.get("over_1000_usd", 0))]
    for label, n in bands:
        share = int(round(100 * n / max(paid, 1)))
        h.append('<tr><td>' + esc(label) + '</td><td class="num"><span class="ev">' + f"{n:,}"
                 + '</span></td><td><div class="sig"><span class="sig__val">' + f"{share}%"
                 + '</span><span class="bar" data-w="' + str(share) + '"><i></i></span></div>'
                 "</td></tr>")
    h += [
        "</tbody></table></div></div>",

        '<h2 class="h2">The servers we measure that have been paid</h2>',
        '<p class="lede">' + esc(
            f"{len(rows)} of them publish a payment address of their own, so the receipts are "
            f"theirs and nobody else\u2019s.") + "</p>",
        table(rows),
        '<p class="mnote o-70">Payment is <b>not</b> an input to the tashan score. '
        '“Someone pays for this” and “this is well made” are different claims — '
        'the top earner here scores 71.</p>',

        '<h2 class="h2">What this does not mean</h2>',
        '<ul class="bul">'
        '<li><b>Charging is not being paid.</b> A service can publish a price and never settle a '
        'single call. Both facts are on this page and they are different columns.</li>'
        '<li><b>Unpaid is not bad.</b> Almost every MCP server is free by design; an absent row here '
        'says nothing about quality. It says nobody has paid this address, because nobody was asked '
        'to.</li>'
        '<li><b>Volume belongs to an address, not to a project.</b> Where one payment address is '
        'shared by several services the chain cannot separate them, so those receipts are counted in '
        'the totals above and never attributed to a capability. '
        + (f"{shared} matched receivers are excluded from the table for exactly that reason."
           if shared else "")
        + "</li>"
        '<li><b>This is Base, and x402 only.</b> Other chains, other payment rails and private '
        'billing are invisible here. We publish what is on the ledger we can read.</li>'
        "</ul>",

        '<h2 class="h2">Re-run it yourself</h2>',
        '<p class="lede">Two Graph products, composed: a subgraph on The Graph Network, read '
        'through The Graph’s Subgraph MCP server. Point any MCP client at it and you get the '
        'same rows.</p>',
        '<div class="code"><code class="mono">' + esc(SUBGRAPH_MCP) + "<br>"
        + esc('tool: execute_query_by_subgraph_id') + "<br>"
        + esc('subgraph_id: ' + (demand.get("source", "").split()[1]
                                 if demand.get("via") == "subgraph-mcp"
                                 and len(demand.get("source", "").split()) > 1 else "—"))
        + "<br><br>"
        + esc('{ x402AddressSummaries(first: 1000, where: {role: RECIPIENT}) {')
        + "<br>" + esc('    address totalPayments totalVolume } }')
        + "</code></div>",
        '<p class="mnote o-70">Addresses from the Bazaar’s own listings. Receipts from the '
        'chain. The join is an <b>exact host match</b> against a homepage or repository we already '
        'hold — never a fuzzy name match.</p>',
        '<p class="mnote o-70">Source: ' + esc(demand.get("source") or "not read yet")
        + ". Recomputed nightly.</p>",
        "</main>",
    ]
    return lds, "\n".join(h), lede + " " + finding


def main():
    if not os.path.exists(DEMAND):
        print("paid: web/data/demand.json missing — run pipeline/paid_demand.py first")
        return 0
    demand = json.load(open(DEMAND, encoding="utf-8"))
    export = json.load(open(EXPORT, encoding="utf-8")) if os.path.exists(EXPORT) else {}
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    lds, body, lede = render(demand, export, today)

    import gen_hubs
    eco = demand.get("economy") or {}
    doc = gen_hubs.head(
        "Who actually gets paid · tashan",
        (f"{eco.get('receivers_paid', 0):,} of {demand.get('receivers_indexed', 0):,} listed x402 "
         f"services have ever been paid. {money(eco.get('paid_usd'))} settled; the median service "
         f"has earned {money(eco.get('median_usd'))}.")[:155],
        BASE + "/paid.html", lds)
    doc += body + chrome.footer_html()
    doc += '<script src="/js/site.js?v=' + str(assets.V) + '" defer></script>\n</body>\n</html>\n'
    open(OUT, "w", encoding="utf-8").write(doc)
    n = len(rows_from(demand, export))
    print(f"paid: {eco.get('receivers_paid', 0)} paid receivers, {n} attributable capabilities "
          f"-> web/paid.html")
    return 0


def _selftest():
    """Pure render. The money formatter is the part that can lie, so it is the part with cases."""
    assert money(0) == "$0.00", "a measured zero must print as zero, not as a dash"
    assert money(None) == "—", "an unmeasured value must never print as $0.00"
    assert money(0.004) == "<$0.01", money(0.004)
    assert money(0.51) == "$0.51" and money(36.528) == "$36.53"
    assert money(166658.8173) == "$166,659", money(166658.8173)
    assert pct(0.6741) == "67%" and pct(None) == "0%"

    # A shared address must never reach the table, however much money it carries.
    demand = {"receivers_indexed": 3, "via": "subgraph-mcp",
              "source": "subgraph ABC via subgraphs.mcp.thegraph.com",
              "economy": {"paid_usd": 100.0, "calls": 10, "receivers_paid": 2,
                          "receivers_never_paid": 1, "median_usd": 0.5, "top1_share": 0.9,
                          "top5_share": 1.0, "under_1_usd": 1, "under_10_usd": 1,
                          "over_1000_usd": 0, "mean_payment_usd": 10.0},
              "records": [
                  {"address": "0xa", "hosts": ["one.dev"], "capabilities": ["pkg:one"],
                   "shared": False, "attributable": True, "paid_usd": 90.0, "calls": 9},
                  {"address": "0xb", "hosts": ["two.dev", "three.dev"], "capabilities": ["pkg:two"],
                   "shared": True, "attributable": False, "paid_usd": 10.0, "calls": 1},
                  {"address": "0xc", "hosts": ["gone.dev"], "capabilities": [], "shared": False,
                   "attributable": False, "paid_usd": 0.0, "calls": 0},
              ]}
    export = {"capabilities": [
        {"id": "pkg:one", "slug": "pkg-one", "name": "one", "kind": "npm", "tashan_score": 71.0},
        {"id": "pkg:two", "slug": "pkg-two", "name": "two", "kind": "npm", "tashan_score": 80.0},
    ]}
    rows = rows_from(demand, export)
    assert [r["id"] for r in rows] == ["pkg:one"], rows
    print("  ok — a shared payment address is never attributed to a capability")

    # Two single-host addresses for one capability must SUM into one row, not rank as two.
    two = dict(demand, records=demand["records"] + [
        {"address": "0xd", "hosts": ["one-alt.dev"], "capabilities": ["pkg:one"],
         "shared": False, "attributable": True, "paid_usd": 10.0, "calls": 1}])
    r2 = rows_from(two, export)
    assert len(r2) == 1 and r2[0]["paid_usd"] == 100.0 and r2[0]["calls"] == 10, r2
    assert len(r2[0]["addresses"]) == 2
    print("  ok — a capability with two payment addresses is one row, summed")

    # A capability that is not in the published export must not appear either, or the page links
    # to a dossier that does not exist — the orphan class tests/test_links.py exists to catch.
    assert rows_from(demand, {"capabilities": []}) == []
    print("  ok — no row is rendered for a capability absent from the export")

    lds, body, lede = render(demand, export, "2026-09-13")
    assert "$0.50" in body, "the median must survive to the page"
    assert "1 never have" in body, "the never-paid count is the finding; it must be stated"
    assert "an input to the tashan score" in body, "the firewall note must be on the page"
    assert "style=" not in body, "an inline style attribute is dropped by the CSP on this site"
    assert "x402AddressSummaries" in body, "the page must print the call it made"
    assert lds[0]["@type"] == "Dataset" and lds[0]["isAccessibleForFree"] is True
    print("  ok — renders with the reproduction call, no inline styles, Dataset JSON-LD")

    # The empty state is a real state: the subgraph is unread until a key exists.
    empty = {"receivers_indexed": 0, "economy": {}, "records": []}
    _, body2, _ = render(empty, {"capabilities": []}, "2026-09-13")
    assert "No capability in the published catalog has an attributable receipt yet" in body2
    print("  ok — the unread state says so instead of printing zeros as findings")


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
