# Aria Probe

> Run a 4-step validation probe for the aria-cowork spec. Tests whether this Cowork plugin can verify cwd, write to the user-attached knowledge folder, read a file pre-placed by aria-knowledge in Code, and capture or fall back gracefully on the transcript surface. Outputs structured results both to the conversation and to a probe-results file. Use when validating the aria-cowork spec before Phase 1 build. Triggers: "/aria-probe", "run aria probe", "validate aria-cowork", "test cowork filesystem".

## Facts
- Page: https://tashan.sh/capability/skill-mikeprasad-aria-probe
- tashan id: skill:mikeprasad/aria-probe
- Source: https://github.com/mikeprasad/aria-knowledge
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
cp -r aria-probe ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
