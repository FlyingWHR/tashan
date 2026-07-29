// Cloudflare Pages Function — POST /api/polar : Polar.sh billing webhook receiver.
//
// Polar follows the Standard Webhooks spec (https://standardwebhooks.com). Three headers arrive with
// every delivery and the signature covers "{webhook-id}.{webhook-timestamp}.{raw body}":
//
//   webhook-id         unique per event; also the idempotency key (Polar retries up to 10x)
//   webhook-timestamp  unix seconds, replay window enforced below
//   webhook-signature  one or more space-separated "v1,<base64 hmac-sha256>" values
//
// THE DETAIL THAT BREAKS HAND-ROLLED VERIFIERS: Polar's webhook secret is BASE64-ENCODED, and the HMAC
// key is those decoded bytes — not the ASCII of the string you copied out of the dashboard. Their SDKs
// hide this; we have no SDK because zero-dependency is a deliberate property of this repo, so it is
// done explicitly here. Getting it wrong fails closed (every delivery 403s), which is the safe
// direction but looks exactly like a misconfigured secret.
//
// Setup is documented in docs/PAYMENTS.md. The endpoint must stay publicly reachable and must never
// sit behind auth middleware — Polar does not follow redirects and disables an endpoint after 10
// consecutive non-2xx responses.

const TOLERANCE_S = 300;          // reject deliveries older/newer than 5 minutes (replay window)

function b64ToBytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function bytesToB64(buf) {
  const b = new Uint8Array(buf);
  let s = "";
  for (let i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
  return btoa(s);
}

// Constant-time-ish compare. A plain === on a signature leaks its prefix through timing; this always
// walks the full length regardless of where the first mismatch is.
export function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

// Exported for the test: the whole verification decision, with no network or platform dependency.
export async function verify(secret, headers, body, nowS) {
  const id = headers["webhook-id"], ts = headers["webhook-timestamp"], sig = headers["webhook-signature"];
  if (!secret || !id || !ts || !sig) return { ok: false, why: "missing signature headers" };

  const t = parseInt(ts, 10);
  if (!Number.isFinite(t)) return { ok: false, why: "bad timestamp" };
  if (Math.abs(nowS - t) > TOLERANCE_S) return { ok: false, why: "timestamp outside tolerance" };

  // Standard Webhooks secrets are conventionally prefixed; the prefix is not part of the key material.
  const raw = secret.startsWith("whsec_") ? secret.slice(6) : secret;
  let keyBytes;
  try {
    keyBytes = b64ToBytes(raw);
  } catch {
    return { ok: false, why: "secret is not valid base64" };
  }
  const key = await crypto.subtle.importKey("raw", keyBytes, { name: "HMAC", hash: "SHA-256" },
                                            false, ["sign"]);
  const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`${id}.${t}.${body}`));
  const expected = bytesToB64(mac);

  // The header can carry several signatures (secret rotation) — any one matching is a pass.
  for (const part of sig.split(" ")) {
    const c = part.indexOf(",");
    if (c > 0 && part.slice(0, c) === "v1" && safeEqual(part.slice(c + 1), expected)) {
      return { ok: true };
    }
  }
  return { ok: false, why: "no matching v1 signature" };
}

// Which events actually change whether someone is entitled. Everything else is acknowledged and
// ignored — Polar disables an endpoint after 10 consecutive non-2xx, so an unrecognised event must
// never be an error.
const GRANTS = new Set(["subscription.created", "subscription.active", "subscription.updated",
                        "subscription.uncanceled", "subscription.cycled", "subscription.resumed",
                        "order.paid"]);
const REVOKES = new Set(["subscription.canceled", "subscription.revoked", "subscription.past_due",
                         "subscription.paused", "order.refunded"]);

export function entitlementFrom(event) {
  const type = event && event.type;
  const data = (event && event.data) || {};
  const customer = data.customer || {};
  const email = (customer.email || data.customer_email || "").toLowerCase() || null;
  if (!email) return null;
  if (GRANTS.has(type)) return { email, state: "active", type };
  if (REVOKES.has(type)) return { email, state: "inactive", type };
  return null;
}

export async function onRequestPost({ request, env }) {
  // Read the body ONCE, as raw text. Re-serialising parsed JSON would change bytes (key order,
  // whitespace, unicode escapes) and the signature would never match again.
  const body = await request.text();
  const h = {
    "webhook-id": request.headers.get("webhook-id") || "",
    "webhook-timestamp": request.headers.get("webhook-timestamp") || "",
    "webhook-signature": request.headers.get("webhook-signature") || "",
  };

  const v = await verify(env.POLAR_WEBHOOK_SECRET, h, body, Math.floor(Date.now() / 1000));
  if (!v.ok) {
    // 403, deliberately: a forged or stale delivery is not something Polar should keep retrying, and
    // we must not leak which check failed.
    return new Response("invalid signature", { status: 403 });
  }

  let event;
  try {
    event = JSON.parse(body);
  } catch {
    return new Response("ok", { status: 202 });     // acknowledge; retrying won't make it parse
  }

  const ent = entitlementFrom(event);
  // TASHAN_KV is optional exactly like TASHAN_AE in e.js: until the namespace is bound there is
  // nowhere to record entitlement, and a 5xx here would get the endpoint disabled for a
  // configuration gap rather than a code fault. Acknowledge and move on.
  if (ent && env.TASHAN_KV) {
    // webhook-id is the idempotency key — Polar retries, and retries must not reorder state.
    await env.TASHAN_KV.put(`ent:${ent.email}`, JSON.stringify({
      state: ent.state, type: ent.type, at: new Date().toISOString(), event_id: h["webhook-id"],
    }));
  }
  return new Response("ok", { status: 200 });
}
