# Arn Code Report

> - This skill should be used when the user says "report issue", "arness code report", "code report", "something went wrong", "report a bug", "file arness code issue", "arness code broke", "report arness code problem", "diagnose issue", "arness doctor", "run doctor", "diagnose arness code", "arn-code-report", or wants to report a problem with an Arness Code workflow skill. Invokes the arn-code-doctor agent to diagnose the issue, then files a GitHub issue on the Arness plugin repository. Do NOT use this for filing issues on the user's own project — use /arn-code-create-issue for that. For Spark issues use /arn-spark-report. For Infra issues use /arn-infra-report.

## Facts
- Page: https://tashan.sh/capability/skill-appsvortex-arn-code-report
- tashan id: skill:AppsVortex/arn-code-report
- Source: https://github.com/AppsVortex/arness
- Type: skill
- Category: cloud
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
cp -r arn-code-report ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
