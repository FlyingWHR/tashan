// HEAD, for every endpoint that has a GET.
//
// WHY. Cloudflare Pages routes by exported handler name, so a Function exporting only
// onRequestGet/onRequestPost answers HEAD with 404. Every agent-facing endpoint we have did:
// /v0.1/audit, /v0.1/kit, /api/history and /.well-known/x402 all 404'd on HEAD while answering GET
// perfectly. Static files were fine, which is why nothing noticed — the board and /v0.1/scores are
// served straight off disk.
//
// It matters because HEAD is what liveness probes use — it is the cheapest way to ask "are you
// there". Our first x402 directory listing was auto-verified and then filed as `health: down`,
// invisible in the index, while the endpoint itself was returning a perfectly good 402 to GET.
//
// RFC 9110: HEAD is GET with the body dropped, and the headers must be the ones GET would send.
// So this calls the real handler rather than inventing a cheaper answer — a probe that gets a
// different status from HEAD than from GET has been told something untrue.
export const headOf = (get) => async (ctx) => {
  const r = await get(ctx);
  return new Response(null, { status: r.status, headers: r.headers });
};
