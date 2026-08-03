# Slm Agent

> SLM Agent scans your codebase for AI API calls and generates a structured migration plan showing exactly where you can swap frontier LLM calls (Opus) for Small Language Models API calls like Haiku or Sonnet. It performs deep cross-file analysis: tracing prompts to their construction site, following callers across files, and classifying each call by what it actually does. Each finding includes a complexity score, confidence level, estimated savings, and for multi-task calls, a step-by-step decom

## Facts
- Page: https://tashan.sh/capability/plugin-scaledown-team-slm-agent-slm-agent
- tashan id: plugin:scaledown-team/slm_agent/slm-agent
- Source: https://github.com/scaledown-team/SLM_Agent
- Type: plugin
- Category: productivity
- tashan score: 57.0 / 100
- Adoption: 22.0
- Upkeep: 98.0
- Freshness: 95.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: solid
- GitHub stars: 14
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install slm-agent@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
