#!/usr/bin/env bash
# tashan — run the whole test suite. Usage: bash tests/run.sh
# Exits nonzero if anything fails (CI-ready). Starts a throwaway web server if none is up.
set -u
cd "$(dirname "$0")/.."
fail=0

# 1. static site: structure, load budgets, SEO/AEO, CSP, analytics wiring
started=""
if ! curl -sf -o /dev/null http://127.0.0.1:4173/ 2>/dev/null; then
  ( cd web && python3 -m http.server 4173 >/dev/null 2>&1 ) &
  started=$!
  sleep 1
fi
echo "── site suite ─────────────────────────────────"
python3 tests/test_site.py --url http://127.0.0.1:4173 || fail=1
[ -n "$started" ] && kill "$started" 2>/dev/null

# 2. headless render: actually RUN capability.js against real data (catches JS-render bugs the HTML checks can't)
echo; echo "── capability render (headless) ───────────────"
node tests/test_render.mjs || fail=1

# 3. the firewall — the ranking can never be bought (scorer reads only public signal)
echo; echo "── firewall (ranking can't be bought) ─────────"
python3 tests/test_firewall.py || fail=1

# 3b. score shape — calibration must never reorder, anchors must never be corpus-relative
echo; echo "── score shape (order-preserving) ─────────────"
python3 tests/test_score.py || fail=1

# 3b2. the scorer version must move whenever the scoring does, or trend() compares two rulers
echo; echo "── scorer version lock ────────────────────────"
python3 tests/test_scorer_version.py || fail=1

# 3b3. every published `npx …` must name a package that resolves to us (shipped wrong twice)
echo; echo "── npx package name ───────────────────────────"
python3 tests/test_pkg_name.py || fail=1

# 3b4. type scale — 42 ad-hoc sizes, six of them under 10px, is how the rail became unreadable
echo; echo "── type scale (12px floor) ────────────────────"
python3 tests/test_type_scale.py || fail=1

# 3b5. the "✓ Official" badge is an endorsement claim — it must be namespace-provable
echo; echo "── official badge (endorsement claim) ─────────"
python3 tests/test_official.py || fail=1

# 3b6. a rename that touches the schema and not the prose — and leaves a sort reading a dead field
echo; echo "── terminology (retired names) ────────────────"
python3 tests/test_terminology.py || fail=1

# 3b7. the product tree must enumerate every surface — this is what makes "no loose ends" checkable
echo; echo "── product tree (every surface) ───────────────"
python3 tests/test_product_tree.py || fail=1

# 3b8. the security audit is the paid feature — every rule in it has to be right
echo; echo "── security scan (the paid feature) ───────────"
python3 tests/test_security_scan.py || fail=1

# 3c. config parser — a wrong capability id invents one row AND loses the real one
echo; echo "── config parser (capability_id) ──────────────"
python3 tests/test_scrape.py || fail=1

# 4. generated tier: asset versioning, hubs, skills, llms.txt, orphan pages
echo; echo "── hubs / SEO+GEO tier ────────────────────────"
python3 tests/test_hubs.py || fail=1

# 5. analytics collector field-shaping
echo; echo "── analytics collector ────────────────────────"
node functions/api/e.test.mjs 2>/dev/null || fail=1

# 5b. billing webhook — the signature check is a security boundary, it must fail closed
echo; echo "── polar webhook (signature) ──────────────────"
node functions/api/polar.test.mjs 2>/dev/null || fail=1

# 5c. the paywall — every way of getting paid data without paying must be closed
echo; echo "── licence gate (paywall) ─────────────────────"
node functions/api/license.test.mjs 2>/dev/null || fail=1

# 3. CLI pure logic
echo; echo "── cli ────────────────────────────────────────"
node cli/tashan.test.mjs || fail=1

# 6b. the MCP server — how agents reach us; protocol + ranking must not regress
echo; echo "── mcp server (agent surface) ─────────────────"
node cli/mcp.test.mjs || fail=1

echo
[ "$fail" = 0 ] && echo "ALL SUITES GREEN ✓" || echo "SOME SUITES FAILED ✗"
exit $fail
