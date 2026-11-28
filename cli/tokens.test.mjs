import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { once } from "node:events";
import { fileURLToPath } from "node:url";
import { compareCosts } from "./costs.mjs";
import { compareCiLog, compareJson } from "./tokens.mjs";

const rows = Array.from({ length: 40 }, (_, n) => ({ package_name: "tool", measured_version: n }));
const input = JSON.stringify(rows, null, 2);
const { output, report } = compareJson(input, true);
assert.equal(report.format, "columns-and-rows");
const packed = JSON.parse(output);
assert.deepEqual(packed.rows.map(row => Object.fromEntries(packed.columns.map((k, i) => [k, row[i]]))), rows);
assert(report.after < report.before);
assert.deepEqual(JSON.parse(compareJson(input).output), rows);

for (const literal of ["9007199254740993", "-0", "1.00", "1e400"]) {
  const text = '[ { "key" : ' + literal + ' }, { "key" : 2 } ]';
  const result = compareJson(text, true);
  assert.notEqual(result.report.format, "columns-and-rows");
  assert(result.output.includes(literal));
}
assert(compareJson('{ "x": 1, "x": 2 }').output.includes('"x":1,"x":2'));
assert.equal(compareJson('0').report.saved, 0);
assert.throws(() => compareJson("invalid"), SyntaxError);
assert.deepEqual(JSON.parse(compareJson(JSON.stringify({ value: ' <|endoftext|> " \\ a b ' }, null, 2)).output),
  { value: ' <|endoftext|> " \\ a b ' });

const requests = [];
const server = createServer(async (req, res) => {
  let body = "";
  for await (const chunk of req) body += chunk;
  const payload = JSON.parse(body);
  requests.push(payload);
  res.writeHead(200, { "content-type": "application/json" });
  res.end(JSON.stringify({ status: payload.key === "fixture" ? "granted" : "revoked" }));
});
server.listen(0, "127.0.0.1");
await once(server, "listening");
async function run(args, key) {
  const child = spawn(process.execPath, [fileURLToPath(new URL("./tashan.mjs", import.meta.url)), "tokens", "-", ...args],
    { env: { ...process.env, TASHAN_KEY: key, TASHAN_POLAR_API: "http://127.0.0.1:" + server.address().port } });
  let stdout = "";
  child.stdout.setEncoding("utf8").on("data", data => { stdout += data; });
  child.stderr.resume();
  const done = once(child, "close");
  child.stdin.write(input.slice(0, 11));
  await new Promise(resolve => setTimeout(resolve, 75));
  child.stdin.end(input.slice(11));
  return { code: (await done)[0], stdout };
}
try {
  const preview = await run(["--table", "--json"], "fixture");
  assert.equal(preview.code, 0);
  assert.deepEqual(JSON.parse(preview.stdout), report);
  assert.equal(requests.length, 0);
  assert.deepEqual(await run(["--table", "--emit"], "fixture"), { code: 0, stdout: output });
  assert.deepEqual(await run(["--emit"], "revoked"), { code: 1, stdout: "" });
  assert(requests.every(req => Object.keys(req).sort().join() === "key,organization_id"));
} finally {
  server.close();
}
console.log("Token preview, exact export, numeric fidelity and Pro entitlement passed.");

const goodLines = Array.from({length: 20}, (_, n) => `  ok   passing test ${n} keeps its own result\r\n`).join("");
const diagnostic = "FAIL checkout.test.js\r\n  Expected 200, received 502\r\n    at checkout:17\r\n";
const log = goodLines + diagnostic + goodLines;
const folded = compareCiLog(log, "/work/build.log");
assert(folded.output.includes(diagnostic));
assert(folded.output.includes("[lines 2–19: 18 passing tests folded]"));
assert.equal(folded.report.folded_lines, 36);
assert(folded.report.saved > 0);
assert.equal(compareCiLog(diagnostic, "/work/log").output, diagnostic);
const pair = { period: "week", fee_usd: 0.25, cases: [{ id: "case-1",
  baseline: { accepted: true, charges: [{ id: "b1", usd: 0.90 }, { id: "retry", usd: 0.10 }] },
  tashan: { accepted: true, charges: [{ id: "t1", usd: 0.40 }] } }] };
assert.equal(compareCosts(pair).net_savings_usd, 0.35);
assert.equal(compareCosts(pair).tokens_saved, null);
const [before, retry] = pair.cases[0].baseline.charges;
const [after] = pair.cases[0].tashan.charges;
before.total_tokens = 80;
after.total_tokens = 90;
assert.equal(compareCosts(pair).baseline.total_tokens, null);
assert.equal(compareCosts(pair).tokens_saved, null);
retry.total_tokens = 0;
assert.equal(compareCosts(pair).tokens_saved, -10);
retry.total_tokens = 30;
assert.equal(compareCosts(pair).baseline.tokens_per_accepted, 110);
assert.equal(compareCosts(pair).tokens_saved, 20);
assert.throws(() => compareCosts({...pair, cases: [{...pair.cases[0],
  baseline: {accepted: true, charges: [{...before, total_tokens: -1}]}}]}), /total_tokens/);
pair.cases[0].tashan.accepted = false;
assert.equal(compareCosts(pair).tokens_saved, null);
assert.equal(compareCosts(pair).net_savings_usd, null);
assert.equal(compareCosts(pair).tashan.usd_per_accepted, null);
pair.cases[0].tashan.charges[0].id = "b1";
assert.throws(() => compareCosts(pair), /unique/);
console.log("CI log recovery, billed retries, subscription cost and quality regressions passed.");
