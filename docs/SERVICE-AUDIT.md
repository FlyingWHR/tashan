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
- **High** — the HTTP suite caught its own missing-slug exception and reported that the local server was absent. It now resolves compact index IDs and checks the responses, sizes and timing of the sampled dossiers. A failed check stops publication.
- **High** — an unverified npm version could enter a paid host config. New scans record the exact version returned by a successful OSV query. A paid kit requires a matching current scan, and returns HTTP 422 without requesting payment when there are no verified pins.
- **High** — the nightly gate compared a dated hackathon submission to live measurements. The submission is archived. The checks for published data, current outreach, classification accuracy and historical series continuity remain in place.
- **Medium** — classification training joined plugin categories using marketplace IDs, although ingestion uses the original repository ID. The classifier now shares identity resolution with ingestion and discards conflicting declarations.
- **Medium** — a publisher description could trigger Tashan’s commercial entitlement guard. Attributed third-party descriptions now have their own markup. Tashan’s offers remain covered by the guard.

The npm package supports local inventory and stdio MCP. HTTP consumers can call the service directly. Demand for other services on the payments page measures receipts at observed addresses. Tashan’s own paid-call conversions are recorded separately in the nightly funnel.

The repository has no `ANTHROPIC_API_KEY` Actions secret. Author-declared task mapping continues automatically. Model-assisted task and expertise grading require a funded credential.
