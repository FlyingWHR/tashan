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
import { PRICED, configured, paymentRequired, requiredHeader, paymentFrom, charge, responseHeader }
  from "../api/_x402.js";

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

export const onRequestGet = () => json({
  error: "POST a JSON body to this endpoint",
  usage: {
    method: "POST",
    body: { task: "web-scraping", client: "claude-code", limit: 5 },
    tasks: "https://tashan.sh/data/tags.json",
    free: "The ranked shortlist for the task, with every risk. No account, no payment.",
    paid: "The assembled kit: the version to pin, checked clean at that version; a ready-to-paste "
        + "config for your host; the direction of travel behind each pick; and why each beat the "
        + "rest. Licence, or per call with x402.",
    not_sold: "We do not sell skill or server content. Each pick links to its own source and "
            + "licence — fetch it from the author.",
  },
}, 400);

// Hosts differ in where the file lives, but the stanza shape is the same everywhere that matters.
const CLIENTS = {
  "claude-code": { file: "~/.claude.json", key: "mcpServers" },
  "claude-desktop": { file: "claude_desktop_config.json", key: "mcpServers" },
  cursor: { file: "~/.cursor/mcp.json", key: "mcpServers" },
  vscode: { file: ".vscode/mcp.json", key: "servers" },
  windsurf: { file: "~/.codeium/windsurf/mcp_config.json", key: "mcpServers" },
};

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

export async function onRequestPost({ request, env }) {
  let body;
  try { body = await request.json(); } catch { return json({ error: "body must be JSON" }, 400); }

  const task = String((body && body.task) || "").trim().toLowerCase();
  if (!task) return json({ error: 'pass {"task": "<slug>"} — slugs at https://tashan.sh/data/tags.json' }, 400);
  const client = CLIENTS[String((body && body.client) || "claude-code")] ? body.client : "claude-code";
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
    shortlist: picks.map((r) => ({
      id: r.id, name: r.name, label: r.label,
      tashan_score: r.tashan_score ?? null,
      vitality: r.vitality || null,
      expertise: r.expertise_verdict || null,
      because: because(r),
      risks: risksOf(r),
      source: r.npm_pkg ? "https://www.npmjs.com/package/" + r.npm_pkg : null,
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
    const out = await charge(env, pr, payment, assemble);
    if (!out.ok) return json({ ...pr, error: "payment " + out.reason }, 402, requiredHeader(pr));
    return json(out.result, 200, responseHeader(out.settlement));
  }

  return json({
    ...(pr || {}),
    error: "payment required to assemble the kit",
    free_result: free,
    plans: OFFER.plans,
    credential: { header: "Authorization: Bearer <licence-key>", obtain: "https://tashan.sh/pricing" },
    docs: "https://tashan.sh/pricing",
  }, 402, { ...requiredHeader(pr), link: '<https://tashan.sh/pricing>; rel="payment"' });
}
