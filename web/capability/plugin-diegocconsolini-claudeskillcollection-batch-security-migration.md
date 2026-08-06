# Batch Security Migration

> Recipe skill that turns Claude Code's built-in /batch into a security-migration tool: 7 copy-paste batch recipes (XSS innerHTML→textContent, HTTP→HTTPS, SQLi parameterization, input validation, log PII redaction, secret rotation, dependency CVE patches), each with a safety tier and false-positive trap, plus scandiff.py — a before/after plugin-security-checker gate that fails on any new HIGH/CRITICAL finding.

## Facts
- Page: https://tashan.sh/capability/plugin-diegocconsolini-claudeskillcollection-batch-security-migration
- tashan id: plugin:diegocconsolini/claudeskillcollection/batch-security-migration
- Source: https://github.com/diegocconsolini/ClaudeSkillCollection
- Type: plugin
- Category: security
- tashan score: 33.0 / 100
- Adoption: 7.0
- Upkeep: 59.0
- Freshness: 88.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add diegocconsolini/ClaudeSkillCollection
/plugin install batch-security-migration@security-compliance-marketplace
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
