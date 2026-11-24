#!/usr/bin/env python3
"""Render the dated directory and chain observations published in web/data/demand.json."""
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
    """Alphabetical entries with an unambiguous catalog match, summed across addresses."""
    import paid_demand
    caps = {c["id"]: c for c in (export.get("capabilities") or [])}
    hosts = {}
    for r in demand.get("records") or []:
        if not r.get("attributable"):
            continue
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
    out.sort(key=lambda x: (x['name'].casefold(), x['id']))
    return out


def stat_block(items):
    h = ['<dl class="stat">']
    for value, label, why in items:
        h.append('<div class="stat__i"><dt class="stat__n mono">' + esc(value) + "</dt>"
                 '<dd class="stat__l">' + esc(label)
                 + '<span class="mnote stat__w o-70"> ' + esc(why) + "</span></dd></div>")
    h.append("</dl>")
    return "\n".join(h)


def table(rows):
    """Render the source addresses for each catalog match."""
    if not rows:
        return '<p>No catalog matches for this sample.</p>'
    out = ['<div class="board"><div class="board__scroll"><table class="board__t"><thead><tr>'
           '<th scope="col">Catalog entry and receiver</th>'
           '<th class="num" scope="col">Volume (USDC)</th><th class="num" scope="col">Indexed events</th>'
           '<th class="num" scope="col">Mean per event</th></tr></thead><tbody>']
    for r in rows:
        href = "/capability/" + r["slug"] + ".html"
        per = (r["paid_usd"] / r["calls"]) if r["calls"] else None
        out.append(
            '<tr data-href="' + href + '">'
            '<td><div class="cap__name"><a class="cap__link" href="' + esc(href) + '">'
            + esc(r["name"]) + "</a>"
            ' <span class="tag">' + esc(r["kind"]) + "</span></div>"
            # THE RECEIPT, ONE CLICK AWAY. The whole argument of this page is that these figures
            # came off a public ledger rather than out of our exporter, and until now a reader had to
            # take that on faith — the addresses were summed and then thrown away. Linking the first
            # one to a block explorer turns "trust us" into "go and look": the USDC transfers are
            # right there, in the same order of magnitude, under somebody else's domain.
            '<div class="mnote o-70 mono">' + esc(r["host"])
            + ''.join(' · <a class="link" rel="nofollow noopener" href="https://basescan.org/address/' + esc(address) + '#tokentxns">' + esc(address[:6] + '…' + address[-4:]) + '</a>' for address in r['addresses'])
            + "</div></td>"
            '<td class="num"><span class="ev">' + esc(money(r["paid_usd"])) + "</span></td>"
            '<td class="num">' + (f'{r["calls"]:,}' if r["calls"]
                                  else '<span class="num--dim">0</span>') + "</td>"
            '<td class="num">' + ('<span class="num--dim">' + esc(money(per)) + "</span>"
                                  if per is not None else '<span class="num--dim">—</span>')
            + "</td></tr>")
    out.append("</tbody></table></div></div>")
    return "".join(out)


def render(demand, export, today):
    directory = demand.get('directory') or {}
    providers = demand.get('providers') or {}
    description = 'Payment offers reported by Coinbase Bazaar, PayAI and the Machine Payments Protocol directory, plus indexed Base USDC activity at sampled receiver addresses.'
    dataset = {'@context': 'https://schema.org', '@type': 'Dataset', 'name': 'Agent payment activity',
               'description': description, 'url': BASE + '/paid', 'isAccessibleForFree': True,
               'license': 'https://creativecommons.org/licenses/by/4.0/',
               'distribution': {'@type': 'DataDownload', 'contentUrl': BASE + '/data/demand.json', 'encodingFormat': 'application/json'}}
    def dated(value):
        return esc(value[:19].replace('T', ' ') + (' UTC' if 'T' in value else '')) if value else 'Unavailable'
    h = ['<main class="wrap payment-activity" id="main"><h1 class="h1">Agent payment activity</h1>',
         '<p class="lede">Where agents can buy services, which resources report recent calls, and how much USDC reached sampled addresses on Base.</p>',
         '<p><a class="link" href="/data/demand.json">Download observations and source dates (JSON)</a></p>',
         '<h2 class="h2">Discovery coverage</h2>']
    if providers.get('coinbase') and providers.get('payai'):
        h.append('<table class="board__t payment-distribution"><thead><tr><th scope="col">Source</th><th scope="col">Published offers</th></tr></thead><tbody>')
        for key, label in [('coinbase', 'Coinbase Bazaar'), ('payai', 'PayAI')]:
            obs = providers[key]
            h.append(f'<tr><td><a class="link" href="{esc(obs["source"])}?limit=100">{label}</a></td><td>{obs["observed_resources"]:,} resource URLs · {obs["base_usdc_resources"]:,} offer Base USDC</td></tr>')
        mpp = providers.get('mpp') or {}
        methods = ', '.join(f'{esc(k)} ({v:,})' for k,v in sorted((mpp.get('methods') or {}).items()))
        coverage = f'{mpp["services"]:,} listed services · {methods}' if 'services' in mpp else 'Coverage unavailable'
        h.append(f'<tr><td><a class="link" href="https://mpp.dev/services">MPP directory</a></td><td>{coverage}</td></tr></tbody></table>')
        h.append(f'<p>x402 scan {dated(directory.get("harvested"))}. {providers["x402_union_urls"]:,} distinct resource URLs across both directories, including {providers["x402_overlap_urls"]:,} exact URLs present in both. One service can publish many URLs.</p>')
        h.append(f'<p>MPP checked {dated(mpp.get("checked_at"))}. Each listed service may offer several payment methods. '+('The latest fetch failed. ' if mpp.get('status') == 'retained' else '')+'Usage and settlement volume for those methods are unmeasured here.</p>')
    else:
        h.append('<p>Multi-provider discovery coverage is unavailable for this snapshot.</p>')
    h.append('<h2 class="h2">Coinbase Bazaar · trailing 30 days</h2>')
    if 'activity_reported' in directory:
        missing = directory['base_usdc_resources'] - directory['activity_reported']
        h += ['<p>Directory checked ' + dated(directory.get('harvested')) + '.</p>', stat_block([
            (f"{directory['observed_resources']:,}", 'Distinct resource URLs observed', 'across the directory scan'),
            (f"{directory['base_usdc_resources']:,}", 'Resources offering Base USDC', f"{directory['receivers']:,} distinct receiver addresses"),
            (f"{directory['active_resources_30d']:,}", 'Resources reporting one or more calls', f"of {directory['activity_reported']:,} reporting a 30-day count"),
        ]), f'<p class="mnote">{missing:,} eligible resources had no call count. The activity count belongs to a resource and can include calls on other rails it offers. Listings can change during pagination.</p>']
    else:
        h.append('<p>Directory activity counts are unavailable for this snapshot.</p>')
    h.append('<h2 class="h2">Base USDC · cumulative receipts</h2>')
    attempt = demand.get('last_refresh_attempt') or {}
    if attempt.get('status') == 'retained':
        h.append('<p>Chain refresh unavailable on ' + dated(attempt.get('at')) + '. Showing the last successful observation.</p>')
    rows = demand.get('records') or []
    eco = demand.get('economy')
    if eco and rows:
        import statistics
        amounts = [r['paid_usd'] for r in rows if r.get('paid_usd') is not None]
        count = len(amounts)
        bands = [('No indexed event', sum(r['calls'] == 0 for r in rows)),
                 ('Below 1 USDC with activity', sum(r['calls'] > 0 and r['paid_usd'] < 1 for r in rows)),
                 ('1 to under 10 USDC', sum(1 <= n < 10 for n in amounts)),
                 ('10 to under 1,000 USDC', sum(10 <= n < 1000 for n in amounts)),
                 ('1,000 USDC and above', sum(n >= 1000 for n in amounts))]
        head = demand.get('indexed_block') or {}
        h += ['<p>Receiver list dated ' + dated(demand.get('cohort_date')) + '. Chain query ' + dated(demand.get('measured_at') or today) + '. Indexed through ' + dated(head.get('timestamp')) + (f" (Base block {head['number']:,})" if head.get('number') else '') + '.</p>',
              stat_block([(money(eco['paid_usd']), 'Indexed USDC volume', f"{eco['calls']:,} indexed events"),
                          (money(statistics.median(amounts)), 'Median per sampled address', f'includes all {count:,} addresses'),
                          (pct(eco['top5_share']), 'Volume at the five largest addresses', 'share of this sample')]),
              '<table class="board__t payment-distribution"><caption>Distribution across the sampled addresses</caption><thead><tr><th scope="col">Cumulative volume</th><th scope="col" class="num">Addresses</th></tr></thead><tbody>']
        h += [f'<tr><td>{label}</td><td class="num">{n:,}</td></tr>' for label,n in bands]
        h += ['</tbody></table>', '<h2 class="h2">Catalog matches</h2>', '<p>Entries appear alphabetically. Each match uses a published receiver host. Shared receivers and ambiguous matches are excluded. Volume can include other activity at the same address.</p>', table(rows_from(demand, export))]
        if head.get('timestamp'):
            dataset['temporalCoverage'] = '../' + head['timestamp']
    else:
        h.append('<p>No successful chain measurement is available for this sample.</p>')
    h += ['<h2 class="h2">Sources and coverage</h2><p>The chain sample uses Base USDC addresses from the x402 directories. Solana and other chains, card settlements, prepaid credits and private billing are outside the volume figures. The total addressable market and buyer identities are unknown. An event does not identify an independent buyer, prove an API call succeeded or establish profit. Payments do not affect Tashan scores.</p>',
          '<p><a class="link" href="https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?limit=1">Coinbase Bazaar directory</a> · <a class="link" href="https://github.com/FlyingWHR/tashan/blob/main/pipeline/paid_demand.py">Measurement query and aggregation</a></p>']
    if demand.get('via') in ('subgraph-mcp', 'graph-gateway'):
        sg = demand.get('source', '').split()
        if len(sg) >= 2 and sg[0] == 'subgraph' and sg[1].isalnum():
            h.append('<p><a class="link" href="https://thegraph.com/explorer/subgraphs/' + esc(sg[1]) + '">Settlement index on The Graph</a></p>')
    h.append('</main>')
    return [dataset], '\n'.join(h), description


def main():
    if not os.path.exists(DEMAND):
        print("paid: web/data/demand.json missing — run pipeline/paid_demand.py first")
        return 0
    demand = json.load(open(DEMAND, encoding="utf-8"))
    export = json.load(open(EXPORT, encoding="utf-8")) if os.path.exists(EXPORT) else {}
    today = (demand.get("measured_at") or "")[:10]
    rows = rows_from(demand, export)
    lds, body, lede = render(demand, export, today)

    import gen_hubs
    eco = demand.get("economy") or {}
    doc = gen_hubs.head(
        "Agent payment activity · tashan", lede,
        BASE + "/paid.html", lds)
    doc += body + chrome.footer_html()
    doc += '<script src="/js/site.js?v=' + str(assets.V) + '" defer></script>\n</body>\n</html>\n'
    open(OUT, "w", encoding="utf-8").write(doc)
    # ONE NUMBER, BOTH SURFACES. paid_demand.py counts every capability with an attributable
    # receipt (37); this page can only show the ones that have a dossier to link to (31), because
    # the export drops what a host cannot launch. demand.json is a SITE artifact — it is what the
    # MCP server's paid_demand tool reads — so it must agree with the page beside it, or an agent
    # quotes 37 while the page a reader opens says 31. That is the cross-surface disagreement this
    # repo already has a test for, arriving through a new door. The raw count stays in
    # data/paid_demand.json, which is the pipeline's own record and not published.
    n = len(rows)
    if demand.get("paid_capabilities") != n:
        demand["paid_capabilities"] = n
        demand["paid_capabilities_note"] = ("capabilities with an attributable receipt AND a "
                                            "published dossier; see data/paid_demand.json for the "
                                            "pre-export count")
        with open(DEMAND, "w", encoding="utf-8") as f:
            json.dump(demand, f)
            f.write("\n")
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
    assert "$10.00" in body, "median includes the zero address"
    assert 'No indexed event</td><td class="num">1' in body
    assert "Indexed through Unavailable" in body and "earned" not in body
    assert lds[0]["@type"] == "Dataset"
    _, empty, _ = render({}, {}, "")
    assert "No successful chain measurement" in empty and "$0.00" not in empty
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
