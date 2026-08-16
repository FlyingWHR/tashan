# Do this next — the things only you can do

*Rewritten 15 Aug 2026. Everything doable from a keyboard has been done. What is left needs an
identity, a dashboard, or money in an account. The history below §1 is kept for its reasoning; this
header is the current state and supersedes any summary further down.*

## ✅ The payment path is working. Nothing on it is waiting for you.

**The success_url was on this list for weeks and should never have been.** It was described as a
text box only a human could edit. `POLAR_ORG_TOKEN` has been a Pages secret the whole time, it is
already used to exchange a checkout for a licence, and Polar exposes `PATCH /v1/checkout-links/{id}`.
So `/api/buy` now sits between the button and Polar: it verifies that field, repairs it if wrong,
and redirects — and if anything at all fails, the customer still reaches the checkout.

Verified live, 15 Aug, end to end:

```
python3 pipeline/check_payments.py     # 21 passing, 0 failing, 1 unverified (x402, see below)
```

Both checkout links now return `https://tashan.sh/api/checkout?checkout_id=…`, read back from
Polar's own checkout page. The annual button was walked in a browser: it lands on "tashan Pro
(annual) — 7 days free, then $50/year", which is the product and the price the page advertises.
KV holds the history and security shards (last nightly: `push-paid` 21s, `push-history` 24s), so a
licence holder gets real data the moment they subscribe.

The rule this cost us: **before escalating a config change, check whether a credential the project
already holds can make it.** Genuinely CEO-only means an account that holds money, or a permission
the current token cannot grant itself. Both remaining items are that.

## A third, small one: the CLI has fixes that are not published

`tashan-cli@0.1.4` is what `npx` serves today, and two behaviour changes sit unpublished in the
repo. Neither is urgent; both are user-facing:

- **Confirmed malware now leads with the verdict.** `check_capability` on claude-cup used to open
  "tashan score 77/100 · 4,837,320 downloads/wk · active" and put "this package IS the attack"
  three lines below. It now opens `DO NOT INSTALL`, and the score is gone at the source.
- **A malformed tool call is reported as an error.** Calling `find_capability` with the wrong
  property name answered `No measured capability matches "undefined"` — indistinguishable from a
  real miss, so an agent would relay "nothing like this exists".

Actions → **publish cli** → Run workflow, `dry_run` checked first. The run summary says
`⚠️ DRY RUN — nothing was published` or `✅ Published tashan-cli@x.y.z`, so it cannot lie to you
about which it did. Bump `cli/package.json` and `server.json` together — `tests/test_agent_surface.py`
fails if they drift.

## ✅ x402 is LIVE ON BASE MAINNET (16 Aug 2026) — real money

    scheme  exact          network  eip155:8453
    asset   0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913   (USDC, Circle-confirmed)
    payTo   0x813e91688330cB03BD9F4e710A28C4B6207e9fC1
    extra   {name: "USD Coin", version: "2"}

`X402_FACILITATOR=https://facilitator.openx402.ai python3 pipeline/check_payments.py` → **25
passing, 0 failing**, including three checks that exist because this is the step that cannot be
undone:

- **payTo and asset pass their EIP-55 checksums** (`pipeline/eip55.py`). A single mistyped character
  in a mixed-case address fails to verify, so this is what stands between a wallet typo and funds
  landing somewhere nobody controls. keccak-256 is hand-rolled — hashlib's sha3_256 is a DIFFERENT
  algorithm — and pinned to the canonical vector plus all four EIP-55 worked examples.
- **Our asset, EIP-712 name and version match the facilitator's `/supported`.** The name is
  "USD Coin", not "USDC"; it defaulted to the ticker until 16 Aug and would have failed every
  signature while looking perfectly configured.

**Pages secrets need a REDEPLOY.** Setting them changes nothing until `wrangler pages deploy` runs,
and in between the check reports "dormant", which reads exactly like a bad value.

**Still unproven: that a payment SETTLES.** We quote correctly on mainnet and nobody has paid yet.
The first real payment is the only thing that proves the loop, and it will arrive from a stranger's
agent rather than from a test.

**To roll back to testnet**, two secrets and a redeploy: `X402_NETWORK` → `eip155:84532`,
`X402_ASSET` → `0x036CbD53842c5426634e7929541eC2318f3dCF7e`.

## The two that are really yours

**Add `Account Analytics: Read` to the Cloudflare API token.** Every click has been recorded since
9 Aug and nothing has ever read one. `pipeline/funnel.py` runs in the nightly and prints
views → offer clicks → checkout into the run summary; without that permission it prints the
permission error instead and exits 0 rather than failing the pipeline.

**Create a wallet, if per-call agent payment is wanted.** `docs/X402.md` is the whole procedure:
four secrets and a verification curl. The protocol layer, the priced endpoints (`/v0.1/kit` at
$0.25, `/v0.1/audit` at $0.05) and 40+ tests are built and dormant — they quote no payment option
that cannot be settled, deliberately. Context for whether it is worth doing: 172 capabilities in our
own corpus already advertise per-call payment, 144 naming x402, and one of them exists purely to
discover 170+ x402 services.

## One decision I made without asking, and why — you can reverse it

**I removed `security-detail` ($0.01) from the price ladder and made `/api/security` free.** It sold
data we already publish for nothing: `redact_paid()` puts advisory ids, severities, fixing versions
and the install command in the public export, and `/v0.1/lookup?name=…` returns every one of them
per capability with no account. The 402 quoting that price listed `/data/lookup.json` in its own
`free` block as a source of the same fields — we were quoting a price beside a pointer to the
giveaway.

I treated this as enforcing policy rather than setting it, because the policy was already written
down in two places: `redact_paid()` ("naming a risk and then charging to say which risk is a worse
position than not scanning at all") and `history.js` ("every score stays free forever… what is
genuinely not obtainable free is the SERIES"). `/api/security` was the one endpoint contradicting
both. No customer was affected — there are none yet on that endpoint.

What is left is a ladder with one rule, which is what makes it defensible to an agent developer who
checks: **every priced resource sells TIME or ASSEMBLY, never the current state of anything.**
`capability-history` $0.01, `config-audit` $0.05, `capability-kit` $0.25. A test now fails if
anything that sells current state reappears on it.

**If you want the revenue line back, the honest version exists:** sell the finding's *history* —
"this advisory appeared on 9 Aug; before that this package was clean" — which is time, which we
have in `change_events`, and which nothing free answers. That is a build, not a config change, and
I did not start it because it is a product decision rather than a correctness fix.

## The one number that decides how good the agent product is

**Task coverage is 21.6%** — 3,121 of 14,419 scored capabilities carry a task tag. The other 11,298
are invisible to `/task/*`, `/role/*`, `/browse` and to `POST /v0.1/kit`, which is the endpoint an
agent pays $0.25 to call.

What that costs, concretely: ask the live kit endpoint "I need to scrape websites" and it returns
`exa-mcp-server` (86) first and never mentions `firecrawl-mcp` (93), the highest-scoring scraping
server we measure. Not a ranking bug — firecrawl-mcp simply carries no scraping tag, because its
author's npm keywords are `web-search, web-data, web-interaction` and the free pass only trusts
what the author declared.

I tried to close this without spending anything and **measured that it does not work**: a
description-only lexical rule would have tagged 2,759 rows at ~38% precision — "Model **Context**
Protocol" → prompt-engineering, currency "**conversion**" → conversion-optimization. That is the
second time this has been measured and rejected; the reasoning is written into
`pipeline/tag_capabilities.py` so it is not attempted a third time. What I did instead was
attributable: 14 synonyms added to the taxonomy for author keywords that mapped to nothing
(`scraper`, `crawl`, `screenshot`, `deploy`, `text to speech`), covering 87 keyword occurrences.

**The only measured way to close the rest is `--grade`, which needs `ANTHROPIC_API_KEY`.** That is a
cost decision, not an engineering gap. Sonnet, ~60 capabilities a run, one call each.

## Deliberately not done, with the reasoning written down

- **`ANTHROPIC_API_KEY` for batch grading** — on hold until there is a paying user; grading runs
  in-session at no API cost. 2,889 capabilities graded that way. See the section above for what the
  hold actually costs now that it has been measured rather than assumed.
- **A verdict word for skills** — `docs/GRADING-RUBRIC.md` has the measurement: the server rubric
  lands skills at 2.7% `deep` against servers' 16–20%, because a skill has no tools. A validated
  replacement criterion exists (16.8%). What ships instead is facts, not a grade, because a new
  public scale over 40% of the corpus is a decision, not a chore.
- **Raising `CLASSIFY_MARGIN`** — measured in `pipeline/classify.py`: 0.4 buys 11 points of
  precision for 21 points of coverage. Not taken; the hand-classified head of each hub is what a
  reader sees.
- **Description bigrams in the classifier** — +2.5 accuracy on 248 held-out rows, which is six
  answers and inside the noise. Left as `CLASSIFY_BIGRAM=1` with the table beside it.

---

## 0b · Enable R2 — ✅ DONE 8 Aug 2026 (`r2://tashan-state/tashan.db`)

*The database was 98.8 MiB against GitHub's hard 100 MiB blob limit while being committed nightly,
so the failure was going to land on `git push` after the pipeline had already run — and a rejected
push means that day's history shard never lands. R2 is enabled, the bucket exists, 98.8 MiB is
stored, and the file is untracked. Proven the only way worth proving it: the local database was
deleted and pulled back byte-identical (same sha256, all four tables intact).*

*`tests/test_history_integrity.py` now fails if `data/tashan.db` is ever tracked again — the size
limit only bites at push time, so a regression would otherwise stay invisible until a day was lost.*

The daily workflow already calls `db_store.py pull` before the pipeline and `push` after, both
`continue-on-error` so nothing breaks while R2 is off. Losing the bucket later costs one night of
change events and a slow re-fetch — never the series, which is sharded to `data/history/` and
restored on every run.

*Why not LFS: it keeps every version, so a 98 MiB nightly commit accrues ~2.9 GiB/month against a
10 GB allowance — free for about three months, then a bill that only grows. Why not Postgres or D1:
nothing serves a request from this database, so there is no concurrency to solve.*

---

## 0 · Publish `tashan-cli@0.1.4` — ✅ DONE 9 Aug 2026, on both channels

*`tashan-cli@0.1.3` told every user with Microsoft's official Playwright MCP server installed that
it had been **"REMOVED from the MCP registry — spam, malware or illegal content"**. It was never
removed from anything: `doctor` fell back to matching the bare leaf name `mcp` after the scoped
lookup missed, and `mcp` resolves to a different, delisted package.*

*Fixed in 0.1.4 (`cli/doctor.mjs` refuses generic leaves: `mcp`, `server`, `cli`, `core`, …),
verified the way the bug was found — packed, installed from the tarball, run against a real config.*

**npm: 0.1.4. MCP registry: 0.1.4, `isLatest: true`.** Both channels now serve the fix; 0.1.3 stays
in the registry as version history with `isLatest: false`, which is how it versions.

Two traps this hit on the way, both now fixed in the workflow rather than in a person's memory:

- **The publish workflow went red after succeeding.** It asserted `attestations: true`, which can
  never hold — npm builds provenance from a PUBLIC source repo and this one is private. So a working
  publish reported failure, which is a fair reason to assume publishing is broken and not retry.
- **A dry run looked exactly like a real one.** `dry_run` defaults to checked; `publish` and its
  verification were both skipped and the run still showed green. The run summary now says
  `⚠️ DRY RUN — nothing was published` or `✅ Published tashan-cli@x.y.z`.

---

## 0c · Add `ANTHROPIC_API_KEY` — grading has never once run in the loop

`gh secret list` shows only `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`. The daily workflow
passes `ANTHROPIC_API_KEY` to two stages and neither has ever had it, so both skip every night:

- `grade_expertise.py` — instruction depth, the grade shown on every dossier and hub
- `tag_capabilities.py --grade` — the job/role mapping that `/browse`, `/task/*` and `/role/*` rank on

Coverage is **858 of 9,643 scored capabilities (8.9%)**, and essentially all of it was graded by
hand. That is the weakest part of the *free* product, and the free product is what does the
acquisition — an agent asking "which of these is documented well enough to use" gets `null` nine
times in ten.

The grader was also reading only the first 14,000 characters of every document until 8 Aug, which
biased it against exactly the thorough READMEs that earn the top band; it now reads the full file
plus the in-repo docs a README links to. So this is worth switching on now rather than before.

**Do** — GitHub → Settings → Secrets and variables → Actions → **New repository secret**

| field | value |
|---|---|
| Name | `ANTHROPIC_API_KEY` |
| Secret | a key from console.anthropic.com |

Cost is small and bounded: Sonnet, ~60 capabilities a run, one call each. Verify on the next daily
run — the log currently prints `SKIPPED — ANTHROPIC_API_KEY is not set`; it should instead start
printing grades. `python3 pipeline/grade_expertise.py --dry-run` checks the prompt path with no key.

---

## 1 · Nothing to do — it was never our setting ✅ resolved 8 Aug 2026

Two days were spent turning off Bot Fight Mode and Browser Integrity Check because `/llms.txt` and
`/v0.1/*` answered `403 error 1010` to a stdlib Python client. Neither was the cause. Measured
against third parties, which is the test that should have been run first:

| user-agent | tashan.sh | pages.dev | cloudflare.com | discord.com |
|---|---|---|---|---|
| `Python-urllib/3.14` | 403 | 403 | **403** | **403** |
| `python-requests/2.31` | 200 | 200 | — | — |
| `curl/8.4.0` | 200 | 200 | 200 | 200 |

Cloudflare refuses the literal string `Python-urllib` everywhere it sits in front of. No setting on
this account changes it, and `error 1010` was diagnosed as Browser Integrity Check from the code
alone — wrongly.

**The real scope is tiny:** only `urllib.request.urlopen()` with its default header. `requests` —
what nearly every Python integration uses — works, as do curl, node-fetch, Go and every named AI
crawler. `llms.txt` now tells callers to send a User-Agent, which is the actual fix and is one line.

Verify: `python3 tests/test_agent_access.py` → AGENT ACCESS OK.

## 2 · npm Trusted Publishing — ✅ DONE 7 Aug 2026 (`tashan-cli@0.1.3`)

*Published over OIDC with no token. Provenance did NOT land and cannot: npm builds the
attestation from a public source repo and this one is private. `start.html` says so
plainly rather than claiming a fix; making the CLI attestable means publishing it from a
public repository, which is a decision, not a task.*

<details><summary>original instructions</summary>

**What it costs today:** `tashan-cli@0.1.2` was published from a laptop and has **no build
provenance** — it is inside the 75% we point at in every outreach message. Fixing it is the
difference between "75% of packages have this problem" and "…and here's how we got out of it."

**Use trusted publishing, not a token.** It is better on three counts:

- **No long-lived credential.** npm trusts this repo and this workflow file over OIDC, so there is
  no secret to leak, rotate, or scope wrong.
- **Provenance is automatic** — no `--provenance` flag, and no way to publish unattested by
  forgetting one.
- **It survives 2FA enforcement.** npm's *"Require two-factor authentication and disallow tokens"*
  blocks token auth and leaves OIDC working, so you can lock the account down without breaking
  releases.

**Do** — npmjs.com → the `tashan-cli` package → Settings → **Trusted Publisher** → Select your
publisher:

| Field | Value |
|---|---|
| Publisher | GitHub Actions |
| Organization or user | `FlyingWHR` |
| Repository | `tashan` |
| **Workflow filename** | `publish-cli.yml` — filename only, case-sensitive, keep the `.yml` |
| Environment name | *(leave blank)* |
| Allowed actions | `npm publish` |

Every field is matched exactly; `publish-cli` or `.github/workflows/publish-cli.yml` both fail.

Then: Actions → **publish cli** → Run workflow. Leave `dry_run` **checked** the first time — it
tests, packs, and verifies without publishing. If green, run it again with `dry_run` unchecked.

**Verify:** the last step prints `tashan-cli@0.1.3 attestations: true`.

*One thing the workflow settles for you: trusted publishing needs **npm ≥ 11.5.1**, and no Node 22
release ever ships it — the whole 22.x line tops out at npm 10.9.x. The first Node bundling a new
enough npm is **24.5.0**, so the publish job runs on Node 24 (current LTS "Krypton", npm 11.17.0)
rather than installing npm globally over the top of the wrong runtime. The CLI is still tested on
Node 18, 22 and 24, because `engines: ">=18"` is a promise to whoever runs `npx tashan-cli` on an
older machine.*

---

## 3 · Publish to the MCP registry — ✅ DONE (`sh.tashan/tashan@0.1.4`, active, isLatest)

**What it costs today:** we ingest `registry.modelcontextprotocol.io` as the spine of our coverage
and are absent from it. It is where every MCP client with a "browse servers" view looks.

```sh
curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=tashan"
# {"servers":[],"metadata":{"count":0}}
```

**Already prepared, including one thing that would have failed the publish:** `server.json` is
written and validated field-by-field against the official `2025-12-11` schema. The registry also
requires an **`mcpName` in `package.json`** equal to `server.json`'s `name`, or it rejects the
publish — both files are individually valid, so it is invisible until you try. That is now in
`cli/package.json` (`sh.tashan/tashan`), both files are at `0.1.3`, and
`tests/test_agent_surface.py` fails the build if they ever drift apart.

**Order matters: step 2 must land first.** The registry verifies the metadata against the npm
package, so `tashan-cli@0.1.3` has to exist on npm before this will work.

```sh
brew install mcp-publisher        # or the tarball from the registry's releases page
```

Then, from the repo root — the namespace `sh.tashan/*` is claimed by proving you control the domain:

```sh
openssl genpkey -algorithm Ed25519 -out key.pem
PUBLIC_KEY="$(openssl pkey -in key.pem -pubout -outform DER | tail -c 32 | base64)"
echo "tashan.sh. IN TXT \"v=MCPv1; k=ed25519; p=${PUBLIC_KEY}\""
```

Add that TXT record in Cloudflare DNS. **It must sit on the apex (`tashan.sh`), not under a selector
like `_mcp-auth`** — the registry follows SPF-style placement, and a record under a selector fails
with a generic signature error that tells you nothing.

The registry JWT from `login` is short-lived, so run the login and the publish as one chain rather
than as two steps you come back to — a pause between them returns
`401 … Registry JWT token … token is expired`, which reads like an auth problem and is only a clock.

```sh
PRIVATE_KEY="$(openssl pkey -in key.pem -noout -text | grep -A3 "priv:" | tail -n +2 | tr -d ' :\n')" \
  && mcp-publisher login dns --domain tashan.sh --private-key "$PRIVATE_KEY" \
  && mcp-publisher publish
```

If it does expire, only the two commands above need repeating — `key.pem` and the TXT record stay
valid, so there is nothing to regenerate and no DNS to touch.

`key.pem` is the private half of the key that proves we own the namespace — anyone holding it can
publish as `sh.tashan/*`. It is in `.gitignore` (`*.pem`); keep it out of the repo and out of chat.

**Simpler alternative if you would rather not touch DNS:** `mcp-publisher login github` works
immediately, but the namespace must become `io.github.FlyingWHR/tashan` — change `name` in
`server.json` **and** `mcpName` in `cli/package.json` to match, or the publish is rejected.

**Verify:** re-run the curl above; expect `count: 1`.

---

</details>

## 4 · Post one Discussion — ✅ DONE 7 Aug 2026

*Posted to [Cline](https://github.com/cline/cline/discussions/13027) and
[Goose](https://github.com/aaif-goose/goose/discussions/11029). Continue was not found in
a search — worth checking, since three beats two for the reason one non-reply is not a
signal.*

<details><summary>original instructions</summary>

Distribution has scored **10/100 at the heaviest weight** across five consecutive audits. Nothing
engineering-side moves it. This is the whole gap.

**Post a Discussion, do not email.** Cline and Continue both set `blank_issues_enabled: false` and
route non-bug messages to Discussions. It is the channel they asked for, it is public — which suits
a company whose claim is public evidence — and other users can upvote it, which an inbox cannot.

| Project | Link |
|---|---|
| **Cline** (65.7k ★) | [new Feature Request discussion](https://github.com/cline/cline/discussions/new?category=feature-requests) |
| **Continue** (35.3k ★) | [new discussion](https://github.com/continuedev/continue/discussions/new) |
| **Goose** (52.4k ★) | [new discussion](https://github.com/aaif-goose/goose/discussions/new) |

The title and body are written and ready to paste: **`docs/OUTREACH.md` §1.** Post to all three —
one non-reply is not a signal, three is.

**Then post #4 the same week** (`docs/OUTREACH.md` §4, the Show HN / r/mcp post). The thread and the
post compound: someone who has seen the name twice replies at a different rate.

**Before posting, re-check the numbers.** They went stale within four hours last time:
```sh
python3 tests/test_outreach_numbers.py
```

---

</details>

## What I will do while you do that

- **The file ceiling.** `web/` is at 18,759 files against Cloudflare Pages' hard **20,000** — about
  620 more capabilities before a deploy is *refused*, not degraded. It has been hit once already.
  `docs/SCALE.md` has the move (prerendered pages behind an SSR Function); the suite now fails at
  19,000 so it cannot surprise a deploy.
- **Expertise and task coverage.** 29% and 36% on the top 1,000 — the honest weak spot. Both need
  `ANTHROPIC_API_KEY` as a repo secret; the nightly stages are wired and skip loudly without it.
