# Mumei

> Quality Enforcement Layer for Claude Code. Uses Hooks to physically gate spec phases, Wave commits, and reviews at the OS boundary — not via prompt-level instructions the agent can ignore. Key features: - 4-phase workflow (brainstorm → plan → implement → review → done) with hook-gated phase entry. The agent cannot edit src/ while requirements are still drafted, cannot commit a Wave with incomplete tasks, cannot push while the latest review verdict is MAJORISSUES. - 3 spec reviewers (requirem

## Facts
- Page: https://tashan.sh/capability/plugin-hir4ta-mumei-mumei
- tashan id: plugin:hir4ta/mumei/mumei
- Source: https://github.com/hir4ta/mumei
- Type: plugin
- Category: productivity
- tashan score: 50.0 / 100
- Adoption: 13.0
- Upkeep: 99.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 2
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install mumei@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
