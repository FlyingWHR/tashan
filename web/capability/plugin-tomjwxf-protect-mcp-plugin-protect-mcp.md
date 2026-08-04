# Protect · tomjwxf

> MCP security gateway that wraps any MCP server with per-tool policies, Ed25519-signed decision receipts, and human approval gates. Shadow mode (default) logs every tool call without blocking. Enforce mode applies per-tool allow/deny/rate-limit/approval policies. Every decision is cryptographically signed and independently verifiable offline. MIT licensed. IETF Internet-Draft published for the receipts protocol.

## Facts
- Page: https://tashan.sh/capability/plugin-tomjwxf-protect-mcp-plugin-protect-mcp
- tashan id: plugin:tomjwxf/protect-mcp-plugin/protect-mcp
- Source: https://github.com/tomjwxf/protect-mcp-plugin
- Type: plugin
- Category: security
- tashan score: 25.0 / 100
- Adoption: 7.0
- Upkeep: 48.0
- Freshness: 64.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install protect-mcp@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
