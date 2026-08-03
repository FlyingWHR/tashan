# Reflect · chanjoongx

> Session-local metacognition harness for long-running Claude Code work. When suggestions get reverted 3+ times within 10 tool calls, reflect invokes Opus 4.7 to reason about why the rejections clustered. The model reads back the last 20 tool calls, the rolled-back diff, and active rules, then writes structured guidance — pattern, signal, adjustment, confidence — to .reflect/session-guidance.md. The next turn auto-loads it via path-scoped rule injection and adjusts. Key features: • 3-tier weight

## Facts
- Page: https://tashan.sh/capability/plugin-chanjoongx-reflect-reflect
- tashan id: plugin:chanjoongx/reflect/reflect
- Source: https://github.com/chanjoongx/reflect
- Type: plugin
- Category: productivity
- tashan score: 27.0 / 100
- Adoption: 7.0
- Upkeep: 50.0
- Freshness: 70.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install reflect@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
