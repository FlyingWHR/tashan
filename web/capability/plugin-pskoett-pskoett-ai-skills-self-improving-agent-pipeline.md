# Self Improving Agent Pipeline

> A pipeline of skills that implements two feedback loops for Claude Code. The inner loop (plan-interview, intent-framed-agent, context-surfing, verify-gate, simplify-and-harden) catches failures during a session — verifying against tests, detecting scope and context drift, and reviewing code before signaling done. The outer loop (learning-aggregator, harness-updater, eval-creator, pre-flight-check) captures learnings, promotes recurring patterns into CLAUDE.md as permanent rules, and turns failur

## Facts
- Page: https://tashan.sh/capability/plugin-pskoett-pskoett-ai-skills-self-improving-agent-pipeline
- tashan id: plugin:pskoett/pskoett-ai-skills/self-improving-agent-pipeline
- Source: https://github.com/pskoett/pskoett-ai-skills
- Type: plugin
- Category: devtools
- tashan score: 42.0 / 100
- Adoption: 7.0
- Upkeep: 100.0
- Freshness: not measured
- Evidence coverage: 62% of the inputs this score can use
- Health: not measured
- Instruction depth: not yet graded
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install self-improving-agent-pipeline@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
