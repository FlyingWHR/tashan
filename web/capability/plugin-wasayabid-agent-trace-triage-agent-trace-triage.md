# Agent Trace Triage

> Agent Trace Triage is a Claude Code plugin for developers building agentic AI systems (LangGraph, CrewAI, custom tool loops, MCP agents). When an agent run fails, stuck in a loop, wrong tool, or burning tokens. the user runs /agent-trace-triage with a JSON/JSONL trace file. The plugin: • Parses traces (JSONL, OpenAI toolcalls, partial LangSmith/OTEL-style exports) • Detects loops deterministically (identical repeat, ping-pong, retry-without-progress) via bundled Node scripts • Classifies fail

## Facts
- Page: https://tashan.sh/capability/plugin-wasayabid-agent-trace-triage-agent-trace-triage
- tashan id: plugin:wasayabid/agent-trace-triage/agent-trace-triage
- Source: https://github.com/WasayAbid/agent-trace-triage
- Type: plugin
- Category: devtools
- tashan score: 34.0 / 100
- Adoption: 7.0
- Upkeep: 60.0
- Freshness: 90.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install agent-trace-triage@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
