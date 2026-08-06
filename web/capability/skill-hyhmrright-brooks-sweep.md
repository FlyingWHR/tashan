# Brooks Sweep

> Full-sweep mode: runs a unified analysis across all quality dimensions — code decay, architecture, tech debt, and test quality — then applies fixes directly to the codebase. Safe changes are auto-applied; risky changes are confirmed before execution. Drawing on twelve classic engineering books. Triggers when: user wants to "fix everything", "sweep the codebase", "auto-fix all issues", "clean up the whole project", or asks for a single command that both diagnoses and remediates quality problems. Do NOT trigger for: read-only audits or health reports where the user only wants findings without code changes; single-dimension reviews (use the focused skill instead: brooks-review / brooks-audit / brooks-debt / brooks-test); server health checks, HTTP /health endpoints, Kubernetes probes, database health, or application uptime.

## Facts
- Page: https://tashan.sh/capability/skill-hyhmrright-brooks-sweep
- tashan id: skill:hyhmrright/brooks-sweep
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
cp -r brooks-sweep ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
