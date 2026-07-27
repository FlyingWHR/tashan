# Market intelligence — the AI capability directory landscape

*2026-07-26. Researched by visiting every site in a browser and reading the actual pages, not from
search snippets. Counts are what each site displayed on the day. LobeHub has its own deep teardown in
`docs/COMPETITIVE-LOBEHUB.md`; Agensi's earlier profile is in `docs/COMPETITIVE.md`.*

---

## 0. The map in one table

| Site | What it really is | Scale (displayed) | Per-item quality signal | Revenue |
|---|---|---|---|---|
| **LobeHub** | Agent runtime; catalog is supply | MCP **81,430** · Skills **332,962** · Agents **234,885** | 9-item hygiene checklist → F/B/A. **Skills: none** | Credits (consumption) |
| **Glama** | Registry + Inspector + **Gateway**; builds & runs every server | **61,109** servers · 9,970 connectors · **306,671 tools** | **Deepest in the field**: sandboxed execution, syscall/network behavioural analysis, open-source TDQS (6 dims/tool) + coherence + cohesiveness → license/quality/maintenance grades | $9–80/mo credits + hosting |
| **MCP Market** | Skills marketplace + hub | Skills **334,042** | None visible | Sells skills |
| **PulseMCP** | Curated directory, partner-first | **22,256**, "last update 5 hours ago" | Classification: Official/Reference/Community + **est. visitors/week** | Partnerships |
| **Smithery** | **Hosted gateway** — they proxy traffic | 400k+ devs/mo (reported) | **98/100 + uptime + calls + latency + top clients** | Hosting/usage |
| **Agensi** | Paid skill store | **2,000+** skills, 3,500 users, 250 creators | "Security scanned" (binary) + install count | **30% of sales** |
| **Official registry** | Canonical identity layer | **≥6,000** | `status` only (active/deprecated/deleted) | None |
| **tashan** | Neutral measurement | **1,240** (721 rated) | Trust 0–100 + expertise verdict + vitality | None yet |

---

## 1. The two numbers that matter

**~333,000 skills.** LobeHub says 332,962; MCP Market says 334,042. Two independent sites landing within
0.3% of each other means both are doing essentially the same thing: a GitHub-wide crawl for `SKILL.md`.
That is the real denominator for skills, and it is the "whole internet of skills" — it is not curated,
it is everything anyone ever committed.

**~61,000–81,000 MCP servers**, depending on whose dedup you believe (Glama 61,109; LobeHub 81,430;
PulseMCP 22,256 after curation; official registry ≥6,000). The spread between 22k and 81k *is* the
story: the same field counted four ways, differing entirely on what you throw away.

tashan is 1,240. On raw listings we are last by two orders of magnitude, and that is the wrong axis to
compete on — see §5.

---

## 2. Who actually grades anything

This is the finding that reframes the strategy.

### MCP servers — crowded, three different philosophies

- **Smithery — runtime telemetry (strongest evidence in the field).** On a server page: `98/100`,
  `5.3k calls`, `99.93% uptime`. The Performance tab shows **per-tool call counts**
  (`query-docs 2,865` vs `get-library-docs 25` — you can literally see which tools are dead),
  **Uptime 30d 99.9%**, **Latency 30d 335ms p50** with a month-long chart, and **Usage → Top Clients**
  broken out by name (Claude Code 68,517 · Codex 42,737 · Cursor …). They can do this because they
  *proxy the traffic*. Nobody working from public metadata can reproduce it.
  **Limit:** it only exists for servers hosted through Smithery, and it is first-party and unauditable.
- **Glama — builds and runs the code, then grades the schema.** *Corrected 2026-07-27: I first described
  this as "three unexplained letter grades". That was wrong — see `docs/COMPETITIVE-GLAMA.md`.* They
  clone full git history, build each server (Dockerfile authored or AI-inferred) and execute it inside a
  **Firecracker microVM**, observing syscalls and network for credential access, unexpected egress and
  exfiltration signatures (findings published as Malicious/Risky). They then score every tool with
  **TDQS** — six dimensions, published, **open-source**, grounded in two Feb-2026 arXiv papers — plus
  tool-set coherence and server cohesiveness, with per-dimension gap analysis shown publicly. Over a
  million scans in twelve months; re-scan on every commit. For remote connectors they add schema-drift
  diffing and **prompt-injection detection in tool descriptions**.
- **LobeHub — a 9-item packaging checklist** graded F(0–60)/B(60–80)/A(80–100): validated, ≥1 install
  method, ≥1 tool, has README, easy install, has LICENSE, has prompts, has resources, and
  **"Not Claimed by Owner"**. It measures tidiness, not life: a well-licensed, fully-documented,
  *abandoned* server scores A. And the ninth item docks a server because its author hasn't signed up to
  LobeHub — platform engagement scored as quality, in public.
- **PulseMCP — provenance + demand**: `Official / Reference / Community` classification (clean, honest,
  instantly useful) plus estimated weekly visitors as a demand proxy.

### Skills — nobody grades them at all

- LobeHub lists 332,962 skills. A skill detail page has tabs *Overview · Installation Method · SKILL.md ·
  Resources · Related Skills · Version History* — **there is no Score tab.** Their MCP servers get a
  grade; their skills get nothing.
- MCP Market: 334,042, no visible quality signal.
- Agensi security-scans, but only its own ~2,000 paid listings.

**So: a third of a million skills exist and not one of them carries a published quality measurement.**
That is the largest unclaimed position in this market, and it happens to be the thing tashan is built to
do. It also means our current honest posture on skills — *catalogued, not rated, here is exactly why* —
is already more rigorous than anything shipping.

---

## 3. Page & info structures worth stealing

**LobeHub — the dual surface.** `[I'm an Agent | I'm a Human]` on every marketplace page *and* every
listing. The agent side hands over a prompt pointing at `/mcp/<id>/skill.md`, and that file is a real
SKILL.md with frontmatter — so the marketplace **installs as a capability**, after which the agent has a
CLI (`search --sort ratingAverage`, `view`, `rate`, `comment`). They are optimising for the moment an
agent discovers it lacks a capability. Full teardown in `COMPETITIVE-LOBEHUB.md`.

**Glama — protocol-aware faceting (102 attributes).** Beyond ~85 categories with counts, they facet on
things derived from MCP itself:
- *Capabilities*: Tools 14,449 · Resources 6,829 · Prompts 6,361 · Logging 1,339 · Apps 103 ·
  Completions 177 · Tasks 192
- *Hosting*: Remote 25,763 · Local 19,383 · Hybrid 10,702
- *Environment*: Network 34,269 · Local 20,915
- *Author*: Claimed 9,187 · Official 3,690
- *Language*: Python 26,216 · TypeScript 21,720 · Go 409

"Does this run on my machine or theirs?" and "does it expose resources or just tools?" are real
pre-install questions. Our 15 categories don't answer either.

**PulseMCP — catalog freshness as a trust signal.** "LAST UPDATE: 5 HOURS AGO" in the masthead. Ours
says "measured Jul 25, 2026", which reads like a publication date, not a heartbeat.

**Agensi — "See it in action".** A `YOU SAY → YOUR AGENT DOES` transcript on the listing, showing a real
prompt and a real output excerpt. It answers "what does this actually do for me" better than any
description. Cheap for us to generate from a README, and nobody else does it.

**Smithery — per-tool listing with annotations**, including `READ-ONLY` markers. A user deciding whether
to grant something access cares enormously about read-only vs write.

---

## 4. Where each is soft

| Competitor | Soft spot |
|---|---|
| LobeHub | Grade ignores adoption + liveness entirely; "Not Claimed by Owner" is a conflict written into the rubric; ratings are agent-generated on their own instruction ("always rate and comment"); three marketplaces = three taxonomies, so the same job is filed three different ways; detail pages are client-rendered skeletons (weak for crawlers/answer engines) |
| Smithery | Only covers what they host; telemetry is first-party and unverifiable; a gateway has an interest in servers running through it |
| Glama | **No demand signal at all** — every grade describes the artifact, none asks whether anyone uses or keeps it; listing is opt-in and GitHub-OAuth-gated, so the deep analysis only reaches servers whose authors showed up; they earn from hosting the things they grade; MCP only, zero skills |
| PulseMCP | Est. visitors is a proxy for the *site*, not the software; partner-gated API ("working directly with partners"); smallest curated corpus |
| Agensi | Structural conflict — 30% of every sale, grading its own shelf; thin liquidity (found a **$19 skill with "0 installs"** displayed on its own page); only covers submitted inventory |
| MCP Market | Pure volume, no measurement |
| Everyone | **Nobody measures skills. Nobody measures demand and retention together. Nobody is disinterested.** (Note: "nobody publishes a re-derivable method" was my earlier claim and it is false — Glama's is open source and better documented than ours.) |

---

## 5. Where tashan cuts in

**Do not compete on listing count.** 333k skills is a GitHub crawl; 81k servers is a crawl with weak
dedup. Our own 757-row corpus contained 19 tutorial servers, two dependency-confusion canaries and 15
duplicate listings — and *finding those is the product*. Volume is the commodity; judgement is not.

Five positions, ranked by how defensible they are:

1. **Be the first to measure skills.** 333k listed, zero graded, by anyone. Our LLM expertise-eval
   applied to `SKILL.md` content is a per-skill signal that no crawler produces and no store wants to
   produce about inventory it sells. This is the biggest open position in the market.
2. **Grade liveness, loudly.** LobeHub's rubric cannot tell a maintained server from an abandoned one;
   Glama's "maintenance" grade is unexplained; Smithery only knows its own tenants. We already compute
   `vitality` and retention. Make "is this still alive?" the headline verdict, and state the contrast
   plainly: *a server can score A on packaging hygiene and be dead.*
3. **Neutrality, stated and testable.** No tashan score moves because a publisher registered, claimed a
   listing, or paid — and `tests/test_firewall.py` proves it in code. LobeHub's rubric docks you for not
   claiming; Agensi takes 30% of what it grades; Smithery and LobeHub both earn from consumption. We are
   the only party with nothing to sell on the shelf. Say it once, plainly, and let readers check.
4. **One catalog, one taxonomy.** Users have jobs, not artifact preferences. LobeHub needs three
   products merged to match this; Glama and PulseMCP don't carry skills at all.
5. **Published coverage.** Not "published method" — Glama's method is open-source and better documented
   than ours, so that ground is contested. What is still unclaimed is the honest denominator: "N of ~M
   known, from these sources, synced T". Nobody states what they are missing.

**Adopt (they're better, and cheap to match):** the dual agent/human surface with per-item `skill.md`;
hosting model (local/remote/hybrid) as a facet; protocol capability facets (tools/resources/prompts);
per-tool enumeration with read-only annotation; provenance classification (Official/Reference/Community);
catalog-freshness heartbeat; "see it in action" transcripts.

**Close (the one real evidence gap):** Smithery proves a server works by running it. We should do the
cheapest honest version — does the package resolve, does the declared entrypoint exist, does the
documented install command parse, does a remote endpoint answer — and label it *exactly* that far.
Never imply we executed code we didn't.

**The position, one line:** *Everyone else counts capabilities or sells them. tashan is the only one
measuring whether they're any good — including the 333,000 skills nobody has graded at all — and it
publishes the arithmetic because it has nothing on the shelf to protect.*

---

## 6. Sources

Visited 2026-07-26: [LobeHub MCP](https://lobehub.com/mcp) · [LobeHub Skills](https://lobehub.com/skills) ·
[LobeHub Agents](https://lobehub.com/agent) · [Glama registry](https://glama.ai/mcp/servers) ·
[Glama attributes](https://glama.ai/mcp/attributes) · [Smithery](https://smithery.ai/) ·
[Smithery server page](https://smithery.ai/servers/upstash/context7-mcp) ·
[PulseMCP directory](https://www.pulsemcp.com/servers) · [Agensi](https://www.agensi.io/) ·
[MCP Market skills](https://mcpmarket.com/tools/skills) ·
[official registry](https://registry.modelcontextprotocol.io/v0.1/servers) ·
[registry aggregator docs](https://modelcontextprotocol.io/registry/registry-aggregators)
