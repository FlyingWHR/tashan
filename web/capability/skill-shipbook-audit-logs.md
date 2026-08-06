# Audit Logs

> Audit log statements in the codebase for PII exposure and sensitive data leaks. Scans all logging calls and reports issues. Does not make changes — only reports findings and asks the user before fixing anything.

## Facts
- Page: https://tashan.sh/capability/skill-shipbook-audit-logs
- tashan id: skill:shipbook/audit-logs
- Source: https://github.com/shipbook/shipbook-mcp
- Type: skill
- Category: security
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
cp -r audit-logs ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
