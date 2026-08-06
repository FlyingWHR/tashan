# Arn Code Plan

> - This skill should be used when the user says "arness code plan", "arn-code-plan", "plan this", "write a plan", "create plan", "implementation plan", "plan feature", "plan the spec", "plan from spec", "generate plan", "arness code plan FEATUREX", "plan the bugfix", "plan bugfix", "make a plan", or wants to generate an implementation plan from a Arness specification. The skill invokes the arn-code-feature-planner agent to generate the plan, presents it for review, and iterates on user feedback until approved. Produces a PLANPREVIEW file that feeds into /arn-code-save-plan.

## Facts
- Page: https://tashan.sh/capability/skill-appsvortex-arn-code-plan
- tashan id: skill:AppsVortex/arn-code-plan
- Source: https://github.com/AppsVortex/arness
- Type: skill
- Category: productivity
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
cp -r arn-code-plan ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
