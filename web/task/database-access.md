# What to use for database access

> Connecting to a database and getting data out — distinct from tuning it. Six independent graders all routed plain Postgres/Mongo/BigQuery connectors into `query-optimization`, whose label reads as EXPLAIN-plan work; that mismatch is what surfaced this gap.

Source: https://tashan.sh/task/database-access.html
Ranked by fit for the task, then how well it documents itself, then the tashan score
  (upkeep and freshness, gated by real adoption). Public evidence only — nothing paid can
  change a rank. Method: https://tashan.sh/methodology.html

## Ranked

| # | Capability | tashan score | Adoption evidence | Activity |
|---|---|---|---|---|
| 1 | [MongoDB](https://tashan.sh/capability/pkg-mongodb-mcp-server.html) | 87 | 206k/wk | active |
| 2 | [Supabase](https://tashan.sh/capability/pkg-supabase-mcp-server-supabase.html) | 96 | 78k/wk | active |
| 3 | [Dbhub](https://tashan.sh/capability/pkg-bytebase-dbhub.html) | 83 | 42k/wk | active |
| 4 | [Teable](https://tashan.sh/capability/pkg-teable-mcp.html) | 50 | 1k/wk | active |
| 5 | [Snowflake](https://tashan.sh/capability/pkg-snowflake-mcp.html) | 39 | 863/wk | active |
| 6 | [Influxdb](https://tashan.sh/capability/pkg-influxdb-mcp-server.html) | 31 | 1k/wk | abandoned |
| 7 | [Supabase · Cappahccino](https://tashan.sh/capability/pkg-supabase-mcp.html) | 23 | 3k/wk | abandoned |
| 8 | [AWS Athena](https://tashan.sh/capability/pkg-lishenxydlgzs-aws-athena-mcp.html) | 19 | 734/wk | abandoned |
| 9 | [NexQL Postgres](https://tashan.sh/capability/pkg-nexql-mcp.html) | 68 | 1k/wk | active |
| 10 | [Idmp Plugin](https://tashan.sh/capability/plugin-taosdata-agent-skills-idmp-plugin.html) | 43 | 2 ★ | active |
| 11 | [Ts Ddd Repository](https://tashan.sh/capability/plugin-llodev-skills-ts-ddd-repository.html) | 42 | 1 marketplaces | active |
| 12 | [Ts Query Cqrs](https://tashan.sh/capability/plugin-llodev-skills-ts-query-cqrs.html) | 42 | 1 marketplaces | active |
| 13 | [Sap Hana CLI](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-hana-cli.html) | 42 | 1 marketplaces | — |
| 14 | [Sap Sqlscript](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-sqlscript.html) | 42 | 1 marketplaces | — |
| 15 | [SQLite Npx](https://tashan.sh/capability/pkg-mcp-server-sqlite-npx.html) | 38 | 3k/wk | abandoned |
| 16 | [MySQL · mysql-mcp](https://tashan.sh/capability/pkg-mysql-mcp.html) | 20 | 958/wk | abandoned |
| 17 | [Snowflake Development](https://tashan.sh/capability/skill-alirezarezvani-snowflake-development.html) | not scored | 1 repos | active |
| 18 | [SQL Database Assistant](https://tashan.sh/capability/skill-alirezarezvani-sql-database-assistant.html) | not scored | 1 repos | active |
| 19 | [Postgres · modelcontextprotocol](https://tashan.sh/capability/pkg-modelcontextprotocol-server-postgres.html) | not scored | 121k/wk | abandoned |
| 20 | [MySQL](https://tashan.sh/capability/pkg-benborla29-mcp-server-mysql.html) | 69 | 12k/wk | active |
| 21 | [Infrawise](https://tashan.sh/capability/pkg-infrawise.html) | 66 | 729/wk | active |
| 22 | [Mssql · vicagbasi](https://tashan.sh/capability/pkg-mssql-mcp-server.html) | 62 | 3k/wk | active |
| 23 | [SSH Manager](https://tashan.sh/capability/pkg-mcp-ssh-manager.html) | 62 | 596/wk | active |
| 24 | [Read Only Local Postgres](https://tashan.sh/capability/pkg-hovecapital-read-only-postgres-mcp-server.html) | 61 | 163/wk | active |
| 25 | [Mssql · BYMCS](https://tashan.sh/capability/pkg-mssql-mcp.html) | 58 | 664/wk | active |
| 26 | [Infino AI](https://tashan.sh/capability/pkg-infino-ai-mcp-server.html) | 57 | 180/wk | active |
| 27 | [Postgres · kristofer84](https://tashan.sh/capability/pkg-mcp-postgres.html) | 51 | 525/wk | active |
| 28 | [DB Access](https://tashan.sh/capability/pkg-rheopyrin-db-access-mcp.html) | 48 | 57/wk | active |
| 29 | [Snowflake · mikdanjey](https://tashan.sh/capability/pkg-snowflake-mcp-server.html) | 24 | 3k/wk | abandoned |
| 30 | [Postgres](https://tashan.sh/capability/pkg-henkey-postgres-mcp-server.html) | 73 | 2k/wk | active |
| 31 | [Run402](https://tashan.sh/capability/pkg-run402-mcp.html) | 71 | 4k/wk | active |
| 32 | [Read Only Local MySQL](https://tashan.sh/capability/pkg-hovecapital-read-only-mysql-mcp-server.html) | 67 | 203/wk | active |
| 33 | [Mssql](https://tashan.sh/capability/pkg-connorbritain-mssql-mcp-server.html) | 66 | 779/wk | active |
| 34 | [DB Connect](https://tashan.sh/capability/pkg-mcp-db-connect.html) | 66 | 769/wk | active |
| 35 | [PostgreSQL (hardened, read-only)](https://tashan.sh/capability/pkg-postgres-mcp-hardened.html) | 63 | 734/wk | active |
| 36 | [Sqemo](https://tashan.sh/capability/pkg-sqemo-mcp.html) | 63 | 477/wk | active |
| 37 | [Dm8](https://tashan.sh/capability/pkg-mcp-dm8-server.html) | 63 | 409/wk | active |
| 38 | [SQLite · jparkerweb](https://tashan.sh/capability/pkg-mcp-sqlite.html) | 60 | 896/wk | active |
| 39 | [Ainative Postgres](https://tashan.sh/capability/pkg-ainative-postgres-mcp.html) | 59 | 632/wk | active |
| 40 | [Redash](https://tashan.sh/capability/pkg-redash-mcp.html) | 58 | 398/wk | active |

Showing the top 40 of 64. The full ranked shelf is at https://tashan.sh/task/database-access.html.

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
