// Cloudflare Pages Function — /api/account : the customer's own record, and the session that
// identifies them.
//
// WHY THIS EXISTS. The account page was rejected four times, and every rejection was the same
// defect wearing a different coat: it was a page *about* an account rather than an account. A
// heading, a paragraph explaining that there is no members' area, a button that threw you onto
// someone else's domain, and — worst — a box asking you to paste a licence key, which is a thing
// you ask a developer to do, not a customer. None of it showed the reader a single fact about
// themselves. That is what "makeshift" meant: the page had no state.
//
// It turns out we never needed an account system to fix that. Polar's customer-portal validate
// endpoint is PUBLIC and keyless, and it returns the whole record:
//
//   customer {name,email} · status · expires_at · limit_activations · usage · display_key
//
// So: who you are, what you are on, when it renews, and how many machines you have used. That is an
// account centre. It needs no seller token, no mail provider, no password, no session table, and no
// PII of ours to leak — the licence key IS the credential, exactly as it already is for the CLI and
// for every gated endpoint behind _license.js.
//
//   GET    /api/account            -> {signed_in:false} or the dashboard record
//   GET    /api/account?t=<token>  -> 302 to /account.html, sets the session cookie (CLI handoff)
//   POST   /api/account  {key}     -> signs in; returns {url} so the CLI can open a signed-in browser
//   DELETE /api/account            -> signs out
//
// THE HANDOFF IS WHY NOBODY TYPES A KEY. `tashan account` posts the key it already has, gets back a
// one-time URL, and opens it. Same shape as `gh auth login`, `wrangler login`, `stripe login` — the
// terminal proves who you are and the browser inherits it. The token is single-use, lives 120
// seconds in KV, and is not itself a credential, so it is safe in a URL where the key would not be.

import { COOKIE, clearCookie, cookieFrom, fetchLicence, setCookie } from "./_license.js";

const HANDOFF_TTL_S = 120;
const PORTAL = "https://polar.sh/tashan/portal";

const json = (body, status = 200, headers = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store", ...headers },
  });

// Never echo a licence key back to the browser. Polar's own `display_key` is already the masked
// form (last four), so there is nothing to invent and nothing to leak into a screenshot.
function dashboard(d) {
  const granted = d.status === "granted";
  const live = !d.expires_at || Date.parse(d.expires_at) > Date.now();
  return {
    signed_in: true,
    active: Boolean(granted && live),
    status: granted && !live ? "expired" : d.status || "unknown",
    email: (d.customer && d.customer.email) || null,
    name: (d.customer && d.customer.name) || null,
    display_key: d.display_key || null,
    expires_at: d.expires_at || null,
    // `usage` counts activations spent; a null limit means Polar was configured without one, which
    // is unlimited rather than zero. Rendering "0 machines" for unlimited would be a lie the
    // customer could act on, so the shape stays null and the page says "no limit".
    machines_used: typeof d.usage === "number" ? d.usage : null,
    machines_limit: typeof d.limit_activations === "number" ? d.limit_activations : null,
    portal: PORTAL,
  };
}

async function signIn(env, key, url) {
  if (!key) return json({ error: "no licence key" }, 400);
  if (!env.POLAR_ORG_ID) return json({ error: "billing not configured" }, 503);

  const res = await fetchLicence(env, key);
  if (res.error === "unavailable") return json({ error: "sign-in unavailable, try again" }, 503);
  if (res.error) return json({ error: "that licence key is not valid" }, 403);

  const headers = { "set-cookie": setCookie(key) };

  // The handoff token, for the CLI. Without KV we can still sign the caller in — the cookie above
  // is already set — but we cannot mint a one-time URL, and putting the key in one instead would
  // trade the whole reason this indirection exists. Say so rather than degrade quietly.
  let handoff = null;
  if (env.TASHAN_KV) {
    const b = crypto.getRandomValues(new Uint8Array(24));
    handoff = Array.from(b).map(x => x.toString(16).padStart(2, "0")).join("");
    await env.TASHAN_KV.put("ho:" + handoff, key, { expirationTtl: HANDOFF_TTL_S });
  }

  return json({
    ...dashboard(res.data),
    url: handoff ? `${url.origin}/api/account?t=${handoff}` : `${url.origin}/account`,
    handoff: Boolean(handoff),
  }, 200, headers);
}

// Single use: read and delete before honouring it. A handoff link that survives being clicked is a
// standing grant sitting in shell history and browser history both.
async function redeem(env, token, url) {
  const back = (q) => Response.redirect(url.origin + "/account" + q, 302);
  if (!env.TASHAN_KV) return back("?e=unavailable");
  const key = await env.TASHAN_KV.get("ho:" + token);
  if (!key) return back("?e=expired");
  await env.TASHAN_KV.delete("ho:" + token);
  return new Response(null, {
    status: 302,
    headers: { location: url.origin + "/account", "set-cookie": setCookie(key) },
  });
}

export async function onRequest({ request, env }) {
  const url = new URL(request.url);

  if (request.method === "GET" && url.searchParams.get("t")) {
    return redeem(env, url.searchParams.get("t"), url);
  }

  if (request.method === "DELETE") {
    return json({ signed_in: false }, 200, { "set-cookie": clearCookie() });
  }

  if (request.method === "POST") {
    let body = {};
    try { body = await request.json(); } catch { /* empty or malformed — treated as no key */ }
    return signIn(env, (body.key || "").trim(), url);
  }

  if (request.method !== "GET") return json({ error: "method not allowed" }, 405);

  // Deliberately the cookie only, not keyFrom(). A ?key= in the address bar would put a bearer
  // credential in browser history and in every Referer this page emits; sign-in is a POST for that
  // reason. The gated data endpoints still accept the other forms — that is where curl belongs.
  const key = cookieFrom(request, COOKIE);
  if (!key) return json({ signed_in: false, portal: PORTAL });

  const res = await fetchLicence(env, key);
  if (res.error === "unavailable") return json({ signed_in: true, unavailable: true, portal: PORTAL }, 503);
  // The stored key stopped working — refunded, revoked, or rotated. Clear the cookie so the page
  // shows a clean signed-out state instead of an error the reader can do nothing about.
  if (res.error) {
    return json({ signed_in: false, portal: PORTAL, was: "invalid" }, 200, { "set-cookie": clearCookie() });
  }
  return json(dashboard(res.data));
}
