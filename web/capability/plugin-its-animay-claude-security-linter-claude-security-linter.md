# Claude Security Linter

> A pre-tool-use hook plugin that automatically scans code for security vulnerabilities before Claude writes it to disk. Detects eval() usage, Function constructor abuse, hardcoded API keys and secrets, Bearer tokens, AWS credentials, innerHTML/outerHTML XSS vectors, inline private keys, and GitHub personal access tokens. Uses a two-tier severity system: errors block the write with detailed remediation guidance, while warnings allow the write but inject advisory context. Runs as pure Node.js wi...

## Facts
- Page: https://tashan.sh/capability/plugin-its-animay-claude-security-linter-claude-security-linter
- tashan id: plugin:its-animay/claude-security-linter/claude-security-linter
- Source: https://github.com/its-animay/claude-security-linter
- Type: plugin
- Category: security
- tashan score: 24.0 / 100
- Adoption: 13.0
- Upkeep: 43.0
- Freshness: 53.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 2
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install claude-security-linter@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
