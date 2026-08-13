// Cloudflare Pages Function — POST /v0.1/audit
//
// THE AGENT-NATIVE PRODUCT. Everything else we sell assumes a human: sign up, hold a licence key,
// amortise $6/mo over a month. An agent maintaining somebody's stack has none of that and does not
// want it. What it has is a list — the servers in this config — and one question: is any of this
// rotting, and what do I do about it. That question is per-request by nature, it is worth real money
// once, and it is the one thing a static index cannot answer, because the answer is about YOUR list.
//
// THE FREE/PAID LINE, AND WHY IT FALLS EXACTLY HERE.
//
//   FREE, always, no credential, no payment, whatever else is in the request: every risk we know
//   about every capability you named. Advisories, deprecation, archived repos, a maintainer count
//   that fell to one, a registry entry that was deleted. This is public evidence and it is the whole
//   product's reason to be trusted — an audit that hides a known vulnerability behind a paywall is
//   not an instrument, it is a hostage. `tests/test_firewall.py` and the pricing page both say the
//   existence of a risk is never gated, and an endpoint aimed at machines is exactly where that
//   promise is easiest to quietly break.
//
//   PAID: the score history behind each row, and therefore the trend — whether the thing you run is
//   a project getting better or one on its way down. That is the un-backfillable series, the one
//   asset here that compounds and the one nobody can re-derive from today's npm.
//
// So the free answer is a complete risk audit, and payment buys the direction of travel.
//
// TWO WAYS TO PAY, one endpoint. A licence key (Authorization: Bearer) for the humans and CLIs that
// already have one; x402 (PAYMENT-SIGNATURE) for callers that would rather spend a fraction of a
// cent than hold an account. See functions/api/_x402.js — the x402 path stays dormant, quoting
// nothing, until a wallet exists.

import { validate, keyFrom, activationFrom, OFFER } from "../api/_license.js";
import { bucketOf } from "../api/history.js";
import { PRICED, configured, paymentRequired, requiredHeader, paymentFrom, charge, responseHeader }
  from "../api/_x402.js";

const MAX_SERVERS = 200;          // bounds the work; an honest cap that is reported, never silent
const PRICE_KEY = "config-audit";

const json = (body, status = 200, extra = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "access-control-allow-origin": "*",
      // Never shared-cached: the response is about the caller's own list, and once it carries paid
      // history it is per-customer data.
      "cache-control": "no-store",
      ...extra,
    },
  });

export const onRequestOptions = () =>
  new Response(null, { status: 204, headers: {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "POST, OPTIONS",
    "access-control-allow-headers": "content-type, authorization, payment-signature, x-tashan-activation",
  } });

export const onRequestGet = () => json({
  error: "POST a JSON body to this endpoint",
  usage: {
    method: "POST",
    body: { servers: ["chrome-devtools-mcp", "pkg:tavily-mcp"], history: false, since: "2026-07-01" },
    free: "Every risk we know about every capability you name — advisories, deprecation, archived "
        + "repos, single-maintainer, registry removal. No credential, no payment.",
    paid: "`history: true` adds the score series and the trend behind each row. Pay with a licence "
        + "(Authorization: Bearer <key>) or per call with x402.",
    limit: MAX_SERVERS,
  },
}, 400);

/** Resolve a caller's name or id to a record, the same way /v0.1/lookup does. */
function resolve(data, name) {
  const keys = data.keys || {};
  const k = String(name || "").trim();
  const i = keys[k] ?? keys[k.replace(/^npm:/, "")] ?? keys["pkg:" + k];
  return i === undefined ? null : data.records[i];
}

/**
 * The free half: every risk we hold about one row, and a plain verdict.
 *
 * `flags` are facts, each one independently checkable against the sources we publish. `verdict` is
 * the only opinion here and it is a function of the flags alone — an agent that disagrees with our
 * weighting can ignore it and read the flags, which is why both ship.
 */
function assess(r) {
  const flags = [];
  if (r.sec_advisory_count) flags.push({ k: "advisory", n: r.sec_advisory_count,
    say: r.sec_advisory_count + " known advisor" + (r.sec_advisory_count === 1 ? "y" : "ies")
       + " at the version you would install today" });
  if (r.npm_deprecated) flags.push({ k: "deprecated", say: "the author has marked it deprecated on npm" });
  if (r.gh_archived) flags.push({ k: "archived", say: "the repository is archived" });
  if (r.registry_status === "deleted") flags.push({ k: "delisted", say: "removed from the MCP registry" });
  if (r.single_maintainer) flags.push({ k: "bus-factor", say: "one maintainer" });
  if (r.vitality && r.vitality !== "active") flags.push({ k: "vitality", say: "not active: " + r.vitality });
  if (r.sec_remote_content) flags.push({ k: "remote-content",
    say: "can carry third-party text into the model's context" });

  const stop = flags.some(f => ["advisory", "deprecated", "delisted"].includes(f.k));
  const look = flags.length > 0;
  return {
    id: r.id, name: r.name, label: r.label,
    tashan_score: r.tashan_score ?? null,
    rated: r.rated !== false,
    vitality: r.vitality || null,
    expertise: r.expertise_verdict || null,
    flags,
    verdict: stop ? "replace" : look ? "review" : "keep",
    url: "https://tashan.sh/capability/" + r.slug + ".html",
  };
}

/** The paid half: the series, and what it did between `since` and now. */
async function history(env, rows, since) {
  const want = new Map();
  for (const a of rows) want.set(a.id, bucketOf(a.id));
  const buckets = [...new Set(want.values())];
  const shards = {};
  await Promise.all(buckets.map(async (b) => {
    shards[b] = (await env.TASHAN_KV.get("hist:" + b, "json")) || {};
  }));
  const out = {};
  for (const a of rows) {
    const shard = shards[want.get(a.id)] || {};
    const series = shard[a.id];
    if (!series) { out[a.id] = { series: null, note: "no history recorded yet" }; continue; }
    const pts = Object.entries(series).sort();               // [date, score] ascending
    const after = since ? pts.filter(([d]) => d >= since) : pts;
    const base = after.length ? after[0] : pts[pts.length - 1];
    const last = pts[pts.length - 1];
    const delta = (Number(last[1]) - Number(base[1]));
    out[a.id] = {
      series,
      // The scorer map ships with every series because a trend across a version boundary measures
      // OUR recalibration, not the project. cli/doctor.mjs refuses to compare across it and so
      // should anyone else.
      scorers: shard._scorers || {},
      first: base[0], latest: last[0],
      change: Number.isFinite(delta) ? Math.round(delta * 10) / 10 : null,
      direction: !Number.isFinite(delta) || Math.abs(delta) < 0.5 ? "flat" : (delta > 0 ? "up" : "down"),
    };
  }
  return out;
}

export async function onRequestPost({ request, env, next }) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "body must be JSON: {\"servers\": [...]}" }, 400);
  }
  const names = Array.isArray(body && body.servers) ? body.servers : null;
  if (!names || !names.length) {
    return json({ error: "pass {\"servers\": [\"<name or id>\", …]}" }, 400);
  }
  const capped = names.length > MAX_SERVERS;
  const list = names.slice(0, MAX_SERVERS);

  const origin = new URL(request.url).origin;
  let data;
  try {
    const r = await fetch(origin + "/data/lookup.json", { cf: { cacheTtl: 300, cacheEverything: true } });
    if (!r.ok) throw new Error("lookup " + r.status);
    data = await r.json();
  } catch (e) {
    // Never invent an answer about whether software is safe.
    return json({ error: "measurement data unavailable", detail: String(e) }, 502);
  }

  const audited = [], unmeasured = [];
  for (const nm of list) {
    const rec = resolve(data, nm);
    if (rec) audited.push(assess(rec));
    // "We have not measured this" is a real answer and must not read as "fine".
    else unmeasured.push(String(nm));
  }

  const base = {
    audited,
    unmeasured,
    summary: {
      requested: names.length,
      measured: audited.length,
      replace: audited.filter(a => a.verdict === "replace").length,
      review: audited.filter(a => a.verdict === "review").length,
      keep: audited.filter(a => a.verdict === "keep").length,
      unmeasured: unmeasured.length,
    },
    generated_at: data.generated_at,
    scorer: data.scorer,
    method: "https://tashan.sh/methodology.html",
    note: "Every finding above is free and needs no account. Absence means unmeasured, never safe. "
        + "Nothing purchasable moves a score, a rank or a listing.",
  };
  if (capped) {
    base.capped = { limit: MAX_SERVERS, dropped: names.length - MAX_SERVERS,
                    say: "Only the first " + MAX_SERVERS + " were audited. Split the list and call again." };
  }
  if (!body.history) {
    base.history_available = {
      how: "re-send with {\"history\": true}",
      buys: "The score series behind each row and its direction of travel since a date you name.",
      pay: ["Authorization: Bearer <licence key> — " + OFFER.plans.map(p => `$${p.amount}/${p.period}`).join(" or "),
            "or per call with x402: " + (configured(env) ? "$" + PRICED[PRICE_KEY].usd + " per audit"
                                                         : "not yet enabled on this deployment")],
      start: "https://tashan.sh/pricing.html",
    };
    return json(base);
  }

  // ---- from here the caller wants the paid half ---------------------------------------------------
  if (!env.TASHAN_KV) return json({ ...base, error: "history store not configured" }, 503);
  const since = typeof body.since === "string" && /^\d{4}-\d{2}-\d{2}$/.test(body.since)
    ? body.since : null;
  const run = async () => ({ ...base, since, history: await history(env, audited, since) });

  // 1. A licence, if one was presented. An expired or invalid key is a 403 and must NOT silently
  //    fall through to "well, pay with crypto then" — that reads as the subscription being ignored.
  const key = keyFrom(request);
  if (key) {
    const v = await validate(env, key, activationFrom(request));
    if (!v.ok) return json({ error: v.why, docs: "https://tashan.sh/pricing" }, v.status || 403);
    return json(await run());
  }

  // 2. x402, if the deployment has a wallet and the caller signed a payment.
  const pr = paymentRequired(env, PRICE_KEY, origin + "/v0.1/audit",
                             "payment required for the history half of this audit");
  const payment = paymentFrom(request);
  if (pr && payment) {
    const out = await charge(env, pr, payment, run);
    if (!out.ok) {
      return json({ ...pr, error: "payment " + out.reason }, 402, requiredHeader(pr));
    }
    return json(out.result, 200, responseHeader(out.settlement));
  }

  // 3. Neither. 402 with the terms — spec-shaped when x402 is live, and always carrying the
  //    subscription price and THE FREE AUDIT ITSELF, because the risks were never the paid part.
  return json({
    ...(pr || {}),
    error: "payment required for the history half of this audit",
    free_result: base,
    plans: OFFER.plans,
    credential: { header: "Authorization: Bearer <licence-key>", obtain: "https://tashan.sh/pricing" },
    docs: "https://tashan.sh/pricing",
  }, 402, { ...requiredHeader(pr), link: '<https://tashan.sh/pricing>; rel="payment"' });
}
