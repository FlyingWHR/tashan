# Billing Verification

> Test the full Credyt billing cycle end-to-end for a specific product. Creates a test customer, funds their wallet, sends a usage event, and verifies fees were charged correctly. Use this to re-verify a product after making changes in the dashboard, to test a specific product independently, or to troubleshoot billing issues. Note that /credyt:billing-setup runs verification automatically — use this skill when you want to verify without re-running full setup.

## Facts
- Page: https://tashan.sh/capability/skill-credyt-billing-verification
- tashan id: skill:credyt/billing-verification
- Source: https://github.com/credyt/ai-skills
- Type: skill
- Category: finance
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
cp -r billing-verification ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
