// The buy button. Two things must hold no matter what breaks: the customer always reaches Polar,
// and the funnel still sees them go. Everything else here is about the self-repair being careful —
// it holds a token that can rewrite our own checkout links, so it must patch the right one, patch
// it only when it is actually wrong, and give up quietly rather than retry forever.
//
//   node functions/api/buy.test.mjs
import assert from "node:assert";
import { onRequest, ensureSuccessUrl, successUrlOk, wantUrl, buyUrl, _LINK } from "./buy.js";

let pass = 0, fail = 0;
const ok = async (name, fn) => {
  try { await fn(); console.log("  ok   " + name); pass++; }
  catch (e) { console.log("  FAIL " + name + "\n       " + e.message); fail++; }
};

function kv() {
  const m = new Map();
  return { m, async get(k) { return m.has(k) ? m.get(k) : null; },
           async put(k, v) { m.set(k, String(v)); }, async delete(k) { m.delete(k); } };
}

function ae() {
  const rows = [];
  return { rows, writeDataPoint(p) { rows.push(p); } };
}

const ORIGIN = "https://tashan.sh";
const MONTHLY = _LINK.monthly, ANNUAL = _LINK.annual;

/** A Polar double recording every call, so a test can assert what was NOT done. */
function polarStub({ links, patchOk = true }) {
  const calls = [];
  return {
    calls,
    api: async (env, path, init = {}) => {
      calls.push({ path, method: init.method || "GET", body: init.body });
      if (path.startsWith("/checkout-links/?")) return { items: links };
      if (init.method === "PATCH") return patchOk ? { id: "ok" } : null;
      return null;
    },
  };
}

const linkFor = (secret, success_url) =>
  ({ id: "cl_" + secret.slice(-4), url: "https://buy.polar.sh/" + secret, success_url });

const call = (env, q = "") =>
  onRequest({ request: new Request(`${ORIGIN}/api/buy${q}`), env });
const locOf = (r) => r.headers.get("location") || "";

console.log("\n── the buy button ─────────────────────────────");

// ---------------------------------------------------------------- never block a sale
await ok("redirects to the monthly checkout by default", async () => {
  const r = await call({});
  assert.equal(r.status, 302);
  assert.equal(locOf(r), buyUrl(MONTHLY));
});

await ok("plan=annual redirects to the annual checkout", async () => {
  const r = await call({}, "?plan=annual");
  assert.equal(locOf(r), buyUrl(ANNUAL));
});

await ok("the two links are different — one product sold twice would be the bug", () => {
  assert.notEqual(MONTHLY, ANNUAL);
});

await ok("an unrecognised plan falls back to monthly, never to a caller-supplied URL", async () => {
  for (const q of ["?plan=https://evil.example", "?plan=../../x", "?plan=", "?plan=ANNUAL"]) {
    const r = await call({}, q);
    assert.equal(locOf(r), buyUrl(MONTHLY), q);
  }
});

await ok("redirects with no token and no KV — an unconfigured site still sells", async () => {
  const r = await call({});
  assert.equal(r.status, 302);
  assert.ok(locOf(r).startsWith("https://buy.polar.sh/"));
});

await ok("redirects even when Polar throws outright", async () => {
  const boom = { POLAR_ORG_TOKEN: "t", TASHAN_KV: kv() };
  const saved = globalThis.fetch;
  globalThis.fetch = async () => { throw new Error("network down"); };
  try {
    const r = await call(boom);
    assert.equal(r.status, 302);
    assert.equal(locOf(r), buyUrl(MONTHLY));
  } finally { globalThis.fetch = saved; }
});

await ok("never caches the redirect — a stale 302 would outlive a changed link", async () => {
  const r = await call({});
  assert.match(r.headers.get("cache-control") || "", /no-store/);
});

// ---------------------------------------------------------------- the funnel must survive
await ok("writes the outbound event funnel.py counts, with a polar host", async () => {
  const a = ae();
  await call({ TASHAN_AE: a });
  assert.equal(a.rows.length, 1);
  const row = a.rows[0];
  assert.equal(row.indexes[0], "outbound", "funnel.py filters on ev='outbound'");
  // funnel.py: WHERE blob4 LIKE '%polar%' — blob 4 is the context key.
  assert.ok(row.blobs[3].includes("polar"), "blob4 must match '%polar%': " + row.blobs[3]);
  assert.equal(row.blobs[0], "outbound");
  assert.deepEqual(row.doubles, [1]);
});

await ok("the recorded event distinguishes monthly from annual", async () => {
  const a = ae();
  await call({ TASHAN_AE: a }, "?plan=annual");
  assert.ok(a.rows[0].blobs[4].includes("annual"), a.rows[0].blobs[4]);
});

await ok("our own payment check is NOT counted as reaching checkout", async () => {
  // The funnel's first week read "0 offer clicks, 43 reached Polar checkout" — impossible for real
  // traffic, and exactly 21 check_payments runs x 2 plans. A metric your own monitoring inflates is
  // worse than no metric: it manufactures the number a founder would celebrate.
  const a = ae();
  await onRequest({ request: new Request(`${ORIGIN}/api/buy?plan=monthly`,
                    { headers: { "user-agent": "tashan-payment-check" } }), env: { TASHAN_AE: a } });
  assert.equal(a.rows.length, 0, "the checker must not appear in the funnel");
});

await ok("...but the redirect still happens, so the check still checks something", async () => {
  const r = await onRequest({ request: new Request(`${ORIGIN}/api/buy?plan=monthly`,
                    { headers: { "user-agent": "tashan-payment-check" } }), env: {} });
  assert.equal(r.status, 302);
  assert.equal(locOf(r), buyUrl(MONTHLY));
});

await ok("a real caller with any other user-agent IS counted", async () => {
  // Only our own checker is excluded. An agent hitting this route is a genuine signal.
  for (const agent of ["Mozilla/5.0", "some-agent/1.0", ""]) {
    const a = ae();
    await onRequest({ request: new Request(`${ORIGIN}/api/buy?plan=monthly`,
                      { headers: agent ? { "user-agent": agent } : {} }), env: { TASHAN_AE: a } });
    assert.equal(a.rows.length, 1, `dropped a real caller: ${agent || "(none)"}`);
  }
});

await ok("a throwing analytics binding does not cost the sale", async () => {
  const r = await call({ TASHAN_AE: { writeDataPoint() { throw new Error("AE down"); } } });
  assert.equal(r.status, 302);
});

// ---------------------------------------------------------------- the repair
await ok("repairs a success_url that does not carry the checkout id", async () => {
  const s = polarStub({ links: [linkFor(MONTHLY, "https://tashan.sh/welcome")] });
  const env = { POLAR_ORG_TOKEN: "t", TASHAN_KV: kv() };
  const why = await ensureSuccessUrl(env, MONTHLY, ORIGIN, s.api);
  assert.equal(why, "repaired");
  const patch = s.calls.find((c) => c.method === "PATCH");
  assert.ok(patch, "expected a PATCH");
  assert.equal(JSON.parse(patch.body).success_url, wantUrl(ORIGIN));
});

await ok("patches the link we publish, not some other link in the organisation", async () => {
  const other = linkFor("polar_cl_SOMEOTHERLINK", "https://elsewhere.example/done");
  const s = polarStub({ links: [other, linkFor(MONTHLY, "https://tashan.sh/welcome")] });
  await ensureSuccessUrl({ POLAR_ORG_TOKEN: "t", TASHAN_KV: kv() }, MONTHLY, ORIGIN, s.api);
  const patch = s.calls.find((c) => c.method === "PATCH");
  assert.ok(patch.path.includes(linkFor(MONTHLY).id), "patched " + patch.path);
});

await ok("leaves a correct success_url alone — both documented spellings", async () => {
  for (const su of [ORIGIN + "/api/checkout?checkout_id={CHECKOUT_ID}",
                    ORIGIN + "/api/checkout?id={CHECKOUT_ID}"]) {
    const s = polarStub({ links: [linkFor(MONTHLY, su)] });
    const why = await ensureSuccessUrl({ POLAR_ORG_TOKEN: "t", TASHAN_KV: kv() }, MONTHLY, ORIGIN, s.api);
    assert.equal(why, "already-ok", su);
    assert.ok(!s.calls.some((c) => c.method === "PATCH"), "must not rewrite a working field: " + su);
  }
});

await ok("a success_url pointing at somebody else's origin is NOT accepted", () => {
  assert.equal(successUrlOk("https://evil.example/api/checkout?checkout_id={CHECKOUT_ID}", ORIGIN), false);
  assert.equal(successUrlOk(ORIGIN + "/api/checkout?checkout_id=", ORIGIN), false);
  assert.equal(successUrlOk(null, ORIGIN), false);
});

await ok("the second click opens no socket at all", async () => {
  const env = { POLAR_ORG_TOKEN: "t", TASHAN_KV: kv() };
  const first = polarStub({ links: [linkFor(MONTHLY, "https://tashan.sh/welcome")] });
  await ensureSuccessUrl(env, MONTHLY, ORIGIN, first.api);
  const second = polarStub({ links: [] });
  const why = await ensureSuccessUrl(env, MONTHLY, ORIGIN, second.api);
  assert.equal(why, "cached");
  assert.equal(second.calls.length, 0, "a healthy link must cost nothing");
});

await ok("an already-correct link is cached too — otherwise the healthy path pays every click", async () => {
  // The repaired path and the already-ok path set the flag in two different places. A sabotage run
  // removing the second one left all 20 checks green: every test that reached the cache had gone
  // through a repair first, so the branch that will run on almost every real click was unmeasured.
  const env = { POLAR_ORG_TOKEN: "t", TASHAN_KV: kv() };
  const good = ORIGIN + "/api/checkout?checkout_id={CHECKOUT_ID}";
  const s1 = polarStub({ links: [linkFor(MONTHLY, good)] });
  assert.equal(await ensureSuccessUrl(env, MONTHLY, ORIGIN, s1.api), "already-ok");
  const s2 = polarStub({ links: [linkFor(MONTHLY, good)] });
  assert.equal(await ensureSuccessUrl(env, MONTHLY, ORIGIN, s2.api), "cached");
  assert.equal(s2.calls.length, 0, "a link that was already right must not be re-listed every click");
});

await ok("a refused PATCH backs off instead of retrying on every click", async () => {
  const env = { POLAR_ORG_TOKEN: "t", TASHAN_KV: kv() };
  const s1 = polarStub({ links: [linkFor(MONTHLY, "https://x/y")], patchOk: false });
  assert.equal(await ensureSuccessUrl(env, MONTHLY, ORIGIN, s1.api), "patch-failed");
  const s2 = polarStub({ links: [linkFor(MONTHLY, "https://x/y")], patchOk: false });
  assert.equal(await ensureSuccessUrl(env, MONTHLY, ORIGIN, s2.api), "backoff");
  assert.equal(s2.calls.length, 0, "backoff must not call Polar");
});

await ok("a link missing from the organisation patches nothing", async () => {
  const s = polarStub({ links: [linkFor("polar_cl_UNRELATED", "https://x/y")] });
  const why = await ensureSuccessUrl({ POLAR_ORG_TOKEN: "t", TASHAN_KV: kv() }, MONTHLY, ORIGIN, s.api);
  assert.equal(why, "not-found");
  assert.ok(!s.calls.some((c) => c.method === "PATCH"), "must never patch a link it cannot identify");
});

await ok("no KV means no repair — without the flag it would call Polar on every single click", async () => {
  const s = polarStub({ links: [linkFor(MONTHLY, "https://x/y")] });
  assert.equal(await ensureSuccessUrl({ POLAR_ORG_TOKEN: "t" }, MONTHLY, ORIGIN, s.api), "unconfigured");
  assert.equal(s.calls.length, 0);
});

await ok("scopes the list to our organisation when the id is configured", async () => {
  const s = polarStub({ links: [linkFor(MONTHLY, "https://x/y")] });
  await ensureSuccessUrl({ POLAR_ORG_TOKEN: "t", POLAR_ORG_ID: "org_9", TASHAN_KV: kv() },
                         MONTHLY, ORIGIN, s.api);
  assert.ok(s.calls[0].path.includes("organization_id=org_9"), s.calls[0].path);
});

// ---------------------------------------------------------------- the whole path, fetch and all
await ok("end to end: a wrong field is repaired and the customer still lands on Polar", async () => {
  const seen = [];
  const saved = globalThis.fetch;
  globalThis.fetch = async (u, init = {}) => {
    seen.push({ url: String(u), method: init.method || "GET" });
    const J = (o) => new Response(JSON.stringify(o), { headers: { "content-type": "application/json" } });
    if (String(u).includes("/checkout-links/?")) return J({ items: [linkFor(MONTHLY, "https://tashan.sh/welcome")] });
    return J({ id: "patched" });
  };
  try {
    const r = await call({ POLAR_ORG_TOKEN: "t", TASHAN_KV: kv() });
    assert.equal(locOf(r), buyUrl(MONTHLY));
    assert.ok(seen.some((c) => c.method === "PATCH"), "expected a real PATCH: " + JSON.stringify(seen));
  } finally { globalThis.fetch = saved; }
});

console.log(`\n  ${pass} passing, ${fail} failing\n`);
process.exit(fail ? 1 : 0);
