# What to use for database access

> Connecting to a database and getting data out — distinct from tuning it. Six independent graders all routed plain Postgres/Mongo/BigQuery connectors into `query-optimization`, whose label reads as EXPLAIN-plan work; that mismatch is what surfaced this gap.

Source: https://tashan.sh/task/database-access.html
Ranked by fit for the task, then how well it documents itself, then the tashan score
  (upkeep and freshness, gated by real adoption). Public evidence only — nothing paid can
  change a rank. Method: https://tashan.sh/methodology.html

## Ranked

| # | Capability | tashan score | Adoption evidence | Activity |
|---|---|---|---|---|
| 1 | [MongoDB](https://tashan.sh/capability/pkg-mongodb-mcp-server.html) | 86 | 206k/wk | active |
| 2 | [Supabase](https://tashan.sh/capability/pkg-supabase-mcp-server-supabase.html) | 95 | 78k/wk | active |
| 3 | [Dbhub](https://tashan.sh/capability/pkg-bytebase-dbhub.html) | 83 | 42k/wk | active |
| 4 | [Teable](https://tashan.sh/capability/pkg-teable-mcp.html) | 49 | 1k/wk | active |
| 5 | [Snowflake](https://tashan.sh/capability/pkg-snowflake-mcp.html) | 38 | 863/wk | active |
| 6 | [NexQL Postgres](https://tashan.sh/capability/pkg-nexql-mcp.html) | 67 | 1k/wk | active |
| 7 | [Idmp Plugin](https://tashan.sh/capability/plugin-taosdata-agent-skills-idmp-plugin.html) | 42 | 2 ★ | active |
| 8 | [Ts Ddd Repository](https://tashan.sh/capability/plugin-llodev-skills-ts-ddd-repository.html) | 42 | 1 marketplaces | active |
| 9 | [Ts Query Cqrs](https://tashan.sh/capability/plugin-llodev-skills-ts-query-cqrs.html) | 42 | 1 marketplaces | active |
| 10 | [Sap Hana CLI](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-hana-cli.html) | 42 | 1 marketplaces | — |
| 11 | [Sap Sqlscript](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-sqlscript.html) | 42 | 1 marketplaces | — |
| 12 | [SQLite Npx](https://tashan.sh/capability/pkg-mcp-server-sqlite-npx.html) | 37 | 3k/wk | abandoned |
| 13 | [Snowflake Development](https://tashan.sh/capability/skill-alirezarezvani-snowflake-development.html) | not scored | 1 repos | active |
| 14 | [SQL Database Assistant](https://tashan.sh/capability/skill-alirezarezvani-sql-database-assistant.html) | not scored | 1 repos | active |
| 15 | [Postgres · modelcontextprotocol](https://tashan.sh/capability/pkg-modelcontextprotocol-server-postgres.html) | not scored | 121k/wk | abandoned |
| 16 | [MySQL](https://tashan.sh/capability/pkg-benborla29-mcp-server-mysql.html) | 69 | 12k/wk | active |
| 17 | [Infrawise](https://tashan.sh/capability/pkg-infrawise.html) | 66 | 729/wk | active |
| 18 | [Mssql · vicagbasi](https://tashan.sh/capability/pkg-mssql-mcp-server.html) | 62 | 3k/wk | active |
| 19 | [SSH Manager](https://tashan.sh/capability/pkg-mcp-ssh-manager.html) | 61 | 596/wk | active |
| 20 | [Read Only Local Postgres](https://tashan.sh/capability/pkg-hovecapital-read-only-postgres-mcp-server.html) | 60 | 163/wk | active |
| 21 | [Mssql · BYMCS](https://tashan.sh/capability/pkg-mssql-mcp.html) | 57 | 664/wk | active |
| 22 | [Infino AI](https://tashan.sh/capability/pkg-infino-ai-mcp-server.html) | 57 | 180/wk | active |
| 23 | [Postgres · kristofer84](https://tashan.sh/capability/pkg-mcp-postgres.html) | 51 | 525/wk | active |
| 24 | [DB Access](https://tashan.sh/capability/pkg-rheopyrin-db-access-mcp.html) | 47 | 59/wk | active |
| 25 | [Postgres](https://tashan.sh/capability/pkg-henkey-postgres-mcp-server.html) | 73 | 2k/wk | active |
| 26 | [Run402](https://tashan.sh/capability/pkg-run402-mcp.html) | 71 | 4k/wk | active |
| 27 | [Mssql](https://tashan.sh/capability/pkg-connorbritain-mssql-mcp-server.html) | 66 | 779/wk | active |
| 28 | [Read Only Local MySQL](https://tashan.sh/capability/pkg-hovecapital-read-only-mysql-mcp-server.html) | 66 | 203/wk | active |
| 29 | [DB Connect](https://tashan.sh/capability/pkg-mcp-db-connect.html) | 65 | 769/wk | active |
| 30 | [PostgreSQL (hardened, read-only)](https://tashan.sh/capability/pkg-postgres-mcp-hardened.html) | 63 | 734/wk | active |
| 31 | [Sqemo](https://tashan.sh/capability/pkg-sqemo-mcp.html) | 62 | 477/wk | active |
| 32 | [Dm8](https://tashan.sh/capability/pkg-mcp-dm8-server.html) | 62 | 409/wk | active |
| 33 | [SQLite · jparkerweb](https://tashan.sh/capability/pkg-mcp-sqlite.html) | 60 | 896/wk | active |
| 34 | [Ainative Postgres](https://tashan.sh/capability/pkg-ainative-postgres-mcp.html) | 58 | 632/wk | active |
| 35 | [Redash](https://tashan.sh/capability/pkg-redash-mcp.html) | 57 | 398/wk | active |
| 36 | [Metaengine](https://tashan.sh/capability/pkg-metaengine-mcp-server.html) | 48 | 60/wk | active |
| 37 | [Androidapi](https://tashan.sh/capability/pkg-androidapi-mcp.html) | 45 | 52/wk | active |
| 38 | [Sqlike](https://tashan.sh/capability/pkg-sqlike-mcp.html) | 45 | 39/wk | active |
| 39 | [Dynoxide](https://tashan.sh/capability/pkg-dynoxide.html) | 70 | 5k/wk | active |
| 40 | [SAP HANA CLI](https://tashan.sh/capability/pkg-hana-cli.html) | 65 | 1k/wk | active |

Showing the top 40 of 60. The full ranked shelf is at https://tashan.sh/task/database-access.html.

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
