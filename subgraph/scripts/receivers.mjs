// Harvest public Base USDC receiver addresses and resource activity from the Coinbase x402 Bazaar.
// Re-run this whenever the directory grows:  node scripts/receivers.mjs
// It rewrites receivers.json and regenerates subgraph.yaml from subgraph.template.yaml.

import { writeFileSync, readFileSync, renameSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");
const INDEX = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources";
const PAYAI = "https://facilitator.payai.network/discovery/resources";
const MPP = "https://mpp.dev/api/services";
const BASE = "eip155:8453";
const USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913";

async function read(url) {
  for (let attempt = 0; ; attempt++) {
    try {
      const r = await fetch(url, { headers: { "user-agent": "tashan/payment-coverage (+https://tashan.sh)" }, signal: AbortSignal.timeout(30000) });
      if (!r.ok) throw new Error(`${new URL(url).hostname} HTTP ${r.status}`);
      return await r.json();
    } catch (err) {
      if (attempt === 2) throw err;
      await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
    }
  }
}

async function page(source, offset, limit) {
  const data = await read(`${source}?limit=${limit}&offset=${offset}`);
  if (!Array.isArray(data.items) || data.pagination?.offset !== offset ||
      !Number.isSafeInteger(data.pagination.total) || data.pagination.limit !== limit) {
    throw new Error(`Unexpected discovery page from ${source}`);
  }
  return data;
}

export function receiversOf(items) {
  const out = new Map();
  for (const item of items) {
    let host;
    try { host = new URL(item.resource).hostname.toLowerCase().replace(/^www\./, ""); } catch { continue; }
    if (!host) continue;
    const addresses = new Set();
    for (const a of item.accepts || []) {
      if (![BASE, "base"].includes(a.network) || String(a.asset).toLowerCase() !== USDC) continue;
      const addr = String(a.payTo || a.recipient || "").toLowerCase();
      if (!/^0x[0-9a-f]{40}$/.test(addr) || addresses.has(addr)) continue;
      addresses.add(addr);
      const seen = out.get(addr) || { resources: 0, hosts: new Set() };
      seen.resources += 1;
      seen.hosts.add(host);
      out.set(addr, seen);
    }
  }
  return out;
}

async function scan(source) {
  const limit = 1000;
  const first = await page(source, 0, limit);
  const total = first.pagination.total;
  if (!total) throw new Error("Directory returned no resources");
  const listings = new Map();
  function collect(batch, offset) {
    if (batch.items.length < Math.min(limit, total - offset)) throw new Error("Incomplete discovery page");
    for (const item of batch.items) {
      if (typeof item.resource !== "string" || !Array.isArray(item.accepts)) throw new Error("Invalid listing");
      const accepts = item.accepts.map(({ network, asset, payTo, recipient }) => ({ network, asset, payTo, recipient }));
      listings.set(item.resource, { resource: item.resource, accepts, quality: { l30DaysTotalCalls: item.quality?.l30DaysTotalCalls } });
    }
  }
  collect(first, 0);
  for (let start = limit; start < total; start += 3 * limit) {
    const offsets = [start, start + limit, start + limit * 2].filter(offset => offset < total);
    const pages = await Promise.all(offsets.map(offset => page(source, offset, limit)));
    pages.forEach((batch, i) => collect(batch, offsets[i]));
  }
  return { listings, total };
}

function mppCoverage(catalog) {
  if (!Array.isArray(catalog.services) || !catalog.services.length) throw new Error("MPP catalog unavailable");
  const ids = new Set();
  const methods = {};
  for (const service of catalog.services) {
    if (typeof service.id !== "string" || !service.id || ids.has(service.id) || !service.methods || typeof service.methods !== "object" || Array.isArray(service.methods)) throw new Error("Invalid MPP service");
    ids.add(service.id);
    for (const method of Object.keys(service.methods)) methods[method] = (methods[method] || 0) + 1;
  }
  return { source: MPP, checked_at: new Date().toISOString(), services: ids.size, methods };
}

function summarize(scan, found) {
  const stats = { reported_resources: scan.total, observed_resources: scan.listings.size,
    base_usdc_resources: 0, receivers: 0, activity_reported: 0, active_resources_30d: 0 };
  const addresses = new Set();
  for (const [url, item] of scan.listings) {
    const eligible = receiversOf([item]);
    if (!eligible.size) continue;
    stats.base_usdc_resources++;
    for (const [address, entry] of eligible) {
      addresses.add(address);
      const combined = found.get(address) || { urls: new Set(), hosts: new Set() };
      combined.urls.add(url);
      for (const host of entry.hosts) combined.hosts.add(host);
      found.set(address, combined);
    }
    const calls = item.quality?.l30DaysTotalCalls;
    if (!Number.isSafeInteger(calls) || calls < 0) continue;
    stats.activity_reported++;
    if (calls > 0) stats.active_resources_30d++;
  }
  stats.receivers = addresses.size;
  return stats;
}

async function main() {
  const [coinbase, payai, mppRead] = await Promise.all([scan(INDEX), scan(PAYAI),
    read(MPP).then(mppCoverage).catch(() => null)]);
  let mpp = mppRead;
  if (!mpp) {
    const previous = JSON.parse(readFileSync(join(ROOT, "receivers.json"), "utf8")).providers?.mpp;
    mpp = { ...previous, source: MPP, status: previous?.checked_at ? "retained" : "unavailable" };
  }
  const found = new Map();
  const stats = summarize(coinbase, found);
  const payaiStats = summarize(payai, found);
  if (!stats.receivers || !payaiStats.receivers) throw new Error("Incomplete Base USDC receiver cohort");
  const overlap = [...coinbase.listings.keys()].filter(url => payai.listings.has(url)).length;
  const providers = { coinbase: { source: INDEX, ...stats }, payai: { source: PAYAI, ...payaiStats }, mpp,
    x402_overlap_urls: overlap, x402_union_urls: coinbase.listings.size + payai.listings.size - overlap };
  const addrs = [...found.keys()].sort();
  writeFileSync(
    join(ROOT, "receivers.json.tmp"),
    JSON.stringify(
      {
        source: INDEX,
        network: BASE,
        harvested: new Date().toISOString().slice(0, 10),
        resources: coinbase.listings.size,
        providers,
        coverage: stats,
        receivers: Object.fromEntries(
          addrs.map(a => [a, { resources: found.get(a).urls.size, hosts: [...found.get(a).hosts].sort() }]),
        ),
      },
      null,
      2,
    ) + "\n",
  );

  renameSync(join(ROOT, "receivers.json.tmp"), join(ROOT, "receivers.json"));
  const tpl = readFileSync(join(ROOT, "subgraph.template.yaml"), "utf8");
  const list = addrs.map((a) => `          - "${a}"`).join("\n");
  writeFileSync(join(ROOT, "subgraph.yaml"), tpl.replace("__RECEIVERS__", "\n" + list));
  console.log(`${providers.x402_union_urls} distinct x402 resource URLs · ${addrs.length} Base receivers → receivers.json, subgraph.yaml`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  if (process.argv.includes("--selftest")) {
    const offer = { network: BASE, asset: USDC, payTo: "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" };
    const got = receiversOf([
      { resource: "https://a.example/x", accepts: [{ network: BASE, asset: USDC, payTo: "0xAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaa" }] },
      { resource: "https://www.a.example/y", accepts: [offer, offer] },
      { resource: "https://b.example/z", accepts: [{ network: "solana:x", payTo: "SoLaNa" }] },
      { resource: "not a url", accepts: [{ network: BASE, asset: USDC, payTo: "0xnope" }] },
    ]);
    const same = { resource: "https://one.example/api", accepts: [offer, { ...offer, network: "base" }], quality: { l30DaysTotalCalls: 0 } };
    const combined = new Map();
    const summary = summarize({ total: 1, listings: new Map([[same.resource, same]]) }, combined);
    summarize({ total: 1, listings: new Map([[same.resource, same]]) }, combined);
    if (summary.activity_reported !== 1 || summary.active_resources_30d !== 0 || combined.get(offer.payTo).urls.size !== 1) throw new Error("Overlapping offers or missing reporting denominators");
    const mpp = mppCoverage({ services: [{ id: "one", methods: { stripe: {}, tempo: {} } }] });
    if (mpp.services !== 1 || mpp.methods.stripe !== 1 || mpp.methods.tempo !== 1) throw new Error("MPP multi-method service counted twice");
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
