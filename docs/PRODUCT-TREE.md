# Product tree

Every surface this product exposes, what it is for, and what it reads. Regenerate with
`python3 pipeline/gen_product_tree.py`; `tests/test_product_tree.py` fails when a route
exists on disk with no purpose written here.

Derived columns come from disk on every run. **Purpose** is hand-written in
`pipeline/gen_product_tree.py` — a page nobody can describe in one line should not exist.

## Pages

| Route | Purpose | JS | Data | Gate | Inbound |
|---|---|---|---|---|---|
| `/index.html` | The Index. Find a capability by job or category, ranked and audited. | hero, index, ridge, site, terminal | categories.json, index.json, tags.json, tasks.json | free | 92 |
| `/methodology.html` | How every number is derived, so the score is re-checkable. | methodology, site, terminal | index.json | free | 50 |
| `/about.html` | Why a rater that sells nothing it measures is the only kind worth reading. | site, terminal | index.json | free | 43 |
| `/start.html` | How to use it: the CLI, the MCP server, the plugin. | site, terminal | capabilities.json, index.json | free | 43 |
| `/pricing.html` | What Pro costs and exactly what it adds. | site, terminal | index.json | sells | 42 |
| `/refunds.html` | Cancellation and the 7-day refund. | site, terminal | index.json | post-sale | 25 |
| `/requests.html` | Ask for a capability to be measured. | requests, site, terminal | index.json, requests.json | free | 23 |
| `/support.html` | How to get help, and what we can see when you ask. | site, terminal | index.json | free | 23 |
| `/for-hosts.html` | For IDEs and agent hosts: swap one base URL, get the measurement. | site, terminal | index.json | free | 22 |
| `/privacy.html` | What we collect, which is close to nothing. | site, terminal | index.json | free | 21 |
| `/terms.html` | Terms of service. | site, terminal | index.json | free | 21 |
| `/browse.html` | Parent index for every category and task hub — the full taxonomy. | — | — | free | 20 |
| `/capability.html` | Client-side dossier fallback (?id=). Prerendered twins are the canonical URLs. | capability, site, terminal | index.json | free | 0 |
| `/welcome.html` *(noindex)* | Post-checkout: activate the licence. noindex, reached only from Polar. | site, terminal | index.json | post-sale | 0 |

## Generated trees

| Route pattern | Pages | Generator |
|---|---|---|
| `/capability/*.html` | 5,788 | `pipeline/prerender.py` |
| `/category/*.html` | 15 | `pipeline/gen_hubs.py` |
| `/task/*.html` | 53 | `pipeline/gen_hubs.py` |
| `/learn/*.html` | 7 | `pipeline/gen_content.py` |

## Non-page surfaces

| File | Kind | Exposes |
|---|---|---|
| `cli/tashan.mjs` | CLI | search / top / info / add / doctor / activate / mcp |
| `cli/mcp.mjs` | MCP server | find_capability / check_capability / audit_config |
| `functions/api/history.js` | Paid API | score history, licence-gated |
| `functions/api/polar.js` | Webhook | Polar billing events -> entitlement |
| `functions/api/_license.js` | Gate | shared licence validation, fails closed |
| `plugin/.claude-plugin/plugin.json` | Claude Code plugin | installs the MCP server |
| `web/llms.txt` | Answer-engine feed | site summary + top capabilities |

## Guards

Each of these exists because the failure it prevents already shipped once.

- `cli/mcp.test.mjs` — node cli/mcp.test.mjs — protocol + rendering for the MCP server. No network.
- `cli/tashan.test.mjs` — node cli/tashan.test.mjs  — pure-logic tests for the CLI (no network, no deps).
- `functions/api/e.test.mjs` — node functions/api/e.test.mjs  — validates the analytics collector's field shaping (no deps).
- `functions/api/license.test.mjs` — The paywall. Run: node functions/api/license.test.mjs
- `functions/api/polar.test.mjs` — Polar webhook verification — the security boundary. Run: node functions/api/polar.test.mjs
- `tests/test_expertise.py` — A published grade must not contradict itself.
- `tests/test_firewall.py` — The firewall test — the ranking can never be bought.
- `tests/test_hubs.py` — tashan — the generated content tier: asset versioning, category hubs, skills, llms.txt.
- `tests/test_icons.py` — Every taxonomy id has an icon, and no icon is invisible at the size it ships.
- `tests/test_links.py` — Every link and every install instruction must lead somewhere that exists.
- `tests/test_official.py` — The "✓ Official" badge is an endorsement claim. It must be provable from the namespace.
- `tests/test_pkg_name.py` — Every `npx …` invocation we publish must name a package that actually resolves to US.
- `tests/test_product_tree.py` — docs/PRODUCT-TREE.md must describe every surface that exists, and describe none that don't.
- `tests/test_score.py` — The two score-shape properties everything else rests on.
- `tests/test_scorer_version.py` — SCORER_VERSION must change whenever the scoring changes.
- `tests/test_scrape.py` — capability_id() — the config parser that decides what a row IS.
- `tests/test_security_scan.py` — The security audit is the paid feature. Every rule in it has to be right, or we sell noise.
- `tests/test_site.py` — tashan site test suite — structure, load budgets, SEO/AEO, CSP.
- `tests/test_terminology.py` — Retired names must not survive in user-visible copy, and sorts must read fields that exist.
- `tests/test_type_scale.py` — Type scale: every font-size comes from the scale, and nothing renders under 12px.
