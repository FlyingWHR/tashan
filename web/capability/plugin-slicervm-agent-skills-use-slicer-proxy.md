# Use Slicer Proxy

> Filter, audit, and inject secrets into HTTP(S) egress from Slicer microVMs with Slicer Proxy — default-deny allow rules, credential injection, audit and passthrough modes, on Linux and macOS.

## Facts
- Page: https://tashan.sh/capability/plugin-slicervm-agent-skills-use-slicer-proxy
- tashan id: plugin:slicervm/agent-skills/use-slicer-proxy
- Source: https://github.com/slicervm/agent-skills
- Type: plugin
- Category: security
- tashan score: 42.0 / 100
- Adoption: 7.0
- Upkeep: 100.0
- Freshness: not measured
- Evidence coverage: 62% of the inputs this score can use
- Health: not measured
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add slicervm/agent-skills
/plugin install use-slicer-proxy@slicer
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
