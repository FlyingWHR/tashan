// node functions/.well-known/x402.test.mjs
//
// The first directory submission was accepted, auto-verified, and then filtered out of the index
// with `health: down` — because the crawler probes /.well-known/x402 by name and we 404'd. Listed,
// verified, invisible.
import assert from "node:assert";
import { onRequestGet } from "./x402.js";
import { PRICED } from "../api/_x402.js";

let pass = 0, fail = 0;
const ok = (c, m) => { c ? pass++ : (fail++, console.log("  FAIL " + m)); };

const res = await onRequestGet({ request: new Request("https://tashan.sh/.well-known/x402") });
const doc = await res.json();

ok(res.status === 200, "200, or a crawler treats the seller as down");
ok(/application\/json/.test(res.headers.get("content-type")), "must be JSON");
ok(doc.version === 1, "version 1 is the shape every listed seller serves");

// IT MUST ENUMERATE PRICED, NOT A LIST OF ITS OWN. A second copy of "what we sell" drifts: a new
// priced endpoint ships undiscoverable, or a removed one is advertised after it is gone.
const priced = Object.values(PRICED).filter((p) => p && p.path);
ok(doc.resources.length === priced.length,
   `every priced resource is listed: ${doc.resources.length} vs ${priced.length}`);
for (const p of priced) {
  ok(doc.resources.includes("https://tashan.sh" + p.path), `missing ${p.path}`);
}
ok(doc.resources.every((u) => u.startsWith("https://tashan.sh/")),
   "absolute URLs on our own origin: " + JSON.stringify(doc.resources));

// The origin comes from the request, so a preview deployment advertises itself rather than prod.
const pv = await (await onRequestGet({
  request: new Request("https://abc123.tashan.pages.dev/.well-known/x402") })).json();
ok(pv.resources.every((u) => u.startsWith("https://abc123.tashan.pages.dev/")),
   "origin follows the request: " + JSON.stringify(pv.resources));

console.log(`well-known/x402: ${pass}/${pass + fail} passed` + (fail ? ` · ${fail} FAILED` : " · all green"));
process.exit(fail ? 1 : 0);
