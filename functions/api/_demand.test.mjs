// node functions/api/_demand.test.mjs
import { demand, _SELF } from "./_demand.js";

let pass = 0, fail = 0;
const ok = (c, m) => { c ? pass++ : (fail++, console.log("  FAIL " + m)); };

const rec = () => { const rows = []; return { rows, TASHAN_AE: { writeDataPoint: (d) => rows.push(d) } }; };
const req = (ua = "some-agent/1.0", country = "US") =>
  ({ headers: { get: (h) => (h.toLowerCase() === "user-agent" ? ua : null) }, cf: { country } });

// A refusal is recorded. This is the whole point of the file: without it, an agent that wanted the
// answer and could not pay is indistinguishable from no traffic at all.
{
  const env = rec();
  demand(env, req(), "failed", "capability-kit", "insufficient_funds");
  ok(env.rows.length === 1, "a failed payment is recorded");
  const b = env.rows[0].blobs;
  ok(b[3] === "failed" && b[4] === "insufficient_funds", "stage and reason both survive: " + b.slice(3, 5));
  ok(b[1] === "capability-kit", "the priced resource is named");
  ok(env.rows[0].indexes[0] === "x402", "indexed apart from page views");
}

// OUR OWN CHECKER MUST NEVER APPEAR. check_payments.py drives the full payment path on every run;
// counting it would manufacture exactly the demand number a founder wants to see. This already
// happened once on /api/buy — 43 checkouts nobody made.
{
  const env = rec();
  demand(env, req("tashan-payment-check/1.0"), "quoted", "config-audit");
  ok(env.rows.length === 0, "self-check excluded");
  demand(env, req("python-urllib/3 tashan-payment-check"), "settled", "config-audit");
  ok(env.rows.length === 0, "excluded anywhere in the UA, not just as a prefix");
  // ...but a REAL agent still counts. Over-excluding would silently delete the signal.
  demand(env, req("claude-code/2.1"), "quoted", "config-audit");
  ok(env.rows.length === 1, "a real agent is still recorded");
}

// NEVER THROWS. Telemetry that can fail a request would turn a metric into an outage — and this one
// sits directly in the payment path, so a throw here costs the sale it is trying to measure.
{
  ok(_SELF === "tashan-payment-check", "exclusion token matches check_payments.py's UA");
  const boom = { TASHAN_AE: { writeDataPoint: () => { throw new Error("AE down"); } } };
  let threw = false;
  try { demand(boom, req(), "settled", "x"); } catch (_) { threw = true; }
  ok(!threw, "an analytics failure never reaches the caller");
  try { demand(null, null, "quoted", "x"); demand({}, req(), "quoted", "x"); }
  catch (_) { fail++; console.log("  FAIL no env / no AE binding must be a no-op"); }
  pass++;
}

// A hostile user-agent cannot bloat a row (AE caps blob bytes; an oversized write is dropped).
{
  const env = rec();
  demand(env, req("x".repeat(5000)), "quoted", "y".repeat(500), "z".repeat(500));
  const b = env.rows[0].blobs;
  ok(b[7].length === 64 && b[1].length === 128 && b[4].length === 128, "every field truncated");
}

console.log(`demand: ${pass}/${pass + fail} passed` + (fail ? ` · ${fail} FAILED` : " · all green"));
process.exit(fail ? 1 : 0);
