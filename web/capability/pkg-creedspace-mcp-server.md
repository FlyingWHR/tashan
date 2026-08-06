# Creedspace

> Constitutional-AI safety guardrails for any LLM — personas, constitutions, adjudication.

## Facts
- Page: https://tashan.sh/capability/pkg-creedspace-mcp-server
- tashan id: pkg:@creedspace/mcp-server
- Source: https://github.com/Creed-Space/creedspace-mcp-server
- npm: https://www.npmjs.com/package/@creedspace/mcp-server
- Type: npm
- Category: security
- tashan score: 58.0 / 100
- Adoption: 33.0
- Upkeep: 66.0
- Freshness: 96.0
- Evidence coverage: 100% of the inputs this score can use
- Health: active
- Instruction depth: solid
- npm downloads: 233/week
- License: MIT
- Official: no

## Install

```sh
claude mcp add creedspace-mcp-server -- npx -y @creedspace/mcp-server
```

## Security audit
- Known advisories: 0
- Install-time script: `node -e "try{const f='./dist/postinstall.js';require('fs').existsSync(f)&&require(f)}catch{}"`
- Build provenance: not attested
- Declared permission surface: credentials

Permissions are read from DECLARED dependencies only. Nothing is executed, so an empty result means "nothing declared", never "nothing possible".

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
