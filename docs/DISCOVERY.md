# The discovery gap — how good skills actually get found (2026-07-27)

*Prompted by an observation from the founder: the genuinely good skills — impeccable (design), ponytail
(context discipline), a SwiftUI/iOS skill — were all discovered by watching videos and following links,
not by searching any registry. That is a product gap, and it turned out to be a sourcing gap first.*

---

## 1. We were crawling the wrong artifact

Every directory in this market (us included) crawls GitHub for `SKILL.md`. That finds ~333,000 files, of
which we measured **39% to be a single template with a vendor name swapped**. It is the largest, noisiest,
least curated view of the ecosystem available.

Meanwhile the skills people actually recommend to each other are not published that way at all. They are
published as **plugins**:

```
/plugin marketplace add pbakaus/impeccable
```

and declared in a first-class manifest at `.claude-plugin/marketplace.json`, against a published schema
(`anthropic.com/claude-code/marketplace.schema.json`).

**The evidence was already in our own tool.** `npx tashan-cli doctor` on a working developer's machine found
123 installed items and could identify only 18. The other 105 arrived through the plugin channel. Every
skill the founder named by hand resolves to a plugin repo:

| Named | Actually is |
|---|---|
| impeccable | `pbakaus/impeccable` |
| ponytail | `DietrichGebert/ponytail` |
| the iOS one | `AvdLee/SwiftUI-Agent-Skill` |

Not one of them is findable by crawling `SKILL.md`.

---

## 2. The population, measured

| Source | Count | Nature |
|---|---|---|
| `anthropics/claude-plugins-official` | **273** | Hand-curated by Anthropic, ships with every install |
| `anthropics/claude-plugins-community` | **2,269** | Third-party, reviewed / safety-checked |
| GitHub repos with `.claude-plugin/marketplace.json` | **~5,184** | The long tail (code-search count) |

~2,500 curated plugins reachable in **two HTTP fetches**, against 333,000 crawled files of unknown
provenance. Inclusion in an Anthropic-managed marketplace is itself a quality signal we get for free.

---

## 3. Why this corpus is *ratable* and the SKILL.md corpus is not

This is the important structural point.

We withheld ratings from 854 monorepo skills because they all scored an identical **42.0** — repo
maintenance signals shared across every skill in the repository say "the repo is alive", not "this skill
is good" (`docs/MARKET-SKILLS.md` §3).

**A plugin does not have that problem.** A plugin usually owns its repository, so stars, push recency,
contributor count and license describe *that plugin*. The manifest also carries per-item `version`,
`category`, `tags`, `homepage` and `author`. So plugins can carry an honest score where bare skills
cannot — which means closing the discovery gap also closes part of the grading gap.

Stars are, additionally, the closest public proxy for "the thing people keep recommending in videos and
threads" — which is precisely the informal channel that was doing this job before.

---

## 4. What we found but will NOT use (and why that matters)

Claude Code caches Anthropic's plugin catalogue locally at
`~/.claude/plugins/plugin-catalog-cache.json`. It contains, for 255 plugins:

- **`unique_installs`** — real adoption. frontend-design **1,017,241**; superpowers **913,876**;
  code-review 404,331; context7 392,837.
- **Per-model token cost** — `always_on` and `on_invoke` for each plugin *and each skill inside it*.
  A genuinely novel quality axis: `vercel` costs 2,629 always-on tokens, `frontend-design` costs 83.

Both would be spectacular additions. **Neither is going into a score**, because neither is published
anywhere a reader can fetch. Our own rule is that every input must be re-derivable from public evidence,
and the criticism we level at Smithery and LobeHub is precisely that they rank on first-party numbers
nobody outside can audit. Ingesting a local cache would make us the thing we object to, and would also be
unreproducible for anyone else running this pipeline.

If Anthropic publishes these figures at a citable URL, both become usable immediately — and the
context-cost axis in particular is worth pursuing, because "what does this plugin cost you in context"
is a real question nobody in the market answers.

---

## 5. The wider discovery channels (for later sourcing rounds)

Ranked by signal quality, not size:

1. **Anthropic's two marketplaces** — curated/reviewed. *Ingesting now.*
2. **Plugin manifests across GitHub** (~5,184) — self-published, star-ranked. *Ingesting now.*
3. **Curated human lists** — `ComposioHQ/awesome-claude-plugins`, and the several 2026 "best plugins,
   tested and ranked" write-ups. Inclusion is a human judgement worth treating as a weak endorsement
   signal; several independent lists converging on the same plugin is a strong one.
4. **The SKILL.md crawl** — breadth, low precision. Keep, gate hard.
5. **Video / social** — where discovery actually happens today and the reason this gap existed. Not
   directly ingestible, but it is the demand signal the other four are proxies for.

---

## 6. What changes in the product

- `kind='plugin'` becomes a first-class capability type alongside `npm`, `remote`, `skill`.
- Plugins are **rated**, not merely catalogued, because their signals are per-item.
- `tashan doctor` gets dramatically more useful the moment this lands: the 105 unrecognised items on a
  real machine were overwhelmingly plugin-delivered.
- The honest headline stops being "N skills crawled" and becomes something a user can act on: *of the
  things you can actually install from the channels people actually use, here is what the evidence says.*
