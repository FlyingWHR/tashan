// What we publish must contain what we import.
//
// tashan.mjs gained `import … from "./inventory.mjs"` at the top level while package.json's `files`
// array still listed three modules. npm pack honours `files`, so the next publish would have
// shipped a tarball whose entrypoint imports a file that is not in it — and a missing top-level
// import is not a broken subcommand, it is ERR_MODULE_NOT_FOUND on EVERY command, including
// `--help`. Nothing in the suite could see it: the source tree is complete, only the package is not.
//
// Run: node tests/test_cli_package.mjs
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const CLI = join(dirname(dirname(fileURLToPath(import.meta.url))), "cli");
const pkg = JSON.parse(readFileSync(join(CLI, "package.json"), "utf8"));
const shipped = new Set(pkg.files || []);
let fail = 0;
const ok = (c, what) => { console.log(`  ${c ? "ok  " : "FAIL"} ${what}`); if (!c) fail++; };

// Every entrypoint in `bin`, plus everything any of them imports, transitively.
const seen = new Set();
const queue = Object.values(pkg.bin || {}).map((p) => p.replace(/^\.\//, ""));
while (queue.length) {
  const file = queue.shift();
  if (seen.has(file)) continue;
  seen.add(file);
  let src = "";
  try { src = readFileSync(join(CLI, file), "utf8"); } catch { continue; }
  for (const m of src.matchAll(/^\s*import\s[^;]*?from\s+["'](\.\/[^"']+)["']/gm)) {
    queue.push(m[1].replace(/^\.\//, ""));
  }
}
for (const file of seen) {
  ok(shipped.has(file), `${file} is in package.json "files"`);
}

// And the reverse: nothing listed that is not there, which publishes a broken manifest just as well.
for (const f of shipped) {
  let there = true;
  try { readFileSync(join(CLI, f)); } catch { there = false; }
  ok(there, `"files" entry ${f} exists on disk`);
}

// Tests must never ship.
const tests = readdirSync(CLI).filter((f) => f.endsWith(".test.mjs"));
ok(tests.every((t) => !shipped.has(t)), `no test file is published (${tests.length} present locally)`);

console.log(fail ? `\n  ${fail} failing` : "\n  the tarball contains everything it imports");
process.exit(fail ? 1 : 0);
