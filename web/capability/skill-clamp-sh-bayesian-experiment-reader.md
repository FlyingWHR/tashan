# Bayesian Experiment Reader

> Bayesian counterpart to experiment-result-reader. Computes posterior P(variant beats control), credible intervals, and expected loss from per-variant exposure and conversion data. Beta-Binomial for proportion metrics (CVR), Normal-Normal for continuous metrics (revenue per user). Decision rule combines a confidence threshold with an expected-loss tolerance, so the ship decision reflects both "how likely is this better?" and "how bad is it if I'm wrong?". Use this skill alongside experiment-result-reader when reading any A/B test result. Pairs with analytics-diagnostic-method. Use whenever interpreting an A/B test result the user plans to ship from, when the question is "what's the chance variant wins?", or when a frequentist p-value is on the edge and the user wants the posterior view. Triggers when Clamp MCP returns experiment exposure and conversion data, or when any analytics source surfaces per-variant counts.

## Facts
- Page: https://tashan.sh/capability/skill-clamp-sh-bayesian-experiment-reader
- tashan id: skill:clamp-sh/bayesian-experiment-reader
- Source: https://github.com/clamp-sh/analytics-skills
- Type: skill
- Category: devtools
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
cp -r bayesian-experiment-reader ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
