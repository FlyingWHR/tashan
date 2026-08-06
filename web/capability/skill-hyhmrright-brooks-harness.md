# Brooks Harness

> Maintenance orchestrator for the brooks-lint plugin itself. Runs a sequential subagent pipeline — author → eval → QA → trigger-audit → release — to add or edit a skill, refresh the eval suite, keep the four manifests + all README translations + CHANGELOG + AGENTS/GEMINI in sync, audit trigger boundaries, and cut releases. Drives the five agents in .claude/agents/ (skill-author, eval-curator, consistency-qa, trigger-boundary-auditor, release-manager). Triggers when the maintainer asks to work ON brooks-lint itself: "add a new skill", "edit the brooks-debt guide", "update the eval suite", "fix the trigger descriptions", "make this change and validate it", "release brooks-lint", "bump and publish", and follow-ups: "re-run", "re-validate", "update that skill", "redo the audit", "do the X part again". Do NOT trigger for: USING the brooks-lint analysis skills on some target codebase (that's brooks-review / brooks-audit / brooks-debt / brooks-test / brooks-health / brooks-sweep); generic questions about brooks-lint that don't ask to change it; or maintenance of a different plugin.

## Facts
- Page: https://tashan.sh/capability/skill-hyhmrright-brooks-harness
- tashan id: skill:hyhmrright/brooks-harness
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
cp -r brooks-harness ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
