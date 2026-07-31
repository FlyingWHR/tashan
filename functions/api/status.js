// Licence status for the account page. GET /api/status?key=…  (or Authorization: Bearer …)
//
// The account page has to SHOW something — "you are Pro, this key, these devices, renews then" —
// or it is an article about billing rather than an account. It cannot ask Polar directly because
// the CSP is `default-src 'self'` and loosening that for one panel is a bad trade, so this proxies
// the same public customer-portal validation the CLI uses.
//
// It exposes nothing a holder of the key could not already get from Polar's own public endpoint,
// and it deliberately returns LESS: the key never comes back in the response, only its last four
// characters, so a status panel left open on a screen does not leak the credential.
import { validate, keyFrom, activationFrom } from "./_license.js";

const NO_STORE = { "content-type": "application/json", "cache-control": "no-store" };

export async function onRequestGet({ request, env }) {
  const key = keyFrom(request);
  if (!key) {
    return new Response(JSON.stringify({ state: "none" }), { status: 200, headers: NO_STORE });
  }

  const v = await validate(env, key, activationFrom(request));

  // 503 means WE could not check — Polar down, or billing unconfigured. That is not the same as an
  // invalid key and must never be rendered as one: telling a paying customer their licence is dead
  // because our dependency blinked is the worst possible failure here.
  if (!v.ok && v.status === 503) {
    return new Response(JSON.stringify({ state: "unknown", why: v.why }),
                        { status: 200, headers: NO_STORE });
  }
  if (!v.ok) {
    return new Response(JSON.stringify({ state: "invalid", why: v.why }),
                        { status: 200, headers: NO_STORE });
  }
  return new Response(JSON.stringify({
    state: "active",
    tail: key.slice(-4),                 // enough to recognise, useless to steal
    expires_at: v.expires_at || null,
  }), { status: 200, headers: NO_STORE });
}
