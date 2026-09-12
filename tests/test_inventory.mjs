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

ok(Object.keys(frontmatter("---\nname: a\ndescription: b\n---")).length === 2, "frontmatter reads name and description");
ok(!frontmatter("no frontmatter").name, "and invents nothing when there is none");

console.log(fail ? `\n  ${fail} failing` : "\n  all inventory checks pass");
process.exit(fail ? 1 : 0);
