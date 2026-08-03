# Lucid Apple

> On-device Apple Intelligence as MCP tools for macOS — OCR, tables, entity detection, generation.

## Facts
- Page: https://tashan.sh/capability/pkg-lucid-apple-mcp
- tashan id: pkg:lucid-apple-mcp
- Source: https://github.com/Lucid-Systems-LLC/Lucid-Apple-MCP
- npm: https://www.npmjs.com/package/lucid-apple-mcp
- Type: npm
- Category: design
- tashan score: 42.0 / 100
- Adoption: 23.0
- Upkeep: 48.0
- Freshness: 85.0
- Evidence coverage: 100% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- npm downloads: 42/week
- Official: no

## Install

```sh
claude mcp add lucid-apple -- npx -y lucid-apple-mcp
```

## Security audit
- Known advisories: 0
- Install-time script: `node -e "const{spawnSync}=require('node:child_process');if(process.platform!=='darwin'){console.warn('[lucid-apple-mcp] non-macOS host - skipping Swift helper build (this server is macOS only).');process.exit(0)}const r=spawnSync('swiftc',['-parse-as-library','helper.swift','-o','helper'],{stdio:'in`
- Build provenance: not attested

Permissions are read from DECLARED dependencies only. Nothing is executed, so an empty result means "nothing declared", never "nothing possible".

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
