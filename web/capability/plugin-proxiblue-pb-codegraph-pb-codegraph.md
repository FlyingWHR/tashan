# Pb Codegraph

> Cross-module impact analysis for Magento 2 / Mage-OS — detect blast radius of code changes before deploy. v0.2.0 ships a deterministic codegraph-backed engine (augmenter + MCP shim, graph-backed findsymbol/context/impact/query tools) alongside the original v0.1.0 LLM-driven impact check (grep, magento2-lsp MCP, config XML parsing), auto-selected per project by the presence of a .codegraph/codegraph.db index. pps cutover acceptance-tested; awaiting sign-off before default rollout.

## Facts
- Page: https://tashan.sh/capability/plugin-proxiblue-pb-codegraph-pb-codegraph
- tashan id: plugin:proxiblue/pb-codegraph/pb-codegraph
- Source: https://github.com/ProxiBlue/pb-codegraph
- Type: plugin
- Category: devtools
- tashan score: 45.0 / 100
- Adoption: 11.0
- Upkeep: not measured
- Freshness: 99.0
- Evidence coverage: 59% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: Apache-2.0
- Official: no

## Install

```sh
/plugin marketplace add ProxiBlue/pb-codegraph
/plugin install pb-codegraph@pb-codegraph
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
