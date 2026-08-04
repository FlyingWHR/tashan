# Databricks App Design

> Design the UX of custom-code Databricks Apps (AppKit/React) data screens — KPI/overview pages, reports, charts, tables, and Genie/chat data assistants — mapped to concrete AppKit components. Use when BUILDING or reviewing the UI of an AppKit/React app that displays data or answers data questions: choosing genre, layout, charts, KPIs, semantic color, required states (loading/empty/error), IBCS notation, and AI-result trust (showing generated SQL/sources for Genie/chat). A plain "create a dashboard" request means a managed AI/BI (Lakeview) dashboard → use databricks-aibi-dashboards, NOT this skill. Also NOT for non-data frontend (forms, settings, auth, marketing) or scaffolding/build/deploy (→ databricks-apps). Complements databricks-apps; use it alongside whenever a custom app has a chart, table, KPI, report, or Genie/chat/AI surface.

## Facts
- Page: https://tashan.sh/capability/skill-databricks-databricks-app-design
- tashan id: skill:databricks/databricks-app-design
- Source: https://github.com/databricks/databricks-agent-skills
- Type: skill
- Category: design
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
cp -r databricks-app-design ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
