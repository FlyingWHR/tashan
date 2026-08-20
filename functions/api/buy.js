// Cloudflare Pages Function — GET /api/buy?plan=monthly|annual : the buy button.
//
// WHY THIS EXISTS AT ALL, when a plain link to buy.polar.sh already worked.
//
// The post-purchase hand-off depends on ONE field that lives in somebody else's dashboard: the
// checkout link's `success_url`. It has to be
//     https://tashan.sh/api/checkout?checkout_id={CHECKOUT_ID}
// or the customer lands on /welcome with no id, cannot be identified, and is asked to paste a
// licence key they have not been given yet. That field was wrong for weeks. Nothing we owned could
// see it, nothing we owned could fix it, and the fix was a human remembering to click a text box.
//
// `POLAR_ORG_TOKEN` can already read and write checkout links — the token was here the whole time,
// used only to exchange a checkout for a licence. So the button now walks through us, confirms the
// field, and repairs it if it is wrong. A configuration value that decides whether we get paid
// should not depend on anyone remembering anything.
//
// FOUR RULES, in the order they matter:
//
//  1. NEVER BLOCK A SALE. Every failure path still redirects to Polar. No token, no KV, Polar down,
//     a PATCH refused — the customer buys anyway and lands on the paste form, which is exactly
//     where they landed before this file existed. This endpoint can only improve the outcome, and
//     the `try` around the whole repair is load-bearing, not decoration.
//  2. AT MOST ONE SLOW CLICK. A KV flag records that the field is correct, so the healthy path
//     makes no Polar call at all. The flag expires daily, so a value changed back in the dashboard
//     is caught within a day rather than never.
//  3. RECORD THE CLICK HERE. funnel.py counts reaching Polar as an `outbound` event whose key
//     matches '%polar%', and the browser used to emit it because the href pointed at another host.
//     Routing through our own origin would have silently zeroed the only measurement of the money
//     funnel. Writing it server-side keeps that row alive AND makes it more truthful: it counts
//     redirects actually served, which no ad-blocker can suppress and no beacon can lose.
//  4. NO REDIRECT TARGET COMES FROM THE QUERY STRING. `plan` selects from two constants. A caller
//     cannot steer this at anything but Polar, so there is no open redirect to reason about.

const LINK = {
  // These are the two links pricing.html publishes. They are public URLs, not secrets.
  // tests/test_claims.py fails if these disagree with what the page actually shows, so the button
  // and the page can never drift into selling different things.
  monthly: "polar_cl_pc42cdJpEltRSFaI3Uz2oYgmKbWN6ytw6os6X0IuB0d",
  annual: "polar_cl_ESzG71NaofNkWbLp6wBSpLtuAfuv13XDYE6121Rd2jl",
};

const POLAR = "https://api.polar.sh/v1";
const OK_FLAG = "polar:su_ok:";     // this link's success_url is correct — skip the network entirely
const TRIED_FLAG = "polar:su_try:"; // we just tried and failed — back off rather than hammer Polar
const OK_TTL_S = 60 * 60 * 24;      // re-verify daily: a dashboard edit should not go unnoticed forever
const TRY_TTL_S = 60 * 10;

export const buyUrl = (secret) => "https://buy.polar.sh/" + secret;

/** The success_url we need, and the test for one that is already good enough.
 *
 * BOTH SPELLINGS PASS. Polar's own documentation says to add `checkout_id={CHECKOUT_ID}`; this
 * project's runbook said `id={CHECKOUT_ID}`. /api/checkout now reads either, so a link configured
 * by hand the documented way is CORRECT and must not be rewritten — otherwise every daily
 * re-verification would PATCH a field that was already working. */
export const wantUrl = (origin) => origin + "/api/checkout?checkout_id={CHECKOUT_ID}";

export function successUrlOk(su, origin) {
  if (!su) return false;
  return su.startsWith(origin + "/api/checkout?") && su.includes("{CHECKOUT_ID}");
}

async function polar(env, path, init = {}) {
  const r = await fetch(POLAR + path, {
    ...init,
    headers: {
      authorization: "Bearer " + env.POLAR_ORG_TOKEN,
      "content-type": "application/json",
      ...(init.headers || {}),
    },
  });
  if (!r.ok) return null;
  return await r.json().catch(() => null);
}

/** Confirm — and if necessary repair — this checkout link's success_url. Returns a short reason
 * string for the test; the caller ignores it. Throws nothing the caller has to handle. */
export async function ensureSuccessUrl(env, secret, origin, api = polar) {
  if (!env.POLAR_ORG_TOKEN || !env.TASHAN_KV) return "unconfigured";
  if (await env.TASHAN_KV.get(OK_FLAG + secret)) return "cached";
  if (await env.TASHAN_KV.get(TRIED_FLAG + secret)) return "backoff";

  const q = env.POLAR_ORG_ID ? "?limit=100&organization_id=" + encodeURIComponent(env.POLAR_ORG_ID)
                             : "?limit=100";
  const list = await api(env, "/checkout-links/" + q);
  const items = (list && (list.items || (list.result && list.result.items))) || [];
  const link = items.find((l) => String(l.url || "").endsWith("/" + secret));
  if (!link) {
    // The link we publish is not in the organisation's list. Do not guess and do not patch
    // something else — back off and let the redirect happen.
    await env.TASHAN_KV.put(TRIED_FLAG + secret, "1", { expirationTtl: TRY_TTL_S });
    return "not-found";
  }

  if (successUrlOk(link.success_url, origin)) {
    await env.TASHAN_KV.put(OK_FLAG + secret, "1", { expirationTtl: OK_TTL_S });
    return "already-ok";
  }

  const patched = await api(env, "/checkout-links/" + encodeURIComponent(link.id), {
    method: "PATCH",
    body: JSON.stringify({ success_url: wantUrl(origin) }),
  });
  if (!patched) {
    await env.TASHAN_KV.put(TRIED_FLAG + secret, "1", { expirationTtl: TRY_TTL_S });
    return "patch-failed";
  }
  await env.TASHAN_KV.put(OK_FLAG + secret, "1", { expirationTtl: OK_TTL_S });
  return "repaired";
}

export async function onRequest({ request, env }) {
  const url = new URL(request.url);
  const plan = url.searchParams.get("plan") === "annual" ? "annual" : "monthly";
  const secret = LINK[plan];

  // Rule 3 — the funnel's checkout row, written where it cannot be lost.
  //
  // BUT NOT FOR OUR OWN MONITORING. check_payments.py hits this route twice on every run — once per
  // plan — to verify the redirect and repair the success_url. Moving the event server-side made it
  // immune to ad-blockers and also made it count every non-buyer that touches the URL, and the
  // biggest such non-buyer is us. The first week's funnel read "0 offer clicks, 43 reached Polar
  // checkout", which is arithmetically impossible for real traffic and was ~21 runs x 2 plans.
  //
  // A metric a team can inflate by testing is worse than no metric: it manufactures the exact
  // number a founder would celebrate. Only OUR OWN checker is excluded, by its declared user-agent
  // — a real agent hitting this route IS a genuine signal and must still count.
  // A CRAWLER IS NOT A BUYER. /api/buy is a plain href on pricing.html and is deliberately
  // published in llms.txt, so every bot that follows links reaches it — and the funnel read
  // "0 offer clicks, 47 reached Polar checkout", which is impossible for humans and is the same
  // shape as the 43 fake checkouts our own monitoring once manufactured. The redirect still works
  // for anyone; only the METRIC excludes them, because the point of this row is counting people
  // who chose to buy.
  const ua = request.headers.get("user-agent") || "";
  const isSelfCheck = ua.includes("tashan-payment-check");
  const isBot = /bot|crawl|spider|slurp|bingpreview|facebookexternalhit|headless|python-|curl\/|wget|scrapy|semrush|ahrefs|dataforseo|petalbot|yandex/i.test(ua);
  try {
    if (env.TASHAN_AE && !isSelfCheck && !isBot) {
      env.TASHAN_AE.writeDataPoint({
        indexes: ["outbound"],
        blobs: ["outbound", "/api/buy", "", "buy.polar.sh", "buy-" + plan, "",
                (request.cf && request.cf.country) || "", ""],
        doubles: [1],
      });
    }
  } catch (_) { /* never fail a sale for a metric */ }

  // Rule 1 — the repair is best-effort, always. Rule 2 — usually it does not even open a socket.
  try {
    await ensureSuccessUrl(env, secret, url.origin);
  } catch (_) { /* Polar down, token revoked, KV hiccup: the customer still gets to buy */ }

  return new Response(null, {
    status: 302,
    headers: { location: buyUrl(secret), "cache-control": "no-store" },
  });
}

export const _LINK = LINK;
