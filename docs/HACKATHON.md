# ETHOnline 2026 — where this stands

Written 12 September 2026, ~21:40 Shanghai; **updated 13 September, 00:40**. **Submissions close
Sunday 13 September, 12:00 EDT**, which is Monday 00:00 Shanghai. Read this first when you pick the
work back up.

## The entry

**Continuity**, not Start Fresh. Tashan predates the event — first npm publish 31 July, site live,
registry entry `sh.tashan/tashan` — and the rules judge only work done inside the window. Continuity
is the track that makes pre-existing work prize-eligible at all; without it a pre-existing project
can enter but takes no partner prize and cannot be a finalist.

Two partner slots, third left empty:

- **The Graph.** Track 1 (Composable or Standardized Graph Products, $5,000) has no from-scratch
  restriction, so one slot can take it *and* Track 3 (AI, Continuity, $5,000). Track 1 asks that you
  compose two or more Graph products; that is why the plan pairs our subgraph with The Graph's own
  Subgraph MCP rather than shipping the subgraph alone.
- **Bazantic.** All three tracks look reachable: the continuity gateway, a recipe combining tashan
  with a second service, and agentifying an API that was not in Bazantic before, which ours was not.

## DO THIS FIRST — two minutes, and it makes a claim true

**Publish the CLI.** The npm package is 0.1.4 from 8 August, so a stranger running
`npx tashan-cli mcp` today gets three tools; the fourth, `paid_demand`, exists only in this
repository. The demo shows four. Publishing closes that gap:

```sh
npm login                                   # this machine is not authenticated
# bump BOTH, they are asserted equal by tests/test_server_json.py:
#   cli/package.json  "version": "0.2.0"
#   server.json       "version": "0.2.0"  (twice — top level and the package entry)
cd cli && npm pack && npm i -g ./tashan-cli-0.2.0.tgz && tashan-cli mcp --help
# ^ install the TARBALL before publishing: npm's bin is a symlink, so argv[1] never equals
#   import.meta.url on a real install, and that has shipped broken here before.
npm publish
```

Do not bump the version without publishing: `test_server_json.py` checks the newest version in the
registry manifest is actually on npm, and will correctly go red.

## NEEDS A HUMAN — but no longer blocking

**~~Subgraph Studio deploy key.~~ Optional now.** This was the blocker and it is not one any more:
the Track 1 composition ships by reading an x402 settlement index ALREADY published on The Graph
Network, through The Graph's own Subgraph MCP server. Two Graph products, composed, live, with the
query printed on /paid.html.

Publishing ours is still worth doing — it indexes the same economy independently, and two indexes
disagreeing is a finding rather than an error — but it is now an improvement, not a submission
requirement. If you want it:

```sh
cd subgraph
npx graph auth <DEPLOY_KEY>          # thegraph.com/studio, connect a wallet, create
npx graph codegen && npx graph build # `tashan-x402-demand`, copy the key
npx graph deploy tashan-x402-demand
export TASHAN_SUBGRAPH_ID=<the published subgraph id>
python3 pipeline/subgraph_mcp.py --probe   # reads OURS instead of the public one
```

**The video, and the submission form.** Both below. Those are the real remaining human jobs.

## What shipped in the window

Eight commits, suite green on each.

| | |
|---|---|
| `12723dfb` | The daily pipeline had crashed for twelve days on an event tuple with four fields where the consumer unpacks five. Fixed, and the module's self-check now reads its own source so an unexercised branch cannot ship malformed. |
| `dad625d1` | The subgraph: USDC transfers on Base filtered by `topic2` to 1,079 x402 receivers harvested from the Bazaar. Codegen and build pass. |
| `76266dc4` | `doctor` gained an inventory: servers across every project (not just the current directory), plugins with their install dates, skills told apart by whether a plugin owns them, and a local first-seen ledger. |
| `1a23cf1d` | `pipeline/paid_demand.py` — the subgraph joined to capabilities, narrowly, by exact host. |
| `4ec7adf0` | Site and CLI audits applied. The paywall contradiction, four different ecosystem counts, twelve CLI verbs down to five, and a ship-blocker where the published file list omitted a module the entrypoint imports. |
| `47abe203` | Directory data quality: 2,030 identities exist as more than one kind, 460 with disagreeing scores. Baselined so it cannot grow. |
| `c565d8e9` | Co-use links filtered by id rather than by derived slug — which turned out to be the fix for the failure below, two hours after the run that could have proved it. |
| *(13 Sep)* | That fix identified and proven from the CI log, with the collision case synthesised in `prerender.py --selftest`; the hero's freshness date read the render clock instead of the data; README split; `docs/AI-USAGE.md`. |

## SHIPPED since this was written — the money signal is on the site

`/paid.html`, a row on every dossier, a `paid_demand` tool on the MCP server, and
`/data/demand.json`. Real receipts, no deploy key needed: we read a subgraph that was ALREADY
published on The Graph Network (`x402 Base`, id `Cb56epg3EvQ6JRpPfknbkM54QxpzTvLa7mwKNQQfUyoj`)
through The Graph's own Subgraph MCP server, which is the Track 1 composition and works today.

    997 of 1,079 listed x402 receivers have been paid; 82 never have
    $247,247 settled across 10,414,343 payments
    median receiver: $0.51 all-time · 592 under $1 · 9 over $1,000 · top receiver = 67% of volume
    31 capabilities in the published catalog have attributable receipts

Our own subgraph is still worth publishing — it indexes the same economy independently, and
disagreement between two indexes is a finding. It is no longer a blocker for the submission.

The gateway key is a repo secret (`GRAPH_API_KEY`), so the nightly refreshes the figures. Without a
key the stage keeps the last chain read rather than publishing zeros.

## Still open

1. ~~**The cross-surface consistency suite is red.**~~ **FOUND AND FIXED.** It was `c565d8e9` —
   written the same night, described in its own commit message as "NOT the fix", and it was the fix.
   The evidence, which was in CI the whole time (run `34693420492`, the dispatched run at 12:20Z):

   ```
   FAIL 11590 inline dossier payloads agree with the export on EVERY field they carry
     — co_used links a capability with no page on 8 page(s) — pkg-figma-developer-mcp.html: pkg:stripe-mcp
   ```

   One assertion, in the whole suite. The old filter was `slugify(x["id"]) in have_slugs` — a derived
   label tested against a set of derived labels. `slugify("pkg:stripe-mcp") ==
   slugify("pkg:@stripe/mcp") == "pkg-stripe-mcp"`, the export carries `@stripe/mcp` and has dropped
   the third-party `stripe-mcp`, so a co-use edge pointing at the dropped id matched the SURVIVOR's
   label and was baked into eight dossiers. `c565d8e9` changed the filter to the id and that run was
   two hours too early to see it.

   Why nobody could reproduce it: it needs three coincidences at once — two ids colliding on a slug,
   the loser filtered out of the export, and something co-using the loser. The local export had the
   first two and not the third. The case is now synthesised in `prerender.py --selftest` and asserted
   in both directions, because waiting for that conjunction again is not a test strategy.

   **`bash tests/run.sh` is green**, both on the committed tree and after a full
   `run.py --site` regeneration. Nothing withholds the site any more.

2. **The payment rail has never settled.** Unchanged: `data/onchain.json` reports
   `usdc_received: 0.0, payments: 0`, and `check_payments.py` is 25 passing / 1 unverified (set
   `X402_FACILITATOR` to cross-check the quote). The facilitator refused with
   `address_not_registered`. External dependency.

3. **The 2–4 minute video.** Not startable by a model: the rules auto-reject AI voiceover, under
   720p, over 4 minutes, sped up, or phone-recorded. Script below.

4. **The submission form itself.** `docs/SUBMISSION.md` is written to be pasted — title,
   description, both partner write-ups with real feedback, the AI disclosure, and judging notes.
   Select **Continuity (Extend Open Source / Ship a Feature)**, then The Graph and Bazantic as the
   two partner prizes; leave the third empty.

5. ~~**README split**~~ and ~~**AI-usage documentation**~~ — both done. `README.md` now opens with
   what is pre-existing (386 commits, 23 July – 11 Sep) against the eight in-window commits, and
   `docs/AI-USAGE.md` discloses the tooling, the planning artifacts, the two model-graded signals and
   the fence around them (no model output is published as a measurement, and none can move a rank).

## Found on the way, and NOT hackathon work — but the daily loop is degrading

**`db_store push` has started refusing, and it is right to.** From the same CI run:

```
db_store: 1484.8 MiB -> 297.0 MiB gzipped (20%)
db_store: REFUSING to push — even compressed this is near wrangler's 300 MiB ceiling.
```

This is the 100 MiB git limit again, one storage layer later. The R2 object stops advancing from
11 September, so every run re-walks from an older cursor and nothing about the site says so. It does
not block publishing (the deploy step runs before it) and it cannot cost the series, which is sharded
to `data/history/`. The cheap path: `capability_text` is 308 MiB of the 636 MiB local file and is a
re-fetchable cache — `db_store` already pushes more than one object, so splitting it out puts both
halves under the ceiling without a new dependency or a slow re-fetch.

## The demo — generated, not typed

**`python3 pipeline/demo.py`** prints the beat sheet with every figure read off `web/data/` at the
moment you run it. `--serve` starts the local preview first; `--check` exits non-zero if anything in
it has gone stale, and is the last thing to run before you hit record.

This used to be a script with its numbers typed into the prose, and within a week it told the
presenter to say "11,914 measured of 55,268 tracked" over a page reading 12,656 of 95,195, and
"$247,247 settled" over a page reading $247,318. Reading a stale number aloud, on camera, on a
product whose whole claim is that its numbers are current, is the most expensive sentence in the
submission. So it is derived now, like everything else here.

### The rules, verified 13 Sep 2026 against ethglobal.com/events/ethonline/info/details

> - "Must be between 2 and 4 minutes"
> - "DO NOT export the video in any resolution less than 720p (Upload will fail if the video is less than 720p)"
> - "DO NOT use a text to speech synthesizer / AI Voiceover"
> - "DO NOT use mobile phones to record the video submission"
> - "DO NOT speed up the video to fit under the time limit"
> - "DO NOT play music with text on the video describing your project (instead of talking)"

**The narration has to be a person, and the last two rules close the obvious ways around that** —
no sped-up footage, and no music-over-text standing in for talking. There is no version of this a
model can hand over finished; `demo.py` prepares everything up to the moment the microphone opens
and stops there.

The four beats total 3:30, which leaves slack at both ends of the 2–4 minute window.

## ETHOnline 2026 — what is pre-existing and what was built in the window

Entered on the **Continuity** track, which is the one that admits a project that already existed.
This split is stated up front so nothing here has to be taken on trust: every claim below is
checkable with `git log` or `npm view`.

**Pre-existing (23 July – 11 September 2026, 386 commits).** The instrument itself: the SQLite
pipeline, the scorer (`s5`, frozen and published through 2026-11-01), the four-layer security audit,
the static site and its generated SEO/GEO tier, the CLI and MCP server (`tashan-cli` on npm, first
published 2026-07-31, registry entry `sh.tashan/tashan`), and 34 test files. None of it counts as
hackathon work and none of it is presented as such.

**Built in the window (12–13 September 2026).** Every commit in the window is listed by
`git log --since='2026-09-12T12:00:00+00:00' --oneline` — a count typed here would go stale by the
next commit, which is the defect this project exists to point at. The substantive ones:

| commit | what landed |
|---|---|
| `12723dfb` | The daily pipeline had been dead for twelve days on an event tuple with four fields unpacked into five. Fixed; the module's self-check now reads its own source. |
| `dad625d1` | **The subgraph.** USDC transfers on Base filtered to 1,079 x402 receivers harvested from the Bazaar — indexing the receipts, not the listings. |
| `76266dc4` | `tashan doctor` gained an inventory: every project's servers, plugins with install dates, skills told apart by owner, and a local first-seen ledger. |
| `1a23cf1d` | `pipeline/paid_demand.py` — the subgraph joined to the capability catalog by exact host. The only signal in this product that is money. |
| `4ec7adf0` | Two audits applied: the paywall contradiction, four disagreeing ecosystem counts, twelve CLI verbs reduced to five. |
| `47abe203` | Directory data quality: 2,030 identities exist as more than one kind and 460 carry disagreeing scores. Measured and baselined so it cannot grow. |
| `c565d8e9` | Co-use links filtered by id rather than by derived slug. |
| *(13 Sep)* | That filter **was** the cross-surface consistency failure — proven, not guessed (see below), plus a freshness claim that was reading the render clock instead of the data. |
| *(13 Sep)* | **`/paid.html` — the money signal, on the site.** Settled x402 payments on Base, read through The Graph's own Subgraph MCP server, joined to the catalog. A page, a row on every dossier, a `paid_demand` tool on our MCP server. |
| *(13 Sep)* | A ratchet that punished measuring more: the identity gate compared an absolute count, tripled overnight when 18 days of enrichment backlog cleared, and withheld the site. It ratchets the rate now. |
| *(13 Sep)* | UX: the stat grid had **no CSS at all** (so `/stats.html` shipped its headline numbers as a default `<dl>`), and the nav wrapped and collided with the wordmark on every phone. |
| *(13 Sep)* | The money signal added to the cross-surface consistency suite — ten assertions across the export, the dossier, the page and the agent JSON, because it had already drifted twice in one night. |
| *(13 Sep)* | `/v0.1/servers` carries settled receipts, so the agent-readable registry publishes the newest measurement too. |
| *(13 Sep)* | We are in our own paid table — last, $0.00, never paid. The page says so, rendered from that row. |

**The headline feature: which AI services actually get paid.** Every other number here is a proxy
for demand measured from outside — downloads, publish cadence, stars, appearances in public configs
— and all of them can exist without anyone finding the thing useful. A settled USDC payment cannot.
`/paid.html` asks the chain about all 1,079 x402 payment addresses harvested from the Bazaar's
listings: **997 have been paid at least once, 82 never have**, they have settled **$247,247 across
10.4 million payments**, and the **median service has earned $0.51 in its entire life**. Two thirds
of all volume is one receiver. The page publishes that distribution rather than the total, because a
sum is the one statistic a concentrated economy always passes.

It is read through The Graph's own Subgraph MCP server (`pipeline/subgraph_mcp.py` — an MCP client
over HTTP+SSE, stdlib only, no SDK and no `npx mcp-remote`), so the page can print the endpoint, the
tool and the query and invite you to re-run it. Payment is deliberately **not** an input to the
score, for the same reason the security columns are not.

**The eighteen-day bug, since it is the second most useful thing in this list.** `tests/test_consistency.py`
had been failing every night since 27 August, which by design withholds the whole site — so tashan.sh
served 25 August data for two and a half weeks. The cause: co-use links were filtered by *slug*
against a set of slugs. A slug is a label derived from an id, and `pkg:stripe-mcp` and
`pkg:@stripe/mcp` both derive `pkg-stripe-mcp` — so a link to the id the export had dropped matched
the surviving row's label, survived the filter, and was baked into eight pages. It took three
coincidences at once to show, which is why it never reproduced by hand; the case is now synthesised
in `pipeline/prerender.py --selftest`, asserted in both directions.

See `docs/STORY.md` for how to talk about this to a builder — the argument in the order it convinces, every number checkable on the site. `docs/HACKATHON.md` for the entry's state, `docs/AI-USAGE.md` for how AI was used.
