# Throwing

> A user-invoked command that flips Claude into a more disciplined mode when the user is about to lose patience. After /throwing:pigs, Claude acknowledges briefly, re-anchors on the goal, slows down (smaller turns, more verification, citations from current docs), avoids sycophantic phrasing, and uses a structured escalation if subsequent attempts also fail. Pure prompt-engineering — no hooks, no network calls, no file access.

## Facts
- Page: https://tashan.sh/capability/plugin-robertomarchioro-goldmarktplace-throwing
- tashan id: plugin:robertomarchioro/goldmarktplace/throwing
- Source: https://github.com/robertomarchioro/goldmarktplace
- Type: plugin
- Category: security
- tashan score: 31.0 / 100
- Adoption: 7.0
- Upkeep: 56.0
- Freshness: 81.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install throwing@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
