// Shared licence gate for every paid endpoint. Not routable itself — the leading underscore keeps
// Cloudflare Pages from publishing it as /api/_license.
//
// THERE IS NO ACCOUNT SYSTEM, DELIBERATELY. Polar validates a licence key from a public
// customer-portal endpoint that needs no seller token, so the key IS the credential: no passwords, no
// sessions, no password reset, no account table, and no PII of ours to leak. docs/AUDIT.md called
// "a backend with accounts and persistence" the single blocking investment for revenue. It isn't one.
// The customer manages the subscription in Polar's own portal, which already does cancellation,
// payment-method updates, invoices and receipts.

const POLAR_VALIDATE = "https://api.polar.sh/v1/customer-portal/license-keys/validate";
const CACHE_TTL_S = 300;   // see caching note below

// Never use a licence key as a cache key or log line — it is a bearer credential. Hash it.
async function keyHash(key) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(key));
  return Array.from(new Uint8Array(d)).map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 32);
}

// A key may arrive as `Authorization: Bearer <key>` or `?key=` (the CLI and curl differ in habit).
export function keyFrom(request) {
  const auth = request.headers.get("authorization") || "";
  if (/^Bearer\s+/i.test(auth)) return auth.replace(/^Bearer\s+/i, "").trim();
  try {
    return new URL(request.url).searchParams.get("key") || "";
  } catch {
    return "";
  }
}

export async function validate(env, key) {
  if (!key) return { ok: false, status: 401, why: "no licence key" };
  // FAIL CLOSED. An unconfigured deployment must refuse everyone, never admit everyone — the opposite
  // of e.js, where a missing analytics binding is allowed to no-op because nothing is being protected.
  if (!env.POLAR_ORG_ID) return { ok: false, status: 503, why: "billing not configured" };

  const h = env.TASHAN_KV ? "lic:" + (await keyHash(key)) : null;
  if (h) {
    // Cached for 5 minutes, which is the whole tradeoff: it keeps Polar out of the hot path, and it
    // means a revoked or refunded key keeps working for at most that long. Polar can auto-refund to
    // head off a chargeback, so this window is a real (small) exposure, not a theoretical one.
    const hit = await env.TASHAN_KV.get(h);
    if (hit === "1") return { ok: true, cached: true };
    if (hit === "0") return { ok: false, status: 403, why: "licence not valid" };
  }

  let d;
  try {
    const r = await fetch(POLAR_VALIDATE, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ key, organization_id: env.POLAR_ORG_ID }),
    });
    if (!r.ok) {
      // A 4xx from Polar means the key is bad; a 5xx means Polar is down. Do not cache the second
      // case as a negative, or a Polar outage would lock out paying customers for five minutes each.
      if (r.status >= 500) return { ok: false, status: 503, why: "validation unavailable" };
      if (h) await env.TASHAN_KV.put(h, "0", { expirationTtl: CACHE_TTL_S });
      return { ok: false, status: 403, why: "licence not valid" };
    }
    d = await r.json();
  } catch {
    return { ok: false, status: 503, why: "validation unavailable" };
  }

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
