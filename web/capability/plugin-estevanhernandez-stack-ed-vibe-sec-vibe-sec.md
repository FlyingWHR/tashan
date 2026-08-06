# Vibe Sec

> Security gap finder for vibe-coded apps — the tier-aware security audit and orchestration layer. Defers to gitleaks/OSV-Scanner/Semgrep/Trivy when present, falls back to an in-house baseline when absent, and owns the tier classification (mapped to OWASP ASVS), severity calibration, four-band report, confidence-routed fixes with destructive-action overrides, and threat-model synthesis. /vibe-sec:audit runs the full twelve-concern audit (secrets, deps, supply-chain, config, crypto/PII, auth-model,

## Facts
- Page: https://tashan.sh/capability/plugin-estevanhernandez-stack-ed-vibe-sec-vibe-sec
- tashan id: plugin:estevanhernandez-stack-ed/vibe-sec/vibe-sec
- Source: https://github.com/estevanhernandez-stack-ed/vibe-sec
- Type: plugin
- Category: security
- tashan score: 38.0 / 100
- Adoption: 7.0
- Upkeep: 78.0
- Freshness: 91.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- Official: no

## Install

```sh
/plugin marketplace add estevanhernandez-stack-ed/vibe-plugins
/plugin install vibe-sec@vibe-plugins
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
