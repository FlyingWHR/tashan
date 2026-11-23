# Service audit · 23 November 2026

The September production snapshot contained 13,313 HTML files. A static inventory checked every file for a title, language, heading, main landmark, skip link, canonical destination and internal link or asset. The legacy query-based dossier shell uses `noindex` and selects its record client-side. Of 50,816 distinct internal destinations, none lacked a corresponding file or route family. Browser checks used 390 px and 1,280 px viewports. They exercised all 22 root pages, all nine guides and one record from each generated family, including the search interaction. A stubbed signed-out account was used for the local browser pass.

| Surface | Findings and changes |
|---|---|
| Index, browse, compare | Preserved the ridge canvas and ASCII fallback. Search, dated coverage, the ranked board and API access take precedence. Removed the ticker, bottom status line and six promotional cards. Search data loads on demand on supporting pages. |
| Capability dossiers (12,662), categories (113), tasks (64), roles (23), comparisons (420) | Shared navigation now exposes payments and the agent API. Kept scores, evidence, caveats, source links and available Markdown representations. Removed repeated generic sales bullets. |
| Paid, stats, changes, methodology, about | Stats use the export date. New payment reads record their own timestamp, retained with the last good read. Described the measured November score reversal. Replaced the about-page roadmap and promotional claims with methodology, coverage and corrections. |
| Agent API, CLI setup, config audit, requests, learn (9) | Published the HTTP lookup example and contract. Corrected accepted hosts, kit limits, free-text goals and count-only quotes. Fixed overflowing guide tables and API examples on phones. Documented the published CLI and corrected its MCP handshake. |
| Pricing, account, activate, welcome, support, refunds, privacy, terms, 404, legacy dossier | Kept billing, recovery, support and legal paths accessible. Added no-script fallbacks where a loading shell was the only response. Preserved the signed-in and signed-out offer tests. |

## Operational findings

- **Critical** — the November 22 run could not upload a 460.9 MiB compressed database through Wrangler. The cache now stores large objects in checksum-verified parts and publishes the manifest last. Reads support both formats and the weekday backups.
- **High** — the publication incident could clear on a successful build even if deployment was skipped. It now requires the public lookup to serve the expected snapshot, record and score.
- **High** — a payment-check crash could produce a ready summary. The workflow now uses the checker's exit status and tracks payment failures in a dedicated GitHub issue until the live checks recover.
- **High** — the HTTP suite caught its own missing-slug exception and reported that the local server was absent. It now resolves compact index IDs and checks the responses, sizes and timing of the sampled dossiers. A failed check stops publication.
- **High** — an unverified npm version could enter a paid host config. New scans record the exact version returned by a successful OSV query. A paid kit requires a matching current scan, and returns HTTP 422 without requesting payment when there are no verified pins.
- **High** — the nightly gate compared a dated hackathon submission to live measurements. The submission is archived. The checks for published data, current outreach, classification accuracy and historical series continuity remain in place.
- **Medium** — classification training joined plugin categories using marketplace IDs, although ingestion uses the original repository ID. The classifier now shares identity resolution with ingestion and discards conflicting declarations.
- **Medium** — a publisher description could trigger Tashan’s commercial entitlement guard. Attributed third-party descriptions now have their own markup. Tashan’s offers remain covered by the guard.

The npm package supports local inventory and stdio MCP. HTTP consumers can call the service directly. Demand for other services on the payments page measures receipts at observed addresses. Tashan’s own paid-call conversions are recorded separately in the nightly funnel.

The original audit found both model-assisted grading stages skipped for lack of a credential. They now share a $10 monthly OpenAI allowance. Author-declared task mapping continues independently.

## Production recovery

GitHub Actions run `45092602053` published the 23 November snapshot at `2026-11-23T01:45:41Z`. The public lookup returned the same record, score and timestamp as the export. Issue #1 closed automatically. The run saved 115 daily history shards and successfully stored the 464.9 MiB compressed core and 305.4 MiB compressed skills cache in R2.

A second inventory checked all 13,424 HTML files in the published snapshot and 51,274 distinct internal destinations. It found no broken internal destinations. The query-based `noindex` dossier shell is the sole canonical exception. The 36-page browser check passed at 390 px and 1,280 px. The fresh corpus contains 12,773 measured capabilities out of 119,247 tracked.

At the default shortlist size, 53 of 68 mapped tasks had at least one qualifying package. The production database-access shortlist returned HTTP 200 and its paid request returned an x402 quote. The risk-assessment shortlist reported its kit unavailable and its paid request returned HTTP 422 without a quote. Both served the new snapshot. The published `tashan-cli@0.2.1` completed the MCP handshake, listed all four tools and returned a live package dossier.

The seven-day funnel ending with this run recorded 2,274 pageviews, 14 Polar checkout handoffs, 35 machine quotes and zero tracked x402 attempts or settlements. The payment probes passed 25 checks. The independent comparison against the facilitator's supported terms was unverified, and the probes did not spend funds.

On the same snapshot, reserving one shortlist position for a verified executable raised kit availability to 56 of 68 mapped tasks. Risk assessment, incident response and software architecture had qualifying packages below the old cutoff. Twelve mapped jobs still had no verified install and fourteen had only one. One further taxonomy job had no published mapping. The full index pipeline took 41m04s, the pre-publication suite 37s and the Cloudflare deploy step 25s in run `45092602053`. The grading allowance, expected cost and review queues are documented in [the operating notes](DO-THIS-NEXT.md#0c--nightly-openai-grading).
