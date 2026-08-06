# AI Agent Firewall

> Action firewall for AI agents: blocks the wrong action before it runs, every verdict Ed25519-signed.

## Facts
- Page: https://tashan.sh/capability/pkg-fidacy-mcp
- tashan id: pkg:@fidacy/mcp
- Source: https://github.com/fidacy/fidacy-open
- npm: https://www.npmjs.com/package/@fidacy/mcp
- Type: npm
- Category: security
- tashan score: 71.0 / 100
- Adoption: 47.0
- Upkeep: 73.0
- Freshness: 100.0
- Evidence coverage: 100% of the inputs this score can use
- Health: active
- Instruction depth: solid
- npm downloads: 2,170/week
- License: Apache-2.0
- Official: no

## Install

```sh
claude mcp add ai-agent-firewall -- npx -y @fidacy/mcp
```

## Security audit
- Known advisories: 0
- Install-time script: `node -e "try{require('fs').accessSync('dist/postinstall.js')}catch{process.exit(0)};import('./dist/postinstall.js')" || exit 0`
- Build provenance: not attested

Permissions are read from DECLARED dependencies only. Nothing is executed, so an empty result means "nothing declared", never "nothing possible".

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
