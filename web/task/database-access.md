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
| 8 | [Read Only Local Postgres](https://tashan.sh/capability/pkg-hovecapital-read-only-postgres-mcp-server.html) | 61 | 163/wk | active |
| 9 | [Postgres](https://tashan.sh/capability/pkg-henkey-postgres-mcp-server.html) | 73 | 2k/wk | active |
| 10 | [Run402](https://tashan.sh/capability/pkg-run402-mcp.html) | 71 | 4k/wk | active |
| 11 | [Mssql](https://tashan.sh/capability/pkg-connorbritain-mssql-mcp-server.html) | 67 | 779/wk | active |
| 12 | [Read Only Local MySQL](https://tashan.sh/capability/pkg-hovecapital-read-only-mysql-mcp-server.html) | 67 | 203/wk | active |
| 13 | [SQLite · jparkerweb](https://tashan.sh/capability/pkg-mcp-sqlite.html) | 60 | 896/wk | active |
| 14 | [Dynoxide](https://tashan.sh/capability/pkg-dynoxide.html) | 71 | 5k/wk | active |
| 15 | [SAP HANA CLI](https://tashan.sh/capability/pkg-hana-cli.html) | 67 | 1k/wk | active |
| 16 | [Infrawise](https://tashan.sh/capability/pkg-infrawise.html) | 67 | 729/wk | active |
| 17 | [Mssql Reader](https://tashan.sh/capability/pkg-connorbritain-mssql-mcp-reader.html) | 66 | 1k/wk | active |
| 18 | [DB Connect](https://tashan.sh/capability/pkg-mcp-db-connect.html) | 66 | 769/wk | active |
| 19 | [Wr Admin Mcp Connector](https://tashan.sh/capability/pkg-wr-admin-mcp-connector.html) | 65 | 992/wk | active |
| 20 | [Seedfast](https://tashan.sh/capability/pkg-seedfast.html) | 65 | 421/wk | active |
| 21 | [Mongo](https://tashan.sh/capability/pkg-mcp-mongo-server.html) | 64 | 649/wk | active |
| 22 | [PostgreSQL (hardened, read-only)](https://tashan.sh/capability/pkg-postgres-mcp-hardened.html) | 63 | 734/wk | active |
| 23 | [Sqemo](https://tashan.sh/capability/pkg-sqemo-mcp.html) | 63 | 477/wk | active |
| 24 | [Dm8](https://tashan.sh/capability/pkg-mcp-dm8-server.html) | 63 | 409/wk | active |
| 25 | [Mssql · vicagbasi](https://tashan.sh/capability/pkg-mssql-mcp-server.html) | 62 | 3k/wk | active |
| 26 | [SSH Manager](https://tashan.sh/capability/pkg-mcp-ssh-manager.html) | 62 | 596/wk | active |
| 27 | [SQL Preview](https://tashan.sh/capability/pkg-sql-preview.html) | 62 | 345/wk | active |
| 28 | [Ainative Postgres](https://tashan.sh/capability/pkg-ainative-postgres-mcp.html) | 59 | 632/wk | active |
| 29 | [Mssql · BYMCS](https://tashan.sh/capability/pkg-mssql-mcp.html) | 58 | 664/wk | active |
| 30 | [Redash](https://tashan.sh/capability/pkg-redash-mcp.html) | 58 | 398/wk | active |
| 31 | [Infino AI](https://tashan.sh/capability/pkg-infino-ai-mcp-server.html) | 57 | 180/wk | active |
| 32 | [Schema Designer](https://tashan.sh/capability/pkg-mcp-schema-designer.html) | 54 | 132/wk | active |
| 33 | [Postgres · kristofer84](https://tashan.sh/capability/pkg-mcp-postgres.html) | 51 | 525/wk | active |
| 34 | [Metaengine](https://tashan.sh/capability/pkg-metaengine-mcp-server.html) | 49 | 60/wk | active |
| 35 | [DB Access](https://tashan.sh/capability/pkg-rheopyrin-db-access-mcp.html) | 48 | 57/wk | active |
| 36 | [Sqlike](https://tashan.sh/capability/pkg-sqlike-mcp.html) | 46 | 39/wk | active |
| 37 | [Breezedeploy](https://tashan.sh/capability/pkg-breezedeploy-mcp.html) | 45 | 31/wk | active |
| 38 | [Alpacacloud](https://tashan.sh/capability/pkg-alpacacloud-mcp.html) | 44 | 52/wk | active |
| 39 | [Bach Snowflake](https://tashan.sh/capability/pkg-bach-snowflake-mcp.html) | 44 | 31/wk | active |
| 40 | [SQL · abhishekmcp](https://tashan.sh/capability/pkg-abhishekmcp-sql.html) | 43 | 52/wk | active |

Showing the top 40 of 48. The full ranked shelf is at https://tashan.sh/task/database-access.html.

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
