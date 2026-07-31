// Shared licence gate for every paid endpoint. Not routable itself — the leading underscore keeps
// Cloudflare Pages from publishing it as /api/_license.
//
// WE DO NOT BUILD THE ACCOUNT SYSTEM — POLAR ALREADY IS ONE. polar.sh/tashan/portal does email-OTP
// sign-in, subscriptions, invoices, payment methods, cancellation, licence keys and the device list.
// Validation runs against a PUBLIC customer-portal endpoint needing no seller token, so the licence
// (plus its activation id) is the whole credential here: no passwords, no sessions, no password
// reset, no account table, and no PII of ours to leak. docs/AUDIT.md called "a backend with accounts
// and persistence" the single blocking investment for revenue. It is not one — it is a link.

const POLAR_VALIDATE = "https://api.polar.sh/v1/customer-portal/license-keys/validate";
const CACHE_TTL_S = 300;   // see caching note below

// Never use a licence key as a cache key or log line — it is a bearer credential. Hash it.
async function keyHash(key) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(key));
  return Array.from(new Uint8Array(d)).map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 32);
}

// The browser session. Signing in on the site sets this, and because keyFrom() reads it, being
// signed in unlocks Pro detail on capability pages too — not just on /account.html. That is the
// whole point: "what happened after I pay" has to be visible somewhere other than a terminal.
export const COOKIE = "tashan_s";

export function cookieFrom(request, name = COOKIE) {
  const raw = request.headers.get("cookie") || "";
  for (const part of raw.split(";")) {
    const i = part.indexOf("=");
    if (i > 0 && part.slice(0, i).trim() === name) return decodeURIComponent(part.slice(i + 1).trim());
  }
  return "";
}

// httpOnly so no script can read the credential, Secure so it never crosses plain http, and Lax
// rather than Strict because the sign-in arrives as a top-level navigation from the CLI's browser
// launch — Strict would drop the cookie on exactly that hop and the handoff would silently no-op.
export function setCookie(key, maxAge = 60 * 60 * 24 * 30) {
  return `${COOKIE}=${encodeURIComponent(key)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`;
}

export const clearCookie = () => setCookie("", 0);

// A key may arrive as `Authorization: Bearer <key>` (the CLI), `?key=` (curl), or the session
// cookie (the browser). Order matters: an explicit credential always beats an ambient one.
export function keyFrom(request) {
  const auth = request.headers.get("authorization") || "";
  if (/^Bearer\s+/i.test(auth)) return auth.replace(/^Bearer\s+/i, "").trim();
  try {
    const q = new URL(request.url).searchParams.get("key");
    if (q) return q;
  } catch { /* opaque URL — fall through to the cookie */ }
  return cookieFrom(request);
}

// A licence key may be activated to a limited number of devices. The activation id identifies
// WHICH device is calling; a key whose seat was released must stop working here too, or the device
// limit is decorative and one shared key serves everyone.
export function activationFrom(request) {
  return (request.headers.get("x-tashan-activation") || "").trim() || null;
}

// The one place this codebase talks to Polar about a licence. `validate()` reduces the record to a
// yes/no for the gate; /api/account renders the same record as the customer's dashboard. Two callers,
// one request shape — because the last time one concept had two copies here, a hub table and the
// index board disagreed about what a row was.
export async function fetchLicence(env, key, activationId = null) {
  try {
    const r = await fetch(POLAR_VALIDATE, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(activationId
        ? { key, organization_id: env.POLAR_ORG_ID, activation_id: activationId }
        : { key, organization_id: env.POLAR_ORG_ID }),
    });
    if (!r.ok) return { error: r.status >= 500 ? "unavailable" : "invalid", status: r.status };
    return { data: await r.json() };
  } catch {
    return { error: "unavailable", status: 0 };      // offline / DNS — never "invalid"
  }
}

export async function validate(env, key, activationId = null) {
  if (!key) return { ok: false, status: 401, why: "no licence key" };
  // FAIL CLOSED. An unconfigured deployment must refuse everyone, never admit everyone — the opposite
  // of e.js, where a missing analytics binding is allowed to no-op because nothing is being protected.
  if (!env.POLAR_ORG_ID) return { ok: false, status: 503, why: "billing not configured" };

  // The activation is part of the identity being cached. Hashing only the key would let a
  // released device ride a positive cached under the same key from a still-active one.
  const h = env.TASHAN_KV ? "lic:" + (await keyHash(key + "|" + (activationId || "-"))) : null;
  if (h) {
    // Cached for 5 minutes, which is the whole tradeoff: it keeps Polar out of the hot path, and it
    // means a revoked or refunded key keeps working for at most that long. Polar can auto-refund to
    // head off a chargeback, so this window is a real (small) exposure, not a theoretical one.
    const hit = await env.TASHAN_KV.get(h);
    if (hit === "1") return { ok: true, cached: true };
    if (hit === "0") return { ok: false, status: 403, why: "licence not valid" };
  }

  const res = await fetchLicence(env, key, activationId);
  if (res.error) {
    // A 4xx from Polar means the key is bad; a 5xx means Polar is down. Do not cache the second
    // case as a negative, or a Polar outage would lock out paying customers for five minutes each.
    if (res.error === "unavailable") return { ok: false, status: 503, why: "validation unavailable" };
    if (h) await env.TASHAN_KV.put(h, "0", { expirationTtl: CACHE_TTL_S });
    return { ok: false, status: 403, why: "licence not valid" };
  }
  const d = res.data;

  const granted = d && d.status === "granted";
  const live = !d.expires_at || Date.parse(d.expires_at) > Date.now();
  const ok = Boolean(granted && live);
  if (h) await env.TASHAN_KV.put(h, ok ? "1" : "0", { expirationTtl: CACHE_TTL_S });
  return ok
    ? { ok: true, expires_at: d.expires_at || null }
    : { ok: false, status: 403, why: granted ? "licence expired" : "licence " + (d.status || "not valid") };
}

// One shape for every refusal, so no endpoint invents its own and leaks detail by accident.
export function deny(v) {
  return new Response(JSON.stringify({ error: v.why, docs: "https://tashan.sh/pricing.html" }), {
    status: v.status || 403,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}
