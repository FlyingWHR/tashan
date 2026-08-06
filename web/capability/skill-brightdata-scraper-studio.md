# Scraper Studio

> Build and run AI-generated Bright Data scrapers from the terminal via bdata scraper create and bdata scraper run. Use this skill whenever the user wants to generate a scraper from a natural-language description, build a custom scraper without writing code, turn a URL + plain-English description into a reusable scraper, run an existing Bright Data collector against a URL, or batch-scrape a list of URLs through one collector. Triggers on phrases like 'build me a scraper for', 'create a scraper that extracts', 'generate a scraper from a description', 'turn this URL into a scraper', 'run this scraper on', 'run my collector', 'batch scrape', 'scrape these URLs', 'scrape a list of URLs', 'competitive pricing table', 'scraper studio', scraper create, scraper run, --urls, --input-file, collectorid, automatetemplate, or /dca/. Covers the AI flow (template create → trigger AI generation → poll progress), the single-URL run flow (async + poll by default, --sync for fast pages), the multi-URL batch flow (--urls / --input-file → one /dca/trigger call with array body), and the silent auto-fallback to the batch endpoint when a URL expands past the realtime page limit. Requires the Bright Data CLI.

## Facts
- Page: https://tashan.sh/capability/skill-brightdata-scraper-studio
- tashan id: skill:brightdata/scraper-studio
- Source: https://github.com/brightdata/skills
- Type: skill
- Category: search
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: 93.0
- Freshness: 86.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
cp -r scraper-studio ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
