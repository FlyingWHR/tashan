# What to use for database access

> Connecting to a database and getting data out — distinct from tuning it. Six independent graders all routed plain Postgres/Mongo/BigQuery connectors into `query-optimization`, whose label reads as EXPLAIN-plan work; that mismatch is what surfaced this gap.

Source: https://tashan.sh/task/database-access.html
Ranked by fit for the task, then how well it documents itself, then the tashan score
  (upkeep and freshness, gated by real adoption). Public evidence only — nothing paid can
  change a rank. Method: https://tashan.sh/methodology.html

## Ranked

| # | Capability | tashan score | Adoption evidence | Activity |
|---|---|---|---|---|
| 1 | [MongoDB](https://tashan.sh/capability/pkg-mongodb-mcp-server.html) | 84 | 54k/wk | active |
| 2 | [Supabase](https://tashan.sh/capability/pkg-supabase-mcp-server-supabase.html) | 98 | 112k/wk | active |
| 3 | [Dbhub](https://tashan.sh/capability/pkg-bytebase-dbhub.html) | 80 | 12k/wk | active |
| 4 | [Snowflake](https://tashan.sh/capability/pkg-snowflake-mcp.html) | 34 | 702/wk | abandoned |
| 5 | [NexQL Postgres](https://tashan.sh/capability/pkg-nexql-mcp.html) | 60 | 367/wk | active |
| 6 | [Idmp Plugin](https://tashan.sh/capability/plugin-taosdata-agent-skills-idmp-plugin.html) | 42 | 2 ★ | active |
| 7 | [Sap Hana CLI](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-hana-cli.html) | 42 | 1 marketplaces | — |
| 8 | [Sap Sqlscript](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-sqlscript.html) | 42 | 1 marketplaces | — |
| 9 | [Ts Ddd Repository](https://tashan.sh/capability/plugin-llodev-skills-ts-ddd-repository.html) | 39 | 1 marketplaces | active |
| 10 | [Ts Query Cqrs](https://tashan.sh/capability/plugin-llodev-skills-ts-query-cqrs.html) | 39 | 1 marketplaces | active |
| 11 | [SQLite Npx](https://tashan.sh/capability/pkg-mcp-server-sqlite-npx.html) | 34 | 2k/wk | abandoned |
| 12 | [Postgres · modelcontextprotocol](https://tashan.sh/capability/pkg-modelcontextprotocol-server-postgres.html) | not scored | 95k/wk | abandoned |
| 13 | [MySQL](https://tashan.sh/capability/pkg-benborla29-mcp-server-mysql.html) | 65 | 11k/wk | active |
| 14 | [Infrawise](https://tashan.sh/capability/pkg-infrawise.html) | 61 | 416/wk | active |
| 15 | [Read Only Local Postgres](https://tashan.sh/capability/pkg-hovecapital-read-only-postgres-mcp-server.html) | 56 | 163/wk | active |
| 16 | [Mssql · vicagbasi](https://tashan.sh/capability/pkg-mssql-mcp-server.html) | 55 | 2k/wk | active |
| 17 | [Mssql · BYMCS](https://tashan.sh/capability/pkg-mssql-mcp.html) | 53 | 664/wk | active |
| 18 | [Infino AI](https://tashan.sh/capability/pkg-infino-ai-mcp-server.html) | 52 | 180/wk | active |
| 19 | [Postgres · kristofer84](https://tashan.sh/capability/pkg-mcp-postgres.html) | 49 | 793/wk | active |
| 20 | [DB Access](https://tashan.sh/capability/pkg-rheopyrin-db-access-mcp.html) | 43 | 59/wk | active |
| 21 | [Run402](https://tashan.sh/capability/pkg-run402-mcp.html) | 72 | 4k/wk | active |
| 22 | [Postgres · henkey](https://tashan.sh/capability/pkg-henkey-postgres-mcp-server.html) | 69 | 1k/wk | active |
| 23 | [PostgreSQL (hardened, read-only)](https://tashan.sh/capability/pkg-postgres-mcp-hardened.html) | 61 | 799/wk | active |
| 24 | [Read Only Local MySQL](https://tashan.sh/capability/pkg-hovecapital-read-only-mysql-mcp-server.html) | 61 | 203/wk | active |
| 25 | [Mssql](https://tashan.sh/capability/pkg-connorbritain-mssql-mcp-server.html) | 59 | 516/wk | active |
| 26 | [Sqemo](https://tashan.sh/capability/pkg-sqemo-mcp.html) | 58 | 316/wk | active |
| 27 | [Dm8](https://tashan.sh/capability/pkg-mcp-dm8-server.html) | 57 | 409/wk | active |
| 28 | [SQLite · jparkerweb](https://tashan.sh/capability/pkg-mcp-sqlite.html) | 54 | 549/wk | active |
| 29 | [Ainative Postgres](https://tashan.sh/capability/pkg-ainative-postgres-mcp.html) | 53 | 632/wk | active |
| 30 | [Redash · seob717](https://tashan.sh/capability/pkg-redash-mcp.html) | 53 | 398/wk | active |
| 31 | [DB Connect](https://tashan.sh/capability/pkg-mcp-db-connect.html) | 53 | 142/wk | active |
| 32 | [Metaengine](https://tashan.sh/capability/pkg-metaengine-mcp-server.html) | 45 | 60/wk | active |
| 33 | [Androidapi](https://tashan.sh/capability/pkg-androidapi-mcp.html) | 41 | 55/wk | active |
| 34 | [Sqlike](https://tashan.sh/capability/pkg-sqlike-mcp.html) | 41 | 39/wk | active |
| 35 | [Runner](https://tashan.sh/capability/pkg-synapsor-runner.html) | 66 | 1k/wk | active |
| 36 | [SQL Preview](https://tashan.sh/capability/pkg-sql-preview.html) | 63 | 782/wk | active |
| 37 | [Data Studio](https://tashan.sh/capability/pkg-geek-fun-data-studio-mcp.html) | 63 | 460/wk | active |
| 38 | [SAP HANA CLI](https://tashan.sh/capability/pkg-hana-cli.html) | 60 | 1k/wk | active |
| 39 | [Seedfast](https://tashan.sh/capability/pkg-seedfast.html) | 59 | 421/wk | active |
| 40 | [Mongo](https://tashan.sh/capability/pkg-mcp-mongo-server.html) | 58 | 649/wk | active |

Showing the top 40 of 78. The full ranked shelf is at https://tashan.sh/task/database-access.html.

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
