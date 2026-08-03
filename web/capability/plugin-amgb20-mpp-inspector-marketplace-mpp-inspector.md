# Mpp Inspector

> Inspect, debug, and test Machine Payments Protocol (HTTP 402) endpoints directly from Claude Code. Parses spec-compliant WWW-Authenticate challenges, discovers MPP endpoints on any domain, compares pricing across services, validates receipts, and dry-runs payment flows. Supports Tempo, Stripe, Lightning, Solana, and Card payment methods. Includes 4 slash commands (/mpp-inspect, /mpp-scan, /mpp-flow, /mpp-protocol) and 5 MCP tools for programmatic access.

## Facts
- Page: https://tashan.sh/capability/plugin-amgb20-mpp-inspector-marketplace-mpp-inspector
- tashan id: plugin:amgb20/mpp-inspector-marketplace/mpp-inspector
- Source: https://github.com/amgb20/mpp-inspector-marketplace
- Type: plugin
- Category: security
- tashan score: 32.0 / 100
- Adoption: 13.0
- Upkeep: 65.0
- Freshness: 63.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 2
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install mpp-inspector@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
