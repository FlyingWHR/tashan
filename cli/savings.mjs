// Local daily totals for JSON text returned by connected stdio MCP tools.
import { appendFileSync, mkdirSync, createReadStream } from "node:fs";
import { once } from "node:events";
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { dirname } from "node:path";
import { compareJson } from "./tokens.mjs";

function appendReceipt(path, before, after, possible) {
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
  const date = new Date().toLocaleDateString("en-CA");
  appendFileSync(path, JSON.stringify({ date, before, after, possible }) + "\n", { mode: 0o600 });
}

export async function dailySavings(path) {
  const days = new Map();
  try {
    for await (const line of createInterface({ input: createReadStream(path), crlfDelay: Infinity })) {
      const { date, before, after, possible } = JSON.parse(line);
      const row = days.get(date) || { date, calls: 0, original: 0, returned: 0, removed: 0, available: 0 };
      row.calls++;
      row.original += before;
      row.returned += after;
      row.removed += before - after;
      row.available += possible;
      days.set(date, row);
    }
  } catch (err) {
    if (err.code !== "ENOENT") throw err;
  }
  return [...days.values()].sort((a, b) => b.date.localeCompare(a.date));
}

export function dailyText(days) {
  if (!days.length) return "No JSON tool results measured yet. Connect a local MCP server with tashan wrap.\n";
  const columns = ["Date", "Calls", "Original", "Returned", "Removed", "Available"];
  const rows = days.map(r => [r.date, r.calls, r.original, r.returned, r.removed, r.available].map(String));
  const widths = columns.map((name, i) => Math.max(name.length, ...rows.map(row => row[i].length)));
  return [columns, ...rows].map(row => row.map((value, i) => value.padStart(widths[i])).join("  ")).join("\n")
    + "\nJSON tool text · o200k_base · Available = additional tokens removable in preview mode.\n";
}

const parse = line => { try { return JSON.parse(line); } catch { return null; } };

// Compare only complete JSON documents in successful tool text. An unusual numeric
// literal or duplicate key elsewhere in the envelope must survive a pass-through.
function measure(line, msg, pro, table) {
  if (msg.error || msg.result?.isError || !Array.isArray(msg.result?.content)) return null;
  let before = 0, delta = 0, matched = false;
  for (const block of msg.result.content) {
    if (block?.type !== "text" || typeof block.text !== "string" || !/^\s*(?:\[|\{)/.test(block.text)) continue;
    let value;
    try { value = compareJson(block.text, table); } catch { continue; }
    matched = true;
    before += value.report.before;
    delta += value.report.saved;
    if (pro) block.text = value.output;
  }
  if (!matched) return null;
  let output = line;
  if (delta) {
    const compactEnvelope = line.replace(/"(?:\\[\s\S]|[^"\\])*"|[ \t\r\n]+/g, m => m.startsWith('"') ? m : "");
    if (JSON.stringify(JSON.parse(line)) !== compactEnvelope) return null;
    if (pro) output = JSON.stringify(msg);
  }
  return { output, before, after: pro ? before - delta : before, possible: pro ? 0 : delta };
}

function writeLine(stream, line) {
  return new Promise((resolve, reject) => {
    stream.write(line + "\n", err => err ? reject(err) : resolve());
  });
}

export async function wrapServer(command, args, { path, table, getPro }) {
  const env = { ...process.env };
  delete env.TASHAN_KEY;
  const child = spawn(command, args, { stdio: ["pipe", "pipe", "inherit"], env });
  const pending = new Set();
  const onSignal = () => child.kill("SIGTERM");
  process.once("SIGTERM", onSignal);
  process.once("SIGINT", onSignal);
  const incoming = createInterface({ input: process.stdin, crlfDelay: Infinity });
  const outgoing = createInterface({ input: child.stdout, crlfDelay: Infinity });
  const forward = async () => {
    for await (const line of incoming) {
      const msg = parse(line);
      if (msg?.method === "tools/call" && msg.id != null) pending.add(msg.id);
      await writeLine(child.stdin, line);
    }
    child.stdin.end();
  };
  const send = async () => {
    for await (const line of outgoing) {
      const msg = parse(line);
      const result = msg && !msg.method && pending.delete(msg.id)
        ? measure(line, msg, await getPro(), table) : null;
      await writeLine(process.stdout, result ? result.output : line);
      if (result) {
        try { appendReceipt(path, result.before, result.after, result.possible); }
        catch (err) { process.stderr.write("Could not record daily usage: " + err.message + "\n"); }
      }
    }
  };
  const closed = once(child, "close");
  child.stdin.on("error", () => {}); // A child can exit before consuming its input.
  try {
    const writing = forward().catch(err => {
      if (err.code !== "EPIPE" && err.code !== "ERR_STREAM_DESTROYED") throw err;
    });
    const result = await Promise.all([closed.then(status => {
      incoming.close();
      process.stdin.pause();
      return status;
    }), writing, send()]);
    return result[0][0] ?? 1;
  } finally {
    incoming.close();
    outgoing.close();
    process.stdin.pause();
    process.removeListener("SIGTERM", onSignal);
    process.removeListener("SIGINT", onSignal);
    if (child.exitCode === null && child.signalCode === null) child.kill();
  }
}
