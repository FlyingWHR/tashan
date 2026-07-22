# Mastered

**The intelligence layer for AI capabilities.** *Measure what actually works.*

Not another directory — an instrument that measures **real adoption from public evidence**
(not stars, not listings, not opinions). V1 ranks **MCP servers** by how many people truly
run them, mined from public GitHub configs. Roadmap: retention/churn, controlled evals,
compatibility, cost.

## Structure
```
scraper/scrape.py   public-signal scraper (GitHub configs → measured adoption)
data/               capabilities.json (source of truth) + raw/ file cache
web/                the site (static, deployable) — reads /data/capabilities.json
  css/ js/ assets/  design system (Geist + Geist Mono self-hosted), leaderboard + detail
  index / methodology / about / capability
brand/BRAND.md      identity + design system (near-black + amber "terminal")
```

## Run the scraper
```sh
python3 scraper/scrape.py          # uses the `gh` CLI token for auth
```
Mines `mcp.json` / `claude_desktop_config.json` / `.cursor` configs from public GitHub,
extracts each declared MCP server, and aggregates **reach** (distinct owners), repos, host-repo
star distribution, freshness, and co-use → `data/capabilities.json`.
- Rate-limited: GitHub code-search = 10/min (the scraper sleeps); ~700-config sample per run.
- Resumable: fetched file contents cache in `data/raw/`.
- Honest: it's a **sample**, not a census. Adoption ≠ quality (see `web/methodology.html`).

## Build / deploy
The site reads `/data/capabilities.json`, so copy the dataset into the web root before deploy:
```sh
mkdir -p web/data && cp data/capabilities.json web/data/capabilities.json
```
Then deploy `web/` as a static site (Cloudflare Pages — same setup as stilltime.io):
```sh
npx wrangler@3 pages deploy web --project-name mastered
```
`_headers` ships a strict CSP + revalidating CSS/JS/data + hard-cached fonts. No build step,
no framework, no external requests.

## The moat (why this isn't scrapeable)
Directories list supply; **Mastered measures demand.** Owner-reach, retention, evals, and cost —
compounded per capability — become an evidence base no listing can copy. See `brand/BRAND.md`
and `../skills-marketplace-research/REPORT.md` for the thesis.
