# Anomaly Detection Time Series

> Formal time-series methods that augment the hand-coded fingerprint library in traffic-change-diagnosis. Use this skill when traffic-change-diagnosis fingerprints overlap, when the user asks "is this real?", or when the change date is contested. Applies STL decomposition, Bayesian online changepoint detection, Prophet, quantile regression, sequential probability ratio test, and Granger causality. Use whenever interpreting a series where day-of-week confounds an eyeballed drop, where two candidate causes share a week, or where an alert needs to fire before an analyst sees the chart. Pairs with analytics-diagnostic-method for the surrounding investigation and with sequential-monitoring for the SPRT details. Triggers when Clamp MCP traffictimeseries returns a series spanning more than 14 days, or when via Clamp the user shares a daily/hourly metric history that needs a non-eyeball verdict.

## Facts
- Page: https://tashan.sh/capability/skill-clamp-sh-anomaly-detection-time-series
- tashan id: skill:clamp-sh/anomaly-detection-time-series
- Source: https://github.com/clamp-sh/analytics-skills
- Type: skill
- Category: data
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
cp -r anomaly-detection-time-series ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
