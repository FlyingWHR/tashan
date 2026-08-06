# Brd Browser Debug

> Debug Bright Data Scraping Browser sessions using the Browser Sessions API. Use this skill when the user encounters a Bright Data browser session error, puppeteer stack trace, failed scraper run, or asks about session bandwidth, duration, captchas, or connection issues. Also use when a Bright Data scraper produces unexpected results such as empty data, 0 items found, missing products, or fewer results than expected — session data can reveal whether the issue is network/proxy-side (blocks, captchas, redirects, timeouts) or client-side (selectors, extraction logic). Triggers on phrases like 'why did my session fail', 'debug my bright data session', 'check my scraping browser sessions', 'how much bandwidth did my scraper use', 'got 0 results', 'found 0', 'scraper returned empty', 'scraper not working', 'script didn't work', or when a Bright Data error code or brd.superproxy.io stack trace appears in the conversation. Requires BRIGHTDATAAPIKEY environment variable.

## Facts
- Page: https://tashan.sh/capability/skill-brightdata-brd-browser-debug
- tashan id: skill:brightdata/brd-browser-debug
- Source: https://github.com/brightdata/skills
- Type: skill
- Category: browser
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
cp -r brd-browser-debug ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
