# What tashan does, in plain language — and how to show it

Every feature below is **live today** unless marked otherwise, and every demo step has been run
against the real thing. Grouped by the person it is for, because "MCP registry subregistry with
`_meta` namespacing" is a sentence about our schema and nobody has ever wanted one.

Status vocabulary is `data/entitlements.json`'s: **live** = shipped and reachable · **beta** =
shipped, may change · **planned** = not built, and must never be shown as a feature.

**Setup for every web demo:** `python3 pipeline/serve.py` → http://localhost:4173
(faster than production and identical, except the `/v0.1/*` and `/api/*` endpoints, which are
Cloudflare Functions — demo those against `https://tashan.sh`).

---

## 1. For someone about to install something

### 1.1 Find the right tool by naming the job, not the category — *live*

**What it is.** You say "review code" or "query postgres" and get a ranked shortlist, with the
reason each one matched written next to it. 64 jobs and 23 roles, each mapped from the author's own
keywords, and every mapping states its evidence.

**Why it matters.** Every other directory files by *what a thing is* — "database", "browser". People
do not search for a category, they search for a task they are stuck on.

**Demo — 20 seconds**
```
Press ⌘K anywhere on the site.    Type: review code
```
Or click straight through: **Jobs** in the nav → `/browse.html` → any tile, e.g.
`/task/code-review.html`, `/role/engineer.html`.
Say: *"Sixty-four jobs. The board re-ranks to what we have measured for that work, and every
mapping says why it matched."*

### 1.2 Every score shows its work — *live*

**What it is.** Click any capability and you get a dossier: the tashan score and its four inputs
(upkeep, freshness, adoption, and how much of the evidence we actually hold), each linking back to
the public source it came from — npm, GitHub, the MCP registry, OSV.

**Why it matters.** A number you cannot check is an opinion. This is the whole product.

**Demo — 25 seconds**
```
Click any row on the board → e.g. /capability/pkg-upstash-context7-mcp.html
```
Say: *"Every number has its inputs on the page, and every input links to where it came from. If you
don't believe a number, go and check it."*

### 1.3 Nobody can buy a rank — *live, and it is a test, not a promise*

**What it is.** Commercial relationships never touch task fit, measurements, findings, rankings or
recommendations. It is asserted in code: `tests/test_firewall.py` reads the scorer's source and
fails the build if it references any column that is not public signal.

**Why it matters.** Every directory says this. We are the only one where it is a build failure.

**Demo — 15 seconds, and this is the line judges remember**
```sh
python3 tests/test_firewall.py
```
Say: *"That is not a promise on an about page. It reads the scorer's source and fails the build if
it touches a column that is not public signal."*

### 1.4 Head-to-head comparison — *live*

**What it is.** Any two capabilities side by side, measured the same day by the same scorer. 420
pairs are pre-generated for what people actually search; `/compare.html` covers the pair you have.

**Demo — 15 seconds**
```
/compare.html  → pick two      (or a pre-built pair under /compare/)
```
Say: *"The question people actually ask, answered with two measurements taken the same day."*

### 1.5 The security read, free and in full — *live*

**What it is.** For each package we can resolve: known advisories **at the version you would install
today**, whether it runs a script at install time and exactly what that script is, whether the
publisher built it in CI with an attestation, how many maintainers are left, and the full declared
permission surface — files, shell, network, browser, credentials, cloud.

**Why it matters.** All of it is free, including the fix. A product that exists to stop you
installing something dangerous would be worse at its job if it charged for the warning.

**Demo — 20 seconds**
```sh
curl -s 'https://tashan.sh/v0.1/lookup?name=tavily-mcp' | jq
```
Say: *"Which CVE, what severity, which version fixes it, and the exact install-time command. No key,
no account. A finding is never paywalled."*

**Say the limits out loud — they are the credibility, not the caveat:** we read public evidence. We
do not run the server, read its source, or test it for prompt injection. A clean result means
nothing *known* is wrong. A package we have never measured is reported as **unmeasured, never safe**.

---

## 2. For someone who already has a stack

### 2.1 `doctor` — what is rotting on this machine — *live*

**What it is.** One command reads the agent configs already on your disk — Claude Code, Claude
Desktop, Cursor, VS Code, Windsurf and `~/.claude/skills/` — and names anything deprecated,
archived, abandoned, carrying an advisory, running an install script, or shadowing an official
package name. Local only: no account, no key, no upload.

**Why it matters.** This is the demo that lands, because it finds things on *your* laptop that you
did not know were there. The line that gets a reaction is usually the skills nobody owns.

**Demo — 25 seconds, and this is how to open the video**
```sh
npx tashan-cli doctor
```
Real output from this machine today: *12 MCP servers, 11 plugins, 241 skills across 52 projects —
113 of those skills owned by no plugin.*
Say: *"A hundred and thirteen skills that nothing will ever update but me. I didn't know that before
I wrote this, and neither does anyone else running an agent."*

Extras worth showing if there is time: `--all` lists every row (it prints only what needs a decision
by default), `--json` pipes it, and the exit code is `2` when something needs attention, so it drops
straight into CI.

### 2.2 Check a config without installing anything — *live*

**What it is.** Paste your `mcpServers` block into the browser and get the same findings. The config
is parsed **in your browser**; only bare package names are sent, and the `env` block is never read —
which matters because an MCP config keeps API tokens and database URLs right next to the package
name.

**Why it matters.** It is the only page on the site where a visitor can *do* something rather than
read about it, and it needs nothing installed.

**Demo — 20 seconds**
```
/audit.html → "or try an example config" → Check my setup
```
Say: *"Parsed in your browser. Your keys never leave this page."*

---

## 3. For an agent (this is the audience the product is *for*)

### 3.1 Your agent checks before it installs — *live*

**What it is.** tashan runs as an MCP server with four tools:

| tool | plain language |
|---|---|
| `find_capability` | "what should I use for this job?" — ranked, with install command |
| `check_capability` | "is this one safe and maintained?" — before installing, not after |
| `audit_config` | "what is already on this machine, and what is wrong with it?" |
| `paid_demand` | "has anyone ever actually paid for this?" |

**Why it matters.** An agent cannot ask a follow-up question, so every answer carries its own
caveat: confirmed malware is refused outright, a clean scan says *"nothing known is wrong"* rather
than *"safe"*, and a name we have never seen comes back *unmeasured, not necessarily bad*.

**Demo — 30 seconds**
```sh
claude mcp add tashan -- npx -y tashan-cli mcp
```
then, in the agent: *"Find me something for web scraping and check it before you install it."*
Say: *"It gets the full security audit, free. Nothing about risk is ever behind the paid tier."*

> **Note before recording:** npm currently has 0.1.4, which ships **three** tools — `paid_demand`
> came later. Either publish first, or say "three tools" and demo `paid_demand` from the repo.

### 3.2 Ask one question, get one answer — *live*

**What it is.** Plain HTTP, no SDK, no key, no quota.

```sh
curl -s 'https://tashan.sh/v0.1/lookup?name=tavily-mcp'   # one capability, everything we hold
curl -s 'https://tashan.sh/v0.1/search?q=postgres'        # ranked search
curl -s  https://tashan.sh/v0.1/scores                    # every score, name → [score, health, evidence]
curl -s  https://tashan.sh/llms.txt                       # the whole site as markdown, for a model
```
All four verified answering today. Say: *"We want you calling it — that is the distribution."*

### 3.3 Pay per call instead of holding a subscription — *live (x402)*

**What it is.** An agent turning up once does not want a subscription. Ask a question free; pay for
the *assembled* answer per call, over [x402](https://x402.org/) — HTTP 402, a stablecoin transfer on
Base, fractions of a cent, no account to create and no key to store.

**Demo — 25 seconds, and it is a two-part reveal**
```sh
# free: the ranked shortlist for a job, plus everything excluded and why
curl -s -X POST https://tashan.sh/v0.1/kit -H 'content-type: application/json' \
  -d '{"task":"web-scraping","client":"claude-code"}' | jq '.shortlist[0]'

# paid: the same thing assembled — versions pinned to what the advisory scan cleared
curl -i -X POST https://tashan.sh/v0.1/kit -H 'content-type: application/json' \
  -d '{"task":"web-scraping","kit":true}'          # → HTTP 402, with the terms in the body
```
Say: *"Asking is free. Assembling is the work. An unpinned config is an unverified one — the
verification is the product."*

---

## 4. The money layer — the part nobody else publishes

> **Read this before demoing it.** The numbers below come from a *different population* than the
> rest of the site, and sliding between the two is the fastest way to lose a room. The x402 listing
> is ~1,000 services. Our catalogue is ~12,000 capabilities. They overlap by 77. Say them
> separately.

### 4.0 What x402 is, in one breath

**A way for software to pay software.** A server answers `402 Payment Required` with a price; the
caller sends a stablecoin (USDC, on Base) and gets the answer. No account, no card, no signup.

It exists because an AI agent that needs *one* answer cannot sign up for a monthly subscription. If
agents are going to buy things, this is roughly the shape it takes.

### 4.1 Which AI services have actually been paid — *live*

**What it is, as a chain of four steps** — this is the order to say it in:

1. There is a **public listing** where x402 services advertise themselves, each with a wallet
   address to pay. We resolved every address on it: **1,079**.
2. That listing publishes **no evidence about any of them**. It tells you a service exists and wants
   money. It does not tell you whether anyone has ever sent any.
3. So we **asked the Base chain** how much each of those 1,079 addresses has actually received, ever.
4. Then we **joined the receipts back to our own catalogue**, so a capability page can say *this one
   has really been paid*.

**What came back:**

| | |
|---|---|
| paid at least once | **998** |
| never paid a cent | **81** |
| total settled | **$247,318** across **10.4M** payments — average **2.4¢** each |
| **median service, over its entire life** | **$0.51** |
| earned under $1 | 591 |
| earned over $1,000 | **9** |
| the single largest receiver's share of all money | **67%** (top five: 89%) |

**Say it in one sentence:** *the agent economy is real, tiny, and almost entirely one company.* Half
of everything advertising itself as a paid AI service has made less than fifty-one cents, ever.

**Why it matters — the reason this is the centrepiece.** Everything else on this site is a **proxy**.
Downloads count machines running `npm install`, which is mostly CI. Stars count people who liked a
tweet. Neither means a human ever found the thing useful. **A settled payment is not a proxy** —
somebody decided it was worth money and sent money. It is the only non-proxy signal we have, and the
only number here that cannot be reproduced by scraping npm.

**And the honest answer beats the hopeful one.** A builder deciding whether to charge agents is
better served by "the median is fifty-one cents and two thirds of the money is one receiver" than by
any forecast. That is the finding, and nobody else is publishing it.

**The join, stated plainly** (this is what the table at the bottom of the page is): of the 1,079
addresses, **77** map to a capability we measure and **57** have a published dossier. Those 57
capability pages carry a `Settled` line. The other ~1,000 addresses are services we do not otherwise
track — they count toward the market figures above, and nowhere else.

**Demo — 40 seconds, the centrepiece. Three moves, in this order.**
```
/paid.html
```

**Move 1 — the market.** Read the figures off the top of the page.
Say: *"Nine hundred and ninety-eight of a thousand and seventy-nine listed services have ever been
paid. Eighty-one never have. Two hundred and forty-seven thousand dollars in total — and the median
service has earned fifty-one cents in its entire life."*

**Move 2 — one row where the signals disagree.** Scroll to the table, land on **blockrun-mcp**:
$166,661 across 8,718,793 calls, tashan score **68**.
Say: *"Two thirds of all the money in this market is that one row. And it scores sixty-eight —
perfectly healthy, not the top of our board. Adoption and payment are different questions, and this
is what it looks like when they disagree. Payment is deliberately **not** an input to the score:
'someone pays for this' and 'this is well made' are different claims."*

**Move 3 — us.** ⌘F for `tashan`, land on our own row: **$0.00, never paid.**
Say: *"We publish an x402 price too, so we are in our own table — on zero. Nobody put us there and
nobody exempted us. An instrument that leaves itself out of its own measurement is not an
instrument."*

> Do **not** say "the last row" — the table is regenerated nightly and another zero-earning row can
> sort below us by name.

### 4.2 It is re-runnable, and the page prints the query — *live*

**What it is.** Read from a subgraph on The Graph Network, through The Graph's Subgraph MCP server.
The page prints the exact query, so anyone can point an MCP client at it and get the same rows.

**Demo — 15 seconds.** Scroll to *"Re-run it yourself"* at the bottom of `/paid.html`.
Say: *"Two Graph products, composed. The query is on the page. You do not have to take our word for
any of this."*

---

## 5. For a publisher or maintainer

### 5.1 A live badge for your README — *live*

**What it is.** An SVG that shows your current measurement and **updates when the evidence does,
including downward.** That is the point of it.

**Demo — 10 seconds**
```md
![tashan](https://tashan.sh/badge/pkg-upstash-context7-mcp.svg)
```
Say: *"Nothing about a badge, a claim or a payment changes a score."*

### 5.2 Ask for something to be measured — *live*

**What it is.** `/requests.html` — request a capability be measured. When nobody has requested
anything it shows the next 40 in the measurement queue, ranked by demand, so the page is never empty.
**You can request a grade, never a placement.**

### 5.3 What moved in the ecosystem — *live*

**What it is.** `/changes.html` — dated changes: a new advisory, an install script appearing, a
maintainer leaving. Built from a series that **cannot be backfilled**, which is why nobody can copy
it by scraping us tomorrow.

**Demo — 15 seconds.** Open it and say: *"This is the freshest thing we publish, and the one page a
competitor cannot reproduce by copying today's data — you had to have been recording yesterday."*

---

## 6. For an IDE or agent host

### 6.1 Change one URL — *live*

**What it is.** If your host already reads the official MCP registry, point it at us instead and
every entry arrives byte-compatible, with one extra namespaced block carrying the measurement. No
SDK, no integration, no awareness of us beyond a base URL.

```
registry.modelcontextprotocol.io/v0.1/servers
            ↓
         tashan.sh/v0.1/servers
```

**Demo — 20 seconds.** Show `/for-hosts.html`, then:
```sh
curl -s https://tashan.sh/v0.1/scores | jq '."tavily-mcp"'
```
Say: *"Unscored servers are **absent** rather than zero. We never publish a number we did not
measure."*

---

## 7. What money actually buys

The rule, one sentence, everywhere: **the facts are free, the work is paid.**

| | Free, forever, no account | tashan Pro — $6/mo |
|---|---|---|
| Every score and grade | ✓ | ✓ |
| Every risk finding **in full** — which CVE, what the install script runs, the permission surface | ✓ | ✓ |
| `doctor` over your own config | ✓ | ✓ |
| Agent endpoints, badges, MCP server | ✓ | ✓ |
| **The whole series behind a row**, back to the first day we measured it | | ✓ |
| **The replacement, named** — not just the news that something died | | ✓ |

**Demo — 20 seconds.** `/pricing.html`, then:
Say: *"Free tells you what is true today. A change can only be seen once — on the day it happens.
Every measurement on the Index is a snapshot anyone could recompute from public sources. A change is
not: it exists only because we recorded yesterday. That is the thing worth paying for."*

---

## Do not demo these

- **`watch` — proactive alerts on the day something changes. Status: `planned`.** Not built. It must
  never appear as a feature, in a video or anywhere else. `tests/test_entitlements.py` enforces this
  in copy; nothing enforces it in a live demo except you.
- **Anything implying we audit, certify, endorse or vouch for a capability.** `terms.html` explicitly
  disclaims all four, and `tests/test_claims.py` fails the build if marketing contradicts it.
- **"Fully audited" / "audited before you install."** 9,059 of 12,656 are scanned. Coverage is
  published on `/methodology.html` and moves only when we do the work. Say the real number.

## The honest weak spots, said before anyone finds them

A judge who has read this far will ask. Answering first is worth more than the question costing you.

- **Coverage is uneven, and stated.** The aggregate measured/tracked ratio *falls* every time
  discovery succeeds, so it is reported and never targeted. The commitment is over the top 100 and
  top 1,000 by adoption evidence, because what costs a reader is an absence on the thing they looked
  up, not a gap in the tail.
- **Skills are catalogued, not ranked.** A skill is a folder inside a repository, so its only upkeep
  evidence is the repository's — shared by every skill in it. Ranking them would mean publishing one
  repo's number 300 times. They stay browsable, searchable and installable, with a `rating_basis`
  saying exactly why there is no number.
- **The grade reads documentation, not quality.** Instruction depth is a read of what the docs cover
  against a published rubric. It is not a judgment of the software, and we withdrew two bands
  (`wrapper`, `slop`) precisely because they claimed more than reading a README can support.
- **Payment is not quality, and unpaid is not bad.** Almost every MCP server is free by design.
  Being unpaid is the normal case.
- **The paid data is Base, and x402 only.** Other chains, other rails and private billing are
  invisible to us. We publish what is on the ledger we can read.

---

## The five-minute version, if you only get one shot

1. `npx tashan-cli doctor` — find rot on the judge's own machine. *(§2.1)*
2. The homepage, then any dossier — every number shows its work. *(§1.2)*
3. `python3 tests/test_firewall.py` — nobody can buy a rank, and it is a build failure. *(§1.3)*
4. `/paid.html` — x402 lets software pay software. Of the ~1,000 services advertising themselves
   that way, the median has earned **fifty-one cents**, ever — and we are in our own table on
   zero. *(§4.1)*
5. `claude mcp add tashan` — the agent checks before it installs. *(§3.1)*

`python3 pipeline/demo.py` prints this as a timed beat sheet with every figure read live, and
`--check` refuses to let you record a stale one.
