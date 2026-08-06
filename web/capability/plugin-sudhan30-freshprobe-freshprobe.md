# Freshprobe

> Data freshness and endpoint liveness verification for AI agents. Probes external APIs and endpoints before agents act on their data, returning deterministic FRESH/STALE/UNKNOWN verdicts with confidence scores. Analyzes HTTP cache headers, measures latency percentiles (P50/P95/P99), fingerprints content for change detection, checks TLS certificate health, and evaluates against configurable freshness policies. Exposes three MCP tools (freshprobecheck, freshprobebatch, freshprobepolicy) and incl

## Facts
- Page: https://tashan.sh/capability/plugin-sudhan30-freshprobe-freshprobe
- tashan id: plugin:sudhan30/freshprobe/freshprobe
- Source: https://github.com/Sudhan30/freshprobe
- Type: plugin
- Category: security
- tashan score: 28.0 / 100
- Adoption: 13.0
- Upkeep: 47.0
- Freshness: 63.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 2
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install freshprobe@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
