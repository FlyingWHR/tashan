# Agent Email Inbox

> Use when building any system where email content triggers actions — AI agent inboxes, automated support handlers, email-to-task pipelines, or any workflow processing untrusted inbound email. Always use this skill when the user wants to receive emails and act on them programmatically, even if they don't mention "agent" — the skill contains critical security patterns (sender allowlists, content filtering, sandboxed processing) that prevent untrusted email from controlling your system.

## Facts
- Page: https://tashan.sh/capability/skill-resend-agent-email-inbox
- tashan id: skill:resend/agent-email-inbox
- Source: https://github.com/resend/resend-skills
- Type: skill
- Category: productivity
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: 98.0
- Freshness: 96.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
cp -r agent-email-inbox ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
