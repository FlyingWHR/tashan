# Cc Boost

> cc-boost is an open-source Claude Code plugin that reduces token consumption by filtering noisy tool output before it reaches the context window. It strips ANSI escape codes, collapses repetitive npm/pip progress bars into single summary lines, and folds consecutive nodemodules stack frames into compact summaries — typically achieving 60–90% character reduction on verbose command output. It also intercepts interactive scaffold commands (create-next-app, vite, sveltekit, remix, angular) that C

## Facts
- Page: https://tashan.sh/capability/plugin-sworddut-cc-boost-cc-boost
- tashan id: plugin:sworddut/cc-boost/cc-boost
- Source: https://github.com/sworddut/cc-boost
- Type: plugin
- Category: cloud
- tashan score: 24.0 / 100
- Adoption: 7.0
- Upkeep: 46.0
- Freshness: 60.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install cc-boost@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
