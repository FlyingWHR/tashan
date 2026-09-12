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

## The demo — a 3:30 script, read it while you record

Rules that auto-reject: under 720p, over 4 minutes, sped up, AI voiceover, phone-recorded. Your
voice, a real terminal, a real browser. Local preview is fine and faster than production:
`python3 pipeline/serve.py` then http://localhost:4173.

**0:00–0:25 — the problem, on your own machine.**

```sh
npx tashan-cli doctor
```

Say: "Twelve MCP servers, eleven plugins, two hundred and forty-one skills. A hundred and thirteen
of those skills are owned by no plugin — nothing will ever update them but me. I did not know that
before I wrote this, and neither does anyone else running an agent."

**0:25–1:10 — what tashan is.** Open http://localhost:4173. Point at the hero: 11,914 measured of
55,268 tracked. Click any capability. Say: "Every number has its inputs on the page — upkeep,
freshness, adoption, how much of the evidence we actually have. And an advisory scan against the
version you would install today." Then the sentence that matters: "Nobody can pay to move a rank.
That is not a promise on an about page, it is `tests/test_firewall.py` — it reads the scorer's
source and fails if it touches a column that is not public signal."

**1:10–2:30 — the window's work, and the point of the whole thing.** Click *Who gets paid*.

Say: "Everything I just showed you is a proxy. Downloads, stars, publish cadence — all of them can
exist without one person finding the thing useful. This cannot." Then read the four figures off the
page: 997 of 1,079 listed x402 services have been paid at least once, 82 never have, $247,247
settled across 10.4 million payments — "and the median service has earned fifty-one cents in its
entire life. Two thirds of all the money is one receiver."

"A directory lists all of them and publishes evidence about none of them. This is the first index of
which ones anybody actually paid."

Scroll to the table. Land on blockrun: $166,659 across 8.7 million calls, tashan score 71, 1.3k
downloads a week. Say: "Adoption and payment are different questions, and this is what it looks like
when they disagree. Payment is deliberately not an input to the score — 'someone pays for this' and
'this is well made' are different claims."

Then find our own row — ⌘F for `tashan.sh`; it sorts last today, on $0.00 — and pause on it:
Tashan CLI, tashan.sh, $0.00, never paid. (Do not say "the last row": the table is regenerated
nightly and another zero-earning row could sort below us by name.)
Say: "We publish a price too, so we are in our own table — last, with zero. Nobody put us there and
nobody exempted us; the join found us like it found everyone else." That is the single most
persuasive thing on the page, and it costs one sentence.

**2:30–3:10 — how it is read, which is the part to be proud of.** Scroll to *Re-run it yourself*.

Say: "These receipts are not ours. They are a subgraph on The Graph Network, and we read it through
The Graph's own Subgraph MCP server — the same tool call any agent can make. The endpoint, the tool
and the query are printed on the page, so you can re-run it and check me." Then show an agent doing
exactly that:

```sh
# with the MCP server configured, ask an agent: "has anyone actually paid for blockrun?"
```

Or show the raw call if a live agent is risky on camera:

```sh
printf '%s\n%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"paid_demand","arguments":{"name":"blockrun"}}}' \
  | TASHAN_SITE=http://127.0.0.1:4173 node cli/mcp.mjs
```

**3:10–3:30 — the close.** Say: "tashan predates this hackathon; the README says exactly which
commits are new. What is new is that the instrument now measures money, and that an agent can ask
it. Thirteen commits, the suite green on every one."

### Do not say
- Do not say "$247k settled" without the median in the same breath. A sum is the one statistic a
  concentrated economy always passes, and overselling it is the exact thing this product exists to
  point at.
- Do not call an unpaid capability worse. Almost every MCP server is free by design.
- Do not claim we index the whole x402 economy. It is Base, it is x402, and it is the addresses we
  could resolve from public listings.
