# Agent Email Inbox

> Use when building any system where email content triggers actions — AI agent inboxes, automated support handlers, email-to-task pipelines, or any workflow processing untrusted inbound email. Always use this skill when the user wants to receive emails and act on them programmatically, even if they don't mention "agent" — the skill contains critical security patterns (sender allowlists, content filtering, sandboxed processing) that prevent untrusted email from controlling your system.

## Facts
- Page: https://tashan.sh/capability/skill-resend-agent-email-inbox
- tashan id: skill:resend/agent-email-inbox
- Source: https://github.com/resend/resend-skills
- Type: skill
- Category: other
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: not measured
- Freshness: not measured
- Evidence coverage: not measured
- Health: not measured
- Instruction depth: not yet graded
- Official: no

## Install

```sh
cp -r agent-email-inbox ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
