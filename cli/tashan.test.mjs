// node cli/tashan.test.mjs  — pure-logic tests for the CLI (no network, no deps).
import { search, top, find, installSnippets, slugify } from "./tashan.mjs";
import assert from "node:assert";

const rows = [
  { id: "pkg:context7", slug: "context7", name: "context7", kind: "mcp", category: "docs",
    npm_pkg: "@upstash/context7-mcp", source_repo: "upstash/context7", trust: 88, maintenance: 90,
    vitality: "active", expertise: 82, expertise_verdict: "deep", npm_downloads: 137460 },
  { id: "pkg:firecrawl-mcp", slug: "firecrawl-mcp", name: "firecrawl-mcp", kind: "mcp", category: "web",
    npm_pkg: "firecrawl-mcp", source_repo: "mendableai/firecrawl", trust: 75, npm_downloads: 79087, expertise_verdict: "solid" },
  { id: "skill:anthropics/pdf", slug: "skill-anthropics-pdf", name: "pdf", kind: "skill", category: "docs",
    trust: 60, npm_pkg: null, source_repo: "anthropics/skills" },
  { id: "pkg:remote-thing", slug: "remote-thing", name: "remote-thing", kind: "remote",
    trust: 40, npm_pkg: null, source_repo: "acme/remote" },
  { id: "pkg:untrusted", slug: "untrusted", name: "untrusted", kind: "mcp", trust: null },
];

// search: exact > prefix > substring; ranked
let r = search(rows, "context7");
assert.strictEqual(r[0].slug, "context7", "exact name wins");
r = search(rows, "fire");
assert.strictEqual(r[0].slug, "firecrawl-mcp", "prefix match");
r = search(rows, "docs");
assert.ok(r.some((x) => x.slug === "context7"), "category match included");
assert.strictEqual(search(rows, "zzzznope").length, 0, "no false matches");

// top: trust-ranked, drops null-trust, category filter
let t = top(rows);
assert.strictEqual(t[0].slug, "context7", "highest trust first");
assert.ok(!t.some((x) => x.trust == null), "null-trust excluded");
assert.deepStrictEqual(top(rows, "web").map((x) => x.slug), ["firecrawl-mcp"], "category filter");

// find: by slug, name, pkg, fuzzy
assert.strictEqual(find(rows, "context7").slug, "context7");
assert.strictEqual(find(rows, "@upstash/context7-mcp").slug, "context7", "by npm pkg");
assert.strictEqual(find(rows, "firecrawl").slug, "firecrawl-mcp", "fuzzy substring");

// install snippets — must match the site's installBlock() shapes
let s = installSnippets(rows[0], null);
assert.strictEqual(s[0].client, "claude");
assert.strictEqual(s[0].cmd, "claude mcp add context7 -- npx -y @upstash/context7-mcp", "claude one-liner matches site");
assert.ok(s.find((x) => x.client === "cursor").cmd.includes('"@upstash/context7-mcp"'), "cursor json snippet");
assert.strictEqual(installSnippets(rows[0], "npx")[0].cmd, "npx -y @upstash/context7-mcp", "client filter");

// skill install
let sk = installSnippets(rows[2], null);
assert.ok(sk[0].cmd.startsWith("cp -r pdf ~/.claude/skills/"), "skill copies into skills dir");

// remote (no npm) → guidance, never a bogus npx
let rm = installSnippets(rows[3], null);
assert.strictEqual(rm[0].client, "remote");
assert.ok(!rm[0].cmd.includes("npx"), "remote has no fake npx command");

assert.strictEqual(slugify("Pkg: Foo/Bar!"), "pkg-foo-bar");

console.log("ok — CLI pure logic (search / top / find / install / slugify)");
