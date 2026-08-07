// node --test functions/api/security.test.mjs
//
// /api/security is the delivery path for the audit's paid half, so it is a paywall, and a paywall
// that fails open is worse than none: it would hand away the one thing $6 buys while still charging
// for it. Every negative path below exists because a positive-looking failure already shipped once
// on /api/status, where a 404 from the billing provider was read as "valid".
//
// The bucket arithmetic is pinned against pipeline/push_security.py. If those two ever disagree,
// every lookup misses and a paying customer gets 404s that look exactly like "nothing recorded".

import { strict as assert } from "node:assert";
import test from "node:test";

import { bucketOf, onRequestGet } from "./security.js";

const KEY = "tashan-live-abcdef";
const ID = "pkg:mcp-server-taskwarrior";
const REC = {
  a: [{ id: "GHSA-95hg-3c55-xf9x", severity: "LOW", summary: "command injection", fixed: "1.2.0" }],
  s: "node ./scripts/post-install.js",
  t: "2026-07-30T18:35:34+00:00",
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
  // sec:meta is what push_security writes last. Its presence is the difference between "we have no
  // record for this id" and "the paid store was never published" — every test below assumes a store
  // that HAS been published, which is the state a paying customer is entitled to.
  TASHAN_KV: kv({ ["sec:" + bucketOf(ID)]: { [ID]: REC },
                  "sec:meta": { shards: 1, capabilities: 1, pushed_at: "2026-08-08T00:00:00Z" } }),
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
  new Request("https://tashan.sh/api/security" + q, { headers });

const withKey = (h = {}) => ({ authorization: "Bearer " + KEY, ...h });

// ---- the gate -----------------------------------------------------------------------------------

test("no licence gets nothing", async () => {
  const r = await onRequestGet({ request: req(), env: ENV() });
  assert.equal(r.status, 401);
  assert.ok(!(await r.text()).includes("GHSA"), "an unauthenticated response leaked the advisory");
});

test("an invalid licence gets nothing — the /api/status bug, guarded", async () => {
  const un = stubPolar(rejected);
  try {
    const r = await onRequestGet({ request: req(undefined, withKey()), env: ENV() });
    assert.equal(r.status, 403);
    assert.ok(!(await r.text()).includes("post-install"), "a refused request leaked the install command");
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
    assert.ok(!(await r.text()).includes("GHSA"));
  } finally { un(); }
});

// ---- the payload --------------------------------------------------------------------------------

test("a valid licence gets exactly what the pricing page sells", async () => {
  const un = stubPolar(granted);
  try {
    const r = await onRequestGet({ request: req(undefined, withKey()), env: ENV() });
    assert.equal(r.status, 200);
    const b = await r.json();
    // "which CVE or GHSA, its severity, the affected range, and the version that fixes it"
    assert.equal(b.advisories[0].id, "GHSA-95hg-3c55-xf9x");
    assert.equal(b.advisories[0].fixed, "1.2.0");
    // "what the install script actually runs"
    assert.equal(b.install_script, "node ./scripts/post-install.js");
    // permissions are NOT here: "what it can reach on your machine" is free, and gating it sold
    // the same fact twice. The endpoint must not start carrying it again.
    assert.equal(b.permissions, undefined);
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
  // This is the whole point of the endpoint: before it existed, capability.js never checked for a
  // licence and a paying customer saw exactly what a stranger saw on every page of the site.
  const un = stubPolar(granted);
  try {
    const r = await onRequestGet({
      request: req(undefined, { cookie: "tashan_s=" + KEY }), env: ENV(),
    });
    assert.equal(r.status, 200);
    assert.equal((await r.json()).install_script, "node ./scripts/post-install.js");
  } finally { un(); }
});

test("a capability with nothing recorded is a stated 404, never an implied clean scan", async () => {
  const un = stubPolar(granted);
  try {
    const r = await onRequestGet({
      request: req("?id=pkg:nothing-here", withKey()), env: ENV(),
    });
    assert.equal(r.status, 404);
    const b = await r.json();
    assert.equal(b.detail, null);
    assert.ok(!/clean|clear|safe|no known/i.test(b.note), `misleading note: ${b.note}`);
  } finally { un(); }
});

test("a missing id is a 400 before any licence work happens", async () => {
  const r = await onRequestGet({ request: req(""), env: ENV() });
  assert.equal(r.status, 400);
});

// ---- the shard arithmetic, pinned to the Python side --------------------------------------------

test("bucketOf matches pipeline/push_security.py::bucket_of", () => {
  // Vectors computed with: sum(ord(c) for c in id) % 64
  const cases = {
    "pkg:tavily-mcp": 2,
    "pkg:mcp-server-taskwarrior": 38,
    "registry:io.github.foo/bar": 18,
    "skill:anthropics/pdf": 61,
    "": 0,
  };
  for (const [id, want] of Object.entries(cases)) {
    assert.equal(bucketOf(id), String(want), `bucketOf(${id})`);
  }
});

// THE MOST EXPENSIVE BUG THIS CODEBASE CAN HAVE: an unpublished paid store answering the same
// innocuous "no audit detail recorded for this id" as a capability we genuinely have nothing on.
// push_security.py skips without CF credentials, so the store can be entirely empty while every
// request a paying customer makes reads as thin coverage rather than an undelivered product. They
// would conclude tashan is useless and refund, and nothing anywhere would say otherwise.


// THE REGRESSION THIS PREVENTS, shipped and caught within the hour: sec:meta was introduced after
// 61 shards were already in KV, so "no manifest" was true of a perfectly healthy store. Reading it
// as "never published" told paying customers their product was undelivered when it was not.
test("a loaded store with no manifest yet is not called unpublished", async () => {
  const un = stubPolar(granted);
  try {
    const r = await onRequestGet({
      request: req("?id=pkg:nothing-here", withKey()),
      // shards present (this bucket has data), manifest absent — the state on the night sec:meta shipped
      env: ENV({ TASHAN_KV: kv({ ["sec:" + bucketOf(ID)]: { [ID]: REC } }) }),
    });
    assert.equal(r.status, 404, "an absent manifest is not evidence of an empty store");
    assert.equal((await r.json()).store_published_at, null, "diagnostic, not a verdict");
  } finally { un(); }
});
