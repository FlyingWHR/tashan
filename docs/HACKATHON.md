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

## BLOCKED — needs a human

**Subgraph Studio deploy key.** thegraph.com/studio, connect a wallet, create a subgraph named
`tashan-x402-demand`, copy the deploy key and slug. A browser wallet connect cannot be automated.
Until it lands the subgraph is finished but unpublished, and an unindexed subgraph is not a
submission.

Once you have it:

```sh
cd subgraph
npx graph auth <DEPLOY_KEY>
npx graph codegen && npx graph build
npx graph deploy tashan-x402-demand
# then, so the pipeline stage has something to read:
export TASHAN_SUBGRAPH_URL=<the studio query URL>
python3 pipeline/paid_demand.py
```

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

## The demo, when it comes to recording

Four beats, ~30s each, one narrative:

1. **The claim.** tashan measures which capabilities get used. Open `tashan doctor` on a real
   machine — 12 servers, 11 plugins, 241 skills, 113 maintained by nobody but the user.
2. **The instrument.** The board: a score, its four inputs, and the security audit beside it. Say
   the firewall out loud — nobody can pay to move a rank, and it is a test, not a promise.
3. **The window's work.** The subgraph: 1,079 x402 receivers on Base, USDC receipts joined to the
   catalog by exact host. The Bazaar lists 14,536 services and publishes evidence about none of them.
4. **The honesty.** An unmeasured capability is published as unmeasured. Show a `null`, not a zero.

The line to land: tashan measures which capabilities get *used*; nothing measures which get *paid*.
