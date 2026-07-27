# Glama — full teardown (2026-07-27)

**Correction first.** In `docs/MARKET.md` I described Glama as "three unexplained letter grades" with an
"enormous unfiltered corpus", and claimed nobody in the field "publishes a method you can re-derive."
All three were wrong. Glama publishes the most detailed methodology of anyone here, open-sourced its
scoring framework, and filters its corpus by whether a server actually builds. This document supersedes
that entry; `MARKET.md` has been corrected.

Glama is the most technically serious competitor in this market. Not LobeHub.

---

## 1. What it actually is

*"The MCP Server Registry, Inspector & Gateway."* Three products off one dataset:

| Surface | Scale (2026-07-27) |
|---|---|
| `/mcp/servers` — open-source registry | **61,109** |
| `/mcp/connectors` — hosted remote endpoints | **9,970** |
| `/mcp/tools` — **individual tools, indexed and graded** | **306,671** (414,802 incl. connectors) |
| `/mcp/clients` — client compatibility matrix | **158** |
| `/mcp/inspector` · `/mcp/methodology` · `/api/mcp/v1/*` | — |

Run by **punkpeye**, who also maintains `awesome-mcp-servers` — i.e. the person behind the canonical
community list also owns the registry. That is a distribution position we should not underestimate.

**Business model:** $9 / $26 / $80 per month for AI credits + *hosted* MCP servers + log retention.
The registry is top-of-funnel for a chat/API/hosting product.

---

## 2. Their pipeline (from `/mcp/methodology` — read it, it is unusually candid)

> "Over one million such scans in the past twelve months."

1. **Maintainer verification** — GitHub OAuth, and Glama checks the submitter has write/admin on the
   repo. You cannot list someone else's server.
2. **Full git history clone**, continuously synced. Every tag, every commit retained. Schema changes,
   behavioural changes and maintainer transitions are part of a permanent record.
3. **Sandboxed build + execution in Firecracker microVMs.** Dockerfile authored by the maintainer or
   *AI-inferred* from project structure. **If the build fails, the listing is withheld from search,
   categories and recommendations** — it exists but is not discoverable.
4. **Protocol introspection** — they actually run `tools/list`, `resources/list`, `prompts/list` and
   capture full JSON Schema, including the MCP annotation hints (`readOnlyHint`, `destructiveHint`,
   `idempotentHint`, `openWorldHint`).
5. **Behavioural analysis at the syscall and network layer** while it runs: access to credential paths
   (SSH keys, cloud creds, browser cookie stores), egress to hosts not in the manifest, exfiltration
   payload signatures, process forks into unrelated binaries, writes outside the working directory.
   Findings are classified **Malicious** (internal review → de-listing) or **Risky** (surfaced publicly
   on the listing).
6. **TDQS — Tool Definition Quality Score.** Six dimensions, 1–5 each, per tool: Purpose Clarity,
   Usage Guidelines, Behavioral Transparency, Parameter Semantics, Conciseness, Contextual Completeness.
   Plus **tool-set coherence** (do the tools compose into a non-overlapping API?) and **server
   cohesiveness** (does it do what it claims — "a server that claims to be a Postgres client but exposes
   arbitrary shell execution scores poorly here").
7. **Re-scan on every commit.**

For **connectors** they can't build, so: sandbox credentials from the maintainer (never production),
scheduled introspection, **schema-drift diffing between sweeps**, and **prompt-injection detection in
tool/resource descriptions** — role-override attempts, exfiltration prompts embedded where an LLM will
read them. Score drift over time is itself recorded as a signal.

### TDQS is grounded in published research and open-sourced

Two Feb-2026 papers underpin it:
- *"MCP Tool Descriptions Are Smelly"* (arXiv 2602.14878) — 856 tools / 103 servers: **97% have at least
  one defect, 56% don't say what the tool does, 89% omit usage constraints.**
- *"From Docs to Descriptions"* (arXiv 2602.18914) — 10,831 servers: well-described tools are selected
  by models **260% more often.**

Framework at `github.com/glama-ai/tool-definition-quality-score`. Per-dimension breakdowns are public on
every listing, *with gap analysis and concrete fix suggestions for maintainers*.

---

## 3. Info tree

Detail page tabs: **Overview · Schema · Related Servers · Score · Discussions**, plus Favorite,
categories, author, language, hosting badge, and "How do I use X?".

Public API — unauthenticated, documented, no key:
```
GET https://glama.ai/api/mcp/v1/servers/<namespace>/<slug>
```
Returns: `id · name · namespace · slug · description · repository.url · spdxLicense{name,url} ·
attributes[] · tools[] · environmentVariablesJsonSchema · url`

That `environmentVariablesJsonSchema` is worth noting — a full JSON Schema of every env var a server
needs, with types and constraints. It answers "what do I have to configure" before you install.

### Faceting — 102 attributes, protocol-aware

- ~85 categories with counts (Developer Tools 15,969 · Search 9,240 · App Automation 4,962 …)
- **Capabilities**: Tools 14,449 · Resources 6,829 · Prompts 6,361 · Logging 1,339 · Apps 103 ·
  Completions 177 · Tasks 192
- **Hosting**: Remote 25,763 · Local 19,383 · Hybrid 10,702 — **Environment**: Network 34,269 · Local 20,915
- **Author**: Claimed 9,187 · Official 3,690 — **Language**: Python 26,216 · TypeScript 21,720 · Go 409

The **client directory** faceted by protocol support (Tools 158 · Resources 45 · Prompts 42 ·
Sampling 16 · DCR 16 · Elicitation 15 · Roots 9 · Tasks 2) is effectively a compatibility matrix for the
protocol. Nobody else publishes one.

---

## 4. Where they are genuinely ahead of us

1. **They run the code; we read metadata.** Firecracker sandbox + syscall/network observation is the
   strongest evidence anyone in this market produces, and unlike Smithery's proxy telemetry it covers
   61k servers rather than only paying tenants.
2. **Tool-level granularity.** 306,671 tools individually graded. The user's real question is often
   "what can actually call X" — they answer it; we don't index tools at all.
3. **Security findings as a public signal.** Malicious/Risky, from observed behaviour. Our
   name-confusion note is a rounding error next to this.
4. **Prompt-injection + schema-drift detection on remote connectors.** A whole threat class we don't touch.
5. **Freshness.** Re-scan per commit; the tools index said "Last updated 2026-07-27 10:59" — within the hour.
6. **A published, open-source, research-grounded method.** I claimed this ground for tashan. It is
   contested, and on tool-description quality they are ahead.

## 5. Where they are soft — the real openings

1. **No demand signal, anywhere.** Every Glama score describes the *artifact*: is it well-built, well-
   described, coherent, safe. Nothing measures whether **anyone actually uses it**. No downloads, no
   config reach, no retention. A beautifully-documented server that nobody has ever installed scores A/A.
   *This is our entire wedge and it is untouched.*
2. **Listing is opt-in and identity-gated.** "Before a server is listed, the submitting maintainer
   authenticates through GitHub OAuth" with write/admin verification. Whatever the official-registry
   superset adds, the deep analysis only reaches servers whose authors showed up. They cannot tell you
   about the thing nobody claimed.
3. **They earn from hosting.** Credits + hosted servers + log retention. They profit when you *run*
   capabilities on Glama — so "don't use any of these" is never a comfortable verdict, and the gateway
   is the funnel the registry feeds.
4. **MCP only.** Zero coverage of agent skills. ~333,000 skills exist; Glama indexes none of them.
5. **Quality ≠ liveness in their headline.** Maintenance is graded (we saw `D maintenance` on a server
   "last updated a year ago", so it works) but it sits as one letter beside two others, and a stale
   server still shows `A quality`. The composite tells you the code is nice, not that the project lives.

---

## 6. What this changes for us

**Stop claiming a methodology edge.** Glama's is better documented than ours and their framework is on
GitHub. Ours is re-derivable and theirs is too. Say what's actually distinct instead:

- **We measure demand; they measure the artifact.** "Is it well-made" and "does anyone keep it" are
  different questions, and only one of them is answered by reading the source. This is a clean,
  defensible split — we should state it as complementary rather than competitive, because it is.
- **Third-party retention.** They hold the *server's own* git history; we hold *other people's* configs
  over time. Added-then-removed by someone who isn't the author is a verdict no source analysis reaches.
- **Skills.** They don't do it. Nobody does.
- **Disinterest.** They host, LobeHub runs, Smithery proxies, Agensi sells. We do none of it.

**Adopt, cheaply:** the `environmentVariablesJsonSchema` idea (what must I configure?), hosting model as
a facet, protocol-capability facets, and the client compatibility matrix — all derivable from data we
already fetch or could fetch statically.

**Do not attempt:** a Firecracker build farm. It is the correct thing for them and the wrong thing for
us — it is exactly the heavy stack we decided against, it would take the neutrality budget, and they
have a year and a million scans of head start. The honest cheap version of "does it work" (does the
package resolve, does the entrypoint exist, does the endpoint answer) is the ceiling worth reaching for.

**One line:** *Glama tells you whether a server is well-built, well-described and safe to run. It cannot
tell you whether anyone kept it. We should be the answer to the second question and link to them for the
first.*
