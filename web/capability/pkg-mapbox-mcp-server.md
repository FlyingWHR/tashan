# Mapbox

> Geospatial intelligence with Mapbox APIs like geocoding, POI search, directions, isochrones, etc.

## Facts
- Page: https://tashan.sh/capability/pkg-mapbox-mcp-server
- tashan id: pkg:@mapbox/mcp-server
- Source: https://github.com/mapbox/mcp-server
- npm: https://www.npmjs.com/package/@mapbox/mcp-server
- Type: npm
- Category: data
- tashan score: 75.0 / 100
- Adoption: 45.0
- Upkeep: 99.0
- Freshness: 98.0
- Evidence coverage: 100% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- npm downloads: 1,663/week
- Official: no

## Install

```sh
claude mcp add mapbox-mcp-server -- npx -y @mapbox/mcp-server
```

## Security audit
- Known advisories: 0
- Install-time script: `patch-package || (cd ../../.. && node ./node_modules/patch-package/index.js --patch-dir ./node_modules/@mapbox/mcp-server/patches) || true`
- Build provenance: not attested

Permissions are read from DECLARED dependencies only. Nothing is executed, so an empty result means "nothing declared", never "nothing possible".

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
