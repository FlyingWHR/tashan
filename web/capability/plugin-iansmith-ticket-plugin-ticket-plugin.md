# Ticket Plugin

> A Claude Code plugin that keeps a durable per-ticket plan, findings, and progress log for every ticket you work on — without bloating the ticket itself or polluting the repo. Auto-detects Linear or JIRA as your ticket system at run-time. The four slash commands form a complete loop around a ticket: - /ticket-plugin:start <KEY fetches the ticket, transitions it to "In Progress", and seeds taskplan.md, findings.md, and progress.md. Resuming an existing ticket reads back the tracking files and

## Facts
- Page: https://tashan.sh/capability/plugin-iansmith-ticket-plugin-ticket-plugin
- tashan id: plugin:iansmith/ticket-plugin/ticket-plugin
- Source: https://github.com/iansmith/ticket-plugin
- Type: plugin
- Category: productivity
- tashan score: 40.0 / 100
- Adoption: 7.0
- Upkeep: 81.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: NOASSERTION
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install ticket-plugin@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
