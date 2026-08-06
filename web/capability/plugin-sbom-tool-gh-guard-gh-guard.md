# Gh Guard

> GH-Guard hardens CI/CD pipelines for Rust projects. It generates production-tested GitHub Actions workflows with SHA-pinned actions, OIDC-based Trusted Publishing, SLSA L3 provenance, and layered dependency auditing via cargo-deny, Dependabot, and osv-scanner. Five commands: /audit scans your repo against supply chain best practices, /harden walks you through fixes at three levels (Minimal/Standard/Hardened), /generate creates individual config files, /check-updates catches stale SHA pins, and

## Facts
- Page: https://tashan.sh/capability/plugin-sbom-tool-gh-guard-gh-guard
- tashan id: plugin:sbom-tool/gh-guard/gh-guard
- Source: https://github.com/sbom-tool/gh-guard
- Type: plugin
- Category: security
- tashan score: 37.0 / 100
- Adoption: 23.0
- Upkeep: 64.0
- Freshness: 61.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 15
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install gh-guard@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
