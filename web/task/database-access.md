# What to use for database access

> Connecting to a database and getting data out — distinct from tuning it. Six independent graders all routed plain Postgres/Mongo/BigQuery connectors into `query-optimization`, whose label reads as EXPLAIN-plan work; that mismatch is what surfaced this gap.

Source: https://tashan.sh/task/database-access.html
Ranked by fit for the task, then how well it documents itself, then the tashan score
  (upkeep and freshness, gated by real adoption). Public evidence only — nothing paid can
  change a rank. Method: https://tashan.sh/methodology.html

## Ranked

| # | Capability | tashan score | Adoption evidence | Activity |
|---|---|---|---|---|
| 1 | [Idmp Plugin](https://tashan.sh/capability/plugin-taosdata-agent-skills-idmp-plugin.html) | 43 | 2 ★ | active |
| 2 | [Ts Ddd Repository](https://tashan.sh/capability/plugin-llodev-skills-ts-ddd-repository.html) | 43 | 1 marketplaces | active |
| 3 | [Ts Query Cqrs](https://tashan.sh/capability/plugin-llodev-skills-ts-query-cqrs.html) | 43 | 1 marketplaces | active |
| 4 | [Sap Hana CLI](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-hana-cli.html) | 42 | 1 marketplaces | — |
| 5 | [Sap Sqlscript](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-sqlscript.html) | 42 | 1 marketplaces | — |
| 6 | [Snowflake Development](https://tashan.sh/capability/skill-alirezarezvani-snowflake-development.html) | not scored | 1 repos | active |
| 7 | [SQL Database Assistant](https://tashan.sh/capability/skill-alirezarezvani-sql-database-assistant.html) | not scored | 1 repos | active |
| 8 | [Aiven](https://tashan.sh/capability/pkg-mcp-aiven.html) | 71 | 376/wk | active |
| 9 | [Postgres](https://tashan.sh/capability/pkg-henkey-postgres-mcp-server.html) | 74 | 2k/wk | active |
| 10 | [Run402](https://tashan.sh/capability/pkg-run402-mcp.html) | 71 | 4k/wk | active |
| 11 | [Mssql](https://tashan.sh/capability/pkg-connorbritain-mssql-mcp-server.html) | 67 | 779/wk | active |
| 12 | [SQLite · jparkerweb](https://tashan.sh/capability/pkg-mcp-sqlite.html) | 60 | 896/wk | active |
| 13 | [Dynoxide](https://tashan.sh/capability/pkg-dynoxide.html) | 71 | 5k/wk | active |
| 14 | [SAP HANA CLI](https://tashan.sh/capability/pkg-hana-cli.html) | 67 | 1k/wk | active |
| 15 | [Mssql Reader](https://tashan.sh/capability/pkg-connorbritain-mssql-mcp-reader.html) | 67 | 1k/wk | active |
| 16 | [Infrawise](https://tashan.sh/capability/pkg-infrawise.html) | 67 | 729/wk | active |
| 17 | [Wr Admin Mcp Connector](https://tashan.sh/capability/pkg-wr-admin-mcp-connector.html) | 66 | 992/wk | active |
| 18 | [Seedfast](https://tashan.sh/capability/pkg-seedfast.html) | 65 | 421/wk | active |
| 19 | [Oe](https://tashan.sh/capability/pkg-openenthrium-oe-mcp.html) | 64 | 821/wk | active |
| 20 | [Stackql](https://tashan.sh/capability/pkg-stackql-mcp-server.html) | 64 | 316/wk | active |
| 21 | [Sqemo](https://tashan.sh/capability/pkg-sqemo-mcp.html) | 63 | 477/wk | active |
| 22 | [SQL Preview](https://tashan.sh/capability/pkg-sql-preview.html) | 63 | 345/wk | active |
| 23 | [Orangerail](https://tashan.sh/capability/pkg-orangerail.html) | 61 | 561/wk | active |
| 24 | [Ainative Postgres](https://tashan.sh/capability/pkg-ainative-postgres-mcp.html) | 59 | 632/wk | active |
| 25 | [Winctl](https://tashan.sh/capability/pkg-sitharaj88-winctl.html) | 59 | 439/wk | active |
| 26 | [Infino AI](https://tashan.sh/capability/pkg-infino-ai-mcp-server.html) | 58 | 180/wk | active |
| 27 | [Ravendb](https://tashan.sh/capability/pkg-ravendb-mcp.html) | 57 | 253/wk | active |
| 28 | [Schema Designer](https://tashan.sh/capability/pkg-mcp-schema-designer.html) | 54 | 132/wk | active |
| 29 | [Lintbase](https://tashan.sh/capability/pkg-lintbase-mcp.html) | 49 | 68/wk | active |
| 30 | [Metaengine](https://tashan.sh/capability/pkg-metaengine-mcp-server.html) | 49 | 60/wk | active |
| 31 | [Panini Connector](https://tashan.sh/capability/pkg-panini-connector-mcp.html) | 48 | 61/wk | active |
| 32 | [DB Access](https://tashan.sh/capability/pkg-rheopyrin-db-access-mcp.html) | 48 | 57/wk | active |
| 33 | [Drawdb](https://tashan.sh/capability/pkg-drawdb-mcp.html) | 48 | 46/wk | active |
| 34 | [Dev Lifecycle](https://tashan.sh/capability/plugin-eblouin-development-eblouin-plugins-dev-lifecycle.html) | 47 | 1 ★ | active |
| 35 | [Ainative Zerodb](https://tashan.sh/capability/pkg-ainative-zerodb-mcp-server.html) | 47 | 30/wk | active |
| 36 | [Sqlike](https://tashan.sh/capability/pkg-sqlike-mcp.html) | 46 | 39/wk | active |
| 37 | [Kysely SQL](https://tashan.sh/capability/plugin-kingstinct-github-kysely-sql.html) | 45 | 1 marketplaces | active |
| 38 | [Breezedeploy](https://tashan.sh/capability/pkg-breezedeploy-mcp.html) | 45 | 31/wk | active |
| 39 | [SQL · abhishekmcp](https://tashan.sh/capability/pkg-abhishekmcp-sql.html) | 44 | 52/wk | active |
| 40 | [Alpacacloud](https://tashan.sh/capability/pkg-alpacacloud-mcp.html) | 44 | 52/wk | active |

Showing the top 40 of 50. The full ranked shelf is at https://tashan.sh/task/database-access.html.

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
