# Prep Compact

> Claude Code's auto-compact fires late and its generic summary often drops the files, decisions, and blockers you needed. The post-compact session then veers off course. prep-compact nudges you earlier: a UserPromptSubmit hook watches your transcript's byte delta since the last compact. When it crosses a configurable threshold (default 4 MB ≈ 450K tokens on Opus 4.7), Claude is prompted to invoke the prep-compact skill, which drafts a tailored /compact <mini-schema covering goal/next/files/deci

## Facts
- Page: https://tashan.sh/capability/plugin-koenvdheide-prep-compact-prep-compact
- tashan id: plugin:koenvdheide/prep-compact/prep-compact
- Source: https://github.com/koenvdheide/prep-compact
- Type: plugin
- Category: data
- tashan score: 33.0 / 100
- Adoption: 7.0
- Upkeep: 58.0
- Freshness: 87.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install prep-compact@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
