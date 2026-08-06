# Arm Evals

> Arm a forge eval suite into a frozen build contract. Run when .forge/state.json shows phase=evals, after /plugin-forge:build-evals; re-run after any suite edit or triage grader-error to re-version and re-freeze. Four gates in order via forge-eval: reference (every task's reference solution passes its own graders), red (no-plugin baseline; tasks that pass bare carry no signal), metaeval (judge vs human agreement = 0.85 against evals/labels/labels.jsonl), then sha256 FREEZE into .forge/freeze.json with suiteversion vN and phase - armed. Refuses to freeze uncalibrated judges, unresolved no-signal tasks, or a suite with pending change requests.

## Facts
- Page: https://tashan.sh/capability/skill-aznatkoiny-arm-evals
- tashan id: skill:Aznatkoiny/arm-evals
- Source: https://github.com/Aznatkoiny/claude-dev-toolkit
- Type: skill
- Category: comms
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
cp -r arm-evals ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
