#!/usr/bin/env node
// What an AGENT sees when it asks tashan about a capability — on camera, legibly.
//
// The demo for this used to be a printf of three JSON-RPC frames piped into the MCP server. It
// worked and it was unreadable: one smashed line of protocol, then a wall of escaped JSON, on the
// beat whose whole job is showing that the answer is clean enough for a machine to act on. A viewer
// cannot read a demo, they can only recognise one.
//
// So: same protocol, same server, same answer — the handshake is just not the thing on screen.
//
//   node demo/agent-view.mjs                 # defaults to tavily-mcp
//   node demo/agent-view.mjs find "web scraping"
//   node demo/agent-view.mjs paid blockrun
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const SERVER = join(HERE, "..", "cli", "mcp.mjs");

const TOOLS = {
  check: ["check_capability", (a) => ({ name: a })],
  find:  ["find_capability",  (a) => ({ task: a, limit: 3 })],
  paid:  ["paid_demand",      (a) => ({ name: a })],
};

const argv = process.argv.slice(2);
const verb = TOOLS[argv[0]] ? argv.shift() : "check";
const arg = argv.join(" ") || "tavily-mcp";
const [tool, shape] = TOOLS[verb];

const dim = (s) => `\x1b[2m${s}\x1b[0m`;
const jade = (s) => `\x1b[38;5;79m${s}\x1b[0m`;

const send = (p, msg) => p.stdin.write(JSON.stringify(msg) + "\n");
const srv = spawn("node", [SERVER], { stdio: ["pipe", "pipe", "ignore"] });

let buf = "";
srv.stdout.on("data", (d) => {
  buf += d;
  for (const line of buf.split("\n").slice(0, -1)) {
    let m; try { m = JSON.parse(line); } catch { continue; }
    if (m.id !== 2) continue;
    const text = (m.result?.content || []).map((c) => c.text).join("\n").trim();
    console.log(jade(`  ← ${tool}`) + dim(` answered in ${Date.now() - t0} ms`) + "\n");
    for (const l of text.split("\n")) console.log("  " + l);
    console.log();
    srv.kill();
    process.exit(0);
  }
  buf = buf.slice(buf.lastIndexOf("\n") + 1);
});

console.log("\n" + dim("  an agent asks tashan, over MCP — no key, no account"));
console.log(jade(`  → ${tool}`) + dim(`  ${JSON.stringify(shape(arg))}`) + "\n");

const t0 = Date.now();
send(srv, { jsonrpc: "2.0", id: 1, method: "initialize",
            params: { protocolVersion: "2025-06-18", capabilities: {},
                      clientInfo: { name: "demo", version: "1" } } });
send(srv, { jsonrpc: "2.0", method: "notifications/initialized" });
send(srv, { jsonrpc: "2.0", id: 2, method: "tools/call",
            params: { name: tool, arguments: shape(arg) } });

setTimeout(() => { console.error("  no answer in 30s"); srv.kill(); process.exit(1); }, 30000);
