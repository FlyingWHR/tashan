// The inventory is the half of doctor that answers "what do I even have".
//
// It earns a test of its own because its three claims are all the kind that are wrong silently:
// a server in another project is simply absent rather than reported missing, a skill attributed to
// a plugin looks maintained when nothing maintains it, and a first-seen date that gets overwritten
// cannot be recovered from anywhere — the disk records the last edit, never the arrival.
//
// Run: node tests/test_inventory.mjs
import { frontmatter, serversFromClaudeJson, pluginsFrom, skillsIn, idOf, reconcile } from "../cli/inventory.mjs";

let fail = 0;
const ok = (cond, what) => { console.log(`  ${cond ? "ok  " : "FAIL"} ${what}`); if (!cond) fail++; };

// --- identity ----------------------------------------------------------------------------------
// Two projects can each have a server called "github" and they are not the same install.
const a = idOf({ kind: "server", scope: "project", project: "/p/one", name: "github" });
const b = idOf({ kind: "server", scope: "project", project: "/p/two", name: "github" });
ok(a !== b, "the same server name in two projects is two installs, not one");
ok(idOf({ kind: "plugin", name: "telegram", marketplace: "official" }).includes("telegram@official"),
   "a plugin's identity carries the marketplace it came from");

// --- the surfaces doctor could not see -----------------------------------------------------------
const servers = serversFromClaudeJson({
  mcpServers: { top: {} },
  projects: { "/a": { mcpServers: { one: {} } }, "/b": { mcpServers: { two: {}, three: {} } }, "/c": {} },
});
ok(servers.length === 4, `every project's servers are found (got ${servers.length}, expected 4)`);
ok(servers.filter((s) => s.scope === "project").length === 3, "project scope is preserved for reporting");

const plugins = pluginsFrom({ plugins: { "vercel@vercel-marketplace": [{ scope: "user", version: "1.2.3", installedAt: "2026-03-23T14:15:49Z", lastUpdated: "2026-08-16T08:17:06Z", installPath: "/h/cache/vercel/1.2.3" }] } });
ok(plugins.length === 1 && plugins[0].marketplace === "vercel-marketplace", "plugin key splits into name and marketplace");
ok(plugins[0].installedAt === "2026-03-23T14:15:49Z", "the install date already on disk is not thrown away");

// --- yours versus theirs -------------------------------------------------------------------------
const files = {
  "/h/.claude/skills/mine/SKILL.md": "---\nname: mine\ndescription: I wrote this.\n---\n",
  "/h/cache/vercel/1.2.3/skills/theirs/SKILL.md": "---\nname: theirs\ndescription: shipped by a plugin.\n---\n",
};
const deps = {
  exists: (p) => p in files || Object.keys(files).some((f) => f.startsWith(p + "/")),
  list: (d) => (d.startsWith("/h/.claude/skills") ? ["mine"] : ["theirs"]),
  read: (p) => files[p],
  stat: () => ({ mtime: new Date("2026-09-01T00:00:00Z") }),
};
const skills = skillsIn(
  [{ scope: "user", dir: "/h/.claude/skills" }, { scope: "user", dir: "/h/cache/vercel/1.2.3/skills" }],
  ["/h/cache/vercel/1.2.3"],
  deps,
);
ok(skills.find((s) => s.name === "mine").authored === true, "a skill you wrote is yours to maintain");
ok(skills.find((s) => s.name === "theirs").authored === false, "a plugin's skill is not");
ok(skills.find((s) => s.name === "theirs").owner === "/h/cache/vercel/1.2.3", "and it names the plugin that owns it");

// A skill with no frontmatter is still inventoried; it is just undocumented, which is the finding.
const bare = skillsIn([{ scope: "user", dir: "/h/.claude/skills" }], [], {
  ...deps, read: () => "# just a heading", exists: () => true,
});
ok(bare[0].documented === false && bare[0].name === "mine", "an undocumented skill is counted, not dropped");

// --- the ledger ----------------------------------------------------------------------------------
const one = reconcile({ version: 1, seen: {} }, [{ kind: "skill", scope: "user", name: "x" }], "2026-09-01");
const two = reconcile(one.ledger, [{ kind: "skill", scope: "user", name: "x" }, { kind: "skill", scope: "user", name: "y" }], "2026-09-05");
ok(two.fresh.length === 1 && two.fresh[0].name === "y", "only what actually arrived is new");
ok(two.ledger.seen["skill:user:x"].first === "2026-09-01", "first-seen is never rewritten");
const three = reconcile(two.ledger, [{ kind: "skill", scope: "user", name: "x" }], "2026-09-06");
ok(three.gone.length === 1, "something that vanished is reported");
ok(three.ledger.seen["skill:user:y"].first === "2026-09-05",
   "and is kept, because an unmounted disk is not an uninstall and the date cannot be re-derived");

// A skill is a directory. Loose files beside them are not skills — but a versioned directory is.
const mixed = skillsIn([{ scope: "user", dir: "/h/.claude/skills" }], [], {
  exists: () => true,
  list: () => ["real-skill", "cinema-pro-2.0", "_notes.md", "config.json", "run.sh"],
  read: () => "---\nname: x\ndescription: y\n---",
  stat: () => ({ mtime: new Date("2026-09-01T00:00:00Z") }),
});
ok(mixed.length === 2, `loose files are not skills (got ${mixed.length}, expected 2)`);
ok(mixed.some((x) => x.path.endsWith("cinema-pro-2.0")),
   "a versioned directory survives — matching /\\.[a-z0-9]+$/ dropped every one of them");

ok(Object.keys(frontmatter("---\nname: a\ndescription: b\n---")).length === 2, "frontmatter reads name and description");
ok(!frontmatter("no frontmatter").name, "and invents nothing when there is none");

// --- plugin identity: where it lives, never a shared name ----------------------------------------
const { pluginId, mcpCallsIn, usageOf, toolPrefix } = await import("../cli/inventory.mjs");
const officialMk = { source: { source: "github", repo: "anthropics/claude-plugins-official" } };
const manifest = { plugins: [
  { name: "telegram", source: "./external_plugins/telegram" },
  { name: "vercel", source: { source: "url", url: "https://github.com/vercel/vercel-plugin.git", sha: "abc" } },
] };
ok(pluginId("telegram", officialMk, manifest) === "plugin:anthropics/claude-plugins-official/telegram",
   "a relative source lives in the marketplace's own repository");
ok(pluginId("vercel", officialMk, manifest) === "plugin:vercel/vercel-plugin/vercel",
   "a url source names its own home — being listed in Anthropic's marketplace does not make it Anthropic's");
ok(pluginId("vercel-plugin", { source: { source: "directory", path: "/x" } },
            { plugins: [{ name: "vercel-plugin", source: "./" }] }) === null,
   "a marketplace that is only a local directory yields no id, not a guess");
ok(pluginId("absent", officialMk, manifest) === null, "a plugin its manifest does not list has no id");

// --- a departure is news once --------------------------------------------------------------------
const four = reconcile(three.ledger, [{ kind: "skill", scope: "user", name: "x" }], "2026-09-07");
ok(four.gone.length === 0, "something already reported gone is not reported again on every run");

// --- usage: counted from the bytes around a tool call, dated by its own entry -----------------------
const entry = (ts, name) => JSON.stringify({ type: "assistant",
  message: { content: [{ type: "tool_use", id: "toolu_01abc", name, input: {} }] }, timestamp: ts });
const transcript = Buffer.from([
  entry("2026-09-10T10:00:00.000Z", "mcp__chrome-devtools__click"),
  entry("2026-09-12T10:00:00.000Z", "mcp__chrome-devtools__navigate_page"),
  entry("2026-07-01T10:00:00.000Z", "mcp__tavily__search"),
  entry("2026-09-11T10:00:00.000Z", "Bash"),
  entry("2026-09-11T10:00:00.000Z", "mcp__plugin_telegram_telegram__reply"),
  JSON.stringify({ type: "user", timestamp: "2026-09-11T00:00:00Z", message: { content: [{ type: "tool_result",
    content: 'quoted: {"type":"tool_use","id":"x","name":"mcp__fake__y"}' }] } }),
].join("\n"));
const calls = mcpCallsIn(transcript, {}, "2026-08-14");
ok(calls["chrome-devtools"]?.calls === 2 && calls["chrome-devtools"].last === "2026-09-12",
   "calls are counted per server and dated by their own entry");
ok(!calls.tavily, "a call from before the window does not count");
ok(!calls.fake, "a tool_use quoted inside a tool result is text, not a call");
ok(Object.keys(calls).length === 2, `only MCP tools are counted (got ${Object.keys(calls)})`);

const u = { available: true, sinceMs: Date.parse("2026-08-14"), servers: calls,
            skills: { audit: { usageCount: 13, lastUsedAt: Date.parse("2026-09-01") },
                      "watch:watch": { usageCount: 4, lastUsedAt: Date.parse("2026-01-01") } } };
ok(usageOf({ type: "server", client: "Claude Code", name: "chrome-devtools" }, u).calls === 2,
   "a Claude Code server's calls are read");
const idle = usageOf({ type: "server", client: "Claude Code", name: "tavily" }, u);
ok(idle.calls === 0 && idle.recent === false, "a Claude Code server with no calls is a real zero");
ok(usageOf({ type: "server", client: "Cursor", name: "tavily" }, u) === null,
   "a Cursor server has no readable record — null, never a zero");
ok(usageOf({ type: "plugin", client: "Claude Code", name: "telegram" }, u).calls === 1, "a plugin's own servers count toward it");
ok(usageOf({ type: "plugin", client: "Claude Code", name: "ponytail" }, u) === null,
   "a plugin with no calls is silent — hooks leave no trace, so silence is not disuse");
ok(usageOf({ type: "skill", name: "audit" }, u).recent === true, "a skill used inside the window is recent");
ok(usageOf({ type: "skill", name: "watch", plugin: "watch" }, u).recent === false,
   "a plugin's skill is keyed plugin:skill, and use from months ago is not recent");
ok(toolPrefix("claude.ai Gmail") === "claude_ai_Gmail", "a configured name is spelled the way its tool names spell it");

console.log(fail ? `\n  ${fail} failing` : "\n  all inventory checks pass");
process.exit(fail ? 1 : 0);
