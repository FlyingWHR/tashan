# LobeHub — full teardown (2026-07-26)

Researched by walking the live site in a browser (WebFetch gets 403). Every number and label below was
read off the page, not recalled. LobeHub is the most serious competitor in the field — more than Agensi,
because their conflict of interest is mild, their coverage is enormous, and **they already ship a
published quality score.**

---

## 1. Scale

| Marketplace | URL | Listings |
|---|---|---|
| MCP Servers | `/mcp` | **81,430** |
| Skills | `/skills` | **332,962** |
| Agents | `/agent` (`/assistants` redirects) | **234,885** |
| | | **~650,000 total** |

tashan: 1,240. We are 0.2% of their listing count. Any strategy premised on out-listing them is dead
on arrival — and, as §5 argues, out-listing them is also the wrong goal.

---

## 2. Page tree

```
lobehub.com
├── /mcp                                   MCP Server Marketplace
│   ├── hero: count + "ranked by activity, stability, and community feedback"
│   ├── [I'm an Agent | I'm a Human]       ← dual-surface toggle
│   ├── /mcp/skill.md                      ← AGENT ENTRYPOINT (a real SKILL.md)
│   ├── left rail: 16 categories w/ counts (Developer Skills 40.9k, Productivity 3.8k,
│   │              Utility 9.7k, Information Retrieval, Media Generation, Business Services,
│   │              Science & Education, Stocks & Finance, News, Social Media, Gaming,
│   │              Lifestyle, Health, Travel, Weather)
│   ├── sort: Recommended ▾ · search (⌘K) · "Request a Server"
│   ├── home sections: Most Installed · Trending · Highlighted · Recently Updated ·
│   │                  Browse by Category   (each "View All")
│   └── /mcp/<author>-<repo>                DETAIL PAGE
│       ├── breadcrumb: LobeHub / MCP Servers / <id>  (+copy)
│       ├── header: icon, name, validation badge, npm + GitHub links,
│       │           version · author · date, category chip, language, install count
│       ├── tabs: Overview | Installation Method | Server Features |
│       │         Related MCP | Score | Version History          + "Need help?"
│       ├── Overview: "What can you do with this MCP Server?" (collapsible plain-English
│       │             answer FIRST), then README
│       ├── Score tab: grade banner, % bar w/ bands, N/100 points,
│       │              "Required Items: 2/4", 9-item checklist, GitHub badge snippets
│       ├── right rail: Install · Refresh Metadata · Share
│       │               deployment card (Local Service / Hybrid Service, explained)
│       │               Installation Configuration → View Details
│       │               [I'm an Agent | I'm a Human] ← again, per item
│       ├── /mcp/<id>/skill.md              ← PER-ITEM AGENT ENTRYPOINT
│       └── Related MCP Servers → View More
├── /skills                                Skills Marketplace (332,962)
│   ├── "Where Agents Find Their Skills" / "built agent-first and open to every stack"
│   ├── [I'm an Agent | I'm a Human] → /skills/skill.md
│   └── left rail: ~20 DIFFERENT categories (Coding Agents & IDEs 51.1k, Web & Frontend 34k,
│                  DevOps & Cloud 41.8k, Search & Research, Browser & Automation, CLI Utilities,
│                  Git & GitHub, PDF & Documents, Notes & PKM, Calendar & Scheduling, …)
├── /agent                                 Agent Marketplace (234,885)
│   └── left rail: ~14 DIFFERENT categories (Academic, Career, Copywriting, Design,
│                  Education, Emotions, Entertainment, Games, General, Life, Marketing,
│                  Office, Programming, Translation)
├── /badge/mcp/<id>  ·  /badge/mcp-full/<id>?theme=light      embeddable badges
├── Products · Community · Resources · Pricing · Get started
└── footer → Marketplace: Agents · MCP · Skills · AI/LLM Icons · Creator Program
           Solutions: Coding · Pages · Task · for Slack / Telegram / Discord
```

---

## 3. Info tree (per MCP listing)

From their JSON API contract (documented in `skill.md`) plus the rendered page:

```
identifier, name, description, author{name,url}, version, category, tags[]
capabilities { tools: bool, resources: bool, prompts: bool }
tools[] { name, description }                 ← per-tool listing, not just a count
connectionType (stdio | sse | http)
deployment label (Local Service | Hybrid Service) + plain-English explanation
installCount, ratingAverage, ratingCount, commentCount
github { url, stars, language, license }
overview { summary, readme }
isFeatured, isValidated
createdAt, updatedAt
comments[] { id, author{type:"agent"|…, displayName, tags:["claude-code"]},
             content, upvotes, downvotes, createdAt }
score { points/100, grade, requiredItems n/4, 9 criteria }
```

Two things there we do not have: **per-tool enumeration** (what functions does this actually expose)
and **deployment model** (does this run on my machine or theirs). Both are things a user genuinely needs
before installing.

---

## 4. Their score — read it carefully, it's their weak flank

Grade bands: **F (0–60%) · B (60–80%) · A (80–100%)**. Displayed as a headline verdict
("Low-Quality Server — This MCP Server is incomplete or of low quality. Use with caution."),
a points total (`37/100`), and `Required Items: 2/4`.

The nine criteria:

1. **Validated** — passed installation validation; it installs and runs correctly
2. Provides at least one installation method
3. Includes at least one Skill (their word for a tool)
4. Has README
5. Offers easy installation (easier than manual setup)
6. Has LICENSE
7. Includes prompts
8. Includes resources
9. **Not Claimed by Owner** — "you can claim it via GitHub Badge"

They also state they "regularly scan code repositories and documentation to confirm that the server is
operational" and extract features.

### What this means

**It is a packaging-hygiene checklist, not a measure of whether anything is good or alive.** Nothing in
those nine items asks: does anyone use this? was it touched this year? is it archived, deprecated, or
abandoned? is it one person's weekend project? A tidy, well-licensed, fully-documented server that
nobody has installed and nobody has committed to since 2024 scores **A**. That is a real and exploitable
gap — it is the "stars ≠ trust" problem in a new costume.

**Criterion 9 is the tell.** A server loses points because *its author has not signed up to LobeHub*.
That is platform engagement scored as though it were quality, in a rubric presented to users as a
quality grade. It is precisely the conflict `docs/COMPETITIVE.md` predicts of anyone who both runs the
shelf and grades it — and unlike Agensi's, it is written down in public where we can point at it.

**Their ratings are agent-generated on instruction.** `skill.md` tells every agent: *"Always rate and
comment after using a plugin."* Reviews are attributed to agent identities registered via their CLI. It
is a clever supply mechanism for the cold-start review problem, but it means the "community feedback"
leg of their ranking is (a) first-party, (b) unauditable from outside, and (c) trivially gameable by
anyone who can instruct agents at volume.

---

## 5. Where they genuinely beat us — no strawman

1. **Live validation.** They actually install and run the server and confirm it works, and extract its
   real tool list. We infer from metadata. For "will this work?", executing it is stronger evidence than
   anything we currently produce. **This is the one place their evidence is better than ours.**
2. **Per-tool detail.** They list every tool with a description. We show a package.
3. **The dual-surface pattern** (§6) — genuinely excellent, and cheap for us to match.
4. **Deployment clarity** — "Local Service: runs on your device" vs "Hybrid". Plain language for a
   question every user has.
5. **"What can you do with this?"** answered in one collapsible box before the README. Job-first.
6. **Coverage**, by ~500×.
7. **Distribution** — they are the runtime; the catalog is where their users already are.

## 6. The dual-surface pattern (the thing worth stealing outright)

Every marketplace page and every listing offers **[I'm an Agent | I'm a Human]**:

- **Human** → normal install UI.
- **Agent** → a copyable prompt: *"Read https://lobehub.com/mcp/<id>/skill.md and follow the
  instructions to set up the LobeHub MCP Marketplace and install the MCP server."*

And `skill.md` is not documentation — it is a **real SKILL.md with YAML frontmatter**, so the
marketplace installs *as a capability*. Once installed, the agent has a CLI
(`npx @lobehub/market-cli`) with `search --sort ratingAverage`, `view`, `rate`, `comment`, `comments`,
`react`, and an identity registration flow.

**The strategic read: they are not optimising for humans browsing a website. They are making the
marketplace callable by the agent at the moment it discovers it lacks a capability.** That is the right
instinct about where this market goes, and it is the same conclusion `docs/SOURCING.md` §6 reached from
the subregistry angle.

---

## 7. Where we beat them — and what to build

### Already true
- **One catalog, one taxonomy.** They run three marketplaces with three unrelated category sets. The
  same job ("browse the web") lives under *Developer Skills* in MCP, *Browser & Automation* in Skills,
  and nowhere in Agents. A user must know which artifact type they want *before* they can look. We
  merged this on 2026-07-26 — and they structurally cannot follow without merging three products.
- **Server-rendered pages.** Their detail pages render from client-side skeletons; with JS off there is
  nothing to index. Ours are prerendered with JSON-LD. For answer engines and crawlers, we win.
- **Published, re-derivable method.** Ours is a formula over public inputs anyone can recompute. Theirs
  is a checklist plus first-party install counts and agent reviews that nobody outside can verify.
- **We say what we don't know.** 519 rows carry `rated: false` with a stated reason. Their rubric awards
  a confident A to things it has not actually measured the liveness of.

### To build (ranked)

1. **Liveness in the grade — our sharpest wedge.** Publish `abandoned`/`deprecated`/`archived` and
   last-activity prominently, and make the contrast explicit in the methodology: *a server can score A
   on packaging hygiene and still be dead; we grade whether it is alive and used, not whether it has a
   LICENSE file.* We already compute `vitality` — surface it as a headline verdict like their grade
   banner, not a table cell.
2. **Adopt the dual-surface pattern, then go further.** Ship `/capability/<slug>/skill.md` per item and
   a marketplace-level one, as installable SKILL.md with frontmatter. Ours differs by carrying the
   *evidence* — trust, adoption, vitality, what's unrated and why — so an agent choosing between two
   servers gets the measurement, not just the install command.
3. **Close the validation gap.** Their one true evidence advantage. Start with what is cheap and honest:
   does the package resolve and its declared entrypoint exist; does the documented install command
   parse; does a remote endpoint respond. Label it exactly as far as it goes — never imply we ran their
   code if we didn't.
4. **Per-tool enumeration.** Extract the tool list from the manifest/README. "What functions do I
   actually get" is a real user question we currently don't answer.
5. **Deployment model on every row.** Local / hybrid / remote, in plain language.
6. **Name the conflict, once, without whining.** Our methodology should state that no part of a tashan
   score depends on the publisher registering with tashan, claiming a listing, or paying us — and that
   this is checkable in `tests/test_firewall.py`. Then let the reader go look at criterion 9 themselves.

### What NOT to do

Do not chase 650,000 listings. Their most-installed *agent* is "Jailbreak Mode — an unconstrained AI
assistant without moral restrictions." At their scale the catalog is a crawl, not a judgement. Our own
corpus of 757 contained 19 tutorial servers, two dependency-confusion canaries and 15 duplicates — and
finding those is the product. Coverage should grow toward *the servers people actually run*, with the
quality gates loud and documented, and the honest denominator published (`docs/SOURCING.md` §0).

**The one-line position:** *LobeHub tells you a server is well-packaged and that agents on their
platform liked it. tashan tells you whether anyone actually runs it, whether it's still alive, and shows
you the arithmetic — and nothing you can buy or sign up for moves the number.*
