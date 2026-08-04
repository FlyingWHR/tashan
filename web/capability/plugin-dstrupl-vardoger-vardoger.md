# Vardoger

> vardoger personalizes Claude Code by analyzing your own conversation history and turning recurring patterns into tailored rules. How it works: the plugin's analyze skill calls the vardoger CLI, which reads your local ~/.claude/projects/ session files in batches. Claude summarizes each batch for behavioral signals (tools you prefer, libraries you use, coding conventions you follow, mistakes you don't want repeated), then synthesizes the summaries into a single personalization that lands in

## Facts
- Page: https://tashan.sh/capability/plugin-dstrupl-vardoger-vardoger
- tashan id: plugin:dstrupl/vardoger/vardoger
- Source: https://github.com/dstrupl/vardoger
- Type: plugin
- Category: productivity
- tashan score: 42.0 / 100
- Adoption: 16.0
- Upkeep: 62.0
- Freshness: 94.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 4
- License: Apache-2.0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install vardoger@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
