# What to do next

Written 4 Aug 2026, after an external product audit and a Fable investor-style scoring.

**The one-line read:** every axis you control from a keyboard scores 80–90. Every axis needing another
human to adopt something scores near zero. The site is a conversion machine with no traffic feeding
it. Nothing in this file matters as much as §1.

---

## §1 — Only you can do these. Everything else is secondary.

### 1.1 Add two GitHub secrets (5 minutes) — unblocks nightly publishing

The pipeline has measured every night for weeks while the live site served whatever build was last
uploaded by hand. The audit that prompted this file **read a stale deploy** — one of its findings had
already been fixed three days earlier. That gap is now closed in `.github/workflows/daily.yml`, but
it stays dormant until the credentials exist.

1. Cloudflare dashboard → My Profile → API Tokens → **Create Token**
2. Template: *Edit Cloudflare Workers*, or a custom token with **Account → Cloudflare Pages → Edit**
3. GitHub → repo → Settings → Secrets and variables → Actions → **New repository secret**:
   - `CLOUDFLARE_API_TOKEN` = the token
   - `CLOUDFLARE_ACCOUNT_ID` = `9ffa373bbc77a0885b1f78b41c0c8dfc`

Verify: run the workflow by hand and confirm the *Deploy to Cloudflare Pages* step runs rather than
skips. It is gated on a green suite **and** on the secret existing, so today it skips silently.

### 1.2 Turn off Bot Fight Mode (2 minutes) — agents are being refused at the door

Measured 5 Aug: Cloudflare returns **403 to any request whose User-Agent is `Python-urllib/3.x`** —
the default of `urllib.request.urlopen(url)`, the most common way to fetch a URL in Python. It
affects every surface, including the ones we advertise as keyless and agent-ready:

    /  ·  /llms.txt  ·  /v0.1/scores  ·  /v0.1/servers  ·  /data/index.json  ·  /capability/*.md

curl, node-fetch, Go and ChatGPT-User are fine, so this is invisible from a browser and from most
manual testing. But an agent that gets 403 on its first request does not retry with a nicer header —
it concludes the service is down and stops asking. We are inviting integrations and refusing them at
the door.

dash.cloudflare.com -> tashan.sh -> Security -> Bots -> **Bot Fight Mode off**. Free-tier Bot Fight
Mode cannot be scoped by path; Super Bot Fight Mode allows an exception for `/v0.1/*` and `/data/*`
if protection is wanted elsewhere. The deploy token carries `zone:read`, not `zone:write`, so this
cannot be automated from the repo.

**Re-measured 6 Aug 2026, 02:17 — still 403 on all five surfaces.** And there is no code workaround:
serving them from a Pages Function instead of as static assets does not help, because the block is
zone-wide and runs before Workers. `/badge/*.svg` and `/api/security` are Functions and are refused
identically. This is one toggle, and every draft in `docs/OUTREACH.md` ends with someone pasting one
of these URLs into a script.

Verify: `python3 tests/test_agent_access.py` — it runs advisory in the suite and never blocks a deploy.

### 1.3 One host integration conversation (this week)

This is the whole ballgame. Distribution scored 10/100 at 20% weight — the heaviest axis and the
emptiest. One integration moves it to ~50 and revenue reality 30 → 55: about 15 composite points from
a single conversation, which is more than every engineering item below combined.

What you already have to offer, working today, no account required:

- `GET /v0.1/servers` — the whole measured corpus in official-MCP-registry shape, drop-in
- `GET /v0.1/scores` — a 350 KB lookup: name → score, grade, risk flags
- `npx tashan-cli doctor` — reads local configs, uploads nothing
- An MCP server, so an agent can query it as a tool

Targets, roughly in order of fit: MCP client authors (Cursor, Cline, Windsurf, Zed), registry and
directory operators who have supply but no measurement, and CI/security tooling that already scans
dependencies and has no answer for MCP servers.

The ask is not a partnership. It is: *"here is a free endpoint, show a score next to each server."*

### 1.4 Decide whether tashan is priority one

The Fable review puts this third behind FaceTell and Trade Clash, in a business that runs on
accumulated credibility. Three consecutive sprints went to product polish over distribution; this
session was a fourth. That is a real pattern and it is a founder decision, not an engineering one.

---

## §2 — Queued engineering, in dependency order

Each is scoped and ready. None substitutes for §1.

### 2.1 Drain the enrichment backlog (mechanical, ~4 daily runs)

**4,684** npm packages are discovered but unmeasured — they carry no downloads, no dates, no score,
and no page. `@playwright/mcp` (Microsoft's own) is among them.

Either wait for the nightly cap to work through them, or force it in one pass:

```sh
NPM_CAP=5000 python3 pipeline/run.py
```

Expect `signal_history` to show a step change on the day it lands. That is **our corpus growing**, not
capabilities changing. The `s4 → s5` scorer bump means `trend()` will not misreport it as decline.

### 2.2 Walk the remaining skill repos (mechanical, cheap)

**2,878** candidate repos have never been scanned for `SKILL.md`. They are already in the database,
having earned their way in by publishing a plugin or marketplace manifest. 60 repos took skills from
524 → 1,045.

```sh
SKILL_REPO_CAP=300 python3 pipeline/ingest_skills.py
```

Progress commits per repo, so an interrupted run resumes rather than restarting.

### 2.3 Serving: move the board to D1 (the real architecture item)

```
capabilities MEASURED : 7,403
capabilities BROWSABLE: 1,880   ← 75% invisible
lookup.json           : 688 KB gz, downloaded by the CLI on every doctor run
```

We measure 7,403 and let people see 1,880, because `index.json` must fit a first-paint budget. The
architecture is deleting three quarters of the product's own output, and the same pressure already
forced badges off static files at Cloudflare's 20,000-file ceiling (`web/` is at 15,330).

Not Postgres — **D1**, Cloudflare's SQLite at the edge. The pipeline already produces SQLite; push the
same file and serve board queries from a Function, as `/badge/*` and `/api/*` already do. That removes
the download budget entirely and lets the board show everything measured.

**Do this after §1.2.** A complete queryable dataset is most valuable exactly when someone is
consuming it.

### 2.4 Taxonomy shelves for plugins (design work, not a threshold)

The concentration ratchet currently reads 53% and passes — **for the wrong reason**. npm discovery
added ~5,000 packages the classifier does not recognise, so it abstained: `other` went 3.0% → 13.3%
of the board. Diluting two big shelves with a third called "we don't know" lowers the number without
sorting anything.

Per kind, unchanged where it matters: **plugin 74.8%, skill 67.9%**, npm 38.7%, remote 30.1%. The
fifteen shelves were designed for MCP servers; plugins and skills are 70% of the board and are
overwhelmingly "helps you write code" or "helps you work".

`CONCENTRATION_CEIL` is deliberately **not** ratcheted to 53% — the corpus is mid-flight and the
number will climb again as §2.1 lands. Re-measure after enrichment, then set it at whatever it
honestly is, and add the shelves that earn it.

---

## §3 — From the audit, still open

Fixed already: the ranking claim, the stale scorer version, the "complete audit" overclaim, the
"did it work" claim, and the reproducibility overclaim. `tests/test_claims.py` now fails the build on
any of them returning.

Still open, in value order:

**Closed since:** the entitlement matrix (`data/entitlements.json`, enforced by
`tests/test_entitlements.py`), job pages opening with a stack (`gen_hubs.py:stack_for`), the requests
board (now renders the live measurement queue from `coverage.json` when nobody has asked), and the
CLI's own dossier — `tashan-cli` is seeded into the corpus and measured by the same rules, with the
unflattering half stated on `/start.html`.

Still open, in value order:

1. **Comparison as a first-class surface.** 398 head-to-head pages exist and a reader can only reach
   the pairs we pre-generated. A picker plus a side-by-side across fit, depth, adoption, maintenance,
   advisories, install scripts, provenance and expected access is worth more than thousands of thin
   profiles.
2. **Mobile chrome.** At 390px the ticker, nav and fixed status strip take most of the first screen
   before any content.
3. **Original research as content.** The corpus can answer questions nobody else can — how long an
   MCP server stays maintained, what share of them a single maintainer carries, which categories are
   consolidating. Right now every number lives on a page nobody has a reason to visit.

---

## §3b — From the 6 Aug audit

The composite moved 55 → 57. The diagnosis in that audit is worth repeating verbatim, because it is
the same one as last time: *moving trust engineering 93→95 moved the composite +0.2; moving
distribution 10→50 would move it +8.* Four consecutive sprints have gone to the axis that responds to
a keyboard.

**Done this session:**

- **The ruler is frozen.** s5 is published as stable through **2026-11-01** and
  `tests/test_scorer_version.py` now refuses a scoring change inside the window unless
  `TASHAN_SCORER_BREAK_GLASS` is set with a reason. Pro sells score history, and history only accrues
  while the ruler holds still — a scorer rewritten four times in a week sells a series two days long.
- **Coverage restated as demand-weighted.** `pipeline/coverage.py` publishes coverage over the top
  100 / top 1,000 by adoption evidence rather than the aggregate ratio, which fell 47%→41% purely
  because discovery worked. Baked onto the methodology page and guarded by `tests/test_claims.py`.
- **The outreach pack exists** — `docs/OUTREACH.md`, four drafts ready to send, each leading with a
  measured fact about the recipient's own users.

**Not done, and only you can:** send one. `docs/OUTREACH.md` §1 is three emails long.

---

## §4 — Metric to run against

**Weekly actively protected stacks** — machines that ran `doctor` or are monitored, with current
coverage. Not visits, not capabilities measured, not pages indexed.

Today that number is effectively unknown, which is itself the finding: there is no instrumentation
answering "did anyone run this". §1.2 is what starts it moving.
