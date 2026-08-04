# Signet

> Ed25519-signs every tool call and appends to a hash-chained, tamper-evident audit log. Zero config — signing starts immediately after install. No native dependencies (embedded WASM). Audit logs at ~/.signet/audit/ with optional CLI verification via signet audit --verify.

## Facts
- Page: https://tashan.sh/capability/plugin-prismer-ai-signet-signet
- tashan id: plugin:prismer-ai/signet/signet
- Source: https://github.com/Prismer-AI/signet
- Type: plugin
- Category: security
- tashan score: 42.0 / 100
- Adoption: 28.0
- Upkeep: 54.0
- Freshness: 78.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 38
- License: Apache-2.0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install signet@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
