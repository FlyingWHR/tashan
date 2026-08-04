# Awl Frontmatter

> YAML frontmatter standard for Awl agents and commands — required fields (name for agents, description for both), recommended fields (tools, model), optional metadata (version, category, color), the four-tier model assignment rules (inherit/haiku/sonnet/opus), and the validation rules enforced by /awl-meta:validate-frontmatter. Use this skill whenever Claude is editing or creating a file under plugins//agents/.md or plugins//commands/.md, writing YAML frontmatter for an Awl agent/command, running /awl-meta:validate-frontmatter or /awl-meta:create-workflow, or reviewing frontmatter in a PR diff. Make sure to use this skill whenever an Awl agent or command markdown file shows up in the context — writing incorrect frontmatter silently breaks plugin discovery.

## Facts
- Page: https://tashan.sh/capability/skill-threading-needles-awl-frontmatter
- tashan id: skill:Threading-Needles/awl-frontmatter
- Source: https://github.com/Threading-Needles/awl
- Type: skill
- Category: other
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: not measured
- Freshness: not measured
- Evidence coverage: not measured
- Health: not measured
- Instruction depth: not yet graded
- Official: no

## Install

```sh
cp -r awl-frontmatter ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
