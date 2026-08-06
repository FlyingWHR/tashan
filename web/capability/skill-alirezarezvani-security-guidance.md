# Security Guidance · alirezarezvani

> PreToolUse security-anti-pattern hook for Claude Code. Catches 12 common security risks (command injection, XSS, SQL injection, unsafe deserialization, GitHub Actions workflow injection, eval/new Function code injection) BEFORE the Edit/Write/MultiEdit operation completes. Session-state caching prevents duplicate warnings on the same file+rule combo. Stdlib only — no dependencies. Use when you want a safety net during Claude Code sessions that touch security-sensitive code (auth, payments, user input handling, IaC). Disable with ENABLESECURITYREMINDER=0 if you need to perform a verified-safe operation that would otherwise trip a pattern. Triggers — "add security hook", "block unsafe code", "detect command injection before write", "prevent SQL injection patterns", "security warning hook".

## Facts
- Page: https://tashan.sh/capability/skill-alirezarezvani-security-guidance
- tashan id: skill:alirezarezvani/security-guidance
- Source: https://github.com/alirezarezvani/claude-skills
- Type: skill
- Category: security
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: 97.0
- Freshness: 93.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
cp -r security-guidance ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
