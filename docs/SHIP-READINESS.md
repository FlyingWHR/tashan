# Ship readiness — walked as a customer, 31 Jul 2026

**Verdict: no. Not close.** Not because the paid feature is badly built — it works — but because
nothing a customer touches exists yet, and the data underneath it does not yet answer the question
the product is sold on.

Every line below was tested, not assumed.

---

## Blockers — a customer cannot begin

| # | What a customer does | What happens | Evidence |
|---|---|---|---|
| **B1** | Types `tashan.sh` | **NXDOMAIN.** The domain does not resolve. | `stilltime.io` on the same Cloudflare account resolves fine, so this is not local DNS |
| **B2** | Runs `npx tashan-cli doctor` | **404 from npm.** The package does not exist. | `registry.npmjs.org/tashan-cli` → 404. (`tashan` → 200, but that is a stranger's 2020 package with no bin) |
| **B3** | Signs in / clicks "unlock detail" | **503.** No Cloudflare deployment, no KV, no secrets → `/api/account`, `/api/history`, `/api/security` all dead | no `.wrangler` state; task #11 open |
| **B4** | Completes checkout | Lands on Polar's default page, not `/welcome.html` | task #22 open; the checkout link itself is valid (307) |

B1 and B2 mean **every documented command and every URL in the product, the README, the pricing page
and the CLI's own output is dead.** Nothing downstream can be evaluated by a real user.

---

## Data — would ship unconvincing even once deployed

Ran `doctor` against a real machine: **10 servers, 113 skills.**

```
  + nothing deprecated, archived or abandoned.
  11 catalogued, unrated · 97 not in the index
```

**Zero findings.** Nothing for Pro to unlock, so the upsell correctly never appears — and the free
tool told this user nothing either.

**Five of nine servers were not in the index at all**, and they are not obscure:

| in the config | in the index? |
|---|---|
| `@playwright/mcp` | **no** — Microsoft's official Playwright server |
| `@21st-dev/magic` | **no** |
| `@morph-llm/morph-fast-apply` | **no** |
| `freecad-mcp` | registry-only, unscored |
| `Figma` (Cursor) | **no** |

Widened to a list of well-known servers: **13 of 19 present.** Missing: `@playwright/mcp`,
`@21st-dev/magic`, `@browserbasehq/mcp`, `@sentry/mcp-server`, `@stripe/mcp`,
`@elastic/mcp-server-elasticsearch`. These are first-party servers from Microsoft, Sentry, Stripe and
Elastic — exactly the ones a buyer would check first to decide whether we know what we are talking
about. 5,788 measured capabilities does not help if the nine on the buyer's own machine are missing.

Also unresolved and already documented:

- **Trend** — 2 comparable days; needs 30. See `FEATURE-AUDIT.md`.
- **Categories** — 61% of the board in two of fifteen shelves, 61% classifier accuracy.

---

## Access — who can actually read it

| Surface | Static HTML a crawler / no-JS reader gets |
|---|---|
| `/pricing.html` | 3,870 chars — real content ✓ |
| `/capability/*` | 1,120 chars incl. the security audit ✓ (fixed today) |
| `/account.html` | 21 chars — inherently dynamic, `noindex` ✓ |
| **`/` the Index** | **2,003 chars, and not one capability name** ✗ |

The homepage — the highest-authority page, the one that ranks for the brand — renders its board
entirely in JavaScript. A crawler gets the hero headline and ASCII ridge art. The capability pages
and hubs are prerendered; the Index is not.

No `web/404.html`, so a mistyped URL gets Cloudflare's default page.

---

## What IS ready

Worth stating plainly, because it is most of the product:

- The **security audit** — scanner, 100% of npm-backed capabilities, gated detail endpoint with 10
  tests, web reveal, CLI reveal, and the free/paid line enforced in both directions.
- **Cross-surface consistency** — one capability, one set of facts, asserted across 8 surfaces on
  every field the inline payload carries.
- The **account centre**, the **dossier**, the **hubs**, the **badges**, `llms.txt`, the MCP server.
- 29 test suites, green.

---

## The order I would fix them

1. **B1 + B2** — register/point the domain, publish `tashan-cli`. Until both, there is no product to
   evaluate. Everything else is unobservable.
2. **B3** — `wrangler login`, KV namespace, `POLAR_ORG_ID`, then `push_security.py` and
   `push_history.py`. This lights up the entire paid tier.
3. **Ingest the servers people actually run.** `@playwright/mcp` being absent is worse for trust than
   any missing feature: it is the first thing a buyer checks. Coverage of the top ~100 by real-world
   usage matters more than 5,788 rows of tail.
4. **B4**, a `404.html`, and prerendering the Index's top rows.
5. Only then: trend (at ~30 clean days) and the taxonomy.

**Steps 1–3 are the difference between "a good product nobody can reach" and shippable.** None of
them is a code problem; 1, 2 and 4 are account actions only you can take.
