# Skill Security Auditor

> Security audit and vulnerability scanner for AI agent skills before installation. Use when: (1) evaluating a skill from an untrusted source, (2) auditing a skill directory or git repo URL for malicious code, (3) pre-install security gate for Claude Code plugins, OpenClaw skills, or Codex skills, (4) scanning Python scripts for dangerous patterns like os.system, eval, subprocess, network exfiltration, (5) detecting prompt injection in SKILL.md files, (6) checking dependency supply chain risks, (7) verifying file system access stays within skill boundaries. Triggers: "audit this skill", "is this skill safe", "scan skill for security", "check skill before install", "skill security check", "skill vulnerability scan".

## Facts
- Page: https://tashan.sh/capability/skill-alirezarezvani-skill-security-auditor
- tashan id: skill:alirezarezvani/skill-security-auditor
- Source: https://github.com/alirezarezvani/claude-skills
- Type: skill
- Category: security
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: 97.0
- Freshness: 94.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
cp -r skill-security-auditor ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
