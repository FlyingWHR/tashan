# Claude Codex Loop

> claude-codex-loop orchestrates a structured collaboration loop between Claude Code (designer/reviewer) and OpenAI Codex (auditor/implementer). It runs two stages — design and code — each with up to 5 rounds of iterative review plus an independent validation pass. How it works: - Brainstorming (optional) — Explore requirements interactively before designing - Design stage — Claude Code writes a spec, Codex audits it independently each round until convergence - User gate — You review and approve

## Facts
- Page: https://tashan.sh/capability/plugin-whisker17-claude-codex-loop-claude-codex-loop
- tashan id: plugin:whisker17/claude-codex-loop/claude-codex-loop
- Source: https://github.com/Whisker17/claude-codex-loop
- Type: plugin
- Category: devtools
- tashan score: 25.0 / 100
- Adoption: 7.0
- Upkeep: 47.0
- Freshness: 63.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install claude-codex-loop@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
