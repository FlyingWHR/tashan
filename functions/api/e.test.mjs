// node functions/api/e.test.mjs  — validates the analytics collector's field shaping (no deps).
import { toDataPoint } from "./e.js";
import assert from "node:assert";

// a normal pageview
let d = toDataPoint({ e: "pageview", p: "/capability/context7.html", r: "google.com", w: "lg", s: "abc123" }, { country: "US" });
assert.deepStrictEqual(d.indexes, ["pageview"]);
assert.strictEqual(d.blobs[0], "pageview");
assert.strictEqual(d.blobs[1], "/capability/context7.html");
assert.strictEqual(d.blobs[2], "google.com");
assert.strictEqual(d.blobs[6], "US");
assert.strictEqual(d.blobs[7], "abc123");
assert.deepStrictEqual(d.doubles, [1]);

// hostile / oversized input is clamped, never throws
let big = toDataPoint({ e: "x".repeat(500), p: "/".repeat(9999), k: "y".repeat(9999) }, {});
assert.ok(big.blobs[0].length <= 32, "event clamped");
assert.ok(big.blobs[1].length <= 128, "path clamped");
assert.ok(big.blobs[3].length <= 128, "key clamped");

// missing fields → empty strings, still a valid row
let empty = toDataPoint({ e: "conav" }, null);
assert.strictEqual(empty.blobs[1], "");
assert.strictEqual(empty.blobs[6], "");
assert.deepStrictEqual(empty.doubles, [1]);

console.log("ok — e.js field shaping (3 cases)");
