# Trinity

> Trinity is a three-agent harness for Claude Code that turns a one-to-four-sentence requirement into a reviewed pull request. /trinity:run spawns Planner (opus) → Generator (sonnet) → Evaluator (sonnet) inside an isolated git worktree, iterating until the Evaluator returns PASS or the iteration cap is hit, then pushes the branch and opens a PR. The split forces an independent reviewer that only reads files and the diff, eliminating the "graded its own homework" failure mode of single-agent loops.

## Facts
- Page: https://tashan.sh/capability/plugin-yjn279-trinity-trinity
- tashan id: plugin:yjn279/trinity/trinity
- Source: https://github.com/yjn279/trinity
- Type: plugin
- Category: security
- tashan score: 40.0 / 100
- Adoption: 7.0
- Upkeep: 81.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install trinity@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
