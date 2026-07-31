// node cli/mcp.test.mjs — protocol + rendering for the MCP server. No network.
import { handle, handshake, evidence, risks, renderFind, renderCheck } from "./mcp.mjs";
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
assert.deepStrictEqual(names, ["audit_config", "check_capability", "find_capability"]);
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

// The agent is the last checkpoint before an install. It must always learn that a finding EXISTS,
// and — when detail is withheld — exactly how the user opens it. A gate the agent cannot name is a
// gate it will paraphrase, or invent a way around.
{
  const gatedOut = renderCheck({ id: "pkg:x", name: "x", label: "X", tashan_score: 50,
    sec_advisory_count: 2, sec_max_severity: "HIGH", sec_install_script: "node y.js", slug: "pkg-x" }, "x");
  assert.ok(/2 known advisories/.test(gatedOut), "the existence of a finding is always free");
  assert.ok(/tashan-cli login/.test(gatedOut), "the agent must be able to name how to get the fix");
  assert.ok(/Everything above stays free/.test(gatedOut), "the free guarantee is restated to the agent");

  const cleanOut = renderCheck({ id: "pkg:y", name: "y", label: "Y", tashan_score: 90, slug: "pkg-y" }, "y");
  assert.ok(!/tashan-cli login/.test(cleanOut), "nothing withheld, so nothing may be pitched");
  assert.ok(!/Not shown here/.test(cleanOut));
}
