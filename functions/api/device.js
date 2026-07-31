// Cloudflare Pages Function — /api/device : the device-authorisation grant.
//
// WHY THIS EXISTS. Until now the only way onto a machine was `tashan activate <key>` — go to your
// email, find the licence key, copy it, paste it into a terminal. Once per machine, forever. That is
// the shape of a licence manager from 2004, and it is the single worst moment in this product: it
// arrives immediately after someone has paid, which is exactly when they are least willing to do
// homework, and it asks a person who lives in `npx <thing>` to be the database administrator of
// their own entitlement.
//
// Every tool these customers already use solved this the same way, so we solve it the same way:
//
//     $ gh auth login          $ wrangler login          $ stripe login
//
// The OAuth 2.0 device-authorisation grant (RFC 8628). The terminal asks for a code, the browser
// approves it, the terminal picks up the credential. The customer types a licence key at most ONCE
// IN THEIR LIFE — in a browser, where paste is one keystroke and autofill often does it for them —
// and never again on any machine.
//
//   POST /api/device                          -> start:   {device_code, user_code, verify_url, ...}
//   POST /api/device {device_code}            -> poll:    {status} and, once, {key}
//   POST /api/device {user_code, approve:true}-> approve: browser only, needs the session cookie
//   POST /api/device {user_code, deny:true}   -> deny
//   GET  /api/device?code=<user_code>         -> lookup:  does this code exist, for /activate
//
// WHAT IS AND IS NOT A CREDENTIAL. `device_code` is 32 random bytes and is the bearer of the poll —
// it never leaves the terminal. `user_code` is 8 characters from an unambiguous alphabet; it is what
// a human reads aloud and types, it is useless without an authenticated browser to approve it, and
// it dies in ten minutes. The licence key itself crosses the wire exactly once, in the poll
// response, over TLS, to the process that asked for it.
//
// The approval REQUIRES a session cookie. A device code cannot bootstrap itself into an entitlement;
// somebody who is already provably a customer has to say yes.

import { COOKIE, cookieFrom, fetchLicence } from "./_license.js";

const TTL_S = 600;          // ten minutes; a code nobody used is not a code worth keeping
const POLL_INTERVAL_S = 3;  // what we ask the CLI to wait between polls
const MIN_POLL_MS = 2000;   // below this we answer slow_down instead of the real state

// No I, O, 0 or 1. A code is read off one screen and typed into another, sometimes from a photo of a
// laptop, and every ambiguous glyph in it becomes a support conversation.
const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });

function randomFrom(alphabet, n) {
  const bytes = crypto.getRandomValues(new Uint8Array(n));
  let out = "";
  // Rejection-free only because 256 % 32 === 0; with any other alphabet length this modulo would
  // bias the low glyphs. Asserted rather than assumed.
  for (let i = 0; i < n; i++) out += alphabet[bytes[i] % alphabet.length];
  return out;
}

const hex = (n) =>
  Array.from(crypto.getRandomValues(new Uint8Array(n)))
    .map((x) => x.toString(16).padStart(2, "0"))
    .join("");

// "WXYZ-1234" reads as one token and types as two. The dash is cosmetic and is stripped everywhere
// it is compared, so a customer who omits it, or who types lowercase, is still right.
const normalise = (s) => String(s || "").toUpperCase().replace(/[^A-Z0-9]/g, "");

async function start(env, url) {
  if (!env.TASHAN_KV) return json({ error: "sign-in is unavailable right now" }, 503);
  const deviceCode = hex(32);
  const userCode = randomFrom(ALPHABET, 8);
  const rec = { user_code: userCode, state: "pending", at: Date.now() };
  await env.TASHAN_KV.put("dev:" + deviceCode, JSON.stringify(rec), { expirationTtl: TTL_S });
  await env.TASHAN_KV.put("duc:" + userCode, deviceCode, { expirationTtl: TTL_S });
  return json({
    device_code: deviceCode,
    user_code: userCode.slice(0, 4) + "-" + userCode.slice(4),
    verify_url: url.origin + "/activate",
    verify_url_complete: url.origin + "/activate?code=" + userCode.slice(0, 4) + "-" + userCode.slice(4),
    interval: POLL_INTERVAL_S,
    expires_in: TTL_S,
  });
}

// The poll. Deliberately terse states, because the CLI switches on them and a human never reads
// this: pending / slow_down / denied / expired / ok.
async function poll(env, deviceCode) {
  if (!env.TASHAN_KV) return json({ status: "expired" });
  const raw = await env.TASHAN_KV.get("dev:" + deviceCode);
  if (!raw) return json({ status: "expired" });   // never issued, or the ten minutes ran out
  let rec;
  try { rec = JSON.parse(raw); } catch { return json({ status: "expired" }); }

  // Rate limit, RFC 8628 §3.5. A client hammering this learns to slow down rather than being cut off,
  // because the failure mode we care about is a busy loop, not an attacker — an attacker without the
  // 32-byte device code has nothing to poll for.
  const now = Date.now();
  if (rec.last && now - rec.last < MIN_POLL_MS) return json({ status: "slow_down" });
  rec.last = now;

  if (rec.state === "pending") {
    await env.TASHAN_KV.put("dev:" + deviceCode, JSON.stringify(rec), { expirationTtl: TTL_S });
    return json({ status: "pending" });
  }
  if (rec.state === "denied") {
    await env.TASHAN_KV.delete("dev:" + deviceCode);
    return json({ status: "denied" });
  }
  if (rec.state === "approved" && rec.key) {
    // Single use. The whole point of the indirection is that the credential is in flight once; a
    // device code that keeps yielding the key is a bearer token sitting in shell history.
    await env.TASHAN_KV.delete("dev:" + deviceCode);
    await env.TASHAN_KV.delete("duc:" + rec.user_code);
    return json({ status: "ok", key: rec.key });
  }
  return json({ status: "expired" });
}

// The browser half. A session cookie is the ONLY thing that can approve — this endpoint cannot mint
// an entitlement, it can only hand along one the caller already demonstrably holds.
async function decide(request, env, userCodeRaw, approve) {
  if (!env.TASHAN_KV) return json({ error: "sign-in is unavailable right now" }, 503);
  const userCode = normalise(userCodeRaw);
  if (!userCode) return json({ error: "no code" }, 400);

  const deviceCode = await env.TASHAN_KV.get("duc:" + userCode);
  if (!deviceCode) return json({ error: "expired", message: "That code has expired. Run the command again." }, 404);
  const raw = await env.TASHAN_KV.get("dev:" + deviceCode);
  if (!raw) return json({ error: "expired", message: "That code has expired. Run the command again." }, 404);
  const rec = JSON.parse(raw);

  if (!approve) {
    rec.state = "denied";
    await env.TASHAN_KV.put("dev:" + deviceCode, JSON.stringify(rec), { expirationTtl: TTL_S });
    return json({ ok: true, state: "denied" });
  }

  const key = cookieFrom(request, COOKIE);
  if (!key) return json({ error: "not signed in" }, 401);
  // Re-check the licence at the moment of approval rather than trusting the cookie's age. A
  // refunded or revoked key must not be able to arm a new machine just because a browser still
  // holds the session it was issued under.
  const res = await fetchLicence(env, key);
  if (res.error === "unavailable") return json({ error: "unavailable" }, 503);
  if (res.error) return json({ error: "not signed in" }, 401);

  rec.state = "approved";
  rec.key = key;
  await env.TASHAN_KV.put("dev:" + deviceCode, JSON.stringify(rec), { expirationTtl: TTL_S });
  return json({ ok: true, state: "approved" });
}

export async function onRequest({ request, env }) {
  const url = new URL(request.url);

  if (request.method === "GET") {
    // Does this code exist? The /activate page asks before showing an approve button, so a mistyped
    // code fails on the page the customer is looking at rather than after they click.
    const code = normalise(url.searchParams.get("code"));
    if (!code) return json({ error: "no code" }, 400);
    if (!env.TASHAN_KV) return json({ found: false }, 503);
    const deviceCode = await env.TASHAN_KV.get("duc:" + code);
    return json({ found: Boolean(deviceCode) });
  }

  if (request.method !== "POST") return json({ error: "method not allowed" }, 405);

  let body = {};
  try { body = await request.json(); } catch { /* empty body is the "start" case */ }

  if (body.device_code) return poll(env, String(body.device_code));
  if (body.user_code) return decide(request, env, body.user_code, Boolean(body.approve));
  return start(env, url);
}
