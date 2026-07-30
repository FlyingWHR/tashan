#!/usr/bin/env node
// tashan — the measured layer for AI capabilities, in your terminal.
//
//   npx tashan-cli search <query>        find MCP servers & skills, ranked by tashan score
//   npx tashan-cli top [category]        the leaderboard
//   npx tashan-cli info <name>           the measured dossier for one capability
//   npx tashan-cli add <name>            the install command for your client   ← the money shot
//   npx tashan-cli doctor                audit the config you actually have — dead, deprecated, risky
//   npx tashan-cli activate <key>        store your Pro licence on this machine (once, not per shell)
//   npx tashan-cli mcp                   run as an MCP server, so your AGENT can ask before installing
//
// Reads live public data from https://tashan.sh/data/index.json (no account, no backend, no telemetry).
// Zero dependencies. The pure functions are exported for cli/tashan.test.mjs.

import { readFileSync, writeFileSync, mkdirSync, rmSync, chmodSync } from "node:fs";
import { homedir, hostname, platform } from "node:os";
import { join, dirname } from "node:path";
import { configLocations, skillLocations, collect, match, resolve, assess, summarize, trend, withTrend,
         suggest, tokenFrequency, isDying } from "./doctor.mjs";

// ---- licence ---------------------------------------------------------------------------------
// The account system is Polar's, not ours: polar.sh/tashan/portal does email-OTP sign-in,
// subscriptions, invoices, cancellation and payment methods. Device handling is Polar's too — the
// customer-portal license-key endpoints (activate / validate / deactivate) are PUBLIC, needing only
// the org id, so the CLI talks to them directly. We store no passwords, run no sessions, and hold
// no customer record. An earlier cut of this file hand-rolled all of it against our own API, which
// meant no device list, no activation limit, and nothing the customer could see or revoke.
const POLAR_LK = process.env.TASHAN_POLAR_API || "https://api.polar.sh/v1/customer-portal/license-keys";
const ORG_ID = process.env.TASHAN_ORG_ID || "caa0fc1b-2f7f-4e52-864a-c71e878d125d";
export const PORTAL = "https://polar.sh/tashan/portal";

export function keyPath() {
  const base = process.env.XDG_CONFIG_HOME || join(homedir(), ".config");
  return join(base, "tashan", "key");
}
// Stored as JSON so the activation id rides along with the key. A bare string is still accepted:
// that is what TASHAN_KEY gives us, and what a user pasting a key into the file by hand will write.
export function parseLicence(text) {
  const t = (text || "").trim();
  if (!t) return null;
  if (t.startsWith("{")) {
    try {
      const o = JSON.parse(t);
      return o.key ? { key: o.key, activation_id: o.activation_id || null, label: o.label || null } : null;
    } catch { return null; }
  }
  return { key: t, activation_id: null, label: null };
}
export function storedLicence() {
  try { return parseLicence(readFileSync(keyPath(), "utf8")); } catch { return null; }
}
export function resolveLicence(a = {}) {
  if (a.key) return { key: a.key, activation_id: null, label: null };
  if (process.env.TASHAN_KEY) return { key: process.env.TASHAN_KEY, activation_id: null, label: null };
  return storedLicence();
}
export function resolveKey(a = {}) {
  const l = resolveLicence(a);
  return l ? l.key : null;
}

async function polar(path, body) {
  try {
    const r = await fetch(POLAR_LK + path, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ organization_id: ORG_ID, ...body }),
    });
    const json = r.status === 204 ? {} : await r.json().catch(() => null);
    return { status: r.status, json };
  } catch {
    return { status: 0, json: null };          // offline / DNS — never "invalid"
  }
}

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
    return { r, s: s + Math.min(30, (r.tashan_score || 0) / 3) };   // quality-weighted: tashan score lifts within a match tier
  }).filter(Boolean);
  scored.sort((a, b) => b.s - a.s);
  return scored.map((x) => x.r);
}

export function top(rows, cat) {
  let list = rows.filter((r) => r.tashan_score != null);
  if (cat) { const c = cat.toLowerCase(); list = list.filter((r) => (r.category || "").toLowerCase() === c); }
  return list.sort((a, b) => (b.tashan_score || 0) - (a.tashan_score || 0));
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
  return `  ${trustStr(r.tashan_score)}  ${bold(name)} ${kind} ${dl}  ${vd}`;
}
function table(rows, limit) {
  if (!rows.length) return dim("  no matches.");
  const head = "  " + dim("SCORE".padStart(3)) + "  " + dim("CAPABILITY".padEnd(34)) + " " + dim("KIND".padEnd(6)) + " " + dim("  DL");
  return head + "\n" + rows.slice(0, limit).map(row).join("\n");
}

function infoCard(r) {
  const L = [];
  L.push("");
  L.push("  " + bold(pretty(r.name)) + "  " + dim(r.kind || ""));
  L.push("  " + dim(r.id));
  L.push("");
  L.push("  tashan score        " + trustStr(r.tashan_score).trim() + dim("/100") + "   " + dim("upkeep " + (r.upkeep ?? "—") + " · vitality " + (r.vitality || "—")));
  if (r.expertise_verdict) L.push("  Expertise    " + jade(verdict(r.expertise_verdict)) + (r.expertise != null ? dim("  (" + r.expertise + "/100)") : ""));
  L.push("  Adoption     " + dim(fmtNum(r.npm_downloads) + " downloads/wk" + (r.config_reach ? " · reach " + r.config_reach : "")));
  if (r.category) L.push("  Category     " + dim(r.category));
  if (r.npm_deprecated) L.push("  " + red("⚠ deprecated on npm"));
  if (r.gh_archived) L.push("  " + red("⚠ repository archived"));
  L.push("");
  if (r.npm_pkg) L.push("  npm          " + under("https://www.npmjs.com/package/" + r.npm_pkg));
  if (r.source_repo) L.push("  source       " + under("https://github.com/" + r.source_repo));
  // The security audit belongs here too. `info` is what someone runs BEFORE installing — the moment
  // the findings are most actionable — and it was the one surface still silent about them.
  const sec = [];
  if (r.sec_max_severity === "MALICIOUS") sec.push(red("MALICIOUS — listed in OSV's malicious-packages database. Do not install."));
  else if (r.sec_advisory_count) sec.push(red(`${r.sec_advisory_count} known advisor${r.sec_advisory_count === 1 ? "y" : "ies"}`) + dim(` (${(r.sec_max_severity || "unrated").toLowerCase()}) against the current release`));
  else if (r.sec_advisory_count === 0) sec.push(jade("no known advisories") + dim(" against the current release"));
  if (r.sec_install_script) sec.push(C("33")("runs a script at install time"));
  if (r.sec_permissions) {
    try { const ps = JSON.parse(r.sec_permissions); if (ps.length) sec.push(dim("can reach: ") + ps.join(", ")); } catch { /* never break info */ }
  }
  if (sec.length) {
    L.push("");
    L.push("  " + dim("security") + "     " + sec[0]);
    for (const x of sec.slice(1)) L.push("               " + x);
    L.push("");                 // separator belongs to the block, not to the line after it
  }
  L.push("  dossier      " + under(SITE + "/capability/" + (r.slug || slugify(r.id)) + ".html"));
  L.push("");
  L.push("  " + dim("install:  ") + jade("tashan add " + pretty(r.name)));
  L.push("");
  return L.join("\n");
}

function renderAdd(r, client) {
  const snips = installSnippets(r, client);
  if (!snips.length) return red(`  no install method for client "${client}". try: claude · cursor · desktop · codex · npx`);
  const out = ["", "  " + bold(pretty(r.name)) + dim("  — " + SITE + "/capability/" + (r.slug || slugify(r.id)) + ".html"), ""];
  for (const s of snips) {
    out.push("  " + dim(s.label));
    out.push(s.cmd.split("\n").map((l) => "    " + jade(l)).join("\n"));
    out.push("");
  }
  return out.join("\n");
}

// ---- data ----
// Fetch each matched capability's series from the paid endpoint and fold the trend in. One request
// per capability, capped: a config with 40 servers should not open 40 sockets at once, and the
// endpoint is per-id by design (a whole-corpus history download is not what anyone wants).
// ponytail: sequential with a cap; batch the endpoint if a stack of hundreds ever shows up.
async function withTrends(results, lic, base = SITE, limit = 40) {
  const key = lic && lic.key;
  // Send the activation too. Without it the device limit only constrains the CLI's own display and
  // a shared key still buys unlimited access to the paid endpoint, which is the thing being sold.
  const auth = { authorization: `Bearer ${key}` };
  if (lic && lic.activation_id) auth["x-tashan-activation"] = lic.activation_id;
  let n = 0;
  for (const r of results) {
    if (!r.row || n >= limit) continue;
    n++;
    try {
      const res = await fetch(`${base}/api/history?id=${encodeURIComponent(r.row.id)}`,
                              { headers: auth });
      if (res.status === 403 || res.status === 401) {
        process.stderr.write(red("  licence not valid for this device — check " + PORTAL) + "\n");
        return results;                       // stop early; every other call would fail the same way
      }
      if (!res.ok) continue;                  // 404 = nothing recorded yet, 503 = validation down
      const { series, scorers } = await res.json();
      r.assessment = withTrend(r.assessment, trend(series, scorers));
    } catch { /* offline: trend is an enhancement, never a reason doctor fails */ }
  }
  return results;
}

// The CLI reads the LOOKUP for doctor (complete, keyed) and the board for search/top (ranked).
// Two different questions, two different shapes; conflating them is what broke doctor.
async function loadLookup() {
  const r = await fetch(SITE + "/data/lookup.json", { headers: { "user-agent": "tashan-cli" } });
  if (!r.ok) throw new Error(`lookup unavailable (HTTP ${r.status})`);
  return r.json();
}

// A paying customer whose stack happened to be healthy saw output identical to a free user's — no
// confirmation the $6 was doing anything. That is the "did my payment even work" ticket, then the
// cancellation. Ask Polar, the actual source of truth, rather than inferring from our own API.
// Never report "active" on a network failure: a false all-clear is worse than admitting we cannot tell.
async function verifyLicence(lic) {
  if (!lic || !lic.key) return null;
  const { status, json } = await polar("/validate",
    lic.activation_id ? { key: lic.key, activation_id: lic.activation_id } : { key: lic.key });
  if (status === 404 || status === 422) {
    // A 404 here is ambiguous and the two cases need OPPOSITE actions from the user. If the key
    // still validates on its own, the subscription is fine and only this device was released —
    // exactly what happens after freeing a seat in the portal. Telling that person their key is
    // invalid sends them to support over a one-command fix.
    if (lic.activation_id) {
      const bare = await polar("/validate", { key: lic.key });
      if (bare.status === 200 && bare.json && bare.json.status === "granted") return "deactivated";
    }
    return "invalid";
  }
  if (status !== 200 || !json) return "unknown";               // Polar down, or we are offline
  if (json.status !== "granted") return "invalid";             // revoked or disabled
  if (json.expires_at && Date.parse(json.expires_at) <= Date.now()) return "invalid";
  return "active";
}

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

  ${jade("tashan search")} <query>       find MCP servers & skills, ranked by tashan score
  ${jade("tashan top")} [category]       the leaderboard
  ${jade("tashan info")} <name>          the measured dossier for one capability
  ${jade("tashan add")} <name>           the install command  ${dim("(--client claude|cursor|desktop|codex|npx)")}
  ${jade("tashan doctor")}               audit the config you already have — dead, deprecated, risky
  ${jade("tashan activate")} <key>       register this machine — once, not once per shell
  ${dim("Pro names the replacement for anything dead in your config · $6/mo · " + SITE + "/pricing.html")}

  ${dim("flags:")}  --json   --limit <n>   --client <c>   --all   --forget
  ${dim("free tier needs no account · your subscription lives at " + PORTAL)}
`;

export function parseArgs(argv) {
  const a = { _: [], json: false, limit: 20, client: null };
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    if (t === "--json") a.json = true;
    else if (t === "--limit") a.limit = parseInt(argv[++i], 10) || 20;
    else if (t === "--client") a.client = (argv[++i] || "").toLowerCase();
    else if (t.startsWith("--client=")) a.client = t.slice(9).toLowerCase();
    else if (t === "--trend") a.trend = true;
    else if (t === "--all") a.all = true;
    else if (t === "--forget") a.forget = true;
    else if (t === "--key") a.key = argv[++i] || "";
    else if (t.startsWith("--key=")) a.key = t.slice(6);
    else a._.push(t);
  }
  return a;
}

const MARK = { alert: red("!"), warn: C("33")("~"), note: dim("·"), ok: jade("+"), unrated: dim("·"), unknown: dim("?") };

function renderDoctor(results, problems, sum, pro = false, verbose = false, keyState = null) {
  if (!results.length) {
    return "\n  " + bold("No agent config found.") + "\n" +
      dim("  Looked in ~/.claude.json, ~/.cursor/mcp.json, Claude Desktop, .mcp.json, ~/.claude/skills/ …") + "\n";
  }
  const order = { alert: 0, warn: 1, unrated: 2, unknown: 3, ok: 4 };
  // ONLY PRINT WHAT NEEDS A DECISION. A real machine has ~113 skills that are catalogued but unrated,
  // and listing each with an identical "no per-item evidence yet" line buried the ten servers that
  // actually had findings under a wall of repetition. Rows that need attention are shown in full;
  // everything else is counted. The detail is one flag away, not gone.
  const shown = results.filter((r) => r.assessment.level === "alert" || r.assessment.level === "warn"
                                   || (r.alts && r.alts.length));
  const quiet = results.length - shown.length;
  const rows = (verbose ? results.slice() : shown)
    .sort((x, y) => order[x.assessment.level] - order[y.assessment.level]);
  let out = "\n  " + bold("Your stack") + dim(`  ·  ${sum.servers} server${sum.servers === 1 ? "" : "s"}, ${sum.skills} skill${sum.skills === 1 ? "" : "s"}`) + "\n\n";
  if (!rows.length) out += "  " + jade("+") + " " + dim("nothing deprecated, archived or abandoned.") + "\n";
  for (const { item, row, assessment, alts } of rows) {
    const t = row && row.tashan_score != null ? String(Math.round(row.tashan_score)) : "—";
    out += "  " + (MARK[assessment.level] || " ") + " " + bold(pretty(item.name).padEnd(28).slice(0, 28)) +
      dim((item.client + " · " + item.scope).padEnd(22)) + dim("score ") + (t === "—" ? dim(t) : jade(t)) + "\n";
    for (const n of assessment.notes) {
      const txt = typeof n === "string" ? n : n.text;
      out += "      " + dim("↳ ") + (n.level === "alert" ? red(txt) : dim(txt)) + "\n";
    }
    if (alts && alts.length) {
      if (pro) {
        for (const a of alts) {
          out += "      " + jade("→ ") + bold(pretty(a.cap.name)) +
            dim(`  ${Math.round(a.score)}/100 · ${a.cap.vitality || "—"}`) + "\n";
        }
      } else {
        out += "      " + jade("→ ") + dim(`${alts.length} alternative${alts.length === 1 ? "" : "s"} measured better · `) +
          jade("tashan Pro") + dim(" $6/mo — tashan.sh/pricing.html") + "\n";
      }
    }
  }
  for (const p of problems) out += "  " + red("!") + " " + bold("config unreadable") + dim("  " + p.path) + "\n";
  const bits = [];
  if (sum.alert) bits.push(red(sum.alert + " need attention"));
  if (sum.warn) bits.push(sum.warn + " worth a look");
  if (sum.unrated) bits.push(dim(sum.unrated + " catalogued, unrated"));
  if (sum.unknown) bits.push(dim(sum.unknown + " not in the index"));
  out += "\n  " + (bits.length ? bits.join(dim(" · ")) : jade("nothing flagged")) + "\n";
  if (quiet && !verbose) out += dim(`  ${quiet} more not flagged — --all lists every row.`) + "\n";
  // The offer appears only where a free reader has just been shown a finding whose DETAIL exists
  // and is withheld — never on a clean run, never as a recurring nag. If there is nothing to
  // unlock, saying nothing is the honest behaviour and the one that keeps the tool installed.
  if (!pro && keyState === null) {
    const withDetail = rows.filter((r) => r.row &&
      (r.row.sec_advisory_count || r.row.sec_install_script || (r.alts && r.alts.length))).length;
    if (withDetail) {
      out += "\n  " + dim(`${withDetail} finding${withDetail === 1 ? " has" : "s have"} detail behind a licence — `) +
        dim("which advisory and the version that fixes it, what the install script runs, ") +
        dim("and the replacement to move to.") + "\n" +
        "  " + jade("tashan Pro") + dim(" $6/mo · " + SITE + "/pricing.html") + "\n";
    }
  }
  // Say the subscription state out loud, every run. Silence is what makes someone wonder.
  if (keyState === "active")
    out += "  " + jade("Pro") + dim(rows.some((r) => r.alts && r.alts.length)
      ? " · licence active — replacements named above"
      : " · licence active — nothing in your stack needs replacing") + "\n";
  else if (keyState === "deactivated")
    out += "  " + red("This device was deactivated") +
           dim(" — your subscription is fine; run `tashan activate <key>`") + "\n";
  else if (keyState === "invalid") out += "  " + red("Pro key not valid") + dim(" — check " + PORTAL) + "\n";
  else if (keyState === "unknown") out += dim("  Pro · could not reach tashan to check your licence") + "\n";
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
    process.stdout.write("\n  " + bold("Top by tashan score" + (arg ? " · " + arg : "")) + "\n" + table(list, a.limit) + "\n\n" + dim("  ranked on public evidence · tashan.sh") + "\n");
    return 0;
  }
  if (cmd === "info" || cmd === "add") {
    const r = find(rows, arg);
    if (!r) { process.stderr.write(red(`  no capability matches "${arg}". try: tashan search ${arg}`) + "\n"); return 1; }
    if (a.json) { process.stdout.write(JSON.stringify(cmd === "add" ? { capability: r, install: installSnippets(r, a.client) } : r, null, 2) + "\n"); return 0; }
    process.stdout.write((cmd === "add" ? renderAdd(r, a.client) : infoCard(r)) + "\n");
    return 0;
  }
  if (cmd === "mcp") {
    // `npx -y tashan-cli mcp` is the ONE install string: it resolves the published package by name and
    // then runs the server. `npx -y tashan-cli mcp` would resolve a PACKAGE called tashan-mcp, which does
    // not exist — the bin of that name lives inside this package, and npx keys off the package name.
    await import("./mcp.mjs").then((m) => m.serve());
    return 0;
  }
  if (cmd === "activate") {
    // --forget must RELEASE the seat at Polar, not just delete our file. Deleting locally while the
    // activation stays registered burns a device slot the customer cannot get back without support.
    if (a.forget) {
      const lic = storedLicence();
      if (lic && lic.activation_id) {
        const { status } = await polar("/deactivate",
          { key: lic.key, activation_id: lic.activation_id });
        if (status === 0) {
          process.stderr.write("\n  " + red("Offline — the seat was NOT released.") +
            dim("\n  Nothing removed. Run this again online, or release it at " + PORTAL + "\n"));
          return 1;                    // refuse the half-done state rather than silently leaking a seat
        }
      }
      try { rmSync(keyPath()); process.stdout.write("\n  " + jade("This machine is deactivated.") +
        dim(`\n  seat released${lic && lic.activation_id ? "" : " (none was registered)"} · ${keyPath()} removed`) + "\n"); }
      catch { process.stdout.write(dim("\n  no stored licence on this machine\n")); }
      return 0;
    }

    const given = a._[1] || process.env.TASHAN_KEY;
    if (!given) {
      const lic = storedLicence();
      process.stdout.write("\n  " + (lic
        ? bold("This machine is activated.") +
          dim(`\n  ${lic.label || "this device"} · key ${lic.key.slice(0, 12)}…`) +
          dim(`\n  ${keyPath()}`) +
          dim("\n  tashan activate --forget releases the seat · " + PORTAL + " lists every device")
        : bold("This machine is not activated.") +
          dim("\n  tashan activate <key>") +
          dim("\n  Your key, invoices and subscription live at " + PORTAL)) + "\n");
      return lic ? 0 : 1;
    }

    // Register the device with Polar BEFORE writing anything locally. Polar owns the device limit,
    // the labels and the revoke button in the portal; a key stored here that Polar never activated
    // would look fine to us and fail everywhere else.
    const label = `${hostname()} · ${platform()}`;
    const { status, json } = await polar("/activate", { key: given, label });
    if (status === 0) {
      process.stderr.write("\n  " + red("Could not reach Polar to activate.") +
        dim("\n  Nothing was saved. Try again when you are online.\n"));
      return 1;
    }
    if (status === 403) {
      process.stderr.write("\n  " + red("Every device slot on this licence is in use.") +
        dim("\n  Release one at " + PORTAL + ", or run `tashan activate --forget` on a machine") +
        dim("\n  you no longer use.\n"));
      return 1;
    }
    if (status !== 200 || !json || !json.id) {
      process.stderr.write("\n  " + red("That key was rejected.") +
        dim("\n  Copy it again from " + PORTAL + " — it is under your subscription's benefits.\n"));
      return 1;
    }
    const rec = { key: given, activation_id: json.id, label };
    try {
      mkdirSync(dirname(keyPath()), { recursive: true });
      writeFileSync(keyPath(), JSON.stringify(rec, null, 2) + "\n", { mode: 0o600 });
      chmodSync(keyPath(), 0o600);   // an existing file keeps its old mode without this
    } catch (e) {
      // The seat is already taken at Polar; leaving it registered with no local record would strand
      // it. Hand it back before reporting the failure.
      await polar("/deactivate", { key: given, activation_id: json.id });
      process.stderr.write("\n  " + red("Could not write " + keyPath()) + dim("\n  " + e.message +
        "\n  The seat was released again. Fallback: export TASHAN_KEY=" + given.slice(0, 8) + "…\n"));
      return 1;
    }
    process.stdout.write("\n  " + jade("Pro is active on this machine.") +
      dim(`\n  registered with Polar as "${label}" — see every device at ${PORTAL}`) +
      dim(`\n  stored in ${keyPath()} · every shell, every project, no re-export`) +
      dim("\n\n  tashan doctor") + "\n");
    return 0;
  }

  if (cmd === "doctor") {
    const { found, problems } = collect(configLocations(), skillLocations());
    const lic = resolveLicence(a);
    const key = lic ? lic.key : null;
    const keyState = await verifyLicence(lic);
    let lookup = null;
    try { lookup = await loadLookup(); } catch { /* fall back to the board rather than failing */ }
    const look = (item) => (lookup ? resolve(item, lookup) : match(item, rows));
    let results = found.map((item) => { const row = look(item); return { item, row, assessment: assess(item, row) }; });

    // GATE THE COLUMN, NOT THE COMMAND. Everything above this line is free and stays free: what you
    // run, what it is, and every risk verdict. What a key buys is the answer — which replacement.
    // Free output still shows that an answer EXISTS on the rows that have one, because hiding the
    // existence of a warning-adjacent fact would be the same mistake as paywalling the warning.
    const pool = lookup ? lookup.records : rows;
    const df = tokenFrequency(pool);
    for (const r of results) {
      if (r.row && isDying(r.row)) r.alts = suggest(r.row, pool, df);
    }

    // --trend is the whole paid product, and it is the SAME command with one flag. A separate
    // `tashan pro` verb would have been a second thing to learn for no benefit; the question is
    // identical, only the timeframe changes. Without a key it says so and exits 0 — a missing
    // subscription is not an error, and it must never look like the config is broken.
    if (a.trend) {
      if (!key) {
        process.stderr.write(red("  that needs a licence key — run: tashan activate <key> "
          + "(tashan Pro, $6/mo — https://tashan.sh/pricing.html)") + "\n");
        return 0;
      }
      results = await withTrends(results, lic);
    }

    const sum = summarize(results);
    if (a.json) { process.stdout.write(JSON.stringify({ summary: sum, problems, results }, null, 2) + "\n"); return 0; }
    process.stdout.write(renderDoctor(results, problems, sum, keyState === "active", a.all, keyState) + "\n");
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
