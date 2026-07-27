#!/usr/bin/env node
// tashan — the measured layer for AI capabilities, in your terminal.
//
//   npx tashan search <query>        find MCP servers & skills, ranked by Trust
//   npx tashan top [category]        the leaderboard
//   npx tashan info <name>           the measured dossier for one capability
//   npx tashan add <name>            the install command for your client   ← the money shot
//   npx tashan doctor                audit the config you actually have — dead, deprecated, risky
//
// Reads live public data from https://tashan.sh/data/index.json (no account, no backend, no telemetry).
// Zero dependencies. The pure functions are exported for cli/tashan.test.mjs.

import { configLocations, skillLocations, collect, match, assess, summarize } from "./doctor.mjs";

const SITE = process.env.TASHAN_SITE || "https://tashan.sh";
const DATA_URL = SITE + "/data/index.json";

// ---- ANSI (context7-grade: quiet, monochrome + one accent; auto-off when piped / NO_COLOR) ----
const tty = process.stdout.isTTY && !process.env.NO_COLOR;
const C = (n) => (s) => (tty ? `\x1b[${n}m${s}\x1b[0m` : String(s));
const jade = C("38;5;79"), dim = C("2"), bold = C("1"), red = C("31"), under = C("4");

// ---- pure logic (exported, tested) ----
export function slugify(id) { return String(id).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }
// identical to the site's pretty() (web/js/index.js / capability.js) so names + install commands match exactly
export function pretty(name) {
  return String(name || "").replace(/^@modelcontextprotocol\/server-/, "").replace(/-mcp$/, "").replace(/^mcp-server-/, "").replace(/^mcp-/, "");
}

export function search(rows, q) {
  q = (q || "").toLowerCase().trim();
  if (!q) return [];
  const scored = rows.map((r) => {
    // match against the display name with the npm scope stripped ("@upstash/context7" → "context7"),
    // so a query for "context7" prefix-matches the real capability instead of only substring-matching it
    const name = pretty(r.name || "").toLowerCase().replace(/^@[^/]+\//, "");
    const pkg = (r.npm_pkg || "").toLowerCase(), cat = (r.category || "").toLowerCase();
    let s = 0;
    if (name === q || pkg === q) s = 100;
    else if (name.startsWith(q) || pkg.startsWith(q)) s = 70;
    else if (name.includes(q) || pkg.includes(q)) s = 45;
    else if (cat.includes(q)) s = 20;
    if (!s) return null;
    return { r, s: s + Math.min(30, (r.trust || 0) / 3) };   // quality-weighted: Trust lifts within a match tier
  }).filter(Boolean);
  scored.sort((a, b) => b.s - a.s);
  return scored.map((x) => x.r);
}

export function top(rows, cat) {
  let list = rows.filter((r) => r.trust != null);
  if (cat) { const c = cat.toLowerCase(); list = list.filter((r) => (r.category || "").toLowerCase() === c); }
  return list.sort((a, b) => (b.trust || 0) - (a.trust || 0));
}

export function find(rows, key) {
  const k = (key || "").toLowerCase();
  return rows.find((r) => r.slug === k)
      || rows.find((r) => (r.name || "").toLowerCase() === k || (r.npm_pkg || "").toLowerCase() === k)
      || rows.find((r) => slugify(r.id) === slugify(k))
      || rows.find((r) => (r.name || "").toLowerCase().includes(k) || (r.npm_pkg || "").toLowerCase().includes(k));
}

// Install snippets — kept byte-identical to the site's installBlock() (web/js/capability.js) so the
// terminal and the web page never disagree about how to install a capability.
export function installSnippets(c, client) {
  const name = pretty(c.name).replace(/[^a-z0-9_-]/gi, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
  const pkg = c.npm_pkg;
  if (c.kind === "skill") {
    const folder = pretty(c.name).replace(/[^a-z0-9_-]/gi, "-");
    return [
      { client: "claude", label: "Drop the skill into your skills directory", cmd: `cp -r ${folder} ~/.claude/skills/` },
      { client: "project", label: "Or scope it to one project", cmd: `cp -r ${folder} .claude/skills/` },
    ];
  }
  if (!pkg) {
    return [{ client: "remote", label: "Remote / registry server — configure from its source",
              cmd: c.source_repo ? `# see https://github.com/${c.source_repo}` : "# see the capability's source" }];
  }
  const jsonSnip = `{
  "mcpServers": {
    "${name}": { "command": "npx", "args": ["-y", "${pkg}"] }
  }
}`;
  const tomlSnip = `[mcp_servers.${name}]\ncommand = "npx"\nargs = ["-y", "${pkg}"]`;
  const all = [
    { client: "claude",  label: "Claude Code — one command", cmd: `claude mcp add ${name} -- npx -y ${pkg}` },
    { client: "cursor",  label: "Cursor — add to ~/.cursor/mcp.json", cmd: jsonSnip },
    { client: "desktop", label: "Claude Desktop — add to claude_desktop_config.json, then restart", cmd: jsonSnip },
    { client: "codex",   label: "Codex CLI — add to ~/.codex/config.toml", cmd: tomlSnip },
    { client: "npx",     label: "Run it directly", cmd: `npx -y ${pkg}` },
  ];
  return client ? all.filter((s) => s.client === client) : all;
}

// ---- formatting ----
const fmtNum = (n) => n == null ? "—" : n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(0) + "k" : String(n);
const trustStr = (t) => t == null ? dim("  —") : (t >= 70 ? jade : t >= 40 ? C("33") : dim)(String(Math.round(t)).padStart(3));
const verdict = (v) => v ? ({ deep: "deep", solid: "solid", thin: "thin", wrapper: "wrapper", slop: "slop" }[v] || v) : "";

function row(r) {
  const name = pretty(r.name).slice(0, 34).padEnd(34);
  const kind = dim((r.kind || "").padEnd(6));
  const dl = dim(fmtNum(r.npm_downloads).padStart(6));
  const vd = r.expertise_verdict ? dim("· " + verdict(r.expertise_verdict)) : "";
  return `  ${trustStr(r.trust)}  ${bold(name)} ${kind} ${dl}  ${vd}`;
}
function table(rows, limit) {
  if (!rows.length) return dim("  no matches.");
  const head = "  " + dim("TRUST".padStart(3)) + "  " + dim("CAPABILITY".padEnd(34)) + " " + dim("KIND".padEnd(6)) + " " + dim("  DL");
  return head + "\n" + rows.slice(0, limit).map(row).join("\n");
}

function infoCard(r) {
  const L = [];
  L.push("");
  L.push("  " + bold(pretty(r.name)) + "  " + dim(r.kind || ""));
  L.push("  " + dim(r.id));
  L.push("");
  L.push("  Trust        " + trustStr(r.trust).trim() + dim("/100") + "   " + dim("maintenance " + (r.maintenance ?? "—") + " · vitality " + (r.vitality || "—")));
  if (r.expertise_verdict) L.push("  Expertise    " + jade(verdict(r.expertise_verdict)) + (r.expertise != null ? dim("  (" + r.expertise + "/100)") : ""));
  L.push("  Adoption     " + dim(fmtNum(r.npm_downloads) + " downloads/wk" + (r.config_reach ? " · reach " + r.config_reach : "")));
  if (r.category) L.push("  Category     " + dim(r.category));
  if (r.npm_deprecated) L.push("  " + red("⚠ deprecated on npm"));
  if (r.gh_archived) L.push("  " + red("⚠ repository archived"));
  L.push("");
  if (r.npm_pkg) L.push("  npm          " + under("https://www.npmjs.com/package/" + r.npm_pkg));
  if (r.source_repo) L.push("  source       " + under("https://github.com/" + r.source_repo));
  L.push("  dossier      " + under(SITE + "/capability/" + r.slug + ".html"));
  L.push("");
  L.push("  " + dim("install:  ") + jade("tashan add " + (r.slug || pretty(r.name))));
  L.push("");
  return L.join("\n");
}

function renderAdd(r, client) {
  const snips = installSnippets(r, client);
  if (!snips.length) return red(`  no install method for client "${client}". try: claude · cursor · desktop · codex · npx`);
  const out = ["", "  " + bold(pretty(r.name)) + dim("  — " + SITE + "/capability/" + r.slug + ".html"), ""];
  for (const s of snips) {
    out.push("  " + dim(s.label));
    out.push(s.cmd.split("\n").map((l) => "    " + jade(l)).join("\n"));
    out.push("");
  }
  return out.join("\n");
}

// ---- data ----
async function loadData() {
  if (process.env.TASHAN_DATA) {                       // local dev / tests: point at a file
    const fs = await import("node:fs");
    return JSON.parse(fs.readFileSync(process.env.TASHAN_DATA, "utf8"));
  }
  const res = await fetch(DATA_URL, { headers: { "user-agent": "tashan-cli" } });
  if (!res.ok) throw new Error(`could not reach ${DATA_URL} (${res.status})`);
  return res.json();
}
const rowsOf = (d) => (Array.isArray(d) ? d : d.capabilities || []);

const USAGE = `
${bold("tashan")} — the measured layer for AI capabilities ${dim("· " + SITE)}

  ${jade("tashan search")} <query>       find MCP servers & skills, ranked by Trust
  ${jade("tashan top")} [category]       the leaderboard
  ${jade("tashan info")} <name>          the measured dossier for one capability
  ${jade("tashan add")} <name>           the install command  ${dim("(--client claude|cursor|desktop|codex|npx)")}
  ${jade("tashan doctor")}               audit the config you already have — dead, deprecated, risky

  ${dim("flags:")}  --json   --limit <n>   --client <c>
  ${dim("every score is re-derivable from public evidence · no account, no telemetry")}
`;

function parseArgs(argv) {
  const a = { _: [], json: false, limit: 20, client: null };
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    if (t === "--json") a.json = true;
    else if (t === "--limit") a.limit = parseInt(argv[++i], 10) || 20;
    else if (t === "--client") a.client = (argv[++i] || "").toLowerCase();
    else if (t.startsWith("--client=")) a.client = t.slice(9).toLowerCase();
    else a._.push(t);
  }
  return a;
}

const MARK = { alert: red("!"), warn: C("33")("~"), note: dim("·"), ok: jade("+"), unrated: dim("·"), unknown: dim("?") };

function renderDoctor(results, problems, sum) {
  if (!results.length) {
    return "\n  " + bold("No agent config found.") + "\n" +
      dim("  Looked in ~/.claude.json, ~/.cursor/mcp.json, Claude Desktop, .mcp.json, ~/.claude/skills/ …") + "\n";
  }
  const order = { alert: 0, warn: 1, unrated: 2, unknown: 3, ok: 4 };
  const rows = results.slice().sort((x, y) => order[x.assessment.level] - order[y.assessment.level]);
  let out = "\n  " + bold("Your stack") + dim(`  ·  ${sum.servers} server${sum.servers === 1 ? "" : "s"}, ${sum.skills} skill${sum.skills === 1 ? "" : "s"}`) + "\n\n";
  for (const { item, row, assessment } of rows) {
    const t = row && row.trust != null ? String(row.trust) : "—";
    out += "  " + (MARK[assessment.level] || " ") + " " + bold(pretty(item.name).padEnd(28).slice(0, 28)) +
      dim((item.client + " · " + item.scope).padEnd(22)) + dim("trust ") + (t === "—" ? dim(t) : jade(t)) + "\n";
    for (const n of assessment.notes) {
      const txt = typeof n === "string" ? n : n.text;
      out += "      " + dim("↳ ") + (n.level === "alert" ? red(txt) : dim(txt)) + "\n";
    }
  }
  for (const p of problems) out += "  " + red("!") + " " + bold("config unreadable") + dim("  " + p.path) + "\n";
  const bits = [];
  if (sum.alert) bits.push(red(sum.alert + " need attention"));
  if (sum.warn) bits.push(sum.warn + " worth a look");
  if (sum.unrated) bits.push(dim(sum.unrated + " catalogued, unrated"));
  if (sum.unknown) bits.push(dim(sum.unknown + " not in the index"));
  out += "\n  " + (bits.length ? bits.join(dim(" · ")) : jade("nothing flagged")) + "\n";
  out += dim("  local only — nothing was uploaded. tashan info <name> for the full dossier.") + "\n";
  return out;
}

export async function main(argv) {
  const a = parseArgs(argv);
  const cmd = a._[0];
  if (!cmd || cmd === "help" || cmd === "--help" || cmd === "-h") { process.stdout.write(USAGE + "\n"); return 0; }

  let rows;
  try { rows = rowsOf(await loadData()); }
  catch (e) { process.stderr.write(red("  " + e.message) + "\n"); return 1; }

  const arg = a._.slice(1).join(" ");
  if (cmd === "search") {
    const hits = search(rows, arg);
    if (a.json) { process.stdout.write(JSON.stringify(hits.slice(0, a.limit), null, 2) + "\n"); return 0; }
    process.stdout.write("\n" + table(hits, a.limit) + "\n\n" + dim(`  ${hits.length} match${hits.length === 1 ? "" : "es"} · tashan info <name> for the dossier`) + "\n");
    return 0;
  }
  if (cmd === "top") {
    const list = top(rows, arg || null);
    if (a.json) { process.stdout.write(JSON.stringify(list.slice(0, a.limit), null, 2) + "\n"); return 0; }
    process.stdout.write("\n  " + bold("Top by Trust" + (arg ? " · " + arg : "")) + "\n" + table(list, a.limit) + "\n\n" + dim("  ranked on public evidence · tashan.sh") + "\n");
    return 0;
  }
  if (cmd === "info" || cmd === "add") {
    const r = find(rows, arg);
    if (!r) { process.stderr.write(red(`  no capability matches "${arg}". try: tashan search ${arg}`) + "\n"); return 1; }
    if (a.json) { process.stdout.write(JSON.stringify(cmd === "add" ? { capability: r, install: installSnippets(r, a.client) } : r, null, 2) + "\n"); return 0; }
    process.stdout.write((cmd === "add" ? renderAdd(r, a.client) : infoCard(r)) + "\n");
    return 0;
  }
  if (cmd === "doctor") {
    const { found, problems } = collect(configLocations(), skillLocations());
    const results = found.map((item) => ({ item, row: match(item, rows), assessment: assess(item, match(item, rows)) }));
    const sum = summarize(results);
    if (a.json) { process.stdout.write(JSON.stringify({ summary: sum, problems, results }, null, 2) + "\n"); return 0; }
    process.stdout.write(renderDoctor(results, problems, sum) + "\n");
    return sum.alert > 0 ? 2 : 0;      // nonzero exit when something needs attention, so it can gate CI
  }
  process.stderr.write(red(`  unknown command: ${cmd}`) + "\n" + USAGE + "\n");
  return 1;
}

// entrypoint (skip when imported by the test)
import { fileURLToPath } from "node:url";
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then((code) => process.exit(code || 0));
}
