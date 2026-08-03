# Deslop

> Detect and remove AI-generated slop with certainty-based findings and safe auto-fixes. AI coding tools leave behind debug console.logs, print statements, placeholder text ("TODO: implement"), empty catch blocks, over-commented code, and dead abstractions. /deslop runs a 3-phase detection pipeline (regex patterns → multi-pass analyzers → CLI tools) that categorizes every finding by certainty level: HIGH gets auto-fixed, MEDIUM is flagged for review, LOW is reported without action. Behavio

## Facts
- Page: https://tashan.sh/capability/plugin-agent-sh-deslop-deslop
- tashan id: plugin:agent-sh/deslop/deslop
- Source: https://github.com/agent-sh/deslop
- Type: plugin
- Category: productivity
- tashan score: 46.0 / 100
- Adoption: 15.0
- Upkeep: 80.0
- Freshness: 96.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 3
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install deslop@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
