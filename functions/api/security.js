// Cloudflare Pages Function — GET /api/security?id=<capability id> : one capability's audit, FREE.
//
// IT WAS A PAYWALL AND IT SHOULD NOT HAVE BEEN. It was built to deliver what the pricing page sold —
// "the advisory itself, and the version that fixes it" — back when that was paid. It is not paid any
// more: build.py's redact_paid() moved advisory detail and the install command into the public
// export, on the reasoning that "naming a risk and then charging to say which risk is a worse
// position than not scanning at all". Everything here is already free at /v0.1/lookup?name=… and in
// /data/lookup.json, per capability, with no account.
//
// So the gate came off. Charging $0.01 for data we publish free is not a pricing question, it is a
// contradiction — and our own 402 body pointed callers at /data/lookup.json for exactly these
// fields while quoting them a price for them.
//
// THE LINE, restated: the CURRENT STATE is free — every finding, its severity, the fixing version,
// the install command, the permission surface. What is paid is TIME: the series behind a score
// (/api/history) and being told the day something changes. history.js's header has always said so.
//
// This endpoint still earns its place: it answers for ONE capability, where the free bulk file is
// 6.9 MB. It is a convenience over free data, which is a fine thing for a free endpoint to be.

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
    // Free data now, so a shared cache is allowed and wanted — this is the same audit the
    // dossier and /v0.1/lookup publish, not a per-customer payload.
    headers: { "content-type": "application/json", "cache-control": "public, max-age=300", ...extra },
  });

export async function onRequestGet({ request, env }) {
  const id = new URL(request.url).searchParams.get("id");
  if (!id) return json({ error: "pass ?id=<capability id>, e.g. pkg:tavily-mcp" }, 400);

  // NO LICENCE GATE. This endpoint used to require one and `security-detail` was priced at $0.01.
  // It sold nothing: build.py's redact_paid() made advisory detail and the install command FREE in
  // the public export, and /v0.1/lookup?name=… returns the advisory ids, severities, fixed versions,
  // install script and scan date to anyone, with no account. Our own 402 body even named
  // /data/lookup.json as a free source of exactly those fields — quoting a price beside a pointer to
  // the same data for nothing.
  //
  // The rule was already written down, in redact_paid() and in history.js's header: the CURRENT
  // STATE is free, and what is paid is TIME — the series, and being told the day something changes.
  // This endpoint returns current state, so it is free. That is enforcement of the existing policy,
  // not a new one.
  //
  // The endpoint-level licence guards that used to live in security.test.mjs were not deleted with
  // the paywall; they were ported to history.test.mjs, which is the endpoint that still has one.
  if (!env.TASHAN_KV) return json({ error: "security store not configured" }, 503);

  const shard = await env.TASHAN_KV.get("sec:" + bucketOf(id), "json");
  const rec = (shard && shard[id]) || null;
  if (!rec) {
    // NO CUSTOMER-FACING ALARM, because emptiness cannot be proved cheaply and a false one is
    // worse than the bug it guards. The concern was real — push_security.py skips without CF
    // credentials, and an unpopulated store would answer every request with the same innocuous
    // "no audit detail recorded", reading as thin coverage rather than an undelivered product. But
    // the store IS populated (CI pushes 61 shards nightly; a local run without the credentials is
    // not evidence), and a 503 here would tell a paying customer their product is broken when it
    // is not. An absent shard means this bucket has nothing, which is ordinary.
    //
    // So the manifest is a DIAGNOSTIC, not a verdict: `store_published_at` lets an operator see
    // whether the store was ever pushed, and nobody is alarmed on the strength of an inference.
    const meta = await env.TASHAN_KV.get("sec:meta", "json");
    // THIS NOW MEANS ONE THING ONLY: we have never scanned it. It used to mean that OR "scanned and
    // clean", because the store only carried rows with a finding — so 93.7% of everything we had
    // audited answered 404, including chrome-devtools-mcp and @playwright/mcp. The refusal to call
    // an absent record "clean" was correct; the fix was to stop the record being absent. See
    // push_security.py, which now ships every scanned row.
    return json({ id, detail: null, scanned: false,
                  note: "this capability has not been scanned — unknown, not clean. A capability "
                        + "with no npm package cannot be scanned at all.",
                  store_published_at: (meta && meta.pushed_at) || null }, 404);
  }

  // A record with only `t` is a scanned-clean row, and that is an ANSWER, not an empty response.
  // `clean` is stated explicitly rather than left to be inferred from two empty fields, because
  // "advisories: []" is what a caller also sees when something failed to parse.
  const advisories = rec.a || [];
  return json({
    id,
    scanned: true,
    clean: advisories.length === 0 && !rec.s,
    advisories,                       // [{id, severity, summary, fixed}]
    install_script: rec.s || null,    // the literal command run at install time
    scanned_at: rec.t || null,
    source: "tashan security audit",
    licence: "free",
  });
}
