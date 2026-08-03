# NPM Postinstall Attack Scanner

> Detect npm supply chain attacks that use the postinstall + hidden dependency pattern to deliver malware. Built in response to the axios maintainer account takeover (2026-03-31). Scans lockfiles, odemodules, postinstall scripts, version ranges, and npm cache across 5 phases. Returns actionable remediation steps when issues are found.

## Facts
- Page: https://tashan.sh/capability/plugin-aliksir-npm-postinstall-attack-scanner-npm-postinstall-attack-scanner
- tashan id: plugin:aliksir/npm-postinstall-attack-scanner/npm-postinstall-attack-scanner
- Source: https://github.com/aliksir/npm-postinstall-attack-scanner
- Type: plugin
- Category: security
- tashan score: 33.0 / 100
- Adoption: 11.0
- Upkeep: 56.0
- Freshness: 81.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install npm-postinstall-attack-scanner@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
