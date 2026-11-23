// Use the serving code to measure what an agent can buy from the last published snapshot.
import { readFileSync } from "node:fs";
import { safeForKit, selectKit } from "../functions/v0.1/kit.js";

const load = name => JSON.parse(readFileSync(new URL(`../web/data/${name}.json`, import.meta.url)));
const lookup = load("lookup");
const { tasks } = load("tags");
const interest = JSON.parse(readFileSync(0, "utf8"));
const byId = new Map(lookup.records.map(r => [r.id, r]));
// Compare evidence at publication. The request handler rechecks freshness at the time of purchase.
const at = Date.parse(lookup.generated_at);
const shelves = Object.entries(tasks).map(([task, ids]) => {
  const safe = ids.map(id => byId.get(id)).filter(r => r && safeForKit(r));
  const { picks, pins } = selectKit(safe, 5, at);
  const candidates = safe.filter(r => r.npm_pkg && r.npm_runnable !== 0)
    .sort((a, b) => (b.tashan_score || 0) - (a.tashan_score || 0)).slice(0, 5);
  return { task, picks, pins, candidates, interest: interest[task] || {} };
});

// Purchases and signed attempts precede unavailable paid requests and quotes. Then fill thin shelves.
shelves.sort((a, b) => {
  for (const stage of ["settled", "licensed", "attempted", "kit-unavailable", "quoted"]) {
    const delta = (b.interest[stage] || 0) - (a.interest[stage] || 0);
    if (delta) return delta;
  }
  return a.pins.length - b.pins.length || a.task.localeCompare(b.task);
});
const pack = rows => [...new Set(rows.map(r => r.id))];
const mapped = new Set(Object.values(tasks).flat());
const ready = lookup.records.filter(r => r.rated && safeForKit(r) && selectKit([r], 1, at).pins.length);
const unmapped = ready.filter(r => !mapped.has(r.id))
  .sort((a, b) => (b.npm_downloads || 0) - (a.npm_downloads || 0) || a.id.localeCompare(b.id));
const expertise = pack(shelves.flatMap(s => s.pins.filter(r => !r.expertise_verdict)));
const security = pack(shelves.flatMap(s => [...s.pins, ...s.candidates]));
console.log(JSON.stringify({
  generated_at: lookup.generated_at, expertise, tasks: pack(unmapped), security,
  mapped: shelves.length, available: shelves.filter(s => s.pins.length).length,
  one_pin: shelves.filter(s => s.pins.length === 1).length,
  without_kit: shelves.filter(s => !s.pins.length).map(s => s.task),
}));
