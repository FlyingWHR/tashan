# Security Guidance · AlexBramall

> PreToolUse security reminder hook for Claude Code. Catches 12 common security anti-patterns in Edit/Write/MultiEdit operations BEFORE they happen — command injection (exec, os.system, subprocess shell=True), XSS (innerHTML, dangerouslySetInnerHTML, document.write), SQL injection (f-string queries, .format), unsafe deserialization (pickle, yaml.unsafeload), code injection (eval, new Function), and GitHub Actions workflow injection. Session-state caching prevents duplicate warnings; 30-day auto-c

## Facts
- Page: https://tashan.sh/capability/plugin-alexbramall-claude-code-skills-security-guidance
- tashan id: plugin:alexbramall/claude-code-skills/security-guidance
- Source: https://github.com/AlexBramall/claude-code-skills
- Type: plugin
- Category: devtools
- tashan score: 37.0 / 100
- Adoption: 7.0
- Upkeep: 89.0
- Freshness: 76.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add AlexBramall/claude-code-skills
/plugin install security-guidance@claude-code-skills
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
