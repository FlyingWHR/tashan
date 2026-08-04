# Flag Parser

> Parses workflow flags (--quality-locked, --autonomous, --subagents) from $ARGUMENTS at the start of /build and /architect commands. Uses a deterministic python3 runtime with a prose-rule fallback if python3 is unavailable. Returns a strict JSON contract that the agent trusts unconditionally.

## Facts
- Page: https://tashan.sh/capability/skill-xoai-flag-parser
- tashan id: skill:xoai/flag-parser
- Source: https://github.com/xoai/sage
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
cp -r flag-parser ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
