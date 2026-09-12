# ETHOnline 2026 — where this stands

Written 12 September 2026, ~21:40 Shanghai. **Submissions close Sunday 13 September, 12:00 EDT**,
which is Monday 00:00 Shanghai. Read this first when you pick the work back up.

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

Seven commits, suite green on each.

| | |
|---|---|
| `12723dfb` | The daily pipeline had crashed for twelve days on an event tuple with four fields where the consumer unpacks five. Fixed, and the module's self-check now reads its own source so an unexercised branch cannot ship malformed. |
| `dad625d1` | The subgraph: USDC transfers on Base filtered by `topic2` to 1,079 x402 receivers harvested from the Bazaar. Codegen and build pass. |
| `76266dc4` | `doctor` gained an inventory: servers across every project (not just the current directory), plugins with their install dates, skills told apart by whether a plugin owns them, and a local first-seen ledger. |
| `1a23cf1d` | `pipeline/paid_demand.py` — the subgraph joined to capabilities, narrowly, by exact host. |
| `4ec7adf0` | Site and CLI audits applied. The paywall contradiction, four different ecosystem counts, twelve CLI verbs down to five, and a ship-blocker where the published file list omitted a module the entrypoint imports. |
| `47abe203` | Directory data quality: 2,030 identities exist as more than one kind, 460 with disagreeing scores. Baselined so it cannot grow. |
| `c565d8e9` | Co-use links filtered by id rather than by derived slug. |

## Still open

1. **The cross-surface consistency suite is red**, and has been since 27 August. `co_used` on a
   prerendered page names an id absent from the export. Ruled out already: prerender and the test
   read the same file, prerender runs after export in `run.py`, and the export has no colliding
   slugs. This is what keeps the nightly from deploying, so the live site is serving data from
   25 August. **Fix this before the video** — a stale site is the first thing a judge sees.
2. **The payment rail has never settled.** Balance zero, `listed: 0` in the Bazaar, and the
   facilitator refused with `address_not_registered`. One settled call would unlock the Bazaar
   listing and make the demo land. External dependency; may not be fixable tonight.
3. **README split** (pre-existing vs done-in-window) and the **2–4 minute video**. Both required.
   Video rules that auto-reject: under 720p, over 4 minutes, sped up, AI voiceover, phone recording.
4. **AI-usage documentation** is required by the rules: which code and files, and the spec or
   planning artifacts, must be in the repo.

## The demo, when it comes to recording

One narrative: tashan measures which capabilities get used; nothing measures which get *paid*.
The Bazaar lists 14,536 x402 services and publishes no evidence about any of them. Open on
`tashan doctor` against a real machine — 12 servers, 11 plugins, 241 skills, 113 of them maintained
by nobody but the user — then show the same instrument turned on the payment economy.
