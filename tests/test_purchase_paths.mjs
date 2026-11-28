// Exercise both buyers through the product entry points. Only the external
// billing provider, facilitator and index data are fixtures.
import assert from "node:assert/strict";
import { execFile, spawn } from "node:child_process";
import { once } from "node:events";
import { createServer } from "node:http";
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import { onRequest as checkout } from "../functions/api/checkout.js";
import { onRequest as device } from "../functions/api/device.js";
import { onRequest as account } from "../functions/api/account.js";
import { onRequestPost as kit } from "../functions/v0.1/kit.js";
import { handle } from "../cli/mcp.mjs";

const origin = "https://tashan.sh";
const records = new Map();
const env = {
  POLAR_ORG_ID: "fixture-org", POLAR_ORG_TOKEN: "fixture-token",
  X402_PAY_TO: "fixture-merchant", X402_NETWORK: "eip155:84532", X402_ASSET: "fixture-asset",
  X402_FACILITATOR: "https://facilitator.example",
  CHECKOUT_CLAIMS: { async put(key, value, opts) {
    assert.equal(opts.onlyIf.get("if-none-match"), "*");
    if (records.has(key)) return null;
    records.set(key, value);
    return { key };
  } },
  TASHAN_KV: {
    async get(key, type) {
      const raw = records.get(key) ?? null;
      return type === "json" ? JSON.parse(raw) : raw;
    },
    async put(key, value) { records.set(key, value); },
    async delete(key) { records.delete(key); },
  },
};
const json = (body, status = 200) => new Response(JSON.stringify(body), { status });
const granted = { key: "fixture-licence", status: "granted" };
let availableKeys = [], settlements = 0, checkoutStatus = "succeeded";
const pin = { id: "pkg:review", name: "review", npm_pkg: "fixture-review", npm_runnable: 1,
  sec_scanned_at: new Date().toISOString(), sec_scanned_version: "1.0.0",
  npm_latest_version: "1.0.0", sec_advisory_count: 0, tashan_score: 80 };
const receipt = { success: true, transaction: "0x" + "a".repeat(64), network: env.X402_NETWORK };
const realFetch = globalThis.fetch;
globalThis.fetch = async (url, init = {}) => {
  const path = new URL(url).pathname;
  if (path === "/v0.1/kit") return kit({ request: new Request(url, init), env });
  if (path === "/v1/checkouts/fixture-checkout") return json({ status: checkoutStatus, customer_id: "cus",
    modified_at: new Date().toISOString() });
  if (path === "/v1/customer-sessions/") return json({ token: "customer-session" });
  if (path === "/v1/customer-portal/license-keys/") return json({ items: availableKeys });
  if (path.endsWith("/validate")) return json(availableKeys[0]);
  if (path === "/data/tasks.json") return json({ tasks: [{ slug: "code-review", label: "code review" }] });
  if (path === "/data/tags.json") return json({ tasks: { "code-review": [pin.id] } });
  if (path === "/data/lookup.json") return json({ records: [pin] });
  if (path === "/verify") return json({ isValid: JSON.parse(init.body).paymentPayload.fixture === "authorized" });
  if (path === "/settle") { settlements++; return json(receipt); }
  throw new Error("Unexpected fixture URL " + path);
};
function invoke(handler, path, body, cookie) {
  return handler({ env, request: new Request(origin + path, { method: body ? "POST" : "GET",
    headers: cookie ? { cookie } : {}, body: body ? JSON.stringify(body) : undefined }) });
}
const dir = mkdtempSync(join(tmpdir(), "tashan-purchase-"));
const billing = createServer(async (req, res) => {
  let raw = "";
  for await (const chunk of req) raw += chunk;
  const payload = JSON.parse(raw);
  const valid = payload.key === granted.key;
  res.writeHead(valid ? 200 : 403, { "content-type": "application/json" });
  if (req.url === "/activate") res.end(JSON.stringify({ id: "fixture-seat" }));
  else res.end(JSON.stringify({ status: valid && payload.activation_id === "fixture-seat" ? "granted" : "revoked" }));
});
try {
  const redeem = () => invoke(checkout, "/api/checkout?checkout_id=fixture-checkout");
  checkoutStatus = "confirmed";
  assert.equal((await redeem()).headers.get("set-cookie"), null);
  checkoutStatus = "succeeded";
  for (const record of [[], [{ ...granted, status: "revoked" }], [{ ...granted, expires_at: "2000-01-01" }]]) {
    availableKeys = record;
    assert.equal((await redeem()).headers.get("set-cookie"), null);
  }
  availableKeys = [granted];
  const concurrent = await Promise.all([redeem(), redeem()]);
  assert.equal(concurrent.filter(response => response.headers.has("set-cookie")).length, 1);
  const welcome = concurrent.find(response => response.headers.has("set-cookie"));
  const cookie = welcome.headers.get("set-cookie").split(";")[0];
  assert.equal(welcome.headers.get("location"), origin + "/welcome");
  assert.equal((await (await invoke(account, "/api/account", null, cookie)).json()).active, true);
  assert.equal((await redeem()).headers.get("set-cookie"), null);
  const codes = await (await invoke(device, "/api/device", {})).json();
  availableKeys = [{ ...granted, status: "revoked" }];
  assert.equal((await invoke(device, "/api/device", { user_code: codes.user_code, approve: true }, cookie)).status, 403);
  availableKeys = [granted];
  assert.equal((await invoke(device, "/api/device", { user_code: codes.user_code, approve: true }, cookie)).status, 200);
  const approved = await (await invoke(device, "/api/device", { device_code: codes.device_code })).json();
  billing.listen(0, "127.0.0.1");
  await once(billing, "listening");
  const cli = fileURLToPath(new URL("../cli/tashan.mjs", import.meta.url));
  const run = (...args) => promisify(execFile)(process.execPath, [cli, ...args], { env: {
    PATH: process.env.PATH, XDG_CONFIG_HOME: dir, TASHAN_POLAR_API: "http://127.0.0.1:" + billing.address().port } });
  // Exercise the same wrapped server before and after activating this device.
  const samplePath = fileURLToPath(new URL("../web/assets/tool-results.json", import.meta.url));
  const source = readFileSync(samplePath, "utf8");
  const exampleServer = join(dir, "fixture.cjs");
  writeFileSync(exampleServer, `const readline = require("node:readline");
    readline.createInterface({input:process.stdin}).on("line", line => {
      const {id,method} = JSON.parse(line);
      const result = {content:[{type:"text",text:${JSON.stringify(source)}}],structuredContent:{v:99}};
      process.stdout.write(JSON.stringify({jsonrpc:"2.0",id,result})+"\\n");
    });`);
  async function callServer() {
    const child = spawn(process.execPath, [cli, "wrap", "--table", "--", process.execPath, exampleServer], {
      env: { PATH: process.env.PATH, XDG_CONFIG_HOME: dir, TASHAN_POLAR_API: "http://127.0.0.1:" + billing.address().port }
    });
    let output = "", errors = "";
    child.stdout.setEncoding("utf8").on("data", chunk => output += chunk);
    child.stderr.setEncoding("utf8").on("data", chunk => errors += chunk);
    const closed = once(child, "close");
    child.stdin.end(["tools/list", "tools/call"].map((method, id) =>
      JSON.stringify({jsonrpc:"2.0",method,id,params:{name:"fixture"}})).join("\n") + "\n");
    assert.equal((await closed)[0], 0, errors);
    const [listed, called] = output.trimEnd().split("\n").map(JSON.parse);
    assert.equal(listed.result.content[0].text, source);
    assert.deepEqual(called.result.structuredContent, {v:99});
    return called.result.content[0].text;
  }
  assert.equal(await callServer(), source);
  assert.equal(JSON.parse((await run("daily", "--json")).stdout).days[0].removed, 0);
  await run("activate", approved.key);
  const sample = fileURLToPath(new URL("../web/assets/tool-results.json", import.meta.url));
  const preview = JSON.parse((await run("tokens", sample, "--table", "--json")).stdout);
  assert.deepEqual([preview.before, preview.after], [431, 270]);
  const packed = JSON.parse((await run("tokens", sample, "--table", "--emit")).stdout);
  const unpacked = packed.rows.map(row => Object.fromEntries(packed.columns.map((key, i) => [key, row[i]])));
  assert.deepEqual(unpacked, JSON.parse(readFileSync(sample, "utf8")));
  assert.deepEqual(JSON.parse(await callServer()), packed);
  const [day] = JSON.parse((await run("daily", "--json")).stdout).days;
  assert.deepEqual([day.calls, day.original, day.returned, day.available, day.removed], [2,862,701,161,161]);
  assert(!readFileSync(join(dir, "tashan", "tool-usage.jsonl"), "utf8").includes("filesystem"));
  const logfile = join(dir, "build.log");
  writeFileSync(logfile, Array.from({ length: 50 }, (_, i) => "  ok   passing test " + i).join("\n")
    + "\nFAIL checkout refused\nExpected 200, got 502\n");
  const { stdout } = await run("tokens", logfile, "--ci", "--emit");
  assert(stdout.includes("passing tests folded") && stdout.includes("FAIL checkout refused\nExpected 200, got 502"));
  console.log("Human: completed checkout, delayed grant, account, device approval, CLI activation and Pro export passed.");

  const purchase = meta => handle({ id: 1, method: "tools/call", params: { name: "get_tool_kit",
    arguments: { task: "code review", client: "codex" }, _meta: meta } });
  const quote = (await purchase()).result;
  assert(quote.isError && quote.structuredContent.accepts[0].amount === "50000");
  const denied = (await purchase({ "x402/payment": { fixture: "declined" } })).result;
  assert(denied.isError && !denied.structuredContent.kit && settlements === 0);
  const meta = { "x402/payment": { fixture: "authorized" } };
  const paid = (await purchase(meta)).result;
  assert.deepEqual(paid._meta["x402/payment-response"], receipt);
  assert.match(paid.structuredContent.kit.config_text, /fixture-review@1\.0\.0/);
  pin.sec_scanned_at = "2000-01-01";
  assert.deepEqual((await purchase(meta)).result, paid);
  assert.equal(settlements, 1);
  console.log("Agent: quote, refusal, settlement, Codex config, receipt and signed-request recovery passed.");
} finally {
  billing.close();
  globalThis.fetch = realFetch;
  rmSync(dir, { recursive: true, force: true });
}
