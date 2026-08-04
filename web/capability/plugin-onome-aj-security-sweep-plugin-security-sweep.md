# Security Sweep

> Comprehensive security scanner for codebases. Scans for hardcoded secrets (30+ API key formats), injection flaws (SQLi, XSS, command injection, SSRF), authentication issues (JWT misuse, weak password hashing)misconfigurations (CORS, debug mode, insecure TLS, Docker/K8s), dependency risks, AI-specific vulnerabilities (prompt injection, API key exposure, excessive agent permissions), mobile security issues (Android/iOS), and data exposure (PII in logs, weak crypto). Covers OWASP Top 10 (2025), M

## Facts
- Page: https://tashan.sh/capability/plugin-onome-aj-security-sweep-plugin-security-sweep
- tashan id: plugin:onome-aj/security-sweep-plugin/security-sweep
- Source: https://github.com/Onome-AJ/security-sweep-plugin
- Type: plugin
- Category: security
- tashan score: 31.0 / 100
- Adoption: 18.0
- Upkeep: 48.0
- Freshness: 64.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 6
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install security-sweep@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
