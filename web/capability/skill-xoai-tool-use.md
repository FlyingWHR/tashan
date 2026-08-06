# Tool Use

> Guides tool selection across three layers: local scripts (zero context cost), MCP proxy (minimal context), and subagent dispatch (isolated context). Ensures the agent uses the cheapest effective layer and never pollutes the main context window with raw tool output. Use when the agent needs external information, current documentation, database access, or multi-step research.

## Facts
- Page: https://tashan.sh/capability/skill-xoai-tool-use
- tashan id: skill:xoai/tool-use
- Source: https://github.com/xoai/sage
- Type: skill
- Category: search
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: 79.0
- Freshness: 94.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
cp -r tool-use ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
