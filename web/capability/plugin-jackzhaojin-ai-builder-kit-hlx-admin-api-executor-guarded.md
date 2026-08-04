# Hlx Admin API Executor Guarded

> Bundles the hlx-admin-api-executor skill with a PreToolUse hook that blocks any destructive curl command targeting admin.hlx.page before it executes. Claude must present a Change Justification (WHY/WHAT/HOW) and get explicit user approval before the command can run.

## Facts
- Page: https://tashan.sh/capability/plugin-jackzhaojin-ai-builder-kit-hlx-admin-api-executor-guarded
- tashan id: plugin:jackzhaojin/ai-builder-kit/hlx-admin-api-executor-guarded
- Source: https://github.com/jackzhaojin/ai-builder-kit
- Type: plugin
- Category: security
- tashan score: 38.0 / 100
- Adoption: 11.0
- Upkeep: 74.0
- Freshness: 82.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: Apache-2.0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install hlx-admin-api-executor-guarded@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
