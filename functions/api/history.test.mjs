// node --test functions/api/history.test.mjs
//
// /api/history is THE paid endpoint — the retention series is the one asset a competitor starting
// today cannot have, because signal_history cannot be backfilled by anyone including us. So this is
// a paywall, and a paywall that fails open is worse than none: it gives away the only thing $6 buys
// while still charging for it.
//
// THESE GUARDS USED TO LIVE ON /api/security AND ONLY THERE. That endpoint has been made free —
// everything it returns is already in the public export and in /v0.1/lookup, so charging for it was
// selling what we give away. But its tests were the only ENDPOINT-LEVEL cover for the licence gate;
// deleting them along with the paywall would have quietly removed the guards from the one endpoint
// that still needs them. They are ported here, against the payload that is genuinely paid.
//
// Every negative path exists because a positive-looking failure already shipped once on /api/status,
// where a 404 from the billing provider was read as "valid".
//
// The bucket arithmetic is pinned against pipeline/push_history.py. If those two ever disagree,
// every lookup misses and a paying customer gets 404s that look exactly like "nothing recorded".

import { strict as assert } from "node:assert";
import test from "node:test";

import { bucketOf, onRequestGet } from "./history.js";

const KEY = "tashan-live-abcdef";
const ID = "pkg:chrome-devtools-mcp";
const SERIES = {
  tashan_score: { "2026-07-23": 91, "2026-08-14": 92 },
  adoption: { "2026-07-23": 83, "2026-08-14": 87 },
};

function kv(seed = {}) {
  // validate() caches its verdict, so the stub needs put/delete as well as get — without them the
  // gate throws before the handler is reached and every assertion below passes for the wrong reason.
  const m = new Map(Object.entries(seed));
  return {
    get: async (k) => (m.has(k) ? m.get(k) : null),
    put: async (k, v) => void m.set(k, v),
    delete: async (k) => void m.delete(k),
  };
}

const ENV = (over = {}) => ({
  POLAR_ORG_ID: "org_1",
  TASHAN_KV: kv({ ["hist:" + bucketOf(ID)]: { [ID]: SERIES, _scorers: { "2026-08-14": "s5" } } }),
  ...over,
});

function stubPolar(reply) {
  const real = globalThis.fetch;
  globalThis.fetch = async () => reply();
  return () => { globalThis.fetch = real; };
}
const granted = () => new Response(JSON.stringify({ status: "granted" }), { status: 200 });
const rejected = () => new Response("{}", { status: 404 });
const down = () => new Response("", { status: 502 });

const req = (q = "?id=" + encodeURIComponent(ID), headers = {}) =>
  new Request("https://tashan.sh/api/history" + q, { headers });

const withKey = (h = {}) => ({ authorization: "Bearer " + KEY, ...h });

// ---- the gate -----------------------------------------------------------------------------------

test("no licence gets nothing", async () => {
  const r = await onRequestGet({ request: req(), env: ENV() });
  assert.equal(r.status, 402);   // no credential is a price quote, not an auth failure
  const body = await r.text();
  assert.ok(!body.includes("2026-07-23"), "an unauthenticated response leaked the series");
});

test("an invalid licence gets nothing — the /api/status bug, guarded", async () => {
  const un = stubPolar(rejected);
  try {
    const r = await onRequestGet({ request: req(undefined, withKey()), env: ENV() });
    // A REFUSED licence is 403, never 402. Telling somebody whose licence was rejected to go and buy
    // one sends them to the wrong place and reads as their subscription being ignored.
    assert.equal(r.status, 403);
    assert.ok(!(await r.text()).includes("2026-07-23"), "a refused request leaked the series");
  } finally { un(); }
});

test("an unconfigured deployment refuses rather than serving", async () => {
  const r = await onRequestGet({ request: req(undefined, withKey()), env: { TASHAN_KV: kv() } });
  assert.equal(r.status, 503);
});

test("the billing provider being down never opens the gate", async () => {
  const un = stubPolar(down);
  try {
    const r = await onRequestGet({ request: req(undefined, withKey()), env: ENV() });
    assert.ok(r.status >= 400, "a 5xx from Polar must not be read as a valid licence");
    assert.ok(!(await r.text()).includes("2026-07-23"));
  } finally { un(); }
});

// ---- the payload --------------------------------------------------------------------------------

test("a valid licence gets the series", async () => {
  const un = stubPolar(granted);
  try {
    const r = await onRequestGet({ request: req(undefined, withKey()), env: ENV() });
    assert.equal(r.status, 200);
    const b = await r.json();
    assert.equal(b.series.tashan_score["2026-08-14"], 92);
    assert.equal(b.series.adoption["2026-07-23"], 83);
    assert.equal(b.licence, "paid");
  } finally { un(); }
});

test("the scorer version ships with every response", async () => {
  // A consumer trending across two scorer versions is measuring OUR recalibration, not the
  // capability. The map is what lets cli/doctor.mjs refuse that comparison.
  const un = stubPolar(granted);
  try {
    const b = await (await onRequestGet({ request: req(undefined, withKey()), env: ENV() })).json();
    assert.equal(b.scorers["2026-08-14"], "s5");
  } finally { un(); }
});

test("paid data is never cached by a shared cache", async () => {
  const un = stubPolar(granted);
  try {
    const r = await onRequestGet({ request: req(undefined, withKey()), env: ENV() });
    assert.match(r.headers.get("cache-control") || "", /private/);
  } finally { un(); }
});

test("the browser session cookie is accepted, so the website can differentiate", async () => {
  const un = stubPolar(granted);
  try {
    const r = await onRequestGet({ request: req(undefined, { cookie: "tashan_s=" + KEY }), env: ENV() });
    assert.equal(r.status, 200);
  } finally { un(); }
});

test("a capability with no series yet is a stated 404, not an empty success", async () => {
  const un = stubPolar(granted);
  try {
    const r = await onRequestGet({ request: req("?id=pkg:brand-new", withKey()), env: ENV() });
    assert.equal(r.status, 404);
    const b = await r.json();
    assert.equal(b.series, null);
    assert.match(b.note, /no history recorded/i);
  } finally { un(); }
});

test("a missing id is a 400 before any licence work happens", async () => {
  const r = await onRequestGet({ request: req(""), env: ENV() });
  assert.equal(r.status, 400);
});

test("bucketOf matches pipeline/push_history.py::bucket_of", () => {
  // Character sum mod 64, deliberately arithmetic a human can verify by hand. If these drift, every
  // lookup misses silently and a paying customer sees 404s that look like "nothing recorded".
  const py = (id) => {
    let sum = 0;
    for (const ch of id) sum += ch.codePointAt(0);
    return String(sum % 64);
  };
  for (const id of ["pkg:chrome-devtools-mcp", "plugin:a/b/c", "skill:x/y", "registry:z", ""]) {
    assert.equal(bucketOf(id), py(id), id);
  }
});
