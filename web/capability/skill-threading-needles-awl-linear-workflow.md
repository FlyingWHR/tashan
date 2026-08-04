# Awl Linear Workflow

> Linear ticket state machine and workflow document conventions for Awl. Defines the Backlog → Research → Plan → In Dev → In Review → Done lifecycle, the "status update FIRST" rollback discipline, and the Research/Plan/Validation/Handoff/PR document naming patterns used to attach workflow artifacts to tickets. Use this skill whenever Claude sees a Linear ticket reference (PROJ-123, ENG-45, etc.), is about to call any mcplinear tool, transitions ticket status, creates or queries a workflow document attached to a ticket, or starts/finishes work that maps to a ticket. Make sure to apply this skill even when the user didn't invoke an Awl command — any mention of a Linear ticket is enough to trigger it.

## Facts
- Page: https://tashan.sh/capability/skill-threading-needles-awl-linear-workflow
- tashan id: skill:Threading-Needles/awl-linear-workflow
- Source: https://github.com/Threading-Needles/awl
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
cp -r awl-linear-workflow ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
