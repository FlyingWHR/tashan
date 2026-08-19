// node tests/test_audit_parity.mjs
//
// /audit parses an MCP config in the BROWSER — the config holds API keys, so it must never be
// uploaded — while the CLI parses the same shapes in Node. That is two implementations of one
// definition, which is exactly how prerender.py and capability.js drifted three times in one night.
// This runs both over the same fixtures and fails if they ever disagree.

import { readFileSync } from "node:fs";
import { identify as cliIdentify, stripVersion as cliStrip } from "../cli/doctor.mjs";

// web/js/audit.js is a browser IIFE, not a module. Evaluate it with a CommonJS-ish shim so the
// export block at its end hands back the same three functions the page uses. No build step, which
// is the point — the file under test is byte-for-byte the file that ships.
const src = readFileSync(new URL("../web/js/audit.js", import.meta.url), "utf8");
const mod = { exports: {} };
new Function("module", "document", "window", "fetch", src)(
  mod,
  { getElementById: () => null, addEventListener: () => {}, readyState: "complete",
    createElement: () => ({ appendChild() {}, className: "", textContent: "" }) },
  {}, () => Promise.reject(new Error("no network in tests")),
);
const web = mod.exports;

let pass = 0, fail = 0;
const ok = (c, m) => { c ? pass++ : (fail++, console.log("  FAIL " + m)); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// Every config entry shape either implementation claims to understand, plus the ones that have
// actually broken something here before.
const ENTRIES = [
  { command: "npx", args: ["-y", "firecrawl-mcp"] },
  { command: "npx", args: ["firecrawl-mcp@1.2.3"] },
  { command: "npx", args: ["-y", "@playwright/mcp@latest"] },   // must not eat the scope's @
  { command: "npx", args: ["-y", "@upstash/context7-mcp"] },
  { command: "/usr/local/bin/npx", args: ["-y", "tavily-mcp"] },
  { command: "uvx", args: ["mcp-server-git"] },
  { command: "uv", args: ["--directory", "/x", "run", "srv"] },
  { command: "docker", args: ["run", "-i", "--rm", "ghcr.io/x/y:1"] },
  { command: "node", args: ["./local.js"] },
  { url: "https://mcp.example.com/sse" },
  { url: "not a url" },
  {}, null, "string", { args: ["x"] },
];

for (const e of ENTRIES) {
  const a = cliIdentify(e), b = web.identify(e);
  ok(same(a && { kind: a.kind, id: a.id }, b && { kind: b.kind, id: b.id }),
     `identify disagrees on ${JSON.stringify(e)}: cli=${JSON.stringify(a)} web=${JSON.stringify(b)}`);
}
for (const s of ["a@1.2.3", "@scope/p@latest", "@scope/p", "plain", "@only", "a@b@c"]) {
  ok(cliStrip(s) === web.stripVersion(s), `stripVersion disagrees on ${s}`);
}

// --- serversFrom: the paste shapes people actually have ------------------------------------------
const BLOCK = { firecrawl: { command: "npx", args: ["-y", "firecrawl-mcp"] },
                tavily: { command: "npx", args: ["-y", "tavily-mcp"] } };

const cases = [
  ["a whole config file", JSON.stringify({ mcpServers: BLOCK }), ["firecrawl-mcp", "tavily-mcp"]],
  ["the block on its own", JSON.stringify(BLOCK), ["firecrawl-mcp", "tavily-mcp"]],
  ["VS Code's `servers` key", JSON.stringify({ servers: BLOCK }), ["firecrawl-mcp", "tavily-mcp"]],
  // ~/.claude.json nests mcpServers under each project path. Pasting the whole file is the most
  // likely thing a Claude Code user does, and a top-level-only parser finds nothing in it.
  ["a nested settings file", JSON.stringify({ projects: { "/home/x/p": { mcpServers: BLOCK } } }),
   ["firecrawl-mcp", "tavily-mcp"]],
  ["a bare list, newline", "firecrawl-mcp\ntavily-mcp", ["firecrawl-mcp", "tavily-mcp"]],
  ["a bare list, comma", "firecrawl-mcp, tavily-mcp", ["firecrawl-mcp", "tavily-mcp"]],
  ["a JSON array of names", JSON.stringify(["firecrawl-mcp", "tavily-mcp"]),
   ["firecrawl-mcp", "tavily-mcp"]],
  ["broken JSON falls back to names", '{"mcpServers": {"a": ', []],
];
for (const [label, text, want] of cases) {
  const got = web.serversFrom(text).map((s) => s.id);
  ok(same(got.slice().sort(), want.slice().sort()), `${label}: got ${JSON.stringify(got)}`);
}

// THE PRIVACY PROMISE, ENFORCED. The page tells the reader their keys never leave the browser. If a
// secret can reach a parsed id, that sentence becomes a lie the moment someone pastes a real file.
const SECRET = "ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
const withSecrets = JSON.stringify({
  mcpServers: {
    gh: { command: "npx", args: ["-y", "@modelcontextprotocol/server-github"],
          env: { GITHUB_TOKEN: SECRET, DATABASE_URL: "postgres://u:pw@h/db" } },
  },
});
const parsed = web.serversFrom(withSecrets);
const blob = JSON.stringify(parsed);
ok(!blob.includes(SECRET), "a token in env must never survive parsing");
ok(!blob.includes("postgres://"), "a database URL must never survive parsing");
ok(!blob.includes("GITHUB_TOKEN"), "even the env KEY names stay in the browser");
ok(same(parsed.map((p) => p.id), ["@modelcontextprotocol/server-github"]), JSON.stringify(parsed));

// --- the render path, headlessly, against a REAL /v0.1/audit response ----------------------------
//
// Parsing being right is half of it. render() sorts, maps verdicts and writes the "unmeasured" line,
// and a throw in there leaves the user staring at an empty box right after they pasted their config
// — the one moment the page has to work. Same DOM-shim approach as tests/test_render.mjs, which
// caught exactly that class of bug on the dossier.
{
  const fixture = JSON.parse(
    readFileSync(new URL("./fixtures/audit_response.json", import.meta.url), "utf8"));

  // The shim must STORE handlers. A no-op addEventListener silently makes every assertion below
  // test an empty page instead of a rendered one — a green suite proving nothing.
  const mk = (tag) => ({
    tag, className: "", value: "", _text: "", children: [], attrs: {}, on: {},
    appendChild(c) { this.children.push(c); return c; },
    addEventListener(ev, fn) { (this.on[ev] = this.on[ev] || []).push(fn); },
    set textContent(v) { this._text = String(v); this.children = []; },
    get textContent() { return this._text + this.children.map((c) => c.textContent).join(" "); },
    set href(v) { this.attrs.href = v; },
    set disabled(v) { this.attrs.disabled = v; },
  });
  const nodes = {};
  for (const id of ["audOut", "audNote", "audIn", "audGo"]) nodes[id] = mk("div");
  // The commercial panel, as pipeline/chrome.py renders it into the static page: present but hidden.
  const panel = mk("section");
  panel.hidden = true;
  panel.lede = mk("p");
  panel.querySelector = (sel) => (sel === ".pro__lede" ? panel.lede : null);

  let requests = 0, sentBody = null;
  const events = [];
  const mod2 = { exports: {} };
  new Function("module", "document", "window", "fetch", src)(
    mod2,
    { getElementById: (id) => nodes[id] || null, addEventListener: () => {},
      readyState: "complete", createElement: mk,
      querySelector: (sel) => (sel.indexOf('data-pro="audit"') >= 0 ? panel : null) },
    { tashanEvent: (name, props) => events.push({ name, props }) },
    (url, init) => {
      requests++; sentBody = JSON.parse(init.body);
      return Promise.resolve({ ok: true, json: () => Promise.resolve(fixture) });
    },
  );

  nodes.audIn.value = JSON.stringify({ mcpServers: {
    fc: { command: "npx", args: ["-y", "firecrawl-mcp"] },
    tv: { command: "npx", args: ["-y", "tavily-mcp"] },
    cl: { command: "npx", args: ["-y", "cline"] },
    no: { command: "npx", args: ["-y", "totally-not-a-real-pkg-xyz"],
          env: { SECRET_TOKEN: "ghp_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz" } } } });
  ok((nodes.audGo.on.click || []).length === 1, "the button is wired exactly once");
  nodes.audGo.on.click[0]();
  await new Promise((r) => setTimeout(r, 0));

  ok(requests === 1, `a paste triggers exactly one audit request (got ${requests})`);
  // The funnel step between arriving and being offered anything: did the tool actually RUN?
  ok(events.some((e) => e.name === "audit" && e.props && e.props.k === "ran"),
     `a completed audit is recorded: ${JSON.stringify(events)}`);
  // Counts only. What someone pasted is their config, and it never becomes a metric.
  ok(!JSON.stringify(events).includes("firecrawl"), "no package name reaches analytics");
  // THE PRIVACY PROMISE, ON THE WIRE. Asserting the parser drops secrets is not enough — this is
  // the actual request body the page sends.
  ok(!JSON.stringify(sentBody).includes("ghp_"), "no token reaches the request body");
  ok(same(Object.keys(sentBody), ["servers"]), `only names are sent: ${JSON.stringify(sentBody)}`);

  const text = nodes.audOut.textContent;
  ok(/Measured 3 of 4/.test(text), `summary counts measured vs asked — got: ${text.slice(0, 90)}`);
  ok(text.includes("tavily-mcp"), "every audited row is rendered");
  // THE FINDING ITSELF, NOT "[object Object]". A flag is {k, say, n}; String(flag) renders the
  // object tag, and the assertion above passed anyway because it only looked for the package name.
  // The flag sentence IS the product on this page.
  const flagged = fixture.audited.find((r) => (r.flags || []).length);
  ok(!!flagged, "the fixture must contain a flagged row or this proves nothing");
  const sentence = flagged.flags[0].say || flagged.flags[0].k;
  ok(text.includes(sentence), `the flag's sentence must render: expected "${sentence}"`);
  ok(!text.includes("[object Object]"), "no flag renders as [object Object]");
  ok(/have not looked, never that they are safe/.test(text), "the unmeasured line stays honest");
  ok(text.includes("totally-not-a-real-pkg-xyz"), "the unmeasured package is named");

  // THE OFFER MUST BE EARNED. It stays hidden until results exist, and it must pitch WATCHING —
  // selling "unlock the findings" on a page that just gave them away for free would break the one
  // rule the whole product rests on.
  ok(panel.hidden === false, "the Pro panel is revealed once there are results");
  ok(/what one check cannot show you is the change/i.test(panel.lede._text),
     `the pitch is time, not access: ${panel.lede._text.slice(0, 80)}`);
  ok(/1 of these 3 want a look/.test(panel.lede._text),
     `the lede counts what this reader actually pasted: ${panel.lede._text.slice(0, 60)}`);

  // ...AND IT MUST STAY HIDDEN WHEN NOTHING EARNED IT. A panel that greets a reader before they
  // have checked anything is the standing nag this project has a rule against, and revealing it on
  // an empty result is the easiest way to reintroduce one.
  {
    const n2 = {};
    for (const id of ["audOut", "audNote", "audIn", "audGo"]) n2[id] = mk("div");
    const p2 = mk("section"); p2.hidden = true; p2.lede = mk("p");
    p2.querySelector = () => p2.lede;
    const m4 = { exports: {} };
    new Function("module", "document", "window", "fetch", src)(
      m4,
      { getElementById: (id) => n2[id] || null, addEventListener: () => {}, readyState: "complete",
        createElement: mk, querySelector: () => p2 },
      {},
      () => Promise.resolve({ ok: true,
        json: () => Promise.resolve({ audited: [], unmeasured: [], summary: { measured: 0 } }) }),
    );
    n2.audIn.value = "some-package-nobody-measured";
    n2.audGo.on.click[0]();
    await new Promise((r) => setTimeout(r, 0));
    ok(p2.hidden === true, "no results means no offer — the panel must not become a standing nag");
  }

  // The row needing attention must not sit below the fine ones.
  const list = nodes.audOut.children.find((c) => c.tag === "ul");
  ok(list && list.children.length === 3, `three rows rendered (got ${list && list.children.length})`);
  ok(list && list.children[0].textContent.includes("tavily-mcp"),
     "rows sort by what needs attention, not alphabetically");
}

console.log(`audit parity: ${pass}/${pass + fail} passed` + (fail ? ` · ${fail} FAILED` : " · all green"));
process.exit(fail ? 1 : 0);
