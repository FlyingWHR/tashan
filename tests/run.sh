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

# 3b1v. ADVISORY, not gating: the endpoints we advertise to agents must answer agents. The fix is a
# Cloudflare zone setting (Bot Fight Mode), which this repo cannot change and the deploy token cannot
# either — so it must never block publishing. It prints loudly and does not set `fail`.
echo; echo "── agent access (advisory) ────────────────────"
python3 tests/test_agent_access.py || echo "  ^^ NOT gating: fix at dash.cloudflare.com -> tashan.sh -> Security -> Bots"

# 3b1w. pricing, terms and refunds must describe the same product — they described three
echo; echo "── entitlements (one product, one story) ──────"
python3 tests/test_entitlements.py || fail=1

# 3b1x. contrast is arithmetic — an audit found body text at 2.67:1 and it needed an eye to notice
echo; echo "── text contrast (WCAG AA) ───────────────────"
python3 tests/test_a11y_contrast.py || fail=1

# 3b1y. every claim a page makes about itself must be true of that page — an external audit found
# five simultaneous contradictions, all prose asserting what the code did differently
echo; echo "── page claims match page behaviour ───────────"
python3 tests/test_claims.py || fail=1

# 1c. the outreach drafts. The only content in this repo written to leave the building — its own
# opening rule is that a stale number in an outreach email is the sin the product exists to point at,
# and it went stale within four hours of being written.
python3 tests/test_outreach_numbers.py || fail=1

# 3b1z. the badge moved from 6,453 static files to a Function; two renderers, one artifact, and the
# blast radius is other people's READMEs
echo; echo "── badge parity (python == js) ────────────────"
node tests/test_badge_parity.mjs >/dev/null 2>&1 || { echo "  ↳ tests/test_badge_parity.mjs FAILED — rerunning to show why:"; node tests/test_badge_parity.mjs; fail=1; }

# 3b2a. prerender pure logic: description clipping + the .md dossier an answer engine reads
echo; echo "── prerender + markdown dossier ───────────────"
python3 pipeline/prerender.py --selftest || fail=1

# 3b2b. the retention series is the one thing that cannot be rebuilt — its shards must round-trip
echo; echo "── signal_history shards ──────────────────────"
python3 pipeline/snapshot_history.py --selftest || fail=1

# 3b2c. the DB is a cache in R2 now, not a blob in git — a truncated fetch must never look like a run
echo; echo "── db cache store ─────────────────────────────"
python3 pipeline/db_store.py --selftest || fail=1

# 3b2d. the key file must be served at the root or every submission is rejected
echo; echo "── indexnow ───────────────────────────────────"
python3 pipeline/indexnow.py --selftest || fail=1
python3 pipeline/gen_social.py --selftest || fail=1
python3 pipeline/funnel.py --selftest || fail=1
python3 pipeline/skill_doc.py --selftest || fail=1
python3 pipeline/check_payments.py --selftest || fail=1

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

# 3b9. a dead CTA costs the reader their intent — and two shipped
echo; echo "── links + unpublished targets ────────────────"
python3 tests/test_links.py || fail=1

# 3c0. a published grade must not contradict itself (four shipped that did)
echo; echo "── expertise grades (self-consistency) ────────"
python3 tests/test_expertise.py || fail=1

# 3c1. four of the first 39 icons rendered as nothing, with no error anywhere
echo; echo "── icons (visible at ship size) ───────────────"
python3 tests/test_icons.py || fail=1

# 3c1b. the category is a model's guess, not a derivation — measure it, and fail on a dead class
echo; echo "── classifier (macro recall, no dead class) ───"
python3 tests/test_classify.py || fail=1

# 3c1c. THE trust test: one capability, one set of facts, on all 8 surfaces that render it
echo; echo "── cross-surface consistency (trust) ─────────"
python3 tests/test_consistency.py || fail=1

# 3c2. the nav existed in 18 copies and had drifted into 6 variants — one definition now
echo; echo "── chrome (one navigation) ────────────────────"
python3 tests/test_chrome.py || fail=1

# 3c. config parser — a wrong capability id invents one row AND loses the real one
echo; echo "── config parser (capability_id) ──────────────"
python3 tests/test_scrape.py || fail=1

# 4. generated tier: asset versioning, hubs, skills, llms.txt, orphan pages
echo; echo "── hubs / SEO+GEO tier ────────────────────────"
python3 tests/test_hubs.py || fail=1

# 4b. the agent-readable surface. Agents are the audience this product is FOR, so what they can read
# without a browser gets the same guard as the human pages: the Index's server-rendered rows and
# ItemList, the markdown twins for every ranked shelf, the robots/_headers declarations that make
# them fetchable, and the MCP registry manifest staying in step with the package we publish.
echo; echo "── agent surface (no-JS, .md tier, registry) ──"
python3 tests/test_agent_surface.py || fail=1

# 5. analytics collector field-shaping
echo; echo "── analytics collector ────────────────────────"
node functions/api/e.test.mjs >/dev/null 2>&1 || { echo "  ↳ functions/api/e.test.mjs FAILED — rerunning to show why:"; node functions/api/e.test.mjs; fail=1; }

# 5b. billing webhook — the signature check is a security boundary, it must fail closed
echo; echo "── polar webhook (signature) ──────────────────"
node functions/api/polar.test.mjs >/dev/null 2>&1 || { echo "  ↳ functions/api/polar.test.mjs FAILED — rerunning to show why:"; node functions/api/polar.test.mjs; fail=1; }

# 5b2. server.json against the MCP registry's real schema — constraints, not just field names. The
# shallow check in test_agent_surface passed a manifest the registry rejected with a 422 for a
# description 84 characters over a documented limit.
echo; echo "── server.json (registry schema) ──────────────"
python3 tests/test_server_json.py || fail=1

# 5c. the per-question agent endpoints. This Function mounts on /v0.1/* and a Pages Function WINS the
# route over a static asset, so a fall-through mistake here does not degrade the new endpoints — it
# takes /v0.1/scores and /v0.1/servers, both published and linked from llms.txt, off the air.
echo; echo "── /v0.1 lookup + search ──────────────────────"
node functions/v0.1/route.test.mjs >/dev/null 2>&1 || { echo "  ↳ functions/v0.1/route.test.mjs FAILED — rerunning to show why:"; node functions/v0.1/route.test.mjs; fail=1; }

# 5d. the markdown dossier route. This Function mounts on /capability/*, where 9,013 real .html
# files live, so a fall-through mistake takes every capability page off the air — not just the .md
# tier. It also carries the JS half of the shard hash; if that drifts from prerender.py, every
# dossier 404s at once.
echo; echo "── /capability/*.md (sharded dossiers) ────────"
node functions/capability/path.test.mjs >/dev/null 2>&1 || { echo "  ↳ functions/capability/path.test.mjs FAILED — rerunning to show why:"; node functions/capability/path.test.mjs; fail=1; }

# 5c. the paywall — every way of getting paid data without paying must be closed
echo; echo "── licence gate (paywall) ─────────────────────"
node functions/api/license.test.mjs >/dev/null 2>&1 || { echo "  ↳ functions/api/license.test.mjs FAILED — rerunning to show why:"; node functions/api/license.test.mjs; fail=1; }
node functions/api/_x402.test.mjs >/dev/null 2>&1 || { echo "  ↳ functions/api/_x402.test.mjs FAILED — rerunning to show why:"; node functions/api/_x402.test.mjs; fail=1; }
node functions/api/_cdp.test.mjs 2>/dev/null || { node functions/api/_cdp.test.mjs; fail=1; }
node functions/api/_demand.test.mjs 2>/dev/null || { node functions/api/_demand.test.mjs; fail=1; }
node functions/v0.1/audit.test.mjs >/dev/null 2>&1 || { echo "  ↳ functions/v0.1/audit.test.mjs FAILED — rerunning to show why:"; node functions/v0.1/audit.test.mjs; fail=1; }
node functions/v0.1/kit.test.mjs >/dev/null 2>&1 || { echo "  ↳ functions/v0.1/kit.test.mjs FAILED — rerunning to show why:"; node functions/v0.1/kit.test.mjs; fail=1; }

# 5d. the account centre — who is signed in, and what of their record is safe to send back
echo; echo "── account centre (session + record) ──────────"
node --test functions/api/account.test.mjs >/dev/null 2>&1 || { node --test functions/api/account.test.mjs; fail=1; }

# 5d2. the device grant — a code must never be able to mint an entitlement on its own
echo; echo "── device login (RFC 8628 grant) ──────────────"
node functions/api/device.test.mjs 2>/dev/null || { node functions/api/device.test.mjs; fail=1; }

# 5d3. post-purchase sign-in — turns a checkout id into a session using a token that can read every
# customer's record. Almost every test here is about what it must refuse.
echo; echo "── post-purchase sign-in (checkout) ───────────"
node functions/api/checkout.test.mjs 2>/dev/null || { node functions/api/checkout.test.mjs; fail=1; }
node functions/api/buy.test.mjs 2>/dev/null || { node functions/api/buy.test.mjs; fail=1; }

# 5e. the audit's paid half — a paywall that fails open gives away the one thing $6 buys
echo; echo "── security detail API (paid) ─────────────────"
node --test functions/api/security.test.mjs >/dev/null 2>&1 || { node --test functions/api/security.test.mjs; fail=1; }
node --test functions/api/history.test.mjs >/dev/null 2>&1 || { node --test functions/api/history.test.mjs; fail=1; }

# 5e2. the paid series must carry the capability's movement, not our own recalibration
echo; echo "── history integrity (the moat) ───────────────"
python3 tests/test_history_integrity.py || fail=1

# 5f. every feature the pricing page sells must have code that delivers it
echo; echo "── promises (sold == delivered) ───────────────"
python3 tests/test_promises.py || fail=1

# 3. CLI pure logic
echo; echo "── cli ────────────────────────────────────────"
node cli/tashan.test.mjs || fail=1

# 6b. the MCP server — how agents reach us; protocol + ranking must not regress
echo; echo "── mcp server (agent surface) ─────────────────"
node cli/mcp.test.mjs || fail=1

echo
[ "$fail" = 0 ] && echo "ALL SUITES GREEN ✓" || echo "SOME SUITES FAILED ✗"
exit $fail
