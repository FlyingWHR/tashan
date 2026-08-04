# Idle Timing

> - Injects timing block to prompts (not user-visible) covering local date-time, idle time (since agent turn ended), and prior turn execution time. - Shows [after Xm Ys] to user via post submit hook to indicate how long it was between that prompt and agent finishing prior turn. - Provides statusline integration for idle time.

## Facts
- Page: https://tashan.sh/capability/plugin-clankercode-claude-inject-idle-time-idle-timing
- tashan id: plugin:clankercode/claude-inject-idle-time/idle-timing
- Source: https://github.com/clankercode/claude-inject-idle-time
- Type: plugin
- Category: productivity
- tashan score: 42.0 / 100
- Adoption: 16.0
- Upkeep: 74.0
- Freshness: 82.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 4
- License: NOASSERTION
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install idle-timing@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
