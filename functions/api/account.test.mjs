// node --test functions/api/account.test.mjs
//
// The account endpoint decides two things that fail silently when wrong: who is signed in, and what
// of their record is safe to send back. Both are asserted here against a stubbed Polar.
//
// The specific bug this guards is one this codebase has already shipped once, on /api/status: a
// non-2xx from Polar was read as "fine", so a made-up licence key printed "Pro active". Every
// negative path below exists because of that.

import { strict as assert } from "node:assert";
import test from "node:test";

import { onRequest } from "./account.js";
import { COOKIE, cookieFrom, keyFrom, setCookie } from "./_license.js";

const KEY = "tashan-live-abcdef";
const RECORD = {
  status: "granted",
  display_key: "****ABCD",
  expires_at: "2099-01-01T00:00:00Z",
  usage: 2,
  limit_activations: 3,
  customer: { email: "buyer@example.com", name: "Buyer" },
};

// A KV stub with the two methods this endpoint uses, so the handoff path is exercised for real.
function kv() {
  const m = new Map();
  return {
    store: m,
    get: async (k) => (m.has(k) ? m.get(k) : null),
    put: async (k, v) => void m.set(k, v),
    delete: async (k) => void m.delete(k),
  };
}

const ENV = (over = {}) => ({ POLAR_ORG_ID: "org_1", TASHAN_KV: kv(), ...over });

// Swap global fetch for one that answers as Polar would.
function stubPolar(reply) {
  const real = globalThis.fetch;
  globalThis.fetch = async () => reply();
  return () => { globalThis.fetch = real; };
}

const ok = () => new Response(JSON.stringify(RECORD), { status: 200 });
const notFound = () => new Response("{}", { status: 404 });
const down = () => new Response("", { status: 502 });

const req = (opts = {}) => new Request(opts.url || "https://tashan.sh/api/account", {
  method: opts.method || "GET",
  headers: opts.headers || {},
  body: opts.body,
});

// ---- cookie plumbing ---------------------------------------------------------------------------

test("cookieFrom reads its own cookie and not a lookalike prefix", () => {
  const r = req({ headers: { cookie: "tashan_something=nope; tashan_s=real; other=x" } });
  assert.equal(cookieFrom(r), "real");
});

test("cookieFrom returns empty when the cookie is absent", () => {
  assert.equal(cookieFrom(req({ headers: { cookie: "a=b" } })), "");
  assert.equal(cookieFrom(req()), "");
});

test("the session cookie is httpOnly, Secure and SameSite=Lax", () => {
  const c = setCookie(KEY);
  assert.match(c, /HttpOnly/);
  assert.match(c, /Secure/);
  // Lax, not Strict: the CLI handoff arrives as a cross-site top-level navigation and Strict would
  // drop the cookie on exactly that hop.
  assert.match(c, /SameSite=Lax/);
  assert.match(c, new RegExp("^" + COOKIE + "="));
});

test("an explicit credential beats the ambient cookie", () => {
  const r = req({ headers: { cookie: COOKIE + "=from-cookie", authorization: "Bearer from-header" } });
  assert.equal(keyFrom(r), "from-header");
});

test("being signed in on the browser unlocks the gated endpoints too", () => {
  // This is the property that makes the account real rather than decorative: keyFrom() sees the
  // session, so capability pages show Pro detail to a signed-in reader with nothing pasted.
  assert.equal(keyFrom(req({ headers: { cookie: COOKIE + "=" + KEY } })), KEY);
});

// ---- GET: the dashboard ------------------------------------------------------------------------

test("no cookie is a clean signed-out state, not an error", async () => {
  const r = await onRequest({ request: req(), env: ENV() });
  assert.equal(r.status, 200);
  const b = await r.json();
  assert.equal(b.signed_in, false);
  assert.ok(b.portal, "the signed-out state still offers a way in");
});

test("a valid cookie returns the customer's own record", async () => {
  const un = stubPolar(ok);
  try {
    const r = await onRequest({ request: req({ headers: { cookie: COOKIE + "=" + KEY } }), env: ENV() });
    const b = await r.json();
    assert.equal(b.signed_in, true);
    assert.equal(b.active, true);
    assert.equal(b.email, "buyer@example.com");
    assert.equal(b.machines_used, 2);
    assert.equal(b.machines_limit, 3);
    assert.equal(b.display_key, "****ABCD");
  } finally { un(); }
});

test("the full licence key is NEVER echoed back to the browser", async () => {
  const un = stubPolar(() => new Response(JSON.stringify({ ...RECORD, key: KEY }), { status: 200 }));
  try {
    const r = await onRequest({ request: req({ headers: { cookie: COOKIE + "=" + KEY } }), env: ENV() });
    const raw = await r.text();
    assert.ok(!raw.includes(KEY), "the response body leaked the licence key");
  } finally { un(); }
});

test("an expired licence reports expired, not active", async () => {
  const un = stubPolar(() => new Response(
    JSON.stringify({ ...RECORD, expires_at: "2000-01-01T00:00:00Z" }), { status: 200 }));
  try {
    const r = await onRequest({ request: req({ headers: { cookie: COOKIE + "=" + KEY } }), env: ENV() });
    const b = await r.json();
    assert.equal(b.active, false);
    assert.equal(b.status, "expired");
  } finally { un(); }
});

test("a revoked key signs the browser out instead of showing an error it cannot act on", async () => {
  const un = stubPolar(notFound);
  try {
    const r = await onRequest({ request: req({ headers: { cookie: COOKIE + "=" + KEY } }), env: ENV() });
    const b = await r.json();
    assert.equal(b.signed_in, false);
    assert.equal(b.was, "invalid");
    assert.match(r.headers.get("set-cookie") || "", /Max-Age=0/);
  } finally { un(); }
});

test("Polar being down is reported as unavailable, never as signed out", async () => {
  // Signing a paying customer out because a third party had a bad minute is the wrong direction:
  // they would reach for the licence key they do not have to hand.
  const un = stubPolar(down);
  try {
    const r = await onRequest({ request: req({ headers: { cookie: COOKIE + "=" + KEY } }), env: ENV() });
    assert.equal(r.status, 503);
    const b = await r.json();
    assert.equal(b.unavailable, true);
    assert.equal(r.headers.get("set-cookie"), null, "a 5xx must not clear the session");
  } finally { un(); }
});

test("?key= in the address bar does not sign anyone in", async () => {
  // Sign-in is a POST so a bearer credential never lands in browser history or a Referer header.
  const un = stubPolar(ok);
  try {
    const r = await onRequest({
      request: req({ url: "https://tashan.sh/api/account?key=" + KEY }), env: ENV(),
    });
    const b = await r.json();
    assert.equal(b.signed_in, false);
  } finally { un(); }
});

// ---- POST: sign in -----------------------------------------------------------------------------

test("a good key signs in, sets the cookie and mints a one-time handoff", async () => {
  const un = stubPolar(ok);
  const env = ENV();
  try {
    const r = await onRequest({
      request: req({ method: "POST", body: JSON.stringify({ key: KEY }) }), env,
    });
    assert.equal(r.status, 200);
    const b = await r.json();
    assert.equal(b.signed_in, true);
    assert.equal(b.handoff, true);
    assert.match(b.url, /\/api\/account\?t=[0-9a-f]{48}$/);
    assert.match(r.headers.get("set-cookie") || "", new RegExp(COOKIE + "="));
    // the token is stored under its own namespace, and it is the key it maps to
    const t = new URL(b.url).searchParams.get("t");
    assert.equal(await env.TASHAN_KV.get("ho:" + t), KEY);
  } finally { un(); }
});

test("a bad key is refused — the /api/status bug, guarded", async () => {
  const un = stubPolar(notFound);
  try {
    const r = await onRequest({
      request: req({ method: "POST", body: JSON.stringify({ key: "made-up" }) }), env: ENV(),
    });
    assert.equal(r.status, 403);
    assert.equal(r.headers.get("set-cookie"), null, "a refused sign-in must not set a session");
  } finally { un(); }
});

test("an empty or malformed POST body is a 400, not a crash", async () => {
  for (const body of [undefined, "not json", "{}"]) {
    const r = await onRequest({ request: req({ method: "POST", body }), env: ENV() });
    assert.equal(r.status, 400);
  }
});

test("an unconfigured deployment refuses everyone rather than admitting them", async () => {
  const r = await onRequest({
    request: req({ method: "POST", body: JSON.stringify({ key: KEY }) }),
    env: { TASHAN_KV: kv() },                     // no POLAR_ORG_ID
  });
  assert.equal(r.status, 503);
});

test("without KV the caller is still signed in, but no handoff link is invented", async () => {
  const un = stubPolar(ok);
  try {
    const r = await onRequest({
      request: req({ method: "POST", body: JSON.stringify({ key: KEY }) }),
      env: { POLAR_ORG_ID: "org_1" },
    });
    const b = await r.json();
    assert.equal(b.handoff, false);
    assert.ok(!b.url.includes(KEY), "the licence key must never be put in a URL as a fallback");
    assert.match(r.headers.get("set-cookie") || "", new RegExp(COOKIE + "="));
  } finally { un(); }
});

// ---- GET ?t=: redeem ---------------------------------------------------------------------------

test("a handoff token signs the browser in exactly once", async () => {
  const env = ENV();
  await env.TASHAN_KV.put("ho:tok", KEY);

  const first = await onRequest({ request: req({ url: "https://tashan.sh/api/account?t=tok" }), env });
  assert.equal(first.status, 302);
  assert.equal(first.headers.get("location"), "https://tashan.sh/account.html");
  assert.match(first.headers.get("set-cookie") || "", new RegExp(COOKIE + "=" + KEY));

  // replayed from shell history or the browser's back stack: no session this time
  const second = await onRequest({ request: req({ url: "https://tashan.sh/api/account?t=tok" }), env });
  assert.equal(second.status, 302);
  assert.equal(second.headers.get("set-cookie"), null);
  assert.match(second.headers.get("location"), /\?e=expired$/);
});

test("an unknown token redirects to a stated error, not to a signed-in page", async () => {
  const r = await onRequest({ request: req({ url: "https://tashan.sh/api/account?t=nope" }), env: ENV() });
  assert.equal(r.status, 302);
  assert.match(r.headers.get("location"), /\?e=expired$/);
  assert.equal(r.headers.get("set-cookie"), null);
});

// ---- DELETE: sign out --------------------------------------------------------------------------

test("sign out clears the cookie", async () => {
  const r = await onRequest({ request: req({ method: "DELETE" }), env: ENV() });
  const b = await r.json();
  assert.equal(b.signed_in, false);
  assert.match(r.headers.get("set-cookie") || "", /Max-Age=0/);
});

test("an unsupported method is refused", async () => {
  const r = await onRequest({ request: req({ method: "PUT" }), env: ENV() });
  assert.equal(r.status, 405);
});
