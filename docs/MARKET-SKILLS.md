# The skill marketplace segment — research (2026-07-27)

*Visited and measured in-browser. This covers the Agensi-style segment — curated / paid / creator-economy
skill stores — as distinct from the crawl directories in `docs/MARKET.md`.*

---

## 0. The headline: paid skills have almost no demand

Agensi's own creator page publishes skills-per-creator alongside downloads-per-creator. Scraped and
totalled from the live page:

| | |
|---|---|
| Creators listed | **153** (they claim "250+") |
| Skills | **2,032** |
| **Total downloads, entire marketplace** | **5,582** |
| Downloads per skill | **2.75** |
| Creators with **<25 total downloads** | **130 of 153 (85%)** |

The distribution is the story:

| Creator | Skills | Downloads |
|---|---|---|
| Nex AI | 229 | **16** |
| Arnstein Larsen | 218 | **7** |
| Echo Rose | 180 | **3** |
| PromptWagon | 141 | **3** |
| Roy Yuen | 111 | 945 |
| **Samuel Rose** | **10** | **1,679** |

The top uploader has **229 skills and 16 downloads** — 0.07 downloads per skill. The single best-performing
creator has the *fewest* skills on the platform. Volume and demand are inversely correlated here, which is
what a supply-spammed marketplace looks like: creators mass-uploading against a market that isn't buying.

For contrast, **ClaudeSkill** — free, open-source, same SKILL.md format — reports **184,300 installs**
across 2,840 skills. That is roughly **33× Agensi's total download volume** from a comparable catalogue
size, with no payment step.

**Read:** the constraint in this segment is not supply, curation, or payment rails. It is that nobody is
looking for skills to buy yet. A paid skill store is currently a solution to a problem the market has not
expressed.

---

## 1. The segment, site by site

### Agensi — `agensi.io`
- **2,032 skills · 153 creators shown · 5,582 downloads.** Prices $7.99–$19, 30-day refund, Stripe,
  credits, "Make an offer". 30% platform cut (per `docs/COMPETITIVE.md`).
- Trust signal: **"Security scanned"** — a binary badge, no detail, no methodology page found.
  Every creator is "Verified creator".
- Page tree: `/skills` · `/skills/<slug>` · `/creators` · `/creators/<slug>` · `/requests` · `/mcp` ·
  `/dashboard`. Two-audience anchors (`#for-users`, `#for-creators`).
- **Best UX idea in the whole segment:** *"See it in action"* — a `YOU SAY → YOUR AGENT DOES` transcript
  on the listing showing a real prompt and a real output excerpt. It answers "what will this do for me"
  far better than any description. Worth stealing.
- Observed on a live listing: a **$19 skill displaying "0 installs"**. They show the number that
  undermines the sale, which is honest — and devastating.

### ClaudeSkill — `claudeskil.com`
- **2,840 skills · 620 creators · 184.3k installs · 1.2k GitHub sources.**
- **Free forever for open source.** Revenue is *1-on-1 coaching at $100/hr* — the marketplace is a
  funnel for services, not a take-rate business.
- Positioning: *"A registry that behaves like source control, not an app store."*
- **Moderation, stated:** every submission enters a review queue; "malware and typosquats are rejected;
  legitimate open-source ships inside 24 hours."
- **Role-based taxonomy** (38 categories): Android Developer, iOS Developer, Frontend, Designer,
  DevOps, PPT Creator, Video Editor, Prompt Engineer, QA, Data Analyst — *"a skill for whatever hat
  you're wearing today"*. A genuinely different axis from domain categories, and closer to how people
  actually search.
- Creator tooling: install analytics, star history, referrer breakdown, auto-generated SEO/OG/JSON-LD.
- Large attached SEO content farm: "the full 2026 AI landscape" — vibe-coding tool comparisons,
  "AI for lawyers/doctors/teachers", "cursor vs windsurf", "sora 2 vs veo 3", GEO.
- **Caveat on their social proof:** the testimonial wall attributes quotes to named individuals at
  Stripe, Figma, Mercury and Retool — and the same four quotes repeat verbatim in the carousel loop.
  Unverifiable, and the repetition is consistent with placeholder marketing content. Treat the
  184.3k install figure as self-reported and unaudited too.

### SkillsMP — `skillsmp.com`
- Claims **2,330,640 "Collected SKILL.md files"**. Note the careful wording: *files*, not skills. This
  is a GitHub-wide file count including forks and vendored copies — it is 7× LobeHub's 332,962 and
  ~1,000× any curated catalogue. It is a vanity denominator, not a measure of the field.
- Taxonomy axes: Skills · Creators · **Occupations** · Docs. REST API. "Run any Skill in Manus with one
  click" — an execution integration.
- **Their per-skill number is repo-level.** `frontend-design` and `skill-creator` — two distinct skills —
  both display **163.3k**, because both live in `anthropics/skills`. A property of the repository is
  being rendered as though it were a property of the skill.
  *This is exactly the number tashan refused to publish.* We measured the same thing (854 skills all
  scoring 42.0, within-repo spread 42.0–42.0) and withheld it as `rated: false` with a stated reason.
  Someone else is shipping it as a headline figure.

### LobeHub `/skills` (332,962) and MCP Market (334,042)
Covered in `docs/MARKET.md`. Both are GitHub-wide `SKILL.md` crawls; **neither attaches any quality
grade to a skill.** LobeHub grades MCP servers and gives skills no Score tab at all.

---

## 2. Nobody can agree what a "skill" is

| Source | Count | What it's counting |
|---|---|---|
| Agensi | 2,032 | submitted, paid, curated |
| ClaudeSkill | 2,840 | submitted, reviewed, free |
| LobeHub | 332,962 | GitHub-wide crawl |
| MCP Market | 334,042 | GitHub-wide crawl |
| SkillsMP | 2,330,640 | every `SKILL.md` **file**, forks included |
| tashan | 524 | crawl, deduped, template-stubs and description-less entries removed |

Three orders of magnitude between the smallest and largest catalogue of the *same ecosystem*. Every
count is a different question answered: submitted vs crawled vs deduped vs raw files. **Any headline
that says "N skills" without saying which of those it means is noise**, and that includes ours — which
is why `docs/SOURCING.md` §0 requires publishing the denominator and method, not just the number.

---

## 3. What nobody in this segment does

1. **Grade a skill.** Not one of them publishes a per-skill quality measurement. Agensi has a binary
   "security scanned"; ClaudeSkill has a review queue; the crawlers have nothing. The nearest thing to
   a quality signal anywhere is SkillsMP's repo-level number worn as a per-skill badge.
2. **Measure retention.** No one asks whether an installed skill is still installed a month later.
3. **Separate the artifact from its repo.** Everyone either ignores the distinction or launders it.
4. **State a denominator.** Counts range 2k–2.3M with no methodology attached to any of them.

---

## 4. Implications for tashan

**Do not build a paid skill marketplace.** The segment's best-funded attempt has 2,032 paid skills and
5,582 lifetime downloads, and 85% of its verified creators are under 25 downloads. The free registry
next door has 33× the demand. Payment rails are not the missing piece; nothing about our position
improves by adding a checkout, and adding one would cost the disinterest that is the whole asset.

**The grading gap is real and it is ours to take.** ~333k skills crawled (or 2.3M files, depending who
you ask), zero published quality measurements, in a segment where the supply side is visibly spamming.
"Which of these 2,000 paid skills is worth anything" is a question the store selling them structurally
cannot answer.

**Our restraint is a differentiator we should say out loud.** We computed a per-skill score, saw it was
a repo-level artefact, and withheld it. A competitor is shipping the same class of number as a headline.
The methodology page should state the rule plainly: *a number that describes the repository will not be
printed next to the skill.*

**Steal two things:**
- Agensi's **"See it in action"** transcript — the single best answer to "what does this actually do".
- ClaudeSkill's **role-based taxonomy** ("the hat you're wearing today") as a second axis alongside our
  domain categories. Cheap: it is a re-labelling of data we already hold.

**Watch:** ClaudeSkill's moderation stance ("typosquats rejected") is the closest thing in the segment to
our canary/junk gates, and it is a positioning we should not concede — we found and delisted two
dependency-confusion canaries with published evidence, which is stronger than a review-queue claim.
