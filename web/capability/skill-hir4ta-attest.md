# Attest · hir4ta

> Render a detailed reliability view of a mumei feature — pass^3 over the most recent 10 trials plus a table of the last 10 trial rows from reliability-log.jsonl. Triggered only by explicit user invocation /mumei:attest <feature. Reads .mumei/specs/<feature/reliability-log.jsonl or .mumei/plans/<feature/reliability-log.jsonl via hooks/lib/reliability.sh. Exits non-zero with feature not found: <feature to stderr when the feature directory is absent. The k=3 / window=10 parameters are fixed.

## Facts
- Page: https://tashan.sh/capability/skill-hir4ta-attest
- tashan id: skill:hir4ta/attest
- Source: https://github.com/hir4ta/mumei
- Type: skill
- Category: data
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
cp -r attest ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
