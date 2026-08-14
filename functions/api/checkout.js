// Cloudflare Pages Function — GET /api/checkout?checkout_id=<id> : the post-purchase sign-in.
//
// Polar's success_url is set to
//     https://tashan.sh/api/checkout?checkout_id={CHECKOUT_ID}
// so the customer lands HERE, not on a page. `id=` is accepted too — see below. That field is no
// longer maintained by hand: /api/buy verifies and repairs it on the way to the checkout, because
// whether we get paid should not depend on a text box in someone else's dashboard staying right. This exchanges the checkout for their licence key,
// sets the session cookie, and 302s to /welcome. Nothing renders at this URL, no JavaScript is
// involved, and the checkout id never reaches a document — so it never appears in a Referer header
// from a rendered page, and works with JS off.
//
// THE EXCHANGE, three calls, all requiring the organisation token:
//   GET  /v1/checkouts/{id}          -> the checkout, and the customer it belongs to
//   POST /v1/customer-sessions/      -> a short-lived customer access token for that customer
//   GET  /v1/customer-portal/license-keys/  (with THAT token) -> their licence key
//
// WHY THIS ENDPOINT IS THE MOST DANGEROUS ONE IN THE CODEBASE, and what holds it.
// POLAR_ORG_TOKEN can read every customer's record. This function turns a checkout id — a value
// that travels in a redirect URL and lands in browser history — into a signed-in session. So:
//
//   1. SINGLE USE. The id is burned in KV before the cookie is issued. A replay of a leaked URL
//      gets nothing. Without KV we refuse outright rather than run without that guarantee.
//   2. THE CHECKOUT MUST BE PAID. An abandoned or expired checkout signs nobody in — otherwise
//      anyone who started a checkout and walked away holds a key to that customer's account.
//   3. FRESHNESS. A checkout older than the window is refused. The redirect happens seconds after
//      payment; an id surfacing days later is not a customer arriving from Polar.
//   4. NOTHING IS ECHOED. The licence key goes into an HttpOnly cookie and is never in a response
//      body, and the org token is never logged, returned, or sent anywhere but api.polar.sh.
//
// Every failure path lands on /welcome, which still offers the paste-your-key form — so a customer
// is never stranded by an outage on Polar's side.

import { setCookie } from "./_license.js";

const POLAR = "https://api.polar.sh/v1";
const MAX_AGE_S = 60 * 60 * 24;      // a checkout older than a day is not someone arriving from it
const BURN_TTL_S = 60 * 60 * 24 * 30;

const back = (origin, q = "") => Response.redirect(origin + "/welcome" + q, 302);

async function polar(env, path, init = {}, token = null) {
  const r = await fetch(POLAR + path, {
    ...init,
    headers: {
      authorization: "Bearer " + (token || env.POLAR_ORG_TOKEN),
      "content-type": "application/json",
      ...(init.headers || {}),
    },
  });
  if (!r.ok) return { ok: false, status: r.status };
  return { ok: true, data: await r.json().catch(() => null) };
}

export async function onRequest({ request, env }) {
  const url = new URL(request.url);
  // BOTH SPELLINGS. This file's header, and the runbook, said to configure `id={CHECKOUT_ID}` —
  // but Polar's own API documentation for success_url says to add `checkout_id={CHECKOUT_ID}`.
  // Anyone following the vendor's docs would have configured the field correctly and still landed
  // here with nothing to read, and the failure is invisible: a redirect to /welcome and a paste
  // form, exactly like a customer who never paid. Accept either name.
  const id = (url.searchParams.get("id") ||
              url.searchParams.get("checkout_id") || "").trim();

  if (!id) return back(url.origin);
  // NOT CONFIGURED IS ITS OWN ANSWER. These two used to redirect to a bare /welcome, identical to a
  // checkout id that simply did not resolve — so a missing binding and a bad id looked the same from
  // outside, and the only way to discover that auto-sign-in was off was a paying customer landing on
  // a paste form. Saying which lets it be checked before someone buys. It leaks nothing: that the
  // site is not set up is evident to anyone who completes a purchase, and no value is disclosed.
  if (!env.POLAR_ORG_TOKEN) return back(url.origin, "?e=unconfigured");
  // No KV means no single-use guarantee. Refuse rather than issue a session from a replayable URL.
  if (!env.TASHAN_KV) return back(url.origin, "?e=unconfigured");

  // 1. Burn the id FIRST. Doing this after the exchange would leave a window where two concurrent
  //    requests with the same id both succeed.
  const burnKey = "co:" + id;
  if (await env.TASHAN_KV.get(burnKey)) return back(url.origin, "?e=used");
  await env.TASHAN_KV.put(burnKey, "1", { expirationTtl: BURN_TTL_S });

  const co = await polar(env, "/checkouts/" + encodeURIComponent(id));
  if (!co.ok || !co.data) return back(url.origin);

  // 2. Paid, and recent. Polar's terminal success status is "succeeded"; "confirmed" is accepted
  //    too because it is the state a confirmed-but-settling payment sits in.
  const status = String(co.data.status || "").toLowerCase();
  if (status !== "succeeded" && status !== "confirmed") return back(url.origin, "?e=unpaid");

  const when = Date.parse(co.data.modified_at || co.data.created_at || "");
  if (when && (Date.now() - when) / 1000 > MAX_AGE_S) return back(url.origin, "?e=stale");

  const customerId = co.data.customer_id || (co.data.customer && co.data.customer.id);
  if (!customerId) return back(url.origin);

  // 3. A customer session — short-lived, scoped to this one customer, and the only credential the
  //    portal call is allowed to see. The org token never touches the customer-portal API.
  const sess = await polar(env, "/customer-sessions/", {
    method: "POST",
    body: JSON.stringify({ customer_id: customerId }),
  });
  if (!sess.ok || !sess.data || !sess.data.token) return back(url.origin);

  const keys = await polar(env, "/customer-portal/license-keys/?limit=10", {}, sess.data.token);
  if (!keys.ok || !keys.data) return back(url.origin);

  const items = keys.data.items || keys.data.result?.items || [];
  // Prefer a granted key; a customer who has churned and re-subscribed can hold several.
  const rec = items.find((k) => String(k.status || "").toLowerCase() === "granted") || items[0];
  const key = rec && (rec.key || rec.license_key);
  if (!key) return back(url.origin);

  return new Response(null, {
    status: 302,
    headers: { location: url.origin + "/welcome", "set-cookie": setCookie(key) },
  });
}
