# Sourcing strategy — how tashan learns what exists

*Written 2026-07-26. Every number here was measured, not recalled — the commands are inline so they can
be re-run and disproved.*

---

## 0. The uncomfortable measurement

tashan's claim is that it measures **the whole field**, as against a store that only knows its own
opt-in inventory (`docs/COMPETITIVE.md` §"Where tashan wins", point 2). That claim is currently false.

| | measured | how |
|---|---|---|
| Capabilities in tashan | **2,877** | `SELECT COUNT(*) FROM capabilities` |
| Official MCP registry | **≥6,000** | walked `/v0.1/servers`, 60 pages × 100, still more |
| Glama registry | **~61,000** | glama.ai/mcp/servers, "60,943 in the Glama Registry" |
| mcp.so | **20,222** | truefoundry registry comparison, 2026 |
| LobeHub | **56,000+** | ditto |

Two conclusions, both actionable:

1. **We under-cover our own primary source by ~70%.** The official registry has ≥6,000 servers; we hold
   1,717 rows with a `registry_status`. That is not a sourcing-breadth problem, it is a bug (see §2).
2. **The field is ~10–60× larger than our corpus.** The honest headline is not "2,877 capabilities
   tracked" as though that were the field — it is "N of an estimated M". Until the site says that, the
   number flatters us and misleads the reader. Coverage must become a published metric, not a silent one.

The skills side was worse and it was my doing: the source list was seven GitHub repos taken off a single
search, hardcoded, with no rationale. That is not sourcing, it is a guess with a number attached.

---

## 1. The systemic insight: there is a standard, so stop writing scrapers

The Model Context Protocol publishes a **Generic MCP Registry API** — an OpenAPI spec that registries
implement so that downstream consumers can read them all the same way. The official registry implements
it; PulseMCP states it implements it "with PulseMCP-specific extensions"; the docs name Smithery,
PulseMCP, Docker Hub, Anthropic and GitHub as expected consumers/implementers.

```
GET /v0.1/servers                                  list, cursor-paginated
GET /v0.1/servers/{name}/versions                  version history
GET /v0.1/servers/{name}/versions/{version}        one version ("latest" allowed)
    ?updated_since=<RFC3339>                       INCREMENTAL SYNC
    ?search=<substring>                            server-name substring
```

This is the difference between a hobby crawler and a catalog: **one adapter, many sources**. Adding a
registry becomes a row in a manifest, not a new Python file. Anything that does not implement the spec
(marketplaces, awesome-lists, npm) gets a bespoke adapter, but those are the exception, not the pattern.

**Design rule:** a source is *data*, not code. `pipeline/sources.py` holds a manifest; adapters are
selected by the `protocol` field. Adding LobeHub or mcp.so should be a five-line entry.

---

## 2. What is broken in the current ingest (found while measuring)

1. **Wrong API version.** `build.py` calls `/v0/servers`. The current spec is `/v0.1/`. Both answer today;
   `/v0/` is not what the docs describe and will not be maintained forever.
2. **No incremental sync.** We do a capped full crawl (`REG_CAP=4000`) every run. Walking 6,000 servers
   took **562 seconds** — ~9s per 100. Full crawls are why coverage is capped, and the cap is why we hold
   1,717 of ≥6,000. `updated_since` turns an hour-long crawl into a few seconds and removes the reason
   for a cap to exist.
3. **`status` is ignored.** The registry marks servers `deprecated` or `deleted`, and the docs say plainly
   that **`deleted` typically means spam, malware, or illegal content** under the moderation policy, and
   that "aggregators may prefer to remove these servers from their index." We do not read this field on
   sync. An index whose product is trust must not be the last place a known-malicious server stays listed.
   Measured now: 5,955 active / 45 deprecated in the first 6,000.
4. **Single source.** One registry, no npm-keyword sweep, no skill marketplaces, no aggregator cross-check.
   Coverage of a field cannot be asserted from one source.

---

## 3. The source landscape (researched, not assumed)

### 3a. MCP servers

| Source | Protocol | Why it matters | Priority |
|---|---|---|---|
| Official MCP registry | Generic Registry API | Canonical identity + `status` moderation signal | **P0** (have, broken) |
| npm keyword sweep (`mcp`, `modelcontextprotocol`) | npm registry API | Catches servers never submitted to any registry — the "unlisted but popular" case a store structurally cannot see | **P0** |
| PyPI equivalent | PyPI API | Same, for the Python half of the ecosystem | P1 |
| Glama (~61k) | web + Apify actor | Largest known index; use as a **coverage oracle** (what do they have that we don't?) rather than a copy source | P1 |
| mcp.so (~20k), LobeHub (~56k) | web | Same oracle role | P2 |
| Docker MCP catalog | registry API | Container-distributed servers we currently barely see (21 `docker` rows) | P2 |
| GitHub topic/code search | GitHub API | Long tail; low precision, needs the quality gates | P2 |

### 3b. Agent skills

The skills ecosystem went from ~1 registry (Dec 2025) to **8+ marketplaces** by Q2 2026. Sources named
repeatedly across independent write-ups: Agensi, `anthropics/skills`, `addyosmani/agent-skills`, Cursor
Directory, ClaudeSkills.wiki, `awesome-claude-code-skills`, the OpenCode community registry, plus
marketplaces (MCP Market, LobeHub Skills, SkillRegistry, ClaudeSkill, SkillsMP, claudemarketplaces.com).

My seven-repo list caught `anthropics/skills` and some large mirrors and **missed most of the above**.
Note also that one marketplace advertises "2,330,640 skills" — a number that cannot be real in the sense
a user cares about, and a good reminder that **counting is not covering**. Dedup and quality gates decide
whether a source adds signal or noise.

### 3c. What the counts actually mean

Registry totals are not comparable and must not be quoted as though they were. They differ on:
- whether forks/mirrors are collapsed,
- whether a "server" is a package, a repo, or a hosted endpoint,
- whether dead/spam entries are pruned.

So tashan should publish **its own** coverage against a stated denominator and method, and treat
competitor totals as an oracle for *gaps*, never as a scoreboard to match. Chasing 56,000 rows of
unfiltered mirror content would make the product worse — we already found 19 tutorial servers, two
dependency-confusion canaries and 15 duplicate listings inside a corpus of only 757.

---

## 4. Identity: the hard part nobody sees

The same capability appears as an npm package, a registry entry, a GitHub repo, a Docker image and a
marketplace listing. Without identity resolution, more sources means more duplicates, and duplicates are
exactly what makes a catalog feel untrustworthy (we shipped 15 of them).

Resolution order, strongest evidence first:

1. **npm/PyPI package identifier** — globally unique, definitive.
2. **`owner/repo`** — strong, but monorepos host many capabilities, so pair with a subpath.
3. **Registry reverse-DNS name** (`io.github.user/thing`) — unique within the registry namespace.
4. **Normalised display name + identical description** — weakest; the current dedup. Keep as a last resort,
   never as the primary key.

Every row must record **which source(s) asserted it** (`sources` column) so that (a) coverage per source
is measurable, (b) a bad source can be retracted wholesale, and (c) the provenance is publishable —
"tashan says X because registry + npm + GitHub agree" is a stronger claim than a bare score.

---

## 5. Update model — a catalog is a clock, not a snapshot

| Cadence | Job |
|---|---|
| Hourly | Official registry `updated_since` delta; apply `status` changes (incl. removing `deleted`) |
| Daily | npm downloads/publish for tracked packages; GitHub push/release/contributors; `signal_history` snapshot |
| Weekly | Full reconcile against each source (catch deletions and drift the delta feed missed); skill re-scan |
| Monthly | Coverage audit against the oracles; re-grade expertise on changed READMEs |

The docs are explicit that aggregators should poll "on a regular but infrequent basis (e.g. once per
hour)" and that the registry gives **no uptime or durability guarantee** — so our copy is the source of
truth for the site, and every sync must be resumable, cached and idempotent. `signal_history` already
gives the retention moat; sync must never rewrite history, only append.

---

## 6. Integration: stop being a website, become an endpoint

The registry docs describe a **subregistry**: an aggregator that itself implements the OpenAPI spec, and
may inject custom metadata under `_meta` — their own example is literally `user_rating`, `download_count`
and `security_scan`.

That is tashan's distribution answer, and `docs/COMPETITIVE.md` names distribution as the thing we lack.
If tashan serves `/v0.1/servers` with trust, adoption, vitality and expertise under
`sh.tashan/capability`, then any MCP host that already speaks subregistry can consume tashan's scores
natively — no traffic to our site required, and the score travels to the point of decision. A rating
nobody can see at install time is a rating that does not affect anything.

This is a strategic priority, not a nice-to-have: it converts the catalog from a destination into
infrastructure.

---

## 7. What this means for the site (experience, not plumbing)

- **One catalog.** A user has a job ("query Postgres"), not a preference for artifact types. MCP server,
  skill, CLI are *properties* of an answer, filterable — never separate pages. The separate `/skills/`
  directory was a mistake and is being merged into the index.
- **Publish coverage.** "2,877 tracked" implies completeness we don't have. Say "N of ~M known, from
  these sources, last synced T".
- **Provenance on every row.** Which sources asserted this, and when we last checked.
- **Never rank what we can't measure per-item** — and say which inputs are item-level vs repo-level
  rather than hiding the distinction behind a single number.

---

## 8. Order of work

1. Fix the primary source: `/v0.1`, incremental `updated_since`, honour `status`, drop the cap. *(correctness + coverage, cheapest win)*
2. Source manifest + generic adapter; add npm keyword sweep. *(breadth, from a standard)*
3. Identity resolution with a `sources` provenance column. *(makes breadth safe)*
4. Merge skills into the one catalog; publish coverage + provenance in the UI. *(the experience)*
5. Subregistry endpoint with scores in `_meta`. *(distribution)*

Sources for the research in this document: the MCP registry aggregator docs
(<https://modelcontextprotocol.io/registry/registry-aggregators>), the generic registry API reference
(<https://github.com/modelcontextprotocol/registry>), PulseMCP's sub-registry docs
(<https://www.pulsemcp.com/api/docs/v0.1>), Glama's server index
(<https://glama.ai/mcp/servers>), and 2026 registry/marketplace comparisons from TrueFoundry
(<https://www.truefoundry.com/blog/best-mcp-registries>) and Agensi
(<https://www.agensi.io/learn/best-ai-agent-skills-marketplaces-2026>).
