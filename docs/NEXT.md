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

### 1.2 One host integration conversation (this week)

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

### 1.3 Decide whether tashan is priority one

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

1. **Entitlement matrix.** Pricing describes a watch product; Terms and Refunds describe named
   replacements and score history. Generate one matrix and feed pricing, CLI help, account, terms,
   refunds and checkout from it. Mark each line *available / beta / planned*.
2. **Job pages are catalogues, not recommendations.** "Software engineer" lists hundreds of
   heterogeneous artefacts. It should open with a five-item stack — best docs lookup, best browser
   automation, best code review, best database, best testing — then expand by task.
3. **Comparison as a first-class surface.** 364 head-to-head pages exist; a side-by-side table across
   fit, depth, adoption, maintenance, advisories, install scripts, provenance and expected access is
   worth more than thousands of thin profiles.
4. **The CLI's own dossier should be the best on the site.** You ask people to `npx` an unfamiliar
   package in order to find risky packages. Show source, provenance, version, exactly which files are
   read, exactly what leaves the machine, and that it writes nothing.
5. **Requests board.** `requests.json` is empty by design. An empty demand board reads as no demand.
   Hide it, or replace it with a public coverage queue showing what is measured next.

---

## §4 — Metric to run against

**Weekly actively protected stacks** — machines that ran `doctor` or are monitored, with current
coverage. Not visits, not capabilities measured, not pages indexed.

Today that number is effectively unknown, which is itself the finding: there is no instrumentation
answering "did anyone run this". §1.2 is what starts it moving.
