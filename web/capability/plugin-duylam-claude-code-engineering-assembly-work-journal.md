# Work Journal

> Cross-session memory for long-running work: append-only diary (LOG) and decision (DEC) logs under .claude/memory, grouped by work item (JIRA-123, RFC-7, …), with derived open-item tracking so any later session can answer what is still pending, what changed on a ticket, and what was done since a date. Ships its own clock-in/clock-out protocol via a UserPromptSubmit hook.

## Facts
- Page: https://tashan.sh/capability/plugin-duylam-claude-code-engineering-assembly-work-journal
- tashan id: plugin:duylam/claude-code-engineering-assembly/work-journal
- Source: https://github.com/duylam/claude-code-engineering-assembly
- Type: plugin
- Category: productivity
- tashan score: 14.0 / 100
- Adoption: 7.0
- Upkeep: 33.0
- Freshness: not measured
- Evidence coverage: 62% of the inputs this score can use
- Health: not measured
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add duylam/claude-code-engineering-assembly
/plugin install work-journal@engineering-assembly
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
