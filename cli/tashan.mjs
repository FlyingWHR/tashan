#!/usr/bin/env node
// tashan — the measured layer for AI capabilities, in your terminal.
//
//   npx tashan-cli search <query>        find MCP servers & skills, ranked by tashan score
//   npx tashan-cli top [category]        the leaderboard
//   npx tashan-cli info <name>           the measured dossier for one capability
//   npx tashan-cli add <name>            the install command for your client   ← the money shot
//   npx tashan-cli doctor                audit the config you actually have — dead, deprecated, risky
//   npx tashan-cli login                 sign in — prints a code, opens the browser, approve, done
//   npx tashan-cli logout                release this machine's seat
//   npx tashan-cli activate <key>        non-interactive sign-in for CI, where there is no browser
//   npx tashan-cli account               open your account in the browser, already signed in
//   npx tashan-cli mcp                   run as an MCP server, so your AGENT can ask before installing
//
// Reads live public data from https://tashan.sh/data/index.json (no account, no backend, no telemetry).
// Zero dependencies. The pure functions are exported for cli/tashan.test.mjs.

import { spawn } from "node:child_process";
import { readFileSync, writeFileSync, mkdirSync, rmSync, chmodSync, realpathSync } from "node:fs";
import { homedir, hostname, platform } from "node:os";
import { join, dirname, basename } from "node:path";
import { configLocations, skillLocations, collect, match, resolve, assess, summarize, trend, withTrend,
         suggest, tokenFrequency, isDying, identify } from "./doctor.mjs";
import { scan, loadLedger, saveLedger, reconcile, usage, usageOf } from "./inventory.mjs";

// Resolved against this module's own URL, not cwd and not argv[1] — npm installs the bin as a
// SYMLINK, so a path derived from how the process was invoked points somewhere else entirely.
// See [[npm-bin-is-a-symlink]]. Falls back rather than throwing: a missing package.json must not
// take down every command in the CLI just because one of them wanted to print a number.
const VERSION = (() => {
  try { return JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8")).version; }
  catch { return "unknown"; }
})();

// ---- licence ---------------------------------------------------------------------------------
// Billing is Polar's; the account centre is ours. The customer-portal license-key endpoints
// (activate / validate / deactivate) are PUBLIC, needing only the org id, so the CLI talks to them
// directly — we store no passwords, run no sessions and hold no customer record. An earlier cut of
// this file hand-rolled all of it against our own API, which meant no device list, no activation
// limit, and nothing the customer could see or revoke.
//
// `tashan account` posts this key to tashan.sh/api/account and opens the browser on the one-time
// URL it returns, so the customer reaches their plan, machines and invoices without typing anything.
// PORTAL below is the billing side of that — invoices, card, cancellation — and nothing else.
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

// Opening a browser without a dependency. Exported as a pure function so the argument shape is
// testable — `start` is a cmd.exe builtin, not an executable, and its first argument is swallowed as
// the window title, so a URL passed as argv[0] there silently opens nothing.
export function browserCommand(plat, url) {
  if (plat === "darwin") return { cmd: "open", args: [url], shell: false };
  if (plat === "win32") return { cmd: "start", args: ["", url], shell: true };
  return { cmd: "xdg-open", args: [url], shell: false };
}

function openBrowser(url) {
  try {
    const { cmd, args, shell } = browserCommand(platform(), url);
    spawn(cmd, args, { detached: true, stdio: "ignore", shell }).unref();
    return true;
  } catch {
    return false;            // headless box or no handler — the caller prints the link instead
  }
}

// ---- device-authorisation login --------------------------------------------------------------
// `tashan activate <key>` asked every customer to go to their email, find a licence key, and paste
// it into a terminal — once per machine, forever. That is the worst moment in the product and it
// lands immediately after someone pays. This is the flow they already know from `gh auth login`,
// `wrangler login` and `stripe login`: ask for a code, approve it in a browser, the terminal picks
// up the credential. The key is typed at most once in a lifetime, in a browser, where paste is one
// keystroke. `activate` stays for scripts and CI, where a browser is not a thing.
export async function deviceLogin({ open = true, fetchImpl = fetch, sleep = (ms) => new Promise(r => setTimeout(r, ms)) } = {}) {
  const post = async (body) => {
    try {
      const r = await fetchImpl(SITE + "/api/device", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body || {}),
      });
      return { status: r.status, json: await r.json().catch(() => null) };
    } catch {
      return { status: 0, json: null };
    }
  };

  const started = await post({});
  if (started.status !== 200 || !started.json || !started.json.device_code) {
    process.stderr.write("\n  " + red("Could not start sign-in.") +
      dim("\n  " + (started.status === 503 ? "Sign-in is temporarily unavailable." : "Check your connection.") +
          "\n  You can still use `tashan activate <key>` with the key from your purchase email.\n"));
    return 1;
  }
  const { device_code, user_code, verify_url_complete, verify_url, interval, expires_in } = started.json;
  const url = verify_url_complete || verify_url;

  process.stdout.write("\n  " + bold("Your code:  ") + jade(user_code) + "\n" +
    dim("  Approve it at " + url) + "\n");
  if (open && openBrowser(url)) process.stdout.write(dim("  (opened in your browser)") + "\n");
  process.stdout.write(dim("\n  waiting…") + "\n");

  const deadline = Date.now() + (Number(expires_in) || 600) * 1000;
  let wait = Math.max(2, Number(interval) || 3) * 1000;
  while (Date.now() < deadline) {
    await sleep(wait);
    const r = await post({ device_code });
    const st = r.json && r.json.status;
    if (st === "slow_down") { wait += 1000; continue; }   // RFC 8628 §3.5 — back off, do not give up
    if (st === "pending" || r.status === 0) continue;      // offline blips are not a denial
    if (st === "denied") {
      process.stderr.write("\n  " + red("Denied in the browser.") + dim("\n  Nothing was stored.\n"));
      return 1;
    }
    if (st === "ok" && r.json.key) return storeKey(r.json.key);
    break;
  }
  process.stderr.write("\n  " + red("That code expired.") + dim("\n  Run `tashan login` again.\n"));
  return 1;
}

// Register with Polar, then write the file — the same order `activate` uses, and for the same
// reason: Polar owns the device limit, so a key stored locally that Polar never activated looks
// fine here and fails everywhere else.
async function storeKey(key) {
  const label = `${hostname()} \u00b7 ${platform()}`;
  const { status, json } = await polar("/activate", { key, label });
  if (status === 0) {
    process.stderr.write("\n  " + red("Signed in, but could not reach Polar to register this machine.") +
      dim("\n  Nothing was saved. Try again when you are online.\n"));
    return 1;
  }
  if (status === 403) {
    process.stderr.write("\n  " + red("Every device slot on this licence is in use.") +
      dim("\n  Release one at " + PORTAL + ", or run `tashan logout` on a machine you no longer use.\n"));
    return 1;
  }
  if (status !== 200 || !json || !json.id) {
    process.stderr.write("\n  " + red("The licence was rejected when registering this machine.") +
      dim("\n  Check your plan at " + PORTAL + "\n"));
    return 1;
  }
  try {
    mkdirSync(dirname(keyPath()), { recursive: true });
    writeFileSync(keyPath(), JSON.stringify({ key, activation_id: json.id, label }, null, 2) + "\n", { mode: 0o600 });
    chmodSync(keyPath(), 0o600);
  } catch (e) {
    await polar("/deactivate", { key, activation_id: json.id });
    process.stderr.write("\n  " + red("Could not write " + keyPath()) + dim("\n  " + e.message + "\n"));
    return 1;
  }
  process.stdout.write("\n  " + jade("Pro is active on this machine.") +
    dim(`\n  registered as "${label}" \u2014 tashan account shows every device`) +
    dim(`\n  stored in ${keyPath()} \u00b7 every shell, every project, no re-export`) +
    dim("\n\n  tashan doctor") + "\n");
  return 0;
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
// The human label, derived once in build.py's apply_labels over the whole corpus (it must see every
// other row to know two products are both "Notion"). pretty() stays for the places that build an
// IDENTIFIER — an install command, a folder name — and for search matching, where a display label
// with spaces and "·" would be the wrong thing to match against.
export function disp(c) { return (c && c.label) || pretty(c && c.name); }
export function pretty(name) {
  return String(name || "").replace(/^@modelcontextprotocol\/server-/, "").replace(/-mcp$/, "").replace(/^mcp-server-/, "").replace(/^mcp-/, "");
}

// ---- the security audit's DETAIL, read off the public row ---------------------------------------
// Both of these used to arrive from /api/security behind a licence header. build.py's redact_paid()
// no longer strips sec_advisories and no longer flattens sec_install_script to a boolean, so the
// detail rides in the public lookup.json the CLI already downloads. Free on the website, free here.
// Exported (and shared with mcp.mjs) so the terminal, the agent and the page cannot drift apart.

/** The advisories on a row: [{ id, severity, summary, fixed }]. Never throws — a malformed field
 *  must not take down an audit someone is running precisely because they are already worried. */
export function advisoriesOf(row) {
  try {
    const list = JSON.parse((row && row.sec_advisories) || "[]");
    return Array.isArray(list) ? list : [];
  } catch { return []; }
}

/** The literal command a package runs at install time, or null.
 *  THE BOARD DOES NOT CARRY IT. index.json slims sec_install_script to the number 1 (build.py's
 *  _slim) because the board only needs the FACT and the command can be 300 characters; only
 *  lookup.json has the string. A truthiness test would print "install runs: 1" on every board-sourced
 *  row — worse than silence — so this checks the type, not the truth. */
export function installScriptOf(row) {
  const s = row && row.sec_install_script;
  return typeof s === "string" && s.trim() && s !== "1" ? s : null;
}

// ---- the directory's evidence, read the way a person decides ------------------------------------
// One implementation behind doctor and info, so the two cannot describe the same row two ways.

/** Where a row sits in its category, in the dossier's words ("above 98% of browser"). The number is
 *  build.py's rank_pct, carried in lookup.json — recomputed here it disagreed with the dossier on half
 *  the rows. ponytail: 100 prints as 99; rank_pct is rounded, so "above 100%" is odd and untrue. */
export function standing(r) {
  if (!r || r.rank_pct == null || r.tashan_score == null) return null;
  return `above ${Math.min(99, r.rank_pct)}% of ${r.category || "its category"}`;
}

/** The public facts behind a score, most telling first — only the ones this row actually carries. */
export function evidenceOf(r, max = 4) {
  if (!r) return [];
  const out = [];
  if (r.official) out.push(`${r.official} official`);
  if (r.npm_downloads) out.push(`${fmtNum(r.npm_downloads)} downloads/wk`);
  if (r.gh_stars) out.push(`${fmtNum(r.gh_stars)} stars`);
  if (r.sec_provenance) out.push("provenance-attested build");
  if (r.expertise_verdict) out.push(`${r.expertise_verdict} docs`);
  return out.slice(0, max);
}

/** What the agent can reach, summed over everything resolved. From DECLARED dependencies — nothing is
 *  run — so an empty list means "nothing declared", never "nothing possible". */
export function reachOf(results) {
  const perms = {}, remote = [];
  for (const { item, row } of results) {
    if (!row) continue;
    const name = pretty(item.name);
    let ps = [];
    try { ps = JSON.parse(row.sec_permissions || "[]"); } catch { /* a malformed field never breaks the audit */ }
    for (const p of Array.isArray(ps) ? ps : []) {
      perms[p] = perms[p] || [];
      if (!perms[p].includes(name)) perms[p].push(name);
    }
    if (row.sec_remote_content && !remote.includes(name)) remote.push(name);
  }
  return { perms, remote };
}

/** The consequential changes lookup.json carries for what you run, newest first. */
export function recentOf(results, limit = 6) {
  const seen = new Set(), out = [];
  for (const { item, row } of results) {
    if (!row || seen.has(row.id)) continue;
    seen.add(row.id);
    for (const e of row.recent || []) out.push({ ...e, name: pretty(item.name) });
  }
  return out.sort((a, b) => (a.at < b.at ? 1 : a.at > b.at ? -1 : 0)).slice(0, limit);
}

/** A score series as a sparkline over at least ten points of range, centred. Scaled to its own
 *  min–max, a one-point wobble fills the whole height and reads as a collapse. */
export function spark(values, width = 14) {
  const v = (values || []).filter((x) => typeof x === "number").slice(-width);
  if (v.length < 2) return "";
  const lo = Math.min(...v), hi = Math.max(...v), span = Math.max(10, hi - lo), base = (lo + hi - span) / 2;
  return v.map((x) => "▁▂▃▄▅▆▇█"[Math.max(0, Math.min(7, Math.round(((x - base) / span) * 7)))]).join("");
}

/** Which offer a reader without a licence sees, or null.
 *
 *  THE RULE CHANGED, deliberately. It was "only where a finding's detail is withheld", which once the
 *  security detail went free meant a named replacement and nothing else — so a healthy stack, the
 *  common case, never learned anything was for sale. What a licence buys for EVERY measured row is
 *  its score series (entitlements: history, live), so the offer names that, for the rows this reader
 *  has. Still never: where nothing is measured, for an advisory or an install command (both free in
 *  full), or once any licence exists — then the state of the licence is said instead. */
export function offerFor(results, keyState) {
  if (keyState != null) return null;
  const replaceable = results.filter((r) => r.row && r.alts && r.alts.length).length;
  if (replaceable) return { kind: "replacement", n: replaceable };
  const measured = new Set(results.filter((r) => r.row && r.row.tashan_score != null).map((r) => r.row.id)).size;
  return measured ? { kind: "series", n: measured } : null;
}

/** The answer to "should I install this", before the detail. Every branch is a published
 *  measurement and the thresholds are the board's own colour bands (70 / 40). Fit for a particular
 *  job is not judged here — that is the job pages' question. A script at install time does not lower
 *  the verdict, it rides beside it: azure is Microsoft-official, scores 86 and runs one, and folding
 *  the two together would hide exactly that case. */
export function verdictOf(r) {
  if (!r) return null;
  const s = r.tashan_score;
  const why = s == null ? null : [`${Math.round(s)}/100`, standing(r)].filter(Boolean).join(", ");
  const but = r.sec_install_script ? "runs a script at install time" : null;
  if (r.sec_max_severity === "MALICIOUS") return { level: "alert", text: "Do not install", why: "listed in OSV's malicious-packages database" };
  if (r.registry_status === "deleted") return { level: "alert", text: "Do not install", why: "removed from the MCP registry" };
  const dead = r.npm_deprecated ? "deprecated on npm" : r.gh_archived ? "its repository is archived"
    : r.registry_status === "deprecated" ? "deprecated in the MCP registry"
    : r.vitality === "abandoned" ? "no recent activity — looks abandoned" : null;
  if (dead) return { level: "alert", text: "Not recommended", why: dead };
  if (r.sec_advisory_count) {
    const sev = (r.sec_max_severity || "unrated").toLowerCase();
    const bad = sev === "critical" || sev === "high";
    return { level: bad ? "alert" : "warn", text: bad ? "Not recommended" : "Use with care", but,
             why: `${r.sec_advisory_count} known advisor${r.sec_advisory_count === 1 ? "y" : "ies"} (${sev}) against the current release` };
  }
  if (s == null) return { level: "note", text: "Unrated", why: r.rating_basis || "catalogued, no per-item evidence yet" };
  if (s >= 70) return { level: "ok", text: "Strong pick", why, but };
  if (s >= 40) return { level: "note", text: "Reasonable pick", why, but };
  return { level: "warn", text: "Weak evidence", why, but };
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
  // AMONG EXACT MATCHES, THE BEST-MEASURED ONE. `tashan info context7` answered with a plugin that
  // re-lists Context7 (77, no downloads) instead of @upstash/context7-mcp (98, 1.1M/wk), because the
  // plugin is NAMED exactly "context7" and happened to come first. A typed package name or id still
  // wins outright: whoever wrote `@scope/pkg` meant that package, measured or not.
  const bare = (r) => pretty(r.name || "").toLowerCase().replace(/^@[^/]+\//, "");
  const best = (xs) => xs.sort((a, b) => (b.tashan_score ?? -1) - (a.tashan_score ?? -1))[0];
  return rows.find((r) => r.slug === k)
      || rows.find((r) => (r.npm_pkg || "").toLowerCase() === k || String(r.id || "").toLowerCase() === k)
      || best(rows.filter((r) => (r.name || "").toLowerCase() === k || (r.label || "").toLowerCase() === k
                               || bare(r) === k))
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

// Money at the precision the number deserves. Mirrors prerender.paid_line, gen_paid.money and
// mcp.paidUsd — four renderers, one rule, because a figure that reads differently per surface is
// not evidence.
function paidUsd(v) {
  if (v == null) return "unknown";
  if (v === 0) return "$0";
  if (v < 0.01) return "<$0.01";
  if (v < 100) return "$" + v.toFixed(2);
  return "$" + Math.round(v).toLocaleString("en-US");
}

function row(r) {
  const name = disp(r).slice(0, 34).padEnd(34);
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
  const kv = (k, v) => L.push("  " + k.padEnd(13) + v);
  L.push("");
  L.push("  " + bold(disp(r)) + "  " + dim(r.kind || ""));
  L.push("  " + dim(r.id));
  L.push("");
  // THE ANSWER FIRST. This card was nine fields in the order they were registered and never said the
  // one thing somebody running `info` came for: should I install this. The verdict leads with the
  // fact behind it; the evidence follows for whoever wants to check it.
  const v = verdictOf(r);
  if (v) {
    const paint = v.level === "alert" ? red : v.level === "warn" ? C("33") : v.level === "ok" ? jade : bold;
    L.push("  " + paint(v.text) + (v.why ? dim(" — " + v.why) : "") + (v.but ? C("33")(" · " + v.but) : ""));
    L.push("");
  }
  kv("tashan score", trustStr(r.tashan_score).trim() + dim("/100") + (standing(r) ? dim("   " + standing(r)) : ""));
  if (r.official) kv("Publisher", r.official + dim(" (official)"));
  kv("Adoption", dim([r.npm_downloads != null ? fmtNum(r.npm_downloads) + " downloads/wk" : null,
                      r.gh_stars ? fmtNum(r.gh_stars) + " GitHub stars" : null,
                      r.config_reach ? "reach " + r.config_reach : null].filter(Boolean).join(" · ") || "—"));
  kv("Upkeep", dim([r.vitality || "—", r.upkeep != null ? "upkeep " + r.upkeep : null,
                    r.npm_latest_version ? "latest " + r.npm_latest_version : null,
                    r.single_maintainer ? "one primary maintainer" : null].filter(Boolean).join(" · ")));
  if (r.expertise_verdict) kv("Docs", jade(verdict(r.expertise_verdict)) + (r.expertise != null ? dim("  (" + r.expertise + "/100)") : ""));
  // SETTLED RECEIPTS, directly under adoption, because the contrast IS the signal: this row reads
  // "636 downloads/wk" and "$166,659 settled". Printed only where paid_seen_at says we asked the
  // chain — an em-dash would read as "we looked and found nothing" for the ~11,700 capabilities
  // that never published a price and had nothing to look for.
  if (r.paid_seen_at || r.paid_usd != null) {
    L.push("  Settled      " + dim(paidUsd(r.paid_usd) + (r.paid_calls
      ? " · " + fmtNum(r.paid_calls) + " x402 calls, all time"
      : " — its payment address has never been paid")));
  }
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
  if (r.sec_install_script) sec.push(C("33")("runs a script at install time") + (installScriptOf(r) ? dim(": " + installScriptOf(r)) : ""));
  if (r.sec_permissions) {
    try { const ps = JSON.parse(r.sec_permissions); if (ps.length) sec.push(dim("can reach: ") + ps.join(", ")); } catch { /* never break info */ }
  }
  if (r.sec_remote_content) sec.push(dim("can bring third-party text into your model's context"));
  if (r.dep_scanned_at && r.dep_tree_n) {
    sec.push(r.dep_vuln_n
      ? C("33")(`${r.dep_vuln_n} known advisor${r.dep_vuln_n === 1 ? "y" : "ies"} across its ${r.dep_tree_n} installed dependencies`)
      : dim(`${r.dep_tree_n} installed dependencies, none with a known advisory`));
  }
  // The date a reader needs to weigh "no known advisories", and the limit of the method in four words.
  if (sec.length && r.sec_scanned_at) sec.push(dim("scanned " + String(r.sec_scanned_at).slice(0, 10) + " · declared, never executed"));
  if (sec.length) {
    L.push("");
    L.push("  " + dim("security") + "     " + sec[0]);
    for (const x of sec.slice(1)) L.push("               " + x);
    L.push("");                 // separator belongs to the block, not to the line after it
  }
  // What moved in the last 30 days, straight from the record — the same events /changes.html dates.
  const moved = r.recent || [];
  if (moved.length) {
    L.push("  " + dim("changed") + "      " + dim(moved[0].at) + "  " + moved[0].what);
    for (const e of moved.slice(1)) L.push("               " + dim(e.at) + "  " + e.what);
    L.push("");
  }
  L.push("  dossier      " + under(SITE + "/capability/" + (r.slug || slugify(r.id))));
  L.push("");
  // Only real commands. For a capability with no package the helper returns a comment
  // ("# see the capability's source"), and an `install` heading over a comment is worse than no
  // heading at all — it promises a command and delivers a shrug.
  const snips = installSnippets(r).filter((sn) => sn.cmd && !sn.cmd.trimStart().startsWith("#"));
  if (snips.length) {
    L.push("  " + dim("install"));
    for (const sn of snips.slice(0, 2)) L.push("    " + jade(sn.cmd));
    L.push("");
  }
  return L.join("\n");
}

export function renderAdd(r, client) {
  const snips = installSnippets(r, client);
  if (!snips.length) return red(`  no install method for client "${client}". try: claude · cursor · desktop · codex · npx`);
  const out = ["", "  " + bold(disp(r)) + dim("  — " + SITE + "/capability/" + (r.slug || slugify(r.id))), ""];
  // THE WARNING GOES ABOVE THE COMMAND, NOT BESIDE IT. `info` now falls back to the lookup table so
  // that a deprecated or delisted capability can be looked up at all — which is the point — but
  // `add` shares that branch, and it was printing a clean, copyable install line for a package npm
  // marks "no longer supported" with nothing said about it. A warning under the snippet is a
  // warning nobody reads: by then the command is already on the clipboard.
  const stop = [];
  if (r.npm_deprecated) stop.push("the author has marked it DEPRECATED on npm");
  if (r.registry_status === "deleted") stop.push("it has been REMOVED from the MCP registry");
  if (r.gh_archived) stop.push("its repository is ARCHIVED");
  if (r.sec_advisory_count) stop.push(`it has ${r.sec_advisory_count} known advisor` +
    (r.sec_advisory_count === 1 ? "y" : "ies") + " against the version you would install");
  if (stop.length) {
    out.push("  " + red("Not recommended — " + stop.join("; ")) + ".");
    out.push(dim("  The commands below still work. Check " + SITE + "/capability/" +
                 (r.slug || slugify(r.id)) + " before using them."), "");
  }
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
      // 402 means we sent no credential at all, 403 means the one we sent was refused. Telling
      // somebody whose card just failed to "check your device list" sends them to the wrong page.
      if (res.status === 402) {
        process.stderr.write(red("  trend needs tashan Pro — https://tashan.sh/pricing") + "\n");
        return results;
      }
      if (res.status === 403 || res.status === 401) {
        process.stderr.write(red("  licence not valid for this device — check " + PORTAL) + "\n");
        return results;                       // stop early; every other call would fail the same way
      }
      if (!res.ok) continue;                  // 404 = nothing recorded yet, 503 = validation down
      const { series, scorers } = await res.json();
      r.assessment = withTrend(r.assessment, trend(series, scorers));
    } catch { /* offline: trend is an enhancement, never a reason doctor fails */ }

    // THE SECURITY AUDIT USED TO BE FETCHED HERE, from /api/security with the licence header, and it
    // is gone on purpose. build.py's redact_paid() stopped stripping sec_advisories and stopped
    // reducing sec_install_script to a boolean, so the advisory id, its severity, the version that
    // fixes it and the literal install command now ship in the PUBLIC lookup.json — the same file
    // doctor already downloads, and the same facts the website prints to anyone with a browser.
    // Keeping the fetch meant the identical fact was free on the web and $6/mo in the terminal: one
    // product contradicting itself depending on which surface you happened to be standing on.
    // renderDoctor now reads the detail straight off `row`, with no key, no request and no branch.
    // What stays behind this function is TIME — /api/history above — never the current state.
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

// FIVE VERBS. It had twelve, and the extra seven were the same three ideas spelled differently:
// `top` was `search` with no query, `add` was the last line of `info`, and `activate`/`account`
// were a licence key and a URL wearing the costume of commands. A first-time reader had to choose
// between twelve things to find the one that does something without an argument.
//
// The first line says what the tool DOES, not what it is. "The measured layer for AI capabilities"
// is a positioning statement; nobody can act on it.
const USAGE = `
${bold("tashan")} — check your agent's toolbox: anything dead, deprecated or malicious? ${dim("· " + SITE)}

  ${jade("tashan")}                      check the toolbox you already have ${dim("(the default)")}
  ${jade("tashan search")} <query>       find MCP servers & skills, ranked on public evidence
  ${jade("tashan info")} <name>          one capability in full, and how to install it
  ${jade("tashan mcp")}                  run tashan as an MCP server, so your agent can ask
  ${dim("tashan login")} ${dim("/")} ${dim("logout")}         ${dim("Pro: the replacement for anything dead, and 30 days of history")}

  ${dim("flags:")}  --json   --all   --limit <n>   ${dim("· CI: TASHAN_KEY=<key> tashan doctor")}
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

/** What you have, before what is wrong with it.
 *
 *  Counts, not a list: a machine with 113 skills does not want them enumerated every run. The two
 *  lines that earn their place are the ones you cannot get anywhere else — what arrived since the
 *  last run, and how much of the pile has no owner but you.
 */
function renderInventory(inv) {
  if (!inv) return "";
  const proj = inv.servers.filter((s) => s.scope === "project").length;
  const unmanaged = inv.skills.filter((s) => s.authored).length;
  const undocumented = inv.skills.filter((s) => !s.documented).length;
  let out = "  " + dim("inventory  ") +
    `${inv.servers.length} servers` + dim(proj ? ` (${proj} in ${inv.projects} projects)` : "") +
    ` · ${inv.plugins.length} plugins` + dim(inv.marketplaces.length ? ` from ${inv.marketplaces.length} marketplaces` : "") +
    ` · ${inv.skills.length} skills` + "\n";
  if (unmanaged) {
    out += "  " + dim("           ") + jade(String(unmanaged)) +
      dim(` skill${unmanaged === 1 ? "" : "s"} no plugin owns — nothing will update ${unmanaged === 1 ? "it" : "them"} but you`);
    out += undocumented ? dim(`, ${undocumented} with no description`) + "\n" : "\n";
  }
  if (inv.first) {
    out += "  " + dim("           first run — recording what is here now, so the next run can tell you what changed") + "\n";
  } else {
    if (inv.fresh.length) {
      const names = inv.fresh.slice(0, 4).map((f) => f.name).join(", ");
      out += "  " + dim("           ") + jade("new since last run: ") + names +
        dim(inv.fresh.length > 4 ? ` and ${inv.fresh.length - 4} more` : "") + "\n";
    }
    if (inv.gone.length) {
      const names = inv.gone.slice(0, 4).map((f) => f.name).join(", ");
      out += "  " + dim("           gone since last run: " + names +
        (inv.gone.length > 4 ? ` and ${inv.gone.length - 4} more` : "")) + "\n";
    }
  }
  return out + "\n";
}

function renderDoctor(results, problems, sum, pro = false, verbose = false, keyState = null, inv = null,
                      index = null, use = null) {
  if (!results.length) {
    return "\n  " + bold("No agent config found.") + "\n" +
      dim("  Looked in ~/.claude.json, ~/.cursor/mcp.json, Claude Desktop, .mcp.json, ~/.claude/skills/ …") + "\n";
  }
  const order = { alert: 0, warn: 1, ok: 2, unrated: 3, unknown: 4 };
  const flaggedRow = (r) => r.assessment.level === "alert" || r.assessment.level === "warn";
  // A SKILL IS MATCHED BY ITS FOLDER NAME ALONE: "review" in ~/.claude/skills resolves to whichever
  // public skill is also called review, so its record is a guess about identity — and a guessed score
  // printed as evidence is worse than no score. Servers resolve by package or host and plugins by their
  // home; those are the rows that get scored here. A skill still surfaces when it is flagged.
  const measured = (r) => Boolean(r.row && r.row.tashan_score != null && r.item.type !== "skill");
  // THE MEASURED STACK IS THE REPORT. This printed only what needed a decision, which on a healthy
  // machine — 12 servers, 11 plugins, 241 skills — was four lines and not one piece of the evidence we
  // hold about any of it. A result that says nothing on most runs is a result nobody keeps running.
  // Every row we can score is shown with the public evidence behind it; what no public record
  // describes is still counted rather than listed, because 113 identical "no evidence" lines bury the
  // ten that matter. --all lists them.
  const rows = results.filter((r) => verbose || flaggedRow(r) || measured(r) || (r.alts && r.alts.length))
    .sort((x, y) => (order[x.assessment.level] - order[y.assessment.level])
                 || ((y.row?.tashan_score ?? -1) - (x.row?.tashan_score ?? -1)));
  // The header used to carry its own count, taken from what the audit could RESOLVE. Beside the
  // inventory's count those two numbers disagreed, so the inventory carries the count alone and the
  // header says what everything was checked AGAINST — the one number that is ours to state.
  // THE ANSWER FIRST, then what you have, then the evidence.
  const flagged = results.filter(flaggedRow).length;
  let out = "\n  " + bold("tashan doctor") + dim(index
    ? ` · ${index.records.toLocaleString("en-US")} capabilities measured ${index.date} · npm, GitHub, OSV, MCP registry`
    : " · checked against the tashan index") + "\n";
  out += "  " + (flagged
    ? red(`${flagged} need${flagged === 1 ? "s" : ""} attention`)
    : jade("Nothing you run is deprecated, archived or abandoned.")) + "\n\n";
  out += renderInventory(inv);
  const nMeasured = new Set(results.filter(measured).map((r) => r.row.id)).size;
  if (rows.length) {
    out += "  " + bold("your stack") + dim(`  ${nMeasured} scored · score, standing in its category, the evidence behind it`) + "\n";
  }
  for (const { item, row, assessment, alts, use: u } of rows) {
    const t = row && row.tashan_score != null ? Math.round(row.tashan_score) : null;
    const tr = assessment.trend;
    const line = spark(tr && tr.values);
    out += "  " + (MARK[assessment.level] || " ") + " " + bold(pretty(item.name).padEnd(26).slice(0, 26)) +
      (t == null ? dim("  —") : trustStr(t)) +
      (line ? "  " + jade(line) + dim(" " + tr.direction) : "") +
      "  " + dim(standing(row) || `${item.client} · ${item.scope}`) + "\n";
    // One line of facts under the name: how much YOU use it, then why the directory scores it as it does.
    const bits = [];
    if (u) {
      bits.push(u.recent
        ? dim(item.type === "skill" ? `used · last ${u.last}` : `${u.calls.toLocaleString("en-US")} calls in 30 days`)
        : C("33")(item.type === "skill" ? "not used in 30 days" : "no calls in 30 days"));
    }
    for (const e of evidenceOf(row)) bits.push(dim(e));
    if (bits.length) out += "      " + bits.join(dim(" · ")) + "\n";
    for (const n of assessment.notes) {
      const txt = typeof n === "string" ? n : n.text;
      if (/^can reach:/.test(txt)) continue;                                   // summed once, below
      if (n.trend && line && n.level !== "alert" && n.level !== "warn") continue;  // the sparkline says it
      out += "      " + dim("↳ ") + (n.level === "alert" ? red(txt) : dim(txt)) + "\n";
    }
    // WHICH advisory, and what the install script actually runs — directly under the finding that
    // names it, for everyone, with no key and no request. This used to come from /api/security with
    // a licence header while the website printed the identical facts to any visitor: the same
    // product answering the same question two ways depending on the surface. Now it is read straight
    // off `row`, which for doctor is the public lookup record.
    // sec_permissions is deliberately NOT repeated here — assess() already emits "can reach: …" from
    // the same row, free, and printing it twice would read as two separate findings.
    for (const adv of advisoriesOf(row)) {
      out += "      " + jade("→ ") + bold(adv.id) +
        dim(`  ${(adv.severity || "").toLowerCase()}`) +
        (adv.fixed ? dim(" · fixed in ") + jade(adv.fixed) : dim(" · no fix published")) + "\n";
    }
    const script = installScriptOf(row);
    if (script) out += "      " + jade("→ ") + dim("install runs: ") + script + "\n";
    if (alts && alts.length) {
      if (pro) {
        for (const a of alts) {
          out += "      " + jade("→ ") + bold(pretty(a.cap.name)) +
            dim(`  ${Math.round(a.score)}/100 · ${a.cap.vitality || "—"}`) + "\n";
        }
      } else {
        out += "      " + jade("→ ") + dim(`${alts.length} alternative${alts.length === 1 ? "" : "s"} measured better · `) +
          jade("tashan Pro") + dim(" $6/mo — tashan.sh/pricing") + "\n";
      }
    }
  }
  for (const p of problems) out += "  " + red("!") + " " + bold("config unreadable") + dim("  " + p.path) + "\n";

  // WHAT IT CAN REACH, summed once for the whole stack instead of repeated under every row.
  const reach = reachOf(results);
  const kinds = Object.keys(reach.perms).sort();
  if (kinds.length || reach.remote.length) {
    out += "\n  " + bold("what it can reach") +
      dim("  declared by each package's dependencies · nothing executed, so it can under-report") + "\n";
    for (const k of kinds) out += "    " + k.padEnd(12) + dim(reach.perms[k].join(", ")) + "\n";
    if (reach.remote.length) {
      out += "    " + C("33")(String(reach.remote.length)) +
        dim(` can bring third-party text into your model's context: ${reach.remote.join(", ")}`) + "\n";
    }
  }

  // WHAT CHANGED for what you run — the consequential events /changes.html dates, never a release.
  const moved = recentOf(results);
  if (moved.length) {
    out += "\n  " + bold("changed in the last 30 days") + dim("  " + SITE + "/changes.html") + "\n";
    for (const e of moved) out += "    " + dim(e.at) + "  " + bold(e.name) + dim(" — " + e.what) + "\n";
  }

  // WHAT YOU USE. The question about a big pile that always has an answer, and that only this machine
  // can answer: which of it you actually call. Claude Code only — see inventory.usage().
  if (use && use.available) {
    const cc = results.filter((r) => r.item.type === "server" && r.use);
    const called = cc.filter((r) => r.use.calls).sort((a, b) => b.use.calls - a.use.calls);
    const idle = [...new Set(cc.filter((r) => !r.use.calls).map((r) => pretty(r.item.name)))];
    const ownerOf = (s) => (inv && s.owner && (inv.plugins.find((p) => p.path === s.owner) || {}).name) || null;
    const sk = inv ? inv.skills.map((s) => usageOf({ type: "skill", name: s.name, plugin: ownerOf(s) }, use)).filter(Boolean) : [];
    const usedSk = sk.filter((x) => x.recent).length;
    out += "\n  " + bold("what you use") +
      dim(`  your Claude Code history, last ${use.days} days · read on this machine, nothing uploaded`) + "\n";
    if (cc.length) {
      out += "    " + `${called.length} of ${cc.length} servers called` + dim(called.length
        ? "  " + called.slice(0, 4).map((r) => `${pretty(r.item.name)} ${r.use.calls.toLocaleString("en-US")}`).join(" · ")
        : "") + "\n";
    }
    if (idle.length) {
      out += "    " + C("33")(`${idle.length} not called once: `) + dim(idle.join(", ")) + "\n" +
        "    " + dim("each still starts with every session it is configured for · claude mcp remove <name>") + "\n";
    }
    if (sk.length) {
      out += "    " + `${usedSk} of ${sk.length} skills used` +
        dim(sk.length > usedSk ? ` · the other ${sk.length - usedSk} are still listed to the model at session start` : "") + "\n";
    }
  }

  // ONE NUMBER for the pile no public record describes, said as a fact about those items rather than
  // an apology about us: "68 of these we have no evidence about yet" put our gap in the reader's report.
  const unmeasured = (sum.unrated || 0) + (sum.unknown || 0);
  if (sum.warn) out += "\n  " + dim(`${sum.warn} worth a look`) + "\n";
  if (unmeasured && !verbose) {
    out += "\n  " + dim(`${unmeasured} more have no public score — your own, local, or not yet rated · --all lists them`) + "\n";
  }
  // The rule for what is offered, and when, lives in offerFor() where the test can reach it.
  const offer = offerFor(results, keyState);
  if (offer && offer.kind === "replacement") {
    out += "\n  " + dim(`${offer.n} of these ${offer.n === 1 ? "has" : "have"} a measured replacement behind a licence — `) +
      dim("the one to move to, and whether anything else here is on the way down.") + "\n" +
      "  " + jade("tashan Pro") + dim(" $6/mo · " + SITE + "/pricing") +
      dim("  ·  already bought? ") + jade("tashan login") + "\n";
  } else if (offer) {
    out += "\n  " + jade("tashan Pro") +
      dim(` $6/mo · the daily score series behind these ${offer.n}, drawn beside each one, and the`) + "\n" +
      "  " + dim("measured replacement when one of them dies. 7 days free · " + SITE + "/pricing · already bought? ") +
      jade("tashan login") + "\n";
  }
  // Say the subscription state out loud, every run. Silence is what makes someone wonder.
  if (keyState === "active") {
    const series = results.filter((r) => r.assessment.trend && (r.assessment.trend.values || []).length > 1).length;
    out += "\n  " + jade("Pro") + dim(` · licence active — ${series} score series read, ` +
      (results.some((r) => r.alts && r.alts.length) ? "replacements named above" : "nothing in your stack needs replacing")) + "\n";
  }
  else if (keyState === "deactivated")
    out += "  " + red("This device was deactivated") +
           dim(" — your subscription is fine; run `tashan activate <key>`") + "\n";
  else if (keyState === "invalid") out += "  " + red("Pro key not valid") + dim(" — check " + PORTAL) + "\n";
  else if (keyState === "unknown") out += dim("  Pro · could not reach tashan to check your licence") + "\n";
  // "local only — nothing was uploaded" was printed on every run forever. A privacy promise is
  // worth making once, to someone deciding whether to trust the tool; repeated daily it is furniture.
  // It lives in the README and in doctor.mjs's header where the claim can actually be checked.
  return out;
}

// The commands that actually read the Index. `doctor` is in the set because it falls back to
// match(item, rows) when the compact lookup is unavailable.
export const NEEDS_INDEX = new Set(["search", "top", "info", "add", "doctor"]);

export async function main(argv) {
  const a = parseArgs(argv);
  // NO ARGUMENT MEANS DOCTOR. `npx tashan-cli` used to print the menu, which is what you show
  // somebody who already knows what the tool is. doctor is the only command that needs no argument,
  // it is the reason to install this, and it turns a stranger into a user in one keystroke.
  const cmd = a._[0] || "doctor";
  if (cmd === "help" || cmd === "--help" || cmd === "-h") { process.stdout.write(USAGE + "\n"); return 0; }
  // `--version` answered "unknown command" in every form up to 0.1.4. It is the first thing anyone
  // types at a new CLI and the first thing a bug report asks for, and getting an error for it reads
  // as a broken install. Read from package.json so it can never drift from what npm published.
  if (cmd === "--version" || cmd === "-v" || cmd === "version") {
    process.stdout.write(VERSION + "\n"); return 0;
  }

  // Only the commands that read the Index download it. `activate`, `account` and `mcp` do not touch
  // a single row, and downloading ~1 MB before dispatching meant activating Pro FAILED CLOSED on any
  // machine that could not reach /data/index.json — with "fetch failed" and no clue which fetch. A
  // customer whose licence email has just arrived is exactly the person least able to diagnose that.
  let rows = [];
  if (NEEDS_INDEX.has(cmd)) {
    try { rows = rowsOf(await loadData()); }
    catch (e) { process.stderr.write(red("  " + e.message) + "\n"); return 1; }
  }

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
    let r = find(rows, arg);
    // THE BOARD IS NOT THE INDEX OF EVERYTHING, AND THIS IS THE QUERY THAT MATTERS MOST.
    // search/top read index.json — the ranked board — and a capability that is deprecated,
    // delisted or malicious loses its score and drops off it. Those are exactly the ones somebody
    // types into `tashan info`: they were told to install it and want to know if it is safe.
    // `tashan info @modelcontextprotocol/server-github` answered "no capability matches" — a
    // package npm marks "no longer supported", which we measure, and which lookup.json carries
    // for precisely this reason. Falling back to the lookup turns the most valuable question the
    // CLI can be asked from a dead end into the warning it exists to give.
    // AND THE CARD NEEDS THE LOOKUP EVEN WHEN THE BOARD HAS THE ROW. The board is sized for a page's
    // first paint and carries none of what makes a verdict checkable — publisher, provenance, standing,
    // reach, what changed — so `info` read like a stub for exactly the capabilities people look up
    // most. `add` only ever needed the fallback.
    if (!r || cmd === "info") {
      try {
        const lk = await loadLookup();
        if (!r) r = find(lk.records || [], arg);
        else {
          const i = lk.keys ? lk.keys[String(r.id).toLowerCase()] : undefined;
          if (i !== undefined && lk.records[i] && lk.records[i].id === r.id) r = { ...r, ...lk.records[i] };
        }
      } catch { /* offline: the board row, or the message below, is still the right answer */ }
    }
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
  if (cmd === "login") return deviceLogin({ open: !a["no-browser"] });

  // `logout` is what everyone types. It was only ever spelled `activate --forget`, which is a flag
  // on a different verb — nobody guesses it, so nobody released a seat and device slots leaked.
  if (cmd === "logout") a.forget = true;

  if (cmd === "activate" || cmd === "logout") {
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
          dim("\n  tashan activate --forget releases the seat · tashan account lists every device")
        : bold("This machine is not activated.") +
          dim("\n  tashan login") + dim("   approve it in the browser — no key to copy") +
          dim("\n  tashan activate <key>   if you are in CI and have no browser")) + "\n");
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
      dim(`\n  registered as "${label}" — tashan account shows every device`) +
      dim(`\n  stored in ${keyPath()} · every shell, every project, no re-export`) +
      dim("\n\n  tashan doctor") + "\n");
    return 0;
  }

  if (cmd === "account") {
    const lic = resolveLicence(a);
    if (!lic) {
      process.stdout.write("\n  " + bold("No licence on this machine.") +
        dim("\n  tashan login   sign in — no key to copy") +
        dim("\n  " + SITE + "/pricing   what Pro adds · the index stays free") + "\n");
      return 1;
    }
    // The terminal already proved who we are, so the browser inherits it — same handoff as
    // `gh auth login` and `stripe login`. The one-time token is not a credential and expires in two
    // minutes, which is why it may ride in a URL where the licence key never could.
    let out;
    try {
      const r = await fetch(SITE + "/api/account", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ key: lic.key }),
      });
      out = r.ok ? await r.json().catch(() => null) : null;
      if (!out) {
        process.stderr.write("\n  " + red(r.status === 403 ? "That licence is not valid." : "Could not sign in.") +
          dim("\n  Open your account directly: " + PORTAL + "\n"));
        return 1;
      }
    } catch {
      process.stderr.write("\n  " + red("Offline — could not reach " + SITE + ".") +
        dim("\n  Your licence still works locally; tashan doctor runs without a network.\n"));
      return 1;
    }
    const url = out.url || SITE + "/account";
    const opened = openBrowser(url);
    process.stdout.write("\n  " + jade("Opening your account…") +
      dim(`\n  ${out.email || "signed in"}${out.active ? " · Pro active" : ""}`) +
      dim(`\n  ${opened ? "" : "Open this link: "}${url}`) +
      (out.handoff === false ? dim("\n  (one-time sign-in is unavailable, so this opens the page as-is)") : "") +
      "\n");
    return 0;
  }

  if (cmd === "doctor") {
    const { found, problems } = collect(configLocations(), skillLocations());
    // THE AUDIT SEES WHAT THE INVENTORY SEES. collect() reads the top-level config and THIS directory's
    // project file, while the inventory already walked every project in ~/.claude.json and every
    // installed plugin — so doctor counted 12 servers and 11 plugins, then scored neither the project
    // servers nor a single plugin. Both are audited now: a project server by what its entry launches,
    // a plugin by the home its marketplace manifest names, never by a name several plugins share.
    let s = null;
    try { s = scan(); } catch { /* the inventory is an addition; doctor's findings must never depend on it */ }
    if (s) {
      for (const sv of s.servers) {
        if (sv.scope !== "project") continue;               // the top-level block is already in `found`
        found.push({ type: "server", client: "Claude Code", scope: basename(sv.project || "") || "project",
                     name: sv.name, path: join(homedir(), ".claude.json"), ...(identify(sv.entry) || {}) });
      }
      for (const p of s.plugins) {
        found.push({ type: "plugin", client: "Claude Code", scope: p.marketplace || "local", name: p.name,
                     kind: "plugin", id: p.id, path: p.path });
      }
    }
    const lic = resolveLicence(a);
    const key = lic ? lic.key : null;
    const keyState = await verifyLicence(lic);
    let lookup = null;
    try { lookup = await loadLookup(); } catch { /* fall back to the board rather than failing */ }
    // match() resolves by name, which is exactly how a plugin lands on a stranger — no lookup, no plugin row.
    const look = (item) => (lookup ? resolve(item, lookup) : item.kind === "plugin" ? null : match(item, rows));
    // WHAT YOU USE, from Claude Code's own records on this machine — see inventory.usage().
    let use = null;
    try { use = usage(); } catch { /* usage is an addition, never a reason doctor fails */ }
    let results = found.map((item) => {
      const row = look(item);
      return { item, row, assessment: assess(item, row), use: usageOf(item, use) };
    });

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
    if (a.trend && !key) {
      process.stderr.write(red("  that needs a licence key — run: tashan activate <key> "
        + "(tashan Pro, $6/mo — https://tashan.sh/pricing)") + "\n");
      return 0;
    }
    // THE SERIES IS WHAT THE LICENCE BUYS, so a licence gets it without having to know a flag. A paying
    // customer whose run looked identical to a free one is the "did my payment even work" ticket, and
    // --trend was the only way to see a single point of what they paid for.
    if (key && (a.trend || keyState === "active")) results = await withTrends(results, lic);

    const sum = summarize(results);

    // THE INVENTORY. Findings answer "is any of this dangerous"; this answers the question that
    // comes first once the pile is large — what do I have, what arrived since last time, and what
    // is nobody maintaining. It keeps a first-seen date locally because nothing on disk records one
    // for a skill. It reuses the scan above rather than walking every project a second time.
    let inv = null;
    if (s) {
      try {
        const today = new Date().toISOString().slice(0, 10);
        const items = [...s.servers, ...s.plugins, ...s.skills];
        const before = loadLedger();
        const firstRun = Object.keys(before.seen || {}).length === 0;
        const { ledger, fresh, gone } = reconcile(before, items, today);
        saveLedger(ledger);
        // On the first run everything is "new", which is true and useless. Say so instead.
        inv = { ...s, fresh, gone, first: firstRun };
      } catch { /* the inventory is an addition; doctor's findings must never depend on it */ }
    }

    const index = lookup
      ? { records: (lookup.records || []).length, date: String(lookup.generated_at || "").slice(0, 10) }
      : null;
    if (a.json) {
      process.stdout.write(JSON.stringify({
        summary: sum, inventory: inv, problems, results, index,
        reach: reachOf(results), changes: recentOf(results, 100),
        usage: use && { since: use.since, days: use.days, available: use.available, servers: use.servers },
      }, null, 2) + "\n");
      return 0;
    }
    process.stdout.write(renderDoctor(results, problems, sum, keyState === "active", a.all, keyState, inv, index, use) + "\n");
    return sum.alert > 0 ? 2 : 0;      // nonzero exit when something needs attention, so it can gate CI
  }
  process.stderr.write(red(`  unknown command: ${cmd}`) + "\n" + USAGE + "\n");
  return 1;
}

// entrypoint (skip when imported by the test)
import { fileURLToPath } from "node:url";

// IS THIS FILE THE ENTRY POINT? Compare REAL paths, not the strings.
//
// npm installs a bin as a SYMLINK — node_modules/.bin/tashan -> ../tashan-cli/tashan.mjs — so
// process.argv[1] is the link and import.meta.url resolves to the target. A plain === between them
// is false for every npm install, which meant main() never ran: `tashan --help` exited 0 and printed
// NOTHING. Running the file directly by path worked, so every local test passed and the published
// package would have done nothing at all. Caught only by installing the packed tarball.
function isEntry(metaUrl) {
  if (!process.argv[1]) return false;
  try {
    return realpathSync(process.argv[1]) === realpathSync(fileURLToPath(metaUrl));
  } catch {
    return process.argv[1] === fileURLToPath(metaUrl);
  }
}

// EXIT CODE WITHOUT TRUNCATING THE OUTPUT. `process.exit()` does not wait for stdout to drain, and
// when stdout is a PIPE node buffers it asynchronously — so `doctor --json | jq` was cut at the
// 64 KiB pipe buffer and handed the caller unparseable JSON with exit status 0. A terminal hid it
// completely (stdout to a TTY is synchronous on POSIX) and so did `> file`, which is how it survived:
// it only appeared through the pipe, which is the one arrangement /start.html actually tells people
// to use ("Add --json to pipe it"), and only on a machine with enough rows to pass 64 KiB. Truncated
// output plus a success code is the worst pair — a script reads garbage and never learns it did.
//
// Setting exitCode lets node finish flushing and leave on its own. The explicit exit stays behind a
// 'beforeExit' hook: if a stray timer or open handle would hold the process open, we still leave with
// the right status, but only once the event loop has nothing left to do and the write has landed.
if (isEntry(import.meta.url)) {
  main(process.argv.slice(2)).then((code) => {
    process.exitCode = code || 0;
    process.once("beforeExit", () => process.exit(process.exitCode || 0));
  });
}
