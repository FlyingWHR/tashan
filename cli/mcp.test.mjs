// node cli/mcp.test.mjs — protocol + rendering for the MCP server. No network.
import { handle, handshake, evidence, risks, renderFind, renderCheck, renderPaid, trendBlock } from "./mcp.mjs";
import assert from "node:assert";

const rpc = (method, params, id = 1) => handle({ jsonrpc: "2.0", id, method, params });

// ---- handshake ----
assert.strictEqual(handshake({ protocolVersion: "2099-01-01" }).protocolVersion, "2099-01-01",
  "echoes the client's protocol revision rather than pinning one");
assert.ok(handshake({}).protocolVersion, "falls back to a known revision when the client sends none");
assert.ok(/find_capability|check_capability/.test(handshake({}).instructions),
  "instructions tell the agent to consult tashan BEFORE installing");

// ---- protocol ----
const init = await rpc("initialize", { protocolVersion: "2025-06-18" });
assert.strictEqual(init.jsonrpc, "2.0"); assert.ok(init.result.serverInfo.name === "tashan");

const list = await rpc("tools/list");
const names = list.result.tools.map((t) => t.name).sort();
assert.deepStrictEqual(names, ["audit_config", "check_capability", "find_capability", "paid_demand"]);
for (const t of list.result.tools) {
  assert.ok(t.description.length > 40, `${t.name} needs a description an agent can route on`);
  assert.strictEqual(t.inputSchema.type, "object", `${t.name} schema must be an object`);
}

// A notification has no id and must NEVER get a reply — answering one corrupts the stream.
assert.strictEqual(await handle({ jsonrpc: "2.0", method: "notifications/initialized" }), null,
  "notifications are not answered");
assert.strictEqual(await handle({ jsonrpc: "2.0", method: "unknown/thing" }), null,
  "an unknown NOTIFICATION is still not answered");

const bad = await rpc("no/such/method");
assert.strictEqual(bad.error.code, -32601, "unknown request method -> method not found");

// A tool failure must come back as a readable result, not a protocol error, so the agent can relay it.
const boom = await rpc("tools/call", { name: "nope", arguments: {} });
assert.ok(boom.result.isError && /unknown tool/.test(boom.result.content[0].text),
  "tool errors are results with isError, not JSON-RPC errors");

// ---- evidence + risk rendering ----
const good = { id: "pkg:tavily-mcp", name: "tavily-mcp", npm_pkg: "tavily-mcp", tashan_score: 86,
               expertise_verdict: "solid", npm_downloads: 32517, vitality: "active", slug: "tavily-mcp" };
assert.ok(/86\/100/.test(evidence(good)) && /solid/.test(evidence(good)) && /32,517/.test(evidence(good)));
assert.strictEqual(evidence({ id: "x", name: "x" }), "no measurement yet",
  "an unmeasured capability says so rather than printing a fake zero");
assert.deepStrictEqual(risks(good), [], "a healthy capability has no risk lines");

const risky = { id: "pkg:x", name: "x", gh_archived: 1, npm_deprecated: 1,
                similar_official: "@modelcontextprotocol/server-git", single_maintainer: 1 };
const rs = risks(risky);
assert.ok(rs.some((r) => /ARCHIVED/.test(r)) && rs.some((r) => /DEPRECATED/.test(r)));
assert.ok(rs.some((r) => /similar name/.test(r)), "name-confusion is surfaced to the agent");
assert.ok(!rs.some((r) => /typosquat/i.test(r)),
  "never call it a typosquat — that is an accusation we cannot support");

// ---- find rendering ----
const out = renderFind([good], "search the web", "claude");
assert.ok(/tavily/.test(out) && /install \(claude\):/.test(out),
  "gives the agent a runnable install command, naming the target client");
assert.ok(/NOT a security audit/.test(out), "every find carries the not-an-audit caveat");
const empty = renderFind([], "underwater basket weaving", "claude");
assert.ok(/no evidence, not that nothing exists/.test(empty),
  "empty results say we have no evidence rather than implying nothing exists");

// ---- check rendering ----
assert.ok(/Risks found/.test(renderCheck(risky, "x")), "check surfaces risks");
assert.ok(/No deprecation/.test(renderCheck(good, "tavily-mcp")), "a clean check says so plainly");
assert.ok(/unmeasured, not necessarily bad/.test(renderCheck(null, "who-knows")),
  "an unknown capability is not reported as a warning");

console.log("ok — mcp server (protocol / evidence / risk / rendering)");

// ---- task routing: the funnel case. A person describes a JOB, not a package name. ----
{
  const { forTask, inferCategories, taskTokens } = await import("./mcp.mjs");
  const idx = [
    { id: "pkg:tavily-mcp", name: "tavily-mcp", category: "search", tashan_score: 86 },
    { id: "pkg:claude-seo", name: "claude-seo", category: "comms", tashan_score: 91 },
    { id: "pkg:slack-mcp", name: "slack-mcp", category: "comms", tashan_score: 44 },
    { id: "pkg:context7", name: "context7", category: "docs", tashan_score: 98 },
    { id: "pkg:pdf-toolkit-mcp", name: "pdf-toolkit-mcp", category: "docs", tashan_score: 52 },
    { id: "pkg:unrated", name: "unrated-thing", category: "docs", tashan_score: null },
  ];
  assert.deepStrictEqual(inferCategories("search the web").slice(0, 1), ["search"]);
  assert.ok(!taskTokens("I want to work with my PDFs").includes("work"), "noise words are dropped");

  // These exercise the FALLBACK path — no terms bag, so name matching only. Its contract is narrow
  // on purpose: it finds a capability NAMED for the task and admits defeat otherwise. The block below
  // covers the real path, where descriptions are matched and tavily wins "search the web".
  assert.strictEqual(forTask(idx, "send a slack message", 1)[0].name, "slack-mcp",
    "names the Slack tool, not the higher-scoring unrelated top of `comms`");
  assert.strictEqual(forTask(idx, "work with PDFs", 1)[0].name, "pdf-toolkit-mcp",
    "plural 'PDFs' still finds pdf-toolkit, and beats the higher-scoring context7");
  assert.deepStrictEqual(forTask(idx, "search the web", 1), [],
    "without descriptions it CANNOT find tavily — its name says nothing about searching, which is "
    + "precisely why lookup.json ships a token bag");
  assert.ok(!forTask(idx, "docs", 9).some((c) => c.tashan_score == null),
    "never recommends an unscored capability — we have no evidence for it");
  assert.deepStrictEqual(forTask(idx, "underwater basket weaving", 3), [],
    "no match returns nothing rather than the highest-scoring unrelated thing");
}
console.log("ok — mcp task routing");

// ---- the install handoff: what the agent is told to run ----------------------------------------
{
  const { renderFind } = await import("./mcp.mjs");
  const { installSnippets } = await import("./tashan.mjs");
  const cap = { id: "pkg:tavily-mcp", name: "tavily-mcp", npm_pkg: "tavily-mcp",
                tashan_score: 86, vitality: "active", slug: "tavily-mcp" };

  // A Cursor/Codex/Desktop snippet is a multi-line JSON or TOML stanza. The first version printed
  // only line one, so an agent following it would have written "[mcp_servers.tavily-mcp]" with no
  // command and no args into a user's real config file.
  for (const client of ["cursor", "codex", "desktop"]) {
    const out = renderFind([cap], "search the web", client);
    const src = installSnippets(cap, client)[0].cmd.split("\n");
    for (const line of src) {
      assert.ok(out.includes(line.trim()),
        `${client}: the snippet line ${JSON.stringify(line.trim())} must reach the agent`);
    }
  }
  const single = renderFind([cap], "search the web", "claude");
  // pretty() strips the -mcp suffix for the SERVER NAME while the package keeps it, so the correct
  // command is "add tavily -- npx -y tavily-mcp". Asserting the raw package name in both positions
  // would have pinned a command that does not match what the website and CLI emit.
  assert.ok(/claude mcp add tavily -- npx -y tavily-mcp/.test(single),
    "the one-line claude form still arrives intact");
  assert.ok(/install \(claude\)/.test(single), "the target client is named, so the agent cannot mispaste");
}
console.log("ok — install handoff delivers complete config");

// ---- ranking on what a capability DOES, not what it is called ----------------------------------
{
  const { forTask } = await import("./mcp.mjs");
  // lookup.json ships a token bag per record, parallel to records. tavily's NAME contains none of
  // "search the web"; its DESCRIPTION contains all of it. That gap is the whole reason this exists.
  const lookup = {
    records: [
      { id: "a", name: "tavily",      category: "search",   tashan_score: 86 },
      { id: "b", name: "web-search",  category: "search",   tashan_score: 57 },
      { id: "c", name: "kubernetes",  category: "cloud",    tashan_score: 85 },
      { id: "d", name: "cpln",        category: "cloud",    tashan_score: 46 },
      { id: "e", name: "unmeasured",  category: "search",   tashan_score: null },
    ],
    terms: [
      "crawl extract research search tavily web",
      "search web",
      "clusters kubernetes pods deploy",
      "kubernetes control plane manage deploy",
      "search web crawl",
    ],
  };
  const names = (q, n = 2) => forTask(null, q, n, lookup).map((r) => r.name);

  // THE REGRESSION THAT STARTED THIS: name matching put web-search (57) above tavily (86).
  assert.strictEqual(names("search the web")[0], "tavily",
    "matches the description, so the better-measured tool wins over one merely named for the task");
  assert.ok(!names("search the web", 9).includes("unmeasured"),
    "never recommends something we have not measured");
  assert.deepStrictEqual(names("underwater basket weaving"), [],
    "no match returns nothing rather than the highest-scoring unrelated thing");

  // Plural and singular must be the SAME token. Indexing surface forms made a capability whose blurb
  // used the plural outrank one using the singular, purely because the plural was rarer.
  const plural = {
    records: [{ id: "p", name: "pdf-a", tashan_score: 70 }, { id: "q", name: "pdf-b", tashan_score: 70 }],
    terms: ["pdf merge split", "pdfs merge split"],
  };
  assert.strictEqual(forTask(null, "work with PDFs", 2, plural).length, 2,
    "both the singular and plural bags match a plural query");

  // Without a terms bag the caller still gets name matching rather than an exception.
  const noTerms = [{ id: "z", name: "slack-mcp", tashan_score: 44 }];
  assert.strictEqual(forTask(noTerms, "send a slack message", 1)[0].name, "slack-mcp",
    "falls back to name matching when the lookup has no terms");
}
console.log("ok — task ranking uses descriptions, weighted by measurement");

// ---- the score exponent, and why there is no category nudge ------------------------------------
{
  const { forTask } = await import("./mcp.mjs");
  // Swept against ten judged phrases: 0.0 -> 6/10 at rank 1, 1.0 -> 8/10, 1.5 -> 10/10, 2.0 -> 9/10.
  // These two rows encode the failure at each end of that curve.
  const lookup = {
    records: [
      // full match, modest score  vs  partial match, high score  — the 2.0 failure
      { id: "s1", name: "screenshotink", tashan_score: 43 },
      { id: "s2", name: "trusty-squire", tashan_score: 75 },
      // extra weak match, low score  vs  one strong match, high score — the 1.0 failure
      { id: "k1", name: "kubernetes",    tashan_score: 85 },
      { id: "k2", name: "cpln",          tashan_score: 46 },
    ],
    terms: [
      "audit capture diff page screenshot sitemap website",
      "signs website account",
      "clusters kubernetes pods",
      "kubernetes control plane manage deploy",
    ],
  };
  assert.strictEqual(forTask(null, "take a screenshot of a website", 1, lookup)[0].name, "screenshotink",
    "matching BOTH words beats matching one, even at 43 against 75 — score must not overturn coverage");
  // The other end of the curve — one extra weak match must not overturn a large score gap — is NOT
  // asserted on a fixture. idf over four rows bears no relation to idf over 5,788, so a micro-fixture
  // would be testing itself. The evidence is the sweep over ten judged phrases against the real
  // export (0.0 -> 6/10 at rank 1, 1.0 -> 8/10, 1.5 -> 10/10, 2.0 -> 9/10); what a test can usefully
  // do is stop the chosen value drifting silently.
  const src = await (await import("node:fs")).promises.readFile(
    new URL("./mcp.mjs", import.meta.url), "utf8");
  assert.ok(/Math\.pow\(w, 1\.5\)/.test(src),
    "the swept score exponent is 1.5 — changing it requires re-running the sweep, not a guess");
  assert.ok(/const IDENT_WEIGHT = 0\.7;/.test(src),
    "the swept identity weight is 0.7 — bounded by two real cases, see the table at the use site");

  // IDENTITY BEATS A PASSING MENTION, but never a large measurement gap. Both directions, because
  // one without the other is how this went wrong: "query postgres" answered with @hasna/domains and
  // run402-mcp — which mention postgres once — above @henkey/postgres-mcp-server, which is named
  // for it; and the first fix that solved THAT put web-search (57) above tavily (86), which is the
  // regression the assertion above this block exists to prevent. A name is cheap.
  const pg = {
    records: [
      { id: "p1", name: "postgres-mcp-server", tashan_score: 69 },
      { id: "p2", name: "domains",             tashan_score: 72 },
    ],
    terms: [
      "database postgres postgresql queries schema",
      "domains dns records postgres",           // mentions it once, is not about it
    ],
  };
  assert.strictEqual(forTask(null, "query postgres", 1, pg)[0].name, "postgres-mcp-server",
    "a capability NAMED for what was asked must beat one that merely mentions it three points higher");

  // NO CATEGORY BONUS. A flat +0.5 was worth more than a real token match on a common word, which is
  // how a website SIGN-UP tool kept winning "take a screenshot of a website" by matching only
  // "website". Categories are 15 buckets with two thirds of the corpus in two of them — too coarse to
  // outweigh evidence about the words themselves. Asserted on the source for the same reason as the
  // exponent: a fixture small enough to write is too small for idf to mean anything.
  assert.ok(!/cats\.includes\(r\.category\)[^\n]*rel\s*\+=/.test(src),
    "relevance must not be topped up for merely being in the inferred category");
}
console.log("ok — ranking weight is swept, not felt");

// ---- the agent is the last checkpoint before something lands on a machine ------------------------
// risks() is what an agent reads before recommending an install. It must carry the security audit in
// full and for free: an agent that installs confirmed malware because the finding sat behind a
// paywall is the worst outcome this product could produce.
{
  const { risks } = await import("./mcp.mjs");

  let r = risks({ sec_max_severity: "MALICIOUS", sec_advisory_count: 1 });
  assert.ok(r.some((x) => /malicious-packages/.test(x)), "malware is reported to the agent");
  assert.ok(r.some((x) => /Do not install it/.test(x)),
    "...with an explicit instruction, not a hint it has to interpret");

  r = risks({ sec_advisory_count: 3, sec_max_severity: "HIGH" });
  assert.ok(r.some((x) => /3 known advisories/.test(x) && /high/.test(x)),
    "advisory count and severity both reach the agent");

  r = risks({ sec_install_script: "node x.js" });
  assert.ok(r.some((x) => /install time/.test(x) && /before any tool is called/.test(x)),
    "install-time execution is reported, with why it matters");

  r = risks({ sec_permissions: JSON.stringify(["shell", "credentials"]) });
  assert.ok(r.some((x) => /shell, credentials/.test(x)),
    "the permission surface is reported so the agent can relay it to the user");

  assert.ok(Array.isArray(risks({ sec_permissions: "{oops" })),
    "a malformed permissions field must never break the risk report");
  assert.strictEqual(risks({ rated: true }).length, 0,
    "a clean capability produces no risk lines — an agent must not be given noise to relay");
}
console.log("ok — the agent gets the full security audit, free");

// The agent is the last checkpoint before an install, so it gets the finding AND the fix. This block
// used to assert the opposite — that renderCheck named a Pro gate and a licensed URL — while the
// website printed the same advisory id and install command to any visitor. One fact, two prices,
// depending on whether you were holding a browser or a terminal. The detail is public now; what the
// agent must never be handed is a warning it cannot act on.
{
  const detailed = renderCheck({ id: "pkg:x", name: "x", label: "X", tashan_score: 50,
    sec_advisory_count: 2, sec_max_severity: "HIGH", sec_install_script: "node y.js", slug: "pkg-x",
    sec_advisories: JSON.stringify([
      { id: "GHSA-aaaa-bbbb-cccc", severity: "HIGH", summary: "command injection", fixed: "2.1.0" },
      { id: "GHSA-dddd-eeee-ffff", severity: "LOW", summary: "path traversal", fixed: null },
    ]) }, "x");
  assert.ok(/2 known advisories/.test(detailed), "the existence of a finding is always free");
  assert.ok(/GHSA-aaaa-bbbb-cccc/.test(detailed), "...and so is WHICH advisory it is");
  assert.ok(/fixed in 2\.1\.0/.test(detailed), "the fixing version is the only actionable line");
  assert.ok(/no fixed version published/.test(detailed),
    "an unfixed advisory says so — silence would read as 'already fixed, install away'");
  assert.ok(/node y\.js/.test(detailed), "the literal install command reaches the agent");
  assert.ok(!/tashan-cli login/.test(detailed) && !/Not shown here/.test(detailed),
    "nothing about the audit is sold, so nothing about it is pitched");

  // The board (index.json) flattens sec_install_script to a bare 1 to keep first paint small. That
  // is a slimmed field, not a command — printing "runs: 1" would be worse than printing nothing.
  const slim = renderCheck({ id: "pkg:z", name: "z", label: "Z", tashan_score: 50,
    sec_install_script: 1, slug: "pkg-z" }, "z");
  assert.ok(/install time/.test(slim), "the fact still reaches the agent from the slim board row");
  assert.ok(!/Runs this at install time/.test(slim), "but no command is invented from a boolean");

  const cleanOut = renderCheck({ id: "pkg:y", name: "y", label: "Y", tashan_score: 90, slug: "pkg-y" }, "y");
  assert.ok(!/tashan-cli login/.test(cleanOut), "nothing withheld, so nothing may be pitched");
  assert.ok(!/Not shown here/.test(cleanOut));
}
console.log("ok — the agent gets the advisory id, the fix version and the install command, free");

// ---- the paid half, inside the agent's decision loop ---------------------------------------------
// audit_config is the moment the trend is worth most: the agent is holding the user's actual list.
// Everything above it stays free; this is the one thing local files cannot know.
{
  const down = trendBlock({ history: {
    "pkg:a": { direction: "down", change: -12, first: "2026-06-01" },
    "pkg:b": { direction: "up", change: 3, first: "2026-06-01" },
    "pkg:c": { direction: "flat", change: 0, first: "2026-06-01" },
  } }).join("\n");
  assert.ok(/↓ pkg:a  -12 since/.test(down), "a falling capability must be named with its delta");
  assert.ok(/↑ pkg:b  \+3 since/.test(down), "a rising one too, with a sign");
  assert.ok(!/pkg:c/.test(down), "a flat row is noise in a list about movement");
  assert.ok(down.indexOf("pkg:a") < down.indexOf("pkg:b"), "biggest move first — that is the news");

  const quiet = trendBlock({ history: {} }).join("\n");
  assert.ok(/nothing in this config has moved/.test(quiet),
            "'nothing moved' is a real answer and must not read as a failed fetch");

  // These two send someone to different places. Guessing wrong wastes the moment they would act.
  assert.ok(/refused/.test(trendBlock({ status: 403 }).join("")), "a refused licence says so");
  assert.ok(/portal/.test(trendBlock({ status: 403 }).join("")), "...and points at the portal");
  assert.ok(/pricing/.test(trendBlock({ status: 402 }).join("")), "no licence points at pricing");
  assert.ok(!/refused/.test(trendBlock({ status: 402 }).join("")),
            "somebody who never had a licence must not be told theirs was refused");

  const pitch = trendBlock({ count: 14 }).join(" ");
  assert.ok(/these 14 /.test(pitch), "the offer is sized to THEIR config, not generic");
  assert.ok(/7 days free/.test(pitch));
}
console.log("ok — audit_config reports direction, and says which kind of 'no' it got");

// ---------------------------------------------------------------------------
// CONFIRMED MALWARE STOPS FIRST.
//
// This is the highest-stakes string this codebase produces. claude-cup carries MAL-2026-5789 and
// 4.8M weekly installs, and check_capability used to open with "tashan score 77/100 · 4,837,320
// downloads/wk · active" and put "this package IS the attack" three lines below — an endorsement
// followed by a footnote, on the one row where an agent summarising for a human must not drop the
// caveat. The score is gone at the source (eligibility overrides score, as for discontinued rows)
// and the verdict now leads.
{
  const mal = {
    id: "pkg:claude-cup", name: "claude-cup", kind: "npm", npm_pkg: "claude-cup",
    sec_max_severity: "MALICIOUS", sec_advisory_count: 1, npm_downloads: 4837320,
    vitality: "active", rated: false, single_maintainer: 1,
    rating_basis: "Not rated: listed in OSV's malicious-packages database.",
  };
  const out = renderCheck(mal, "claude-cup");
  const head = out.split("\n")[0];

  assert.ok(/^DO NOT INSTALL/.test(head), "the first line must be the verdict, not the metrics: " + head);
  assert.ok(!/score/i.test(head), "no score on the first line of a malware warning: " + head);
  // The number stays — it is what makes the warning land — but it must be framed, not laundered.
  assert.ok(out.includes("4,837,320"), "how far it spread is the point, and must still be shown");
  assert.ok(/not of quality/.test(out), "the adoption figure must be framed, not presented as merit");
  assert.ok(out.indexOf("DO NOT INSTALL") < out.indexOf("4,837,320"),
            "the verdict must precede the adoption figure");
  assert.ok(/do not add it to any config/i.test(out), "the agent needs an instruction, not a mood");

  // "No per-item evidence yet" about a confirmed attack understates it. A row with a stated
  // rating_basis is unrated on purpose, and says why.
  assert.ok(!/no per-item evidence yet/.test(out),
            "a refused rating must not read as missing data:\n" + out);

  // A healthy row is untouched — this branch must not swallow the normal rendering.
  const good = { id: "pkg:x", name: "x", kind: "npm", tashan_score: 92, npm_downloads: 1000,
                 vitality: "active", expertise_verdict: "deep" };
  assert.ok(/tashan score 92/.test(renderCheck(good, "x")), "healthy rows still lead with the score");
  assert.ok(!/DO NOT INSTALL/.test(renderCheck(good, "x")));

  // And an unrated row with NO stated reason still gets the honest "we have not measured this".
  assert.ok(/no per-item evidence yet/.test(renderCheck({ id: "pkg:y", name: "y", rated: false }, "y")),
            "genuinely unmeasured rows must still say so");
}
console.log("ok — confirmed malware leads with the verdict, and the download count is framed");

// ---------------------------------------------------------------------------
// A MISSING REQUIRED ARGUMENT IS A CALLER ERROR, NOT A FINDING.
//
// find_capability takes `task`. Calling it with `query` — an easy mistake for a host or another
// model to make — answered `No measured capability matches "undefined"`, which is the exact
// sentence used for a genuine miss. An agent relaying that to a person reports "nothing like this
// exists" when the truth is "you called it wrong". On an index whose whole claim is that absence
// means unmeasured rather than bad, that confusion is the one we can least afford.
{
  const bad = await handle({ jsonrpc: "2.0", id: 1, method: "tools/call",
    params: { name: "find_capability", arguments: { query: "search the web" } } });
  assert.equal(bad.result.isError, true, "a missing required argument must be flagged as an error");
  const t = bad.result.content[0].text;
  assert.ok(/"task"/.test(t), "it must name the parameter that is missing: " + t);
  assert.ok(/not a result/i.test(t), "and say plainly that it is not a finding: " + t);
  assert.ok(!/undefined/.test(t), "and never quote the missing value back as a search term: " + t);

  // check_capability has the same shape, so it must behave the same way.
  const bad2 = await handle({ jsonrpc: "2.0", id: 2, method: "tools/call",
    params: { name: "check_capability", arguments: {} } });
  assert.equal(bad2.result.isError, true);
  assert.ok(/"name"/.test(bad2.result.content[0].text));

  // audit_config requires nothing, and must not be broken by the guard. Asserted on WHICH error it
  // is, not on success: this tool fetches the published lookup, so a flat `!isError` made a unit
  // test depend on the network and it went red on a dropped connection with nothing wrong in the
  // code. A red that means "your wifi blinked" teaches you to ignore red. The guard is what is
  // under test, so the guard is what is asserted — a missing-argument complaint must not appear for
  // a tool that requires no arguments, however the call otherwise ends.
  const okCall = await handle({ jsonrpc: "2.0", id: 3, method: "tools/call",
    params: { name: "audit_config", arguments: {} } });
  const okText = okCall.result.isError ? String(okCall.result.content[0].text) : "";
  assert.ok(!/required|missing|expects/i.test(okText),
    `the argument guard fired on a tool with no required arguments: ${okText.slice(0, 120)}`);
}
// ---- the agent is quoted, and nothing is named --------------------------------------------------
// The unlicensed path used to end in a sentence with a price in it. An agent holding a funded wallet
// could not act on that, and an agent that wanted to pay was invisible to us — zero quotes from the
// audience most likely to buy, because we never actually asked for a price on their behalf.
{
  const q = { accepts: [{ amount: "10000", asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                          network: "eip155:8453", payTo: "0xPAYTO" }] };
  const lines = trendBlock({ count: 4, quote: q }).join("\n");
  assert.ok(lines.includes("0.01 USDC") && lines.includes("eip155:8453") && lines.includes("0xPAYTO"),
            "the quote's real terms must reach the agent: " + lines);
  assert.ok(/nothing is named until/i.test(lines),
            "the privacy promise must travel with the offer");
  // `watch` is status:planned. It was being sold here, and from four generators, and from the
  // pricing page, before anyone checked what had actually shipped.
  assert.ok(!/watches|tells you the day|notif/i.test(lines),
            "must not sell proactive notification: " + lines);
  assert.ok(/series/.test(lines) && /replacement/.test(lines), "must sell what ships");

  // Offline, or a deployment with no wallet: still honest, and inventing no terms.
  const bare = trendBlock({ count: 4 }).join("\n");
  assert.ok(bare.includes("$6/mo"), "the subscription price still stands on its own");
  assert.ok(!/USDC|PAYMENT-SIGNATURE/.test(bare), "no x402 terms may be invented without a quote");
}
console.log("ok — an unlicensed agent is quoted in terms it can act on, naming nothing");


console.log("ok — a malformed tool call is reported as a caller error, never as 'nothing found'");

// ---- paid_demand: the money signal, and above all what its ABSENCE means ----
const DOC = {
  source: "subgraph ABC via subgraphs.mcp.thegraph.com", receivers_indexed: 1079,
  paid_capabilities: 31,
  economy: { paid_usd: 247247.51, calls: 10414327, receivers_paid: 997, receivers_never_paid: 82,
             median_usd: 0.51, top1_share: 0.6741, top5_share: 0.8911, under_1_usd: 592,
             under_10_usd: 827, over_1000_usd: 9, mean_payment_usd: 0.0237 },
  records: [
    { address: "0xe90", hosts: ["blockrun.ai"], capabilities: ["pkg:@blockrun/mcp"],
      attributable: true, shared: false, paid_usd: 166658.82, calls: 8718732 },
    { address: "0x6e0", hosts: ["blockrun.ai", "api.aidress.ai"], capabilities: ["pkg:@blockrun/mcp"],
      attributable: false, shared: true, paid_usd: 130.83, calls: 33408 },
  ],
};

const eco = renderPaid(DOC, null);
assert.ok(/\$247,248|\$247,247/.test(eco), "the total must be there");
assert.ok(/median/i.test(eco) && /\$0\.51/.test(eco),
  "a total without the median lets a concentrated economy read as a healthy one");
assert.ok(/67%/.test(eco), "concentration is the point, not the sum");

const hit = renderPaid(DOC, "blockrun");
assert.ok(/\$166,659/.test(hit), "the attributable receipt is reported");
assert.ok(!/0x6e0/.test(hit), "a SHARED address must never be attributed to a capability");
assert.ok(/not an input to the tashan score/.test(hit),
  "the firewall has to travel with the number");

const miss = renderPaid(DOC, "tavily-mcp");
assert.ok(/NOT a negative signal/.test(miss),
  "unpaid must not read as bad — almost every MCP server is free by design");

assert.ok(/have not read the chain/.test(renderPaid(null, null)),
  "no data must say so rather than implying nothing has ever been paid");
console.log("ok — paid_demand: totals carry the median, shared addresses excluded, absence explained");
