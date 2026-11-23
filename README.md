# Tashan

Tashan publishes evidence about MCP servers and agent skills. Search the index, check a package before installing, or compare observed x402 payments on Base. The measurements carry their dates and sources.

```sh
curl 'https://tashan.sh/v0.1/lookup?name=tavily-mcp'
curl 'https://tashan.sh/v0.1/search?q=database&limit=3'
```

The [OpenAPI contract](https://tashan.sh/openapi.json) describes free queries and paid operations. Request the current HTTP 402 quote before authorizing payment. HTTP clients need no npm package. `npx tashan-cli` inspects a local stack, and `npx -y tashan-cli mcp` connects it to a stdio MCP host. The CLI ships under [MIT](cli/LICENSE). Published measurements carry [CC BY 4.0](https://tashan.sh/terms).

## Agent access

| Job | Entry point |
|---|---|
| Look up a package or search by name | `GET /v0.1/lookup`, `GET /v0.1/search` |
| Audit a stack or request a task shortlist | `POST /v0.1/audit`, `POST /v0.1/kit` |
| Discover the API and payment terms | `/llms.txt`, `/openapi.json`, `/.well-known/x402` |
| Inspect a local setup | `npx -y tashan-cli doctor` |
| Connect an MCP client | `npx -y tashan-cli mcp` |

Risk findings and shortlists are free. An assembled kit includes exact npm pins with current advisory scans. If the requested selection has no qualifying executable, the service explains why before requesting payment. Each capability links to its source. Compare adoption, maintenance and advisory evidence in the [methodology](https://tashan.sh/methodology).

## Run and maintain

```sh
python3 pipeline/serve.py 4173     # preview the committed site
bash tests/run.sh                 # verify the site, API, client and data contracts
python3 pipeline/run.py --list     # inspect the nightly stages
```

The [daily workflow](.github/workflows/daily.yml) restores SQLite and document caches from Cloudflare R2, ingests sources, exports web data and persists daily measurements in `data/history/`. The website reads static exports. Pages Functions serve HTTP queries and use Cloudflare KV for licensed detail.

GitHub Actions runs verification before deployment and checks the public lookup against the exact snapshot. An open publication incident links to the affected runs. Each run also records payment checks and a seven-day conversion funnel. The `/paid` page separately reports transfers to tracked service addresses on Base.

The [service audit](docs/SERVICE-AUDIT.md) records page coverage, operating dependencies and release checks. The [ETHOnline entry](docs/HACKATHON.md) preserves the September submission and measurements.
