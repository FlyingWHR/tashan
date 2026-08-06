# Architectural Review

> Use to verify the decimalscaled repo still matches its architecture as defined — a read-only audit against the CLAUDE.md ARCHITECTURE CONSTITUTION (rules 1–6) and docs/ARCHITECTURE.md. Run it periodically, after any structural/perf change, or before a release. Covers the defect taxonomy (const-work-width / build-max leaks / per-tier pollution / layering / dead code / policy hygiene), the read-only protocol, what is legitimately NOT a violation, and a copy-paste launch skeleton for the auditor agent.

## Facts
- Page: https://tashan.sh/capability/skill-mootable-architectural-review
- tashan id: skill:mootable/architectural-review
- Source: https://github.com/mootable/decimal-scaled
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
cp -r architectural-review ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
