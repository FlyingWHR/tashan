# Product tree

Every surface this product exposes, what it is for, and what it reads. Regenerate with
`python3 pipeline/gen_product_tree.py`; `tests/test_product_tree.py` fails when a route
exists on disk with no purpose written here.

Derived columns come from disk on every run. **Purpose** is hand-written in
`pipeline/gen_product_tree.py` — a page nobody can describe in one line should not exist.

## Pages

| Route | Purpose | JS | Data | Gate | Inbound |
|---|---|---|---|---|---|
| `/index.html` | The Index. Find a capability by job or category, ranked and audited. | hero, index, ridge, site, terminal | board.json, capabilities.json, categories.json, index.json, tags.json, tasks.json | free | 98 |
| `/account.html` *(noindex)* | Your plan, machines, licence key and invoices — read live from /api/account. | account, signin, site, terminal | board.json, index.json, tasks.json | post-sale | 58 |
| `/start.html` | How to use it: the CLI, the MCP server, the plugin. | site, terminal | board.json, capabilities.json, index.json, tasks.json | free | 53 |
| `/browse.html` | Parent index for every category and task hub — the full taxonomy. | — | — | free | 52 |
| `/pricing.html` | What Pro costs and exactly what it adds. | site, terminal | board.json, index.json, tasks.json | sells | 50 |
| `/methodology.html` | How every number is derived, so the score is re-checkable. | methodology, site, terminal | board.json, coverage.json, index.json, tasks.json | free | 35 |
| `/for-hosts.html` | For IDEs and agent hosts: swap one base URL, get the measurement. | site, terminal | board.json, index.json, tasks.json | free | 27 |
| `/refunds.html` | Cancellation and the 7-day refund. | site, terminal | board.json, index.json, tasks.json | post-sale | 27 |
| `/requests.html` | Ask for a capability to be measured. | requests, site, terminal | board.json, coverage.json, index.json, requests.json, tasks.json | free | 27 |
| `/support.html` | How to get help, and what we can see when you ask. | site, terminal | board.json, index.json, tasks.json | free | 26 |
| `/about.html` | What tashan measures, where it is going, and the principles the scoring follows. | site, terminal | board.json, index.json, tasks.json | free | 25 |
| `/compare.html` | Pick any two capabilities and see them side by side. The 395 pre-generated pairs cover what people search for; this covers the comparison they have. | compare, site, terminal | board.json, compare.json, index.json, tasks.json | free | 25 |
| `/privacy.html` | What we collect, which is close to nothing. | site, terminal | board.json, index.json, tasks.json | free | 25 |
| `/terms.html` | Terms of service. | site, terminal | board.json, index.json, tasks.json | free | 25 |
| `/capability.html` | Client-side dossier fallback (?id=). Prerendered twins are the canonical URLs. | capability, site, terminal | board.json, index.json, tasks.json | free | 1 |
| `/404.html` *(noindex)* | Real 404 with a route back in. noindex; without it Pages served the homepage at status 200 for every unknown URL. | site, terminal | board.json, index.json, tasks.json | free | 0 |
| `/activate.html` *(noindex)* | Approve a device that ran `tashan login`. noindex; the browser half of the RFC 8628 grant, so a licence key is typed once ever, not per machine. | activate, signin, site, terminal | board.json, index.json, tasks.json | post-sale | 0 |
| `/welcome.html` *(noindex)* | Post-checkout: activate the licence. noindex, reached only from Polar. | signin, site, terminal, welcome | board.json, index.json, tasks.json | post-sale | 0 |

## Generated trees

| Route pattern | Pages | Generator |
|---|---|---|
| `/capability/*.html` | 8,966 | `pipeline/prerender.py` |
| `/category/*.html` | 83 | `pipeline/gen_hubs.py` |
| `/task/*.html` | 64 | `pipeline/gen_hubs.py` |
| `/role/*.html` | 23 | `pipeline/gen_hubs.py` |
| `/compare/*.html` | 389 | `pipeline/gen_compare.py` |
| `/learn/*.html` | 7 | `pipeline/gen_content.py` |

## Non-page surfaces

| File | Kind | Exposes |
|---|---|---|
| `cli/tashan.mjs` | CLI | search / top / info / add / doctor / activate / mcp |
| `cli/mcp.mjs` | MCP server | find_capability / check_capability / audit_config |
| `functions/api/account.js` | Account | session + the customer's own record |
| `functions/api/checkout.js` | Post-purchase sign-in | checkout id -> session, single-use |
| `functions/api/device.js` | Device login | RFC 8628 grant for `tashan login` |
| `functions/api/history.js` | Paid API | score history, licence-gated |
| `functions/api/polar.js` | Webhook | Polar billing events -> entitlement |
| `functions/api/_license.js` | Gate | shared licence validation, fails closed |
| `plugin/.claude-plugin/plugin.json` | Claude Code plugin | installs the MCP server |
| `web/llms.txt` | Answer-engine feed | site summary + top capabilities |

## Guards

Each of these exists because the failure it prevents already shipped once.

- `cli/mcp.test.mjs` — node cli/mcp.test.mjs — protocol + rendering for the MCP server. No network.
- `cli/tashan.test.mjs` — node cli/tashan.test.mjs  — pure-logic tests for the CLI (no network, no deps).
- `functions/api/account.test.mjs` — node --test functions/api/account.test.mjs
- `functions/api/checkout.test.mjs` — The post-purchase sign-in. This endpoint turns a checkout id — a value that rides in a redirect
- `functions/api/device.test.mjs` — The device-authorisation grant. This is a credential path, so the tests are about what MUST NOT
- `functions/api/e.test.mjs` — node functions/api/e.test.mjs  — validates the analytics collector's field shaping (no deps).
- `functions/api/license.test.mjs` — The paywall. Run: node functions/api/license.test.mjs
- `functions/api/polar.test.mjs` — Polar webhook verification — the security boundary. Run: node functions/api/polar.test.mjs
- `functions/api/security.test.mjs` — node --test functions/api/security.test.mjs
- `tests/test_a11y_contrast.py` — Every text colour token must be readable on the background it is used against.
- `tests/test_agent_access.py` — The endpoints we advertise to agents must actually answer agents.
- `tests/test_agent_surface.py` — Everything an agent reads must be reachable, current, and true.
- `tests/test_chrome.py` — The navigation exists once. Every page renders that one definition, byte for byte.
- `tests/test_claims.py` — Every claim a page makes about itself must be true of that page.
- `tests/test_classify.py` — The category is a published claim, so its accuracy is a number we hold ourselves to.
- `tests/test_consistency.py` — One capability, one set of facts, on every surface that renders it.
- `tests/test_doc_signals.py` — The self-declared-unmaintained detector, which is allowed to cost a capability 70% of its
- `tests/test_entitlements.py` — Pricing, Terms and Refunds must describe the same product.
- `tests/test_expertise.py` — A published grade must not contradict itself.
- `tests/test_firewall.py` — The firewall test — the ranking can never be bought.
- `tests/test_history_integrity.py` — The paid series must contain the capability's movement, not ours.
- `tests/test_hubs.py` — tashan — the generated content tier: asset versioning, category hubs, skills, llms.txt.
- `tests/test_icons.py` — Every taxonomy id has an icon, and no icon is invisible at the size it ships.
- `tests/test_links.py` — Every link and every install instruction must lead somewhere that exists.
- `tests/test_official.py` — The "✓ Official" badge is an endorsement claim. It must be provable from the namespace.
- `tests/test_outreach_numbers.py` — Every number in docs/OUTREACH.md must still be true of the database.
- `tests/test_pkg_name.py` — Every `npx …` invocation we publish must name a package that actually resolves to US.
- `tests/test_product_tree.py` — docs/PRODUCT-TREE.md must describe every surface that exists, and describe none that don't.
- `tests/test_promises.py` — Every feature the pricing page sells must have code that delivers it.
- `tests/test_score.py` — The two score-shape properties everything else rests on.
- `tests/test_scorer_version.py` — SCORER_VERSION must change whenever the scoring changes.
- `tests/test_scrape.py` — capability_id() — the config parser that decides what a row IS.
- `tests/test_security_scan.py` — The security audit is the paid feature. Every rule in it has to be right, or we sell noise.
- `tests/test_server_json.py` — server.json must satisfy the MCP registry's schema — constraints included, not just field names.
- `tests/test_site.py` — tashan site test suite — structure, load budgets, SEO/AEO, CSP.
- `tests/test_terminology.py` — Retired names must not survive in user-visible copy, and sorts must read fields that exist.
- `tests/test_type_scale.py` — Type scale: every font-size comes from the scale, and nothing renders under 12px.
