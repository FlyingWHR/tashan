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
assert.ok(/tavily/.test(out) && /install:/.test(out), "gives the agent a runnable install command");
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

  // THE REGRESSION THAT MATTERS: category-top ranking picked the highest-scoring row in the category,
  // which is a different tool entirely. Relevance must beat score.
  assert.strictEqual(forTask(idx, "send a slack message", 1)[0].name, "slack-mcp",
    "names the Slack tool, not the higher-scoring unrelated top of `comms`");
  assert.strictEqual(forTask(idx, "work with PDFs", 1)[0].name, "pdf-toolkit-mcp",
    "plural 'PDFs' still finds pdf-toolkit, and beats the higher-scoring context7");
  assert.strictEqual(forTask(idx, "search the web", 1)[0].name, "tavily-mcp");
  assert.ok(!forTask(idx, "docs", 9).some((c) => c.tashan_score == null),
    "never recommends an unscored capability — we have no evidence for it");
  assert.deepStrictEqual(forTask(idx, "underwater basket weaving", 3), [],
    "no match returns nothing rather than the highest-scoring unrelated thing");
}
console.log("ok — mcp task routing");
