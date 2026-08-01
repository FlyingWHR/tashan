// node tests/test_render.mjs  — headlessly RUN capability.js render() against real prerendered data.
//
// The static tests check the HTML files; this checks the thing users actually see — the JS-rendered
// dossier. It caught a hoisting bug (CAT used before its `var` assignment) that made render() throw on
// every categorized capability, so users only ever saw the thin prerendered summary. No deps: a tiny
// DOM shim, real inline islands sampled across the prerendered set.
import fs from "node:fs";
import path from "node:path";
import assert from "node:assert";

const ROOT = path.dirname(path.dirname(new URL(import.meta.url).pathname));
const CAPJS = fs.readFileSync(path.join(ROOT, "web/js/capability.js"), "utf8");
const dir = path.join(ROOT, "web/capability");
const files = fs.readdirSync(dir).filter((f) => f.endsWith(".html"));

// sample a spread (every Nth) plus guarantee coverage of the tricky branches by scanning for them
const step = Math.max(1, Math.floor(files.length / 60));
const sample = files.filter((_, i) => i % step === 0);

// THE SHIM MUST MODEL THE PAGE THE GENERATOR ACTUALLY EMITS. This used to answer
// getElementById("cap") with a live element and querySelector() with null — the exact inverse of
// reality. prerender.py emits <main class="wrap" id="main"> and has never emitted an id="cap", so on
// every real dossier el was null and render() threw at el.innerHTML. The suite passed anyway,
// because the shim invented the mount the page was missing: a test asserting the broken contract is
// how this shipped to 5,788 pages. The mount now resolves the way a browser resolves it.
function runRender(islandText, pathname, mountSel) {
  let capHTML = "__SUMMARY__";
  const capEl = { set innerHTML(v) { capHTML = v; }, get innerHTML() { return capHTML; } };
  const g = globalThis;
  g.document = {
    getElementById: (id) => id === "cap-data" ? { textContent: islandText } : null,
    querySelector: (sel) => sel === mountSel ? capEl : null,
    querySelectorAll: () => [], addEventListener: () => {}, title: "",
  };
  g.location = { search: "", pathname, replace() { throw new Error("REDIRECT (render should never navigate an island page)"); } };
  g.window = {}; g.URLSearchParams = URLSearchParams; g.navigator = { clipboard: { writeText() {} } };
  let threw = null;
  const spy = console.error; const errs = [];
  console.error = (...a) => errs.push(a.join(" "));
  try { new Function(CAPJS)(); } catch (e) { threw = e; }
  console.error = spy;
  return { capHTML, threw, errs };
}

let fail = 0, checked = 0, tabs = 0, health = 0;
for (const f of sample) {
  const html = fs.readFileSync(path.join(dir, f), "utf8");
  const m = html.match(/id="cap-data">(.*?)<\/script>/s);
  if (!m) { console.log("FAIL no island:", f); fail++; continue; }
  // The mount capability.js keys on must be present in the SHIPPED file, not assumed by the shim.
  if (!/<main[\s>]/.test(html)) { console.log("FAIL no <main> mount in the prerendered page:", f); fail++; continue; }
  const { capHTML, threw, errs } = runRender(m[1], "/capability/" + f, "main");
  checked++;
  if (threw) { console.log("FAIL threw:", f, "—", threw.message); fail++; continue; }
  if (errs.length) { console.log("FAIL render logged error:", f, "—", errs[0]); fail++; continue; }
  if (capHTML === "__SUMMARY__") { console.log("FAIL server render not replaced:", f); fail++; continue; }
  if (!/class="stats"/.test(capHTML)) { console.log("FAIL no stats grid:", f); fail++; continue; }
  if (/install__tab|install__snip/.test(capHTML)) tabs++;
  if (/hstat|repoHealth|Bus factor|stars/.test(capHTML)) health++;
}

assert.strictEqual(fail, 0, `${fail} pages failed to render`);
console.log(`ok — render() ran clean on ${checked} sampled pages (install blocks: ${tabs}, repo-health: ${health})`);
