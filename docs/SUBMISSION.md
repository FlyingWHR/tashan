# ETHOnline 2026 — submission copy, ready to paste

Everything the Hacker Dashboard form asks for, written out. Nothing here needs editing to be
submitted; trim if a field has a shorter limit than expected.

**One caveat before pasting:** the figures below were true at 03:00 on 13 September and are
recomputed nightly. `/paid.html` always carries the current ones. If you are submitting much later,
open the page and copy the four headline numbers across — quoting a stale figure is the single
thing this project cannot afford to be caught doing.

**Track:** Continuity (Extend Open Source / Ship a Feature) — *not* Classic "From Scratch".
tashan predates the event, the pre-existing work is documented at the top of `README.md`, and the
in-window commits are listed there individually.

**Partner prizes (up to 3; a partner with several tracks still counts as one).**
1. **The Graph** — Track 1 (Composable/Standardized, $5,000) and Track 3 (AI, Continuity, $5,000).
2. **Bazantic** — Track 1 (Help an Agent Use Your Project) and Track 3 (Agentify a New API).
   Track 2 needs a second sponsor's service in the recipe; see the state box.
3. *Left empty deliberately.* A third slot spent on a partner whose tools we did not actually use
   would be the same sin the product exists to point at.

**Bazantic username: `Seroto`.** Gateway `6l6nau2p5ve7tjjwyhbtvctduy`, Recipe
`check-before-you-install` (published).

> ### ⚠ Run this before submitting: `python3 pipeline/demo.py --fit`
>
> Requirements verified 13 Sep 2026 against `ethglobal.com/events/ethonline2026/prizes`, and checked
> in code rather than remembered — the matrix reports UNKNOWN rather than a pass for anything it
> cannot verify, because a fit check that rounds in your favour is worse than none.
>
> **Cleared:** the repository is public (it was private, which disqualified every track here); the
> Bazantic account, x402/MPP Gateway and published Recipe all exist.
>
> **Open — the video.** It gates all five tracks and nothing else does. 2–4 min, 720p+, a human
> voice: the rules bar text-to-speech, sped-up footage and music-over-text, so there is no version of
> this that is not you talking. `python3 pipeline/demo.py --track <id>` prints the beat sheet for a
> specific judge with every figure read live.
>
> **Open — Bazantic Track 2 only.** It wants information moving between two services with the result
> depending on both. Our Recipe binds three tools and all three are ours, which satisfies Tracks 1
> and 3 and not that one.

---

## Project title

**tashan — the measured layer for AI capabilities**

## One-line description

An instrument that scores AI capabilities (MCP servers, agent skills, plugins) on public evidence —
and now the only index of which of them actually get *paid*.

## Description (long)

Every "best MCP server" list is an opinion. tashan is an instrument: it tracks 95,574 capabilities,
scores 12,662 of them on upkeep, freshness and real adoption, audits the ones it can resolve against
OSV.dev at the version you would install today, and publishes every input so the number can be
re-checked. Nobody can pay to change a score — that is enforced by a test, not a promise.

What was built in this window is the part no directory can copy: **which AI services have actually
been paid.** Every other signal in this space is a proxy for demand measured from the outside —
downloads, stars, publish cadence, appearances in public configs — and each can exist without a
single person finding the thing useful. A settled USDC payment cannot.

So we asked the chain. Of the 1,079 x402 payment addresses we could resolve from the Bazaar's own
listings, **998 have been paid at least once and 81 never have**. Between them they have settled
**$247,356 across 10.4 million payments**. And the median service has earned **$0.51** in its entire
life: 591 of the 998 have earned under a dollar, 9 have earned over a thousand, and 67% of
all volume belongs to one receiver. `/paid.html` publishes that distribution, never the total on its
own, because a sum is the one statistic a concentrated economy always passes.

The receipts are read from a subgraph on The Graph Network **through The Graph's own Subgraph MCP
server** — the same tool call any agent can make. The page prints the endpoint, the tool, the query
and a one-line command that re-runs the whole hop from a clone, so a reader checks us rather than
trusting our exporter. 57 capabilities in the published catalog have receipts
attributable to them, under a rule that keeps it honest: volume is a property of an *address*, so an
address shared by several services is counted in the totals and never attributed to one project.

Payment is deliberately not an input to the score. "Someone pays for this" and "this is well made"
are different claims, and folding them would hide exactly the case worth seeing.

And we are in our own table. tashan.sh publishes an x402 price, so it appears on `/paid.html` like
any other row — last, with $0.00, never paid. Nobody exempted us; the join simply found us. An
instrument that leaves itself out of its own measurement is not an instrument.

## How to try it

- **The site:** https://tashan.sh — the index, and https://tashan.sh/paid.html for the money signal.
- **The CLI:** `npx tashan-cli doctor` audits the agent setup already on your machine — every MCP
  server and skill across Claude Code, Claude Desktop, Cursor, VS Code and Windsurf — and tells you
  what is dead, deprecated, unmaintained or carrying an advisory. Reads local files only.
- **The MCP server:** `npx tashan-cli mcp` (or the Claude Code plugin) — `find_capability`,
  `check_capability`, `audit_config`. The fourth tool, `paid_demand`, is in this repository and
  runs from a clone today (`node cli/mcp.mjs`); it reaches npm with the next release. The published
  package is 0.1.4, from 8 August, and `tests/test_server_json.py` refuses to let the manifest claim
  a version that is not actually on npm — which is why it has not been bumped ahead of the publish.
- **Machine-readable:** `/data/demand.json`, `/v0.1/servers`, `/v0.1/scores`, `/llms.txt`.

## Repository

https://github.com/FlyingWHR/tashan — `README.md` opens with what is pre-existing versus what was
built in the window. `docs/AI-USAGE.md` is the AI disclosure. `docs/HACKATHON.md` is the working
state of the entry. Commit messages carry the reasoning, including what was ruled out.

---

## Partner: The Graph

### What we used, and how

Two Graph products, composed:

1. **The Graph Network / hosted subgraphs.** The x402 settlement index we read (`x402 Base`,
   subgraph id `Cb56epg3EvQ6JRpPfknbkM54QxpzTvLa7mwKNQQfUyoj`) is published on the Network. We also
   wrote our own subgraph (`subgraph/`, USDC transfers on Base filtered to 1,079 harvested x402
   receiver addresses) as an independent second index of the same economy.
2. **Subgraph MCP** (`https://subgraphs.mcp.thegraph.com/sse`). Every figure on `/paid.html` is
   fetched through it — `execute_query_by_subgraph_id`, plus `search_subgraphs_by_keyword` and
   `get_schema_by_subgraph_id` during development. `pipeline/subgraph_mcp.py` is a dependency-free
   MCP client over the HTTP+SSE transport: stdlib `urllib` only, no SDK and no `npx mcp-remote`
   bridge, with the SSE framing and the error paths under an offline self-test.

The composition is the point, not the checkbox. An evidence product should be checkable by the means
it recommends to everyone else, so the measurement is read over the public standard interface and
the page prints the call. "Re-run this yourself" is a stronger claim than "trust our exporter".

### What it unlocked

The Bazaar lists thousands of x402 services and publishes no evidence about any of them. Because the
settlement data was already indexed and reachable over MCP, the gap between "nobody measures this"
and a live page joined to a 95,574-row catalog was one night — with no node to run, no RPC to
rate-limit and no backfill to wait for.

### Feedback

- **Subgraph MCP is the right shape.** Discovering an index by keyword, reading its schema, then
  querying it — three tools, one session — is exactly how an agent wants to meet a subgraph. The
  keyword search finding a published x402 index in one call is what made the feature possible tonight
  rather than after a wallet connect.
- **The SSE transport is the rough edge.** The docs show `npx mcp-remote` as the client, which is a
  Node bridge for what is a GET stream plus a POST per request. Worth documenting the raw transport
  (the `endpoint` event carries a *path*, and joining it to `/sse` instead of the origin gives a hang
  rather than an error) so non-JavaScript pipelines can talk to it directly. We wrote ~120 lines of
  stdlib Python; a paragraph in the docs would have saved most of it.
- **`get_deployment_30day_query_counts` is a genuinely interesting demand signal** and deserves more
  prominence — it is the closest thing the subgraph ecosystem has to the download counts we use
  elsewhere, and we would happily publish it beside ours.
- **One ask:** an entity-level "last indexed block/time" that is trivially queryable per subgraph,
  so a consumer can publish the freshness of what it read. We care about that a lot: a stale number
  presented as current is the failure mode this whole product exists to point at.

---

## Partner: Bazantic

> **DO NOT SUBMIT THIS SECTION AS WRITTEN.** Every Bazantic track requires four things that live on
> *their* platform: an account, an x402/MPP Gateway, a published Recipe, and the username in the
> form. We have none of them. What is described below is our own MCP server and our own x402
> endpoints — genuinely built, genuinely useful, and **not what the track asks for**. An earlier
> draft of this page presented them as qualifying. They do not.
>
> **To actually qualify** (roughly an hour, most of it on their dashboard):
> 1. Create a bazantic.com account.
> 2. Build the Gateway over an endpoint we already serve. `/v0.1/kit` and `/v0.1/audit` are live and
>    already answer HTTP 402 with terms in the body; `.well-known/x402` lists them.
> 3. Publish a Recipe for `paid_demand` — *when* to call it, *why*, and what the answer means.
>    **Track 3 ("Agentify a New API") is the best fit we have**: the paid-demand signal exists
>    nowhere else, so it is genuinely an API that was not previously on Bazantic.
> 4. Put the username in `data/hackathon.json` so `--fit` stops reporting it blocked, and in the
>    submission form.

### What we have built that the Gateway would wrap

- **A signal that exists nowhere else.** Which x402 services have actually been paid — a tool on our
  MCP server (`paid_demand`, in `cli/mcp.mjs`) and a machine-readable file at `/data/demand.json`.
  An agent choosing between two capabilities can ask "has either ever been paid, and how much?" and
  get a sourced answer. This is the thing worth agentifying.
- **Two services in one flow.** tashan + The Graph's Subgraph MCP: our catalog supplies identity and
  quality, their MCP server supplies the settled receipts, and the join is an exact host match.
  Neither half answers the question alone. That is the shape a Recipe would describe.
- **Continuity.** The MCP server, the CLI and the npm package (`tashan-cli`, first published
  2026-07-31) predate the event; what is new is the money signal and the tool that serves it.

### Feedback

The thing that made this integrable was that the answer is a *file* as well as a tool — an agent
that cannot open a session can still fetch `/data/demand.json`. Recipes that assume a live session
exclude the large class of consumers that are really just a cron job and a fetch. Publishing both
shapes cost us nothing and doubled who can use it.

---

## AI tool usage (required disclosure)

Full detail in `docs/AI-USAGE.md`, which is measured rather than asserted:

- **Claude Code (Claude Opus) wrote most of the code, under human direction.** 321 of 399 commits
  carry a `Co-Authored-By` trailer naming the model, which is a `git log` query, not an estimate:
  `git log --format='%(trailers:key=Co-Authored-By,valueonly)' | grep -ci claude`.
- **Planning artifacts are all in the repo** — `PROJECT.md` (the spec), `CLAUDE.md` (the operational
  map and the invariants, each one there because it broke), 33 documents in `docs/`, and commit
  messages that carry the reasoning including what was ruled out.
- **Two published signals are model-graded** and labelled as such: instruction depth, against the
  conjunctive rubric in `docs/GRADING-RUBRIC.md`, and the 15-category taxonomy. Everything else is
  arithmetic on public evidence.
- **No model output is published as a measurement, and none can move a rank.** That last part is
  `tests/test_firewall.py`, not a promise.
- The demo video carries a human voice.

## Judging notes

- **Version control:** ~400 commits since 23 July, no squashed history. The in-window work is
  listed by `git log --since='2026-09-12T12:00:00+00:00' --oneline`, each commit carrying its
  reasoning — including what was ruled out and what is still open.
- **The test suite is the gate.** `bash tests/run.sh` — 34 test files, green, enforced by a
  pre-commit hook. It includes a cross-surface consistency check that renders one capability's facts
  on all eight surfaces and fails if any two disagree; that check is what caught the bug which had
  frozen publishing for eighteen days, and it is in this window's commits.
