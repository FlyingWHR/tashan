// node tests/test_badge_parity.mjs — the JS badge renderer must be byte-identical to the Python one.
//
// Badges moved from 6,453 static .svg files to a Pages Function because the file count was blocking
// deployment entirely. That leaves TWO implementations of one artifact, which is the exact failure
// this codebase has hit six times (prerender vs capability.js, slugify in four places, chrome.alias
// in three). Here the blast radius is other people's READMEs: a drift changes artwork already
// embedded on pages we do not control, and nothing on our side would look wrong.
//
// So: render every badge the corpus actually produces, in both languages, and diff the bytes.
import assert from "node:assert";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { badge } from "../functions/badge/[[path]].js";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

// Every (score, verdict) pair present in the live map, plus the edges that exercise the width maths.
const map = JSON.parse(fs.readFileSync(path.join(ROOT, "web", "data", "badges.json"), "utf8"));
// from pipeline/gen_badges.py's VCOLOR — the definition both renderers key off
const VERDICTS = [...fs.readFileSync(path.join(ROOT, "pipeline", "gen_badges.py"), "utf8")
  .match(/VCOLOR = \{([^}]*)\}/)[1].matchAll(/"([a-z]+)":/g)].map((m) => m[1]);
if (VERDICTS.length < 3) throw new Error("could not read VCOLOR from gen_badges.py — fix this test");

const pairs = new Map();
for (const [, row] of Object.entries(map)) pairs.set(`${row[0]}|${row[1] || ""}`, [row[0], row[1] || null]);
for (const s of [0, 1, 9, 10, 99, 100]) {
  pairs.set(`${s}|`, [s, null]);
  // READ THE LIVE VOCABULARY, do not restate it. This swept a hardcoded list that still contained
  // `wrapper` and `slop` after both were retired, so the suite failed on colours for verdicts
  // nothing can produce — and would equally have missed a NEW verdict added to only one renderer,
  // which is the failure this test exists for.
  for (const v of VERDICTS) pairs.set(`${s}|${v}`, [s, v]);
}
const cases = [...pairs.values()];

// One python3 process for all of them — 300+ subprocess spawns is the difference between a test that
// runs in the suite and one that gets skipped.
const py = `
import json, sys
sys.path.insert(0, ${JSON.stringify(path.join(ROOT, "pipeline"))})
import gen_badges
print(json.dumps([gen_badges.badge(t, v) for t, v in json.loads(sys.stdin.read())]))
`;
const want = JSON.parse(execFileSync("python3", ["-c", py], {
  input: JSON.stringify(cases), encoding: "utf8", maxBuffer: 64 * 1024 * 1024,
}));

let bad = 0;
cases.forEach(([t, v], i) => {
  const got = badge(t, v);
  if (got !== want[i]) {
    if (bad < 3) {
      console.log(`FAIL score=${t} verdict=${v}`);
      console.log("  python:", JSON.stringify(want[i].slice(0, 120)));
      console.log("  js    :", JSON.stringify(got.slice(0, 120)));
    }
    bad++;
  }
});
assert.strictEqual(bad, 0, `${bad}/${cases.length} badges differ between the Python and JS renderers`);

// The static era must be gone: a leftover .svg wins over the Function on the same path, so the badge
// would silently freeze at whatever score it held the day the file was written.
const dir = path.join(ROOT, "web", "badge");
const svgs = fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => f.endsWith(".svg")) : [];
assert.strictEqual(svgs.length, 0, `${svgs.length} static badge .svg still shadow the Function (e.g. ${svgs[0]})`);

console.log(`ok — ${cases.length} badge variants render identically in Python and JS, no static .svg shadowing`);
