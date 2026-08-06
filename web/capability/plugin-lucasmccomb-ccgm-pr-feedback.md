# Pr Feedback

> Structured resolver for PR review comments. /resolve-pr-feedback fetches unresolved review threads via GraphQL, triages new vs already-handled, and if 3+ new items arrive (or a cross-invocation signal fires) runs cluster analysis - categorizes each into 11 fixed concern categories and groups by category + spatial proximity. Clusters surface systemic issues instead of dispatching 10 one-off fixes. Parallel pr-comment-resolver subagents apply unambiguous fixes, post inline replies via gh api, and

## Facts
- Page: https://tashan.sh/capability/plugin-lucasmccomb-ccgm-pr-feedback
- tashan id: plugin:lucasmccomb/ccgm/pr-feedback
- Source: https://github.com/lucasmccomb/ccgm
- Type: plugin
- Category: productivity
- tashan score: 37.0 / 100
- Adoption: 7.0
- Upkeep: 64.0
- Freshness: 100.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add lucasmccomb/ccgm
/plugin install pr-feedback@ccgm
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
