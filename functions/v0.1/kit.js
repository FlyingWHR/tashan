// Cloudflare Pages Function — POST /v0.1/kit
//
// THE THING AN AGENT WILL ACTUALLY PAY FOR. An agent told "set this user up for web scraping" faces
// 12,000 capabilities, no way to tell a maintained one from an abandoned one, and no way to know
// which version it should pin today. It does not want a score. It wants: install these, at these
// versions, here is the config, here is why, here is what to avoid. That is one request, it is worth
// real money once, and it is exactly what we are in a position to assemble.
//
// ==================================================================================================
// WHAT WE SELL, AND WHAT WE WILL NOT.
//
// We do NOT sell skill or server CONTENT. A skill is a folder in somebody else's repository under
// their own licence; charging an agent for its text would be reselling third-party work, and no
// amount of it being convenient makes that ours to do. Every capability here is linked to its own
// source and its own licence, and the agent fetches it from the author.
//
// What IS ours: the measurement, the SELECTION over it, the version that is clean TODAY, and the
// assembled config. That is synthesis and tooling — the two things the firewall has always allowed
// payment for — and it is the part an agent cannot derive without us.
// ==================================================================================================
//
// THE FREE/PAID LINE, same as everywhere: the shortlist and every risk are free, because the ranked
// table behind them is a public page and a paywall over a published fact is theatre. What payment
// buys is the assembly: pinned versions checked clean at that version, the host-specific config
// block, the direction of travel behind each pick, and the reason each one beat the others.

import { validate, keyFrom, activationFrom, OFFER } from "../api/_license.js";
import { headOf } from "../api/_head.js";
import { PRICED, configured, paymentRequired, requiredHeader, paymentFrom, charge, responseHeader }
  from "../api/_x402.js";
import { demand } from "../api/_demand.js";

const PRICE_KEY = "capability-kit";
const MAX_PICKS = 8;

const json = (body, status = 200, extra = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "access-control-allow-origin": "*",
      "cache-control": "no-store",
      ...extra,
    },
  });

export const onRequestOptions = () =>
  new Response(null, { status: 204, headers: {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "POST, OPTIONS",
    "access-control-allow-headers": "content-type, authorization, payment-signature, x-tashan-activation",
  } });

// A NAKED GET IS HOW DISCOVERY FINDS US, and it used to answer 400 with no payment terms at
// all — so every x402 crawler and directory that probes a URL concluded this was not a paid
// endpoint. Two of our three priced resources were invisible to the entire discovery layer,
// which is the layer the wallets are on.
//
// It answers 402 with spec-shaped `accepts` now, carrying the same usage block it always did.
// That is not a claim that everything here costs money — the body says which half is free, in
// the same breath — it is the correct status for a resource that HAS a price, and the one
// machines look for.
export const onRequestGet = ({ request, env } = {}) => {
  // Defaults because a handler that throws when called bare is a footgun: the Pages
  // runtime always passes context, tests and probes do not always bother.
  const origin = request ? new URL(request.url).origin : "https://tashan.sh";
  const pr = paymentRequired(env, PRICE_KEY, origin + "/v0.1/kit");
  demand(env, request, "quoted", PRICE_KEY, "get-probe");
  return json({ ...pr,
  error: "POST a JSON body to this endpoint",
  usage: {
    method: "POST",
    body: { task: "web-scraping", client: "claude-code", limit: 5 },
    or: { goal: "I need to scrape websites", client: "claude-code" },
    tasks: "https://tashan.sh/data/tags.json",
    free: "The ranked shortlist for the task, with every risk. No account, no payment.",
    paid: "The assembled kit: the version to pin, checked clean at that version; a ready-to-paste "
        + "config for your host; the direction of travel behind each pick; and why each beat the "
        + "rest. Licence, or per call with x402.",
    not_sold: "We do not sell skill or server content. Each pick links to its own source and "
            + "licence — fetch it from the author.",
  },
}, 402, { ...requiredHeader(pr), link: '<https://tashan.sh/pricing>; rel="payment"' });
};

// Hosts differ in where the file lives, but the stanza shape is the same everywhere that matters.
const CLIENTS = {
  "claude-code": { file: "~/.claude.json", key: "mcpServers" },
  "claude-desktop": { file: "claude_desktop_config.json", key: "mcpServers" },
  cursor: { file: "~/.cursor/mcp.json", key: "mcpServers" },
  vscode: { file: ".vscode/mcp.json", key: "servers" },
  windsurf: { file: "~/.codeium/windsurf/mcp_config.json", key: "mcpServers" },
};

/** Where the caller can get it — the author's own home, never our page. */
function sourceOf(r) {
  if (r.npm_pkg) return "https://www.npmjs.com/package/" + r.npm_pkg;
  if (r.source_repo) return "https://github.com/" + r.source_repo;
  return null;
}

/** What kind of install this is. `mcp-server` is the only one an mcpServers config can express. */
function installVia(r) {
  if (r.npm_pkg) return "mcp-server";
  if (r.remote_host) return "remote";
  if (r.id.startsWith("plugin:")) return "claude-plugin";
  if (r.id.startsWith("skill:")) return "agent-skill";
  return "unknown";
}

/** Why this one, in the caller's terms — assembled from the row's own measured columns. */
function because(r) {
  const w = [];
  if (r.tashan_score != null) w.push(`scores ${Math.round(r.tashan_score)}`);
  if (r.vitality) w.push(r.vitality);
  if (r.expertise_verdict) w.push(`${r.expertise_verdict} documentation`);
  if (r.sec_provenance) w.push("built in CI with attestation");
  if (r.npm_downloads) w.push(`${Number(r.npm_downloads).toLocaleString("en-US")} weekly installs`);
  return w.join(" · ");
}

function risksOf(r) {
  const f = [];
  if (r.sec_advisory_count) f.push(`${r.sec_advisory_count} advisory at the installable version`);
  if (r.npm_deprecated) f.push("deprecated by its author");
  if (r.gh_archived) f.push("repository archived");
  if (r.single_maintainer) f.push("one maintainer");
  if (r.registry_status === "deleted") f.push("removed from the MCP registry");
  if (r.sec_remote_content) f.push("can carry third-party text into context");
  return f;
}


/**
 * Resolve free text to a task slug — because an agent says "I need to scrape websites", not
 * "web-scraping".
 *
 * Requiring the caller to already know our slugs makes the paid endpoint useless to exactly the
 * caller it was built for: an agent that has never seen this API, holding a sentence from a user.
 * It could fetch /data/tags.json and do this itself, but that is a round trip and a mapping problem
 * we are better placed to solve — we own the vocabulary.
 *
 * Scored, not first-match: a synonym hit is worth more than a label word, and longer phrases beat
 * shorter ones because "web scraping" is diagnostic where "web" alone is not — the same reasoning
 * pipeline/tag_capabilities.py::_terms already applies to matching prose. Returns null rather than
 * guessing when nothing clears the floor: a wrong kit is worse than an honest "name the job".
 */
function resolveGoal(tasks, goal) {
  const g = " " + String(goal || "").toLowerCase().replace(/[^a-z0-9+#. ]+/g, " ").replace(/\s+/g, " ").trim() + " ";
  if (g.trim().length < 3) return null;
  // "scrape" must match the synonym "scraping". pipeline/tag_capabilities.py stems for exactly this
  // reason; without it the most natural phrasing a user would type misses every time.
  // The trailing -e matters: "scraping" -> "scrap" but "scrape" -> "scrape" without it, and the
  // most natural way to ask for this ("I need to scrape websites") would miss every time.
  const stem = (w) => w.replace(/(ing|ers|er|ed|es|s)$/, "").replace(/e$/, "");
  const words = new Set(g.trim().split(" ").filter((w) => w.length > 2).map(stem));
  let best = null, bestScore = 0;
  for (const t of tasks) {
    let score = 0;
    const label = String(t.label || "").toLowerCase();
    const phrases = [label, String(t.slug || "").replace(/-/g, " "), ...(t.synonyms || [])];
    for (const raw of phrases) {
      const p = String(raw || "").toLowerCase().trim();
      if (p.length < 3) continue;
      // A whole phrase present verbatim is the strongest signal, weighted by how specific it is:
      // "web scraping" is diagnostic where "web" alone is not.
      if (g.includes(" " + p + " ")) { score += 2 + p.split(" ").length; continue; }
      // Otherwise, how much of the phrase survives as stems in the sentence.
      const parts = p.split(" ").filter((w) => w.length > 2).map(stem);
      // Scored the same as a verbatim hit: every word of the phrase IS present, just inflected.
      // At 1 + parts.length a lone distinctive synonym scored 2 and fell under the floor, so
      // "scrape websites" resolved to nothing while "web scraping" resolved fine.
      if (parts.length && parts.every((w) => words.has(w))) score += 2 + parts.length;
    }
    if (score > bestScore) { bestScore = score; best = t.slug; }
  }
  // Below the floor we say so rather than guess: a wrong kit is worse than "name the job".
  return bestScore >= 3 ? best : null;
}

export async function onRequestPost({ request, env }) {
  let body;
  try { body = await request.json(); } catch { return json({ error: "body must be JSON" }, 400); }

  let task = String((body && body.task) || "").trim().toLowerCase();
  let resolved_from = null;
  if (!task && body && body.goal) {
    try {
      const tr = await fetch(new URL(request.url).origin + "/data/tasks.json",
                             { cf: { cacheTtl: 300, cacheEverything: true } });
      if (tr.ok) {
        const td = await tr.json();
        const hit = resolveGoal(td.tasks || td, body.goal);
        if (hit) { task = hit; resolved_from = String(body.goal); }
      }
    } catch { /* fall through to the 400 below, which names the alternative */ }
  }
  if (!task) {
    return json({
      error: body && body.goal
        ? 'could not match that goal to a job we measure — pass {"task": "<slug>"} instead'
        : 'pass {"task": "<slug>"} or {"goal": "what you are trying to do"}',
      tasks: "https://tashan.sh/data/tags.json",
    }, 400);
  }
  // THE DEFAULT HAD TO BE THE ASSIGNED VALUE, NOT JUST THE TESTED ONE. This read
  //     CLIENTS[String(body.client || "claude-code")] ? body.client : "claude-code"
  // so with no `client` in the body the lookup succeeded on the fallback string and then assigned
  // `body.client` — undefined. Every later read of CLIENTS[client] was undefined, and assemble()
  // threw on `c.file`. It could only ever surface on the PAID path, because the free and 402 paths
  // never assemble, so the first customer to actually pay would have got a 500.
  const asked = String((body && body.client) || "");
  const client = CLIENTS[asked] ? asked : "claude-code";
  const limit = Math.min(Math.max(parseInt(body && body.limit, 10) || 5, 1), MAX_PICKS);

  const origin = new URL(request.url).origin;
  let tags, lookup;
  try {
    const [a, b] = await Promise.all([
      fetch(origin + "/data/tags.json", { cf: { cacheTtl: 300, cacheEverything: true } }),
      fetch(origin + "/data/lookup.json", { cf: { cacheTtl: 300, cacheEverything: true } }),
    ]);
    if (!a.ok || !b.ok) throw new Error("tags " + a.status + " lookup " + b.status);
    tags = await a.json();
    lookup = await b.json();
  } catch (e) {
    return json({ error: "measurement data unavailable", detail: String(e) }, 502);
  }

  const ids = (tags.tasks || {})[task];
  if (!ids || !ids.length) {
    return json({ task, measured: false,
                  error: "no capabilities mapped to that task yet",
                  tasks: origin + "/data/tags.json" }, 404);
  }
  const byId = new Map(lookup.records.map((r) => [r.id, r]));
  // Rank the way the site does — score first — then drop anything we would tell a human to replace.
  // Shipping a kit that installs a package with a live advisory would make the whole artifact
  // worthless, and it is the one mistake an agent cannot check for us.
  const rows = ids.map((i) => byId.get(i)).filter(Boolean);
  const safe = rows.filter((r) => !r.sec_advisory_count && !r.npm_deprecated && !r.gh_archived
                                  && r.registry_status !== "deleted");
  const excluded = rows.filter((r) => !safe.includes(r) && risksOf(r).length)
    .slice(0, 10)
    .map((r) => ({ id: r.id, name: r.name, why_not: risksOf(r) }));
  const picks = safe
    .sort((a, b) => (b.tashan_score || 0) - (a.tashan_score || 0))
    .slice(0, limit);

  const free = {
    task,
    // Echoed so a caller can see WHICH job we matched their sentence to, and disagree.
    ...(resolved_from ? { resolved_from } : {}),
    shortlist: picks.map((r) => ({
      id: r.id, name: r.name, label: r.label,
      tashan_score: r.tashan_score ?? null,
      vitality: r.vitality || null,
      expertise: r.expertise_verdict || null,
      because: because(r),
      risks: risksOf(r),
      source: sourceOf(r),
      // HOW IT IS INSTALLED, because not everything on a shelf goes in an mcpServers block. A
      // plugin is added through a marketplace and a skill is a folder you drop in — neither is a
      // command a host can launch — so a config assembled from them would be silently short.
      install_via: installVia(r),
      ...(r.slug ? { measurement: origin + "/capability/" + r.slug + ".html" } : {}),
    })),
    // NAMED, NOT HIDDEN. What we left out and why is the most useful half of a recommendation, and
    // it is a risk, so it is free.
    excluded,
    counts: { mapped: rows.length, eligible: safe.length, returned: picks.length },
    generated_at: lookup.generated_at,
    scorer: lookup.scorer,
    method: origin + "/methodology.html",
    licence: "Each capability is its own author's work under its own licence. We do not redistribute "
           + "their content; every pick links to its source. What tashan publishes is the "
           + "measurement, under CC BY 4.0.",
    note: "Every score and every risk above is free and needs no account. Nothing purchasable moves "
        + "a score, a rank or a listing.",
  };

  const assemble = async () => {
    const c = CLIENTS[client];
    const servers = {};
    for (const r of picks) {
      if (!r.npm_pkg) continue;
      const pin = r.npm_latest_version ? `${r.npm_pkg}@${r.npm_latest_version}` : r.npm_pkg;
      servers[(r.name || r.npm_pkg).replace(/^@[^/]+\//, "").replace(/[^a-zA-Z0-9_-]/g, "-")] = {
        command: "npx",
        args: ["-y", pin],
      };
    }
    return {
      ...free,
      kit: {
        client,
        // EVERY PICK IS ACCOUNTED FOR. The config can only express servers, so the rest are listed
        // here with how they are actually installed. Returning a five-row shortlist and a two-row
        // config without saying why is the kind of silent shortfall a paid artifact cannot have.
        not_in_config: picks.filter((r) => installVia(r) !== "mcp-server").map((r) => ({
          id: r.id, name: r.name, install_via: installVia(r), source: sourceOf(r),
          say: installVia(r) === "claude-plugin"
            ? "A Claude Code plugin — added from its marketplace, not an mcpServers entry."
            : installVia(r) === "agent-skill"
              ? "An agent skill — a folder you place in .claude/skills/, not an mcpServers entry."
              : "Served over HTTP — connect to the host below rather than launching a command.",
        })),
        // The pin is the point. "latest" resolves to whatever ships tomorrow, and the advisory scan
        // that cleared this package ran against THIS version — so an unpinned config is an
        // unverified one, and the verification is what was paid for.
        pinned: picks.filter((r) => r.npm_pkg).map((r) => ({
          id: r.id,
          install: r.npm_latest_version ? `${r.npm_pkg}@${r.npm_latest_version}` : r.npm_pkg,
          version_checked: r.npm_latest_version || null,
          advisories_at_that_version: r.sec_advisory_count || 0,
          scanned_at: r.sec_scanned_at || null,
          build_provenance: Boolean(r.sec_provenance),
        })),
        config_file: c.file,
        config: { [c.key]: servers },
        remote_alternatives: picks.filter((r) => r.remote_host)
          .map((r) => ({ id: r.id, host: r.remote_host })),
      },
    };
  };

  if (!body.kit) {
    return json({
      ...free,
      kit_available: {
        how: 're-send with {"kit": true}',
        buys: "Versions pinned to the release the advisory scan actually cleared, a ready-to-paste "
            + "config for your host, and the remote alternatives where they exist.",
        pay: ["Authorization: Bearer <licence key> — "
              + OFFER.plans.map((p) => `$${p.amount}/${p.period}`).join(" or "),
              configured(env) ? `or per call with x402: $${PRICED[PRICE_KEY].usd}`
                              : "per-call x402: not yet enabled on this deployment"],
        start: "https://tashan.sh/pricing.html",
      },
    });
  }

  const key = keyFrom(request);
  if (key) {
    const v = await validate(env, key, activationFrom(request));
    if (!v.ok) return json({ error: v.why, docs: "https://tashan.sh/pricing" }, v.status || 403);
    return json(await assemble());
  }

  const pr = paymentRequired(env, PRICE_KEY, origin + "/v0.1/kit",
                             "payment required to assemble the kit");
  const payment = paymentFrom(request);
  if (pr && payment) {
    const out = await charge(env, pr, payment, assemble, request);
    if (!out.ok) return json({ ...pr, error: "payment " + out.reason }, 402, requiredHeader(pr));
    return json(out.result, 200, responseHeader(out.settlement));
  }

  demand(env, request, "quoted", "capability-kit");
  return json({
    ...(pr || {}),
    error: "payment required to assemble the kit",
    free_result: free,
    plans: OFFER.plans,
    credential: { header: "Authorization: Bearer <licence-key>", obtain: "https://tashan.sh/pricing" },
    docs: "https://tashan.sh/pricing",
  }, 402, { ...requiredHeader(pr), link: '<https://tashan.sh/pricing>; rel="payment"' });
}

// A probe that cannot HEAD this endpoint reports us down. See _head.js.
export const onRequestHead = headOf(onRequestGet);
