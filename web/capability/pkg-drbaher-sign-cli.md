# Sign CLI

> Agent-first e-signature MCP server with offline PAdES signing and hash-chained audit.

## Facts
- Page: https://tashan.sh/capability/pkg-drbaher-sign-cli
- tashan id: pkg:@drbaher/sign-cli
- Source: https://github.com/DrBaher/sign-cli
- npm: https://www.npmjs.com/package/@drbaher/sign-cli
- Type: npm
- Category: search
- tashan score: 52.0 / 100
- Adoption: 28.0
- Upkeep: 62.0
- Freshness: 93.0
- Evidence coverage: 100% of the inputs this score can use
- Health: active
- Instruction depth: deep
- npm downloads: 93/week
- Official: no

## Install

```sh
claude mcp add sign-cli -- npx -y @drbaher/sign-cli
```

## Security audit
- Known advisories: 0
- Install-time script: `node scripts/trim-pdfjs-dist.mjs || exit 0`
- Build provenance: attested
- Declared permission surface: database

Permissions are read from DECLARED dependencies only. Nothing is executed, so an empty result means "nothing declared", never "nothing possible".

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
