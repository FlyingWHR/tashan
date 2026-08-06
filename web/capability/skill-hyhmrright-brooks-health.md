# Brooks Health

> Combined codebase health dashboard that scores a project across all four quality dimensions — PR quality, architecture, tech debt, and test quality — in a single pass, drawing on twelve classic engineering books. Triggers when: user wants an overall quality assessment, asks "how healthy is this codebase?", "run all the checks", "I need a health score before the release", or wants to onboard a new team with a quality overview. Do NOT trigger for: server health checks, HTTP health endpoints, Kubernetes liveness/readiness probes, database health, or application uptime. Also do not trigger when the user specifically requests only one dimension — use the corresponding focused skill instead (brooks-review / brooks-audit / brooks-debt / brooks-test).

## Facts
- Page: https://tashan.sh/capability/skill-hyhmrright-brooks-health
- tashan id: skill:hyhmrright/brooks-health
- Source: https://github.com/hyhmrright/brooks-lint
- Type: skill
- Category: devtools
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
cp -r brooks-health ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
