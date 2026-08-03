# Checkup

> The single user-facing maintenance entrypoint for an existing Claude setup. Health-checks your configuration, decides whether it is fine as-is, needs an upgrade, or needs a rebuild, and takes that action — handing off to /upgrade-setup or /onboarding --rebuild as needed. Use when you want your setup checked and fixed, not just a findings report.

## Facts
- Page: https://tashan.sh/capability/skill-a2ngerer-checkup
- tashan id: skill:a2ngerer/checkup
- Source: https://github.com/a2ngerer/claude_onboarding_agent
- Type: skill
- Category: other
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
cp -r checkup ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
