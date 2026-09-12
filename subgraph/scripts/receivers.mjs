// Who gets paid in the agent economy — harvested from the Coinbase Bazaar, written into the manifest.
//
// The subgraph filters USDC Transfers by topic2, the event's indexed `to`. That list has to come
// from somewhere, and the honest source is the same public directory the market already uses: CDP's
// x402 discovery index. Every address here is one a service PUBLISHED as its payTo, so indexing
// payments to it is reading receipts against a claim its owner made in public.
//
// Re-run this whenever the directory grows:  node scripts/receivers.mjs
// It rewrites receivers.json and regenerates subgraph.yaml from subgraph.template.yaml.

import { writeFileSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");
const INDEX = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources";
const BASE = "eip155:8453";
// tashan's own receiver. It belongs in the set on the same terms as every other: published in the
// discovery manifest at /.well-known/x402, and so far paid exactly nothing — which the subgraph
// will say out loud rather than hide.
const OURS = "0x813e91688330cb03bd9f4e710a28c4b6207e9fc1";

async function page(offset, limit = 100) {
  const r = await fetch(`${INDEX}?limit=${limit}&offset=${offset}`, {
    headers: { "user-agent": "tashan/x402-demand (+https://tashan.sh)" },
  });
  if (!r.ok) throw new Error(`bazaar ${r.status}`);
  return r.json();
}

export function receiversOf(items) {
  const out = new Map();
  for (const item of items) {
    for (const a of item.accepts || []) {
      if (a.network !== BASE) continue;
      const addr = String(a.payTo || a.recipient || "").toLowerCase();
      if (!/^0x[0-9a-f]{40}$/.test(addr)) continue;
      const host = (() => { try { return new URL(item.resource).host; } catch { return ""; } })();
      const seen = out.get(addr) || { resources: 0, hosts: new Set() };
      seen.resources += 1;
      if (host) seen.hosts.add(host);
      out.set(addr, seen);
    }
  }
  return out;
}

async function main() {
  const items = [];
  for (let offset = 0; offset < 20000; ) {
    const d = await page(offset);
    const got = d.items || [];
    items.push(...got);
    offset += got.length;
    if (got.length < 100) break;
  }
  const found = receiversOf(items);
  if (!found.has(OURS)) found.set(OURS, { resources: 0, hosts: new Set(["tashan.sh"]) });

  const addrs = [...found.keys()].sort();
  writeFileSync(
    join(ROOT, "receivers.json"),
    JSON.stringify(
      {
        source: INDEX,
        network: BASE,
        harvested: new Date().toISOString().slice(0, 10),
        resources: items.length,
        receivers: Object.fromEntries(
          [...found].map(([a, v]) => [a, { resources: v.resources, hosts: [...v.hosts].sort() }]),
        ),
      },
      null,
      2,
    ) + "\n",
  );

  const tpl = readFileSync(join(ROOT, "subgraph.template.yaml"), "utf8");
  const list = addrs.map((a) => `          - "${a}"`).join("\n");
  writeFileSync(join(ROOT, "subgraph.yaml"), tpl.replace("__RECEIVERS__", "\n" + list));
  console.log(`${items.length} resources · ${addrs.length} Base receivers → receivers.json, subgraph.yaml`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  if (process.argv.includes("--selftest")) {
    const got = receiversOf([
      { resource: "https://a.example/x", accepts: [{ network: BASE, payTo: "0xAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaa" }] },
      { resource: "https://a.example/y", accepts: [{ network: BASE, payTo: "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }] },
      { resource: "https://b.example/z", accepts: [{ network: "solana:x", payTo: "SoLaNa" }] },
      { resource: "not a url", accepts: [{ network: BASE, payTo: "0xnope" }] },
    ]);
    const a = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    if (got.size !== 1) throw new Error(`expected one receiver, got ${got.size}`);
    if (got.get(a).resources !== 2) throw new Error("the same address on two resources is one receiver, counted twice");
    if (!got.get(a).hosts.has("a.example")) throw new Error("host not recorded");
    console.log("ok   checksummed and lowercase addresses are the same receiver");
    console.log("ok   non-Base rails and malformed addresses are dropped");
  } else {
    main().catch((e) => { console.error(e.message); process.exit(1); });
  }
}
