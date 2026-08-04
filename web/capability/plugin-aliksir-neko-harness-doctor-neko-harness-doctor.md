# Neko Harness Doctor

> Diagnose your Claude Code harness (CLAUDE.md, settings.json, .mcp.json, hooks, skills, memory, MCP servers, and workflow) against 25 anti-pattern indicators. Outputs an S–E overall grade, per-category scores, violations with evidence citations, and prioritized Quick Wins. Includes an interactive fix flow: --fix-mode propose emits structured JSON proposals that Claude Code applies via the Edit tool with per-item user approval. Deterministic (no LLM — grep/AST/JSON only), zero runtime dependenci

## Facts
- Page: https://tashan.sh/capability/plugin-aliksir-neko-harness-doctor-neko-harness-doctor
- tashan id: plugin:aliksir/neko-harness-doctor/neko-harness-doctor
- Source: https://github.com/aliksir/neko-harness-doctor
- Type: plugin
- Category: security
- tashan score: 36.0 / 100
- Adoption: 11.0
- Upkeep: 59.0
- Freshness: 89.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install neko-harness-doctor@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
