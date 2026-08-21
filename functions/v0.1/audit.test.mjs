// node functions/v0.1/audit.test.mjs
//
// The endpoint that sells to machines. Two things have to hold no matter what else changes:
// every RISK is free, and the paid half is never served without a payment that cleared.
import assert from "node:assert";
import { onRequestPost, onRequestGet } from "./audit.js";

let n = 0;
const ok = (name, cond, extra = "") => {
  n++;
  assert.ok(cond, name + (extra ? " — " + extra : ""));
  console.log("  ok   " + name);
};

const LOOKUP = {
  generated_at: "2026-08-14T00:00:00Z",
  scorer: "s5",
  keys: { "good-mcp": 0, "pkg:good-mcp": 0, "sick-mcp": 1, "pkg:sick-mcp": 1, "old-mcp": 2, "pkg:old-mcp": 2,
         "canary-mcp": 3, "pkg:canary-mcp": 3,
         "helper": 4, "skill:acme/helper": 4 },
  records: [
    { id: "pkg:good-mcp", name: "good-mcp", label: "Good", slug: "pkg-good-mcp", tashan_score: 91,
      vitality: "active", rated: true, sec_advisory_count: 0,
      sec_scanned_at: "2026-08-13T00:00:00Z" },
    { id: "pkg:sick-mcp", name: "sick-mcp", label: "Sick", slug: "pkg-sick-mcp", tashan_score: 40,
      vitality: "active", rated: true, sec_advisory_count: 2, single_maintainer: 1,
      sec_scanned_at: "2026-08-13T00:00:00Z" },
    { id: "pkg:old-mcp", name: "old-mcp", label: "Old", slug: "pkg-old-mcp", tashan_score: 55,
      vitality: "dormant", rated: true, npm_deprecated: 1, gh_archived: 1,
      sec_scanned_at: "2026-08-13T00:00:00Z" },
    // A row junk() keeps OFF the board: it survives in lookup.json only to warn, and has no slug.
    { id: "pkg:canary-mcp", name: "canary-mcp", tashan_score: null, sec_advisory_count: 1,
      sec_scanned_at: "2026-08-13T00:00:00Z" },
    // Never security-scanned: a skill is a folder, there is no version to query OSV about.
    { id: "skill:acme/helper", name: "helper", label: "Helper", slug: "skill-acme-helper",
      tashan_score: 63, rated: true, vitality: "active" },
  ],
};

const KV = {
  get: async (k) => (k.startsWith("hist:")
    ? { "pkg:good-mcp": { "2026-06-01": 85, "2026-07-01": 88, "2026-08-01": 91 },
        "pkg:sick-mcp": { "2026-06-01": 70, "2026-08-01": 40 },
        _scorers: { "2026-06-01": "s5", "2026-08-01": "s5" } }
    : null),
  // _license.js caches licence verdicts here; without put() the licence path throws before it can
  // reach the assertion, which is the mock lying about the runtime rather than a product bug.
  put: async () => {},
};

const withFetch = async (fn) => {
  const real = globalThis.fetch;
  globalThis.fetch = async (u) => (String(u).includes("/data/lookup.json")
    ? { ok: true, json: async () => LOOKUP }
    : { ok: false, status: 404, json: async () => ({}) });
  try { return await fn(); } finally { globalThis.fetch = real; }
};

const post = (body, { headers = {}, env = {} } = {}) => withFetch(() => onRequestPost({
  request: new Request("https://tashan.sh/v0.1/audit", {
    method: "POST", headers: { "content-type": "application/json", ...headers },
    body: JSON.stringify(body),
  }),
  env,
}));
const read = async (r) => ({ status: r.status, body: await r.json(), headers: r.headers });

// ---- the free half is genuinely free -------------------------------------------------------------
{
  const { status, body } = await read(await post({ servers: ["good-mcp", "sick-mcp", "old-mcp", "who?"] }));
  ok("no credential, no payment: 200", status === 200);
  ok("every named capability comes back", body.audited.length === 3);
  ok("an unmeasured name is reported as unmeasured, never as fine",
     body.unmeasured.length === 1 && body.unmeasured[0] === "who?");

  const sick = body.audited.find(a => a.id === "pkg:sick-mcp");
  ok("ADVISORIES ARE FREE — the count and the sentence, with no credential",
     sick.flags.some(f => f.k === "advisory" && f.n === 2 && /install today/.test(f.say)),
     JSON.stringify(sick.flags));
  ok("a capability with advisories is told to be replaced", sick.verdict === "replace");
  ok("single-maintainer is a free flag", sick.flags.some(f => f.k === "bus-factor"));

  const old = body.audited.find(a => a.id === "pkg:old-mcp");
  ok("deprecation and archival are free flags",
     old.flags.some(f => f.k === "deprecated") && old.flags.some(f => f.k === "archived"));
  ok("a clean capability is keep", body.audited.find(a => a.id === "pkg:good-mcp").verdict === "keep");
  ok("the summary counts what it audited",
     body.summary.replace === 2 && body.summary.keep === 1 && body.summary.unmeasured === 1,
     JSON.stringify(body.summary));
  ok("the free response says the risks were free and absence is not safety",
     /free and needs no account/i.test(body.note) && /never safe/i.test(body.note));
  ok("...and says what payment would add", Boolean(body.history_available));
  ok("no history leaked into the free response", body.history === undefined);
}

// ---- an unlisted row must not be handed a URL that 404s ------------------------------------------
{
  const { body } = await read(await post({ servers: ["canary-mcp"] }));
  const c = body.audited[0];
  ok("a row with no dossier gets NO url rather than /capability/undefined.html",
     c.url === undefined && c.listed === false, JSON.stringify(c));
  ok("...and says why it is here at all", /only to warn/i.test(c.note || ""));
  ok("...while still carrying its advisory and its verdict",
     c.verdict === "replace" && c.flags.some(f => f.k === "advisory"));
}

// ---- never scanned is not the same as clean -------------------------------------------------------
{
  const { body } = await read(await post({ servers: ["good-mcp", "helper"] }));
  const scanned = body.audited.find(a => a.id === "pkg:good-mcp");
  const never = body.audited.find(a => a.id === "skill:acme/helper");
  ok("a row that was never security-scanned does NOT get `keep`",
     never.verdict === "unknown", never.verdict);
  ok("...and says so as a flag, in words",
     never.flags.some(f => f.k === "unscanned" && /unknown, not clean/.test(f.say)),
     JSON.stringify(never.flags));
  ok("...and carries scanned:false", never.scanned === false);
  ok("`unscanned` alone is not counted as a problem we found — that would make every skill 'review'",
     never.verdict !== "review");
  ok("the summary counts unknown separately from keep",
     body.summary.unknown === 1 && body.summary.keep === 1, JSON.stringify(body.summary));
  ok("a genuinely scanned clean row still earns keep",
     scanned.verdict === "keep" && scanned.scanned === true);
}

// ---- the paid half is not served without payment -------------------------------------------------
{
  const r = await post({ servers: ["good-mcp"], history: true }, { env: { TASHAN_KV: KV } });
  const { status, body } = await read(r);
  ok("history without a credential is 402, not 200", status === 402);
  ok("no history in the refusal", body.history === undefined);
  ok("THE FREE AUDIT IS STILL RETURNED with the 402 — the risks were never the paid part",
     body.free_result && body.free_result.audited.length === 1,
     "refusing to name a vulnerability because nobody paid is the one thing this must never do");
  ok("the refusal quotes the subscription price", Array.isArray(body.plans) && body.plans.length === 2);
  ok("unconfigured x402 emits NO accepts and no PAYMENT-REQUIRED header",
     body.accepts === undefined && !r.headers.get("payment-required"));
}

// ---- x402, once a wallet exists ------------------------------------------------------------------
const X = {
  TASHAN_KV: KV,
  X402_PAY_TO: "0x209693Bc6afc0C5328bA36FaF03C514EF312287C",
  X402_NETWORK: "eip155:8453",
  X402_ASSET: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  X402_FACILITATOR: "https://facilitator.example",
};
{
  const r = await post({ servers: ["good-mcp"], history: true }, { env: X });
  const { status, body } = await read(r);
  ok("configured: the 402 carries a spec-shaped accepts", status === 402
     && body.x402Version === 2 && body.accepts[0].scheme === "exact");
  ok("...and the PAYMENT-REQUIRED header", Boolean(r.headers.get("payment-required")));
  ok("...and STILL returns the free audit", Boolean(body.free_result));
}

// ---- a licence is honoured, and a bad one is not quietly downgraded -------------------------------
{
  // A rejected licence must 403, never fall through to "pay with crypto instead" — that reads to a
  // paying customer as their subscription being ignored.
  const realFetch = globalThis.fetch;
  globalThis.fetch = async (u) => (String(u).includes("/data/lookup.json")
    ? { ok: true, json: async () => LOOKUP }
    : { ok: true, status: 200, json: async () => ({ status: "revoked" }) });
  const r = await onRequestPost({
    request: new Request("https://tashan.sh/v0.1/audit", {
      method: "POST",
      headers: { "content-type": "application/json", authorization: "Bearer dud" },
      body: JSON.stringify({ servers: ["good-mcp"], history: true }),
    }),
    env: { ...X, POLAR_ORG_ID: "org" },
  });
  globalThis.fetch = realFetch;
  const body = await r.json();
  ok("a refused licence is 403 and is NOT downgraded to an x402 quote",
     r.status === 403 && body.accepts === undefined, "status " + r.status);
}

// ---- the paid half, once someone HAS paid ---------------------------------------------------------
// The negative cases above are worthless on their own: an endpoint that refuses everything passes
// every one of them. This is the case that proves the product exists.
{
  const realFetch = globalThis.fetch;
  globalThis.fetch = async (u) => (String(u).includes("/data/lookup.json")
    ? { ok: true, json: async () => LOOKUP }
    : { ok: true, status: 200, json: async () => ({ status: "granted" }) });
  const r = await onRequestPost({
    request: new Request("https://tashan.sh/v0.1/audit", {
      method: "POST",
      headers: { "content-type": "application/json", authorization: "Bearer real" },
      body: JSON.stringify({ servers: ["good-mcp", "sick-mcp"], history: true, since: "2026-06-01" }),
    }),
    env: { ...X, POLAR_ORG_ID: "org" },
  });
  globalThis.fetch = realFetch;
  const body = await r.json();
  ok("a valid licence gets 200 and the history", r.status === 200 && Boolean(body.history),
     "status " + r.status);
  ok("the free half is still there beside the paid half", body.audited.length === 2);

  const up = body.history["pkg:good-mcp"];
  ok("a rising capability reads as up, with the delta",
     up.direction === "up" && up.change === 6, JSON.stringify(up));
  const down = body.history["pkg:sick-mcp"];
  ok("a falling capability reads as down — the whole reason to pay",
     down.direction === "down" && down.change === -30, JSON.stringify(down));
  ok("the scorer map ships with the series, so nobody trends across a recalibration",
     Boolean(up.scorers && up.scorers["2026-08-01"]));
  ok("`since` is echoed so the caller can see what it was measured from", body.since === "2026-06-01");
}

// ---- shape and limits ----------------------------------------------------------------------------
{
  const { status, body } = await read(await post({ servers: [] }));
  ok("an empty list is a 400 with usage", status === 400 && /servers/.test(body.error));
  const g = await read(await onRequestGet({ request: new Request("https://tashan.sh/x"), env: {} }));
  // A NAKED GET IS A DISCOVERY PROBE. It used to answer 400 with no payment terms, so every x402
  // crawler that probes a URL concluded this was not a paid endpoint — two of our three priced
  // resources were invisible to the layer the wallets are on. It still explains how to POST.
  ok("GET still explains how to POST", g.body.usage && g.body.usage.method === "POST");
  ok("...but answers 402 so discovery can see the price", g.status === 402);

  const many = Array.from({ length: 250 }, (_, i) => "good-mcp");
  const { body: b2 } = await read(await post({ servers: many }));
  ok("over the cap: the drop is REPORTED, never silent",
     b2.capped && b2.capped.dropped === 50 && /call again/.test(b2.capped.say),
     JSON.stringify(b2.capped));
}

// ---- a quote that names nothing -----------------------------------------------------------------
// cli/mcp.mjs promises that a config's ids leave the machine only once the user has paid. Honouring
// that meant an agent holding a real config could never be told the price: the audience most likely
// to pay could not reach a quote, could not use a funded wallet, and registered as no demand at all.
// `{history: true, count: N}` asks what direction for N servers costs, and names nothing.
{
  const r = await post({ history: true, count: 7 }, { env: X });
  const { status, body } = await read(r);
  ok("{history, count} quotes without naming anything", status === 402 && body.quoted_for === 7);
  ok("...with real x402 terms", Array.isArray(body.accepts) && Boolean(body.accepts[0].amount));
  ok("...and the spec header", Boolean(r.headers.get("payment-required")));
  // A QUOTE IS A PRICE, NOT A FREE ANSWER. If it ever carried content it would become the way to
  // get the paid half without paying, which is the opposite of what it is for.
  ok("a quote carries no audited content", !body.audited && !body.history);
}
{
  const { status } = await read(await post({ count: 5 }, { env: X }));
  ok("count without history is still a bad request", status === 400);
}
{
  // Naming servers means you want the audit. A quote must never shadow a real request.
  const { status } = await read(await post({ servers: ["good-mcp"], count: 9 }, { env: X }));
  ok("servers win over count", status === 200);
}

console.log(`\nv0.1 audit: ${n}/${n} passed · all green`);
