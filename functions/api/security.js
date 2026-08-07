// Cloudflare Pages Function — GET /api/security?id=<capability id> : the audit's DETAIL, for
// licence holders.
//
// WHY THIS EXISTS. The pricing page sold "the advisory itself — which CVE or GHSA, its severity, the
// affected range, and the version that fixes it" and "what the install script actually runs, and the
// full permission list", and NOTHING delivered either one. No endpoint served them, no CLI path
// printed them, and capability.js made no gated fetch at all — so every capability page carried an
// "unlock detail" link a paying customer could click forever with nothing behind it. Worse, until
// build.py::redact_paid landed, the same values sat in /data/capabilities.json for anyone to curl:
// the leak was simultaneously the only way to obtain what Pro advertised. docs/FEATURE-AUDIT.md has
// the full matrix; tests/test_promises.py fails the build if a sold feature loses its delivery path.
//
// The free tier is untouched and must stay that way. The EXISTENCE of every finding stays public —
// how many advisories, at what severity, that an install script exists, that a permission surface
// exists. This endpoint adds only what you need to act: which advisory, what the script runs, the
// whole permission list. Hiding the existence of a vulnerability behind a paywall would be
// indefensible for a product whose claim is that it tells you the truth about what you run.
//
// Shape and plumbing deliberately mirror history.js — same gate, same KV, same bucket arithmetic —
// because a second pattern for the same job is how this codebase's other defects started.

import { keyFrom, validate, activationFrom, deny } from "./_license.js";

const SHARDS = 64;

// MUST stay byte-for-byte equivalent to bucket_of() in pipeline/push_security.py, and identical to
// bucketOf() in history.js. A cheap character sum, because ids are `<kind>:<name>` and bucketing on
// the first character puts pkg: and plugin: — 5,150 of 6,530 rows — in one shard.
export function bucketOf(id) {
  const s = String(id || "");
  let sum = 0;
  for (let i = 0; i < s.length; i++) sum += s.charCodeAt(i);
  return String(sum % SHARDS);
}

const json = (body, status = 200, extra = {}) =>
  new Response(JSON.stringify(body), {
    status,
    // Private: per-customer paid data, so no shared cache may ever hold it.
    headers: { "content-type": "application/json", "cache-control": "private, max-age=60", ...extra },
  });

export async function onRequestGet({ request, env }) {
  const id = new URL(request.url).searchParams.get("id");
  if (!id) return json({ error: "pass ?id=<capability id>, e.g. pkg:tavily-mcp" }, 400);

  const v = await validate(env, keyFrom(request), activationFrom(request));
  if (!v.ok) return deny(v);

  if (!env.TASHAN_KV) return json({ error: "security store not configured" }, 503);

  const shard = await env.TASHAN_KV.get("sec:" + bucketOf(id), "json");
  const rec = (shard && shard[id]) || null;
  if (!rec) {
    // AN EMPTY STORE IS NOT A CAPABILITY WE HAVE NOTHING ON, and conflating them is the most
    // expensive bug this codebase can have. pipeline/push_security.py skips without CF credentials,
    // so the paid store can be entirely unpopulated while every request answers the same innocuous
    // "no audit detail recorded for this id" — which reads as thin coverage. A customer paying $6
    // would see it for EVERY package, conclude the product is useless, and refund. It does not look
    // broken. It looks bad, which is worse, and nothing surfaces it.
    const meta = await env.TASHAN_KV.get("sec:meta", "json");
    if (!meta) {
      return json({
        id, detail: null, error: "paid detail has not been published yet",
        note: "This is a delivery fault on our side, not a finding about this capability. The audit " +
              "is free and complete on the capability's own page; your licence is unaffected.",
        free: "https://tashan.sh/capability.html?id=" + encodeURIComponent(id),
        support: "https://tashan.sh/support.html",
      }, 503);
    }
    // A capability with no npm package is not scannable, and one with nothing found has nothing to
    // add beyond what the page already says for free. Neither is an error, and neither may be
    // reported in a way that reads as "we scanned it and it was clean".
    return json({ id, detail: null, note: "no audit detail recorded for this id",
                  published_at: meta.pushed_at || null }, 404);
  }

  return json({
    id,
    advisories: rec.a || [],          // [{id, severity, summary, fixed}]
    install_script: rec.s || null,    // the literal command run at install time
    scanned_at: rec.t || null,
    source: "tashan security audit",
    licence: "paid",
  });
}
