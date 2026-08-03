# Audit Project

> Multi-agent iterative code review until zero issues remain. Spawns up to 10 specialist reviewers (code quality, security, performance, test coverage, architecture, database, API, frontend, backend, DevOps) chosen based on the project's signals. Each pass produces certainty-graded findings (HIGH / MEDIUM / LOW); HIGH findings auto-fix where safe. The orchestrator iterates passes until zero open issues remain or a max-iteration cap is reached. Specialists are role-based (defined inline via Task to

## Facts
- Page: https://tashan.sh/capability/plugin-agent-sh-audit-project-audit-project
- tashan id: plugin:agent-sh/audit-project/audit-project
- Source: https://github.com/agent-sh/audit-project
- Type: plugin
- Category: devtools
- tashan score: 46.0 / 100
- Adoption: 15.0
- Upkeep: 80.0
- Freshness: 96.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 3
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install audit-project@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
