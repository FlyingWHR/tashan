// node functions/api/_head.test.mjs
//
// Every agent-facing endpoint answered HEAD with 404 while answering GET perfectly, because Pages
// routes by exported handler name. HEAD is what liveness probes use, so our first x402 directory
// listing was auto-verified and then filed `health: down` — listed, and invisible.
import assert from "node:assert";
import { headOf } from "./_head.js";
import { onRequestHead as auditHead, onRequestGet as auditGet } from "../v0.1/audit.js";
import { onRequestHead as wkHead, onRequestGet as wkGet } from "../.well-known/x402.js";

let pass = 0, fail = 0;
const ok = (c, m) => { c ? pass++ : (fail++, console.log("  FAIL " + m)); };

// RFC 9110: same status, same headers, no body. A probe told a different status by HEAD than by
// GET has been told something untrue — which is worse than not answering at all.
const ctx = (url) => ({ request: new Request(url), env: {} });

for (const [name, head, get, url] of [
  ["/v0.1/audit", auditHead, auditGet, "https://tashan.sh/v0.1/audit"],
  ["/.well-known/x402", wkHead, wkGet, "https://tashan.sh/.well-known/x402"],
]) {
  const h = await head(ctx(url));
  const g = await get(ctx(url));
  ok(h.status === g.status, `${name}: HEAD status ${h.status} must equal GET status ${g.status}`);
  ok(h.status !== 404, `${name}: HEAD must not 404 — that is what a probe reads as down`);
  ok((await h.text()) === "", `${name}: HEAD carries no body`);
  ok(h.headers.get("content-type") === g.headers.get("content-type"),
     `${name}: headers must be the ones GET would send`);
}

// The wrapper is generic: it must not swallow a non-200 that GET genuinely returns.
{
  const fake = async () => new Response("x", { status: 402, headers: { "payment-required": "abc" } });
  const r = await headOf(fake)({});
  ok(r.status === 402, "a 402 from GET stays a 402 on HEAD");
  ok(r.headers.get("payment-required") === "abc", "payment headers survive");
  ok((await r.text()) === "", "still no body");
}

console.log(`head: ${pass}/${pass + fail} passed` + (fail ? ` · ${fail} FAILED` : " · all green"));
process.exit(fail ? 1 : 0);
