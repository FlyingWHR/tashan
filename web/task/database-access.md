# What to use for database access

> Connecting to a database and getting data out — distinct from tuning it. Six independent graders all routed plain Postgres/Mongo/BigQuery connectors into `query-optimization`, whose label reads as EXPLAIN-plan work; that mismatch is what surfaced this gap.

Source: https://tashan.sh/task/database-access.html
Ranked by fit for the task, then how well it documents itself, then the tashan score
  (upkeep and freshness, gated by real adoption). Public evidence only — nothing paid can
  change a rank. Method: https://tashan.sh/methodology.html

## Ranked

| # | Capability | tashan score | Adoption evidence | Activity |
|---|---|---|---|---|
| 1 | [MongoDB](https://tashan.sh/capability/pkg-mongodb-mcp-server.html) | 79 | 119k/wk | active |
| 2 | [Supabase](https://tashan.sh/capability/pkg-supabase-mcp-server-supabase.html) | 99 | 239k/wk | active |
| 3 | [Dbhub](https://tashan.sh/capability/pkg-bytebase-dbhub.html) | 78 | 44k/wk | active |
| 4 | [NexQL Postgres](https://tashan.sh/capability/pkg-nexql-mcp.html) | 50 | 367/wk | active |
| 5 | [Sap Hana CLI](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-hana-cli.html) | 42 | 1 marketplaces | — |
| 6 | [Sap Sqlscript](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-sqlscript.html) | 42 | 1 marketplaces | — |
| 7 | [Idmp Plugin](https://tashan.sh/capability/plugin-taosdata-agent-skills-idmp-plugin.html) | 36 | 2 ★ | active |
| 8 | [Postgres · modelcontextprotocol](https://tashan.sh/capability/pkg-modelcontextprotocol-server-postgres.html) | not scored | 117k/wk | abandoned |
| 9 | [MySQL](https://tashan.sh/capability/pkg-benborla29-mcp-server-mysql.html) | 54 | 12k/wk | active |
| 10 | [Mssql](https://tashan.sh/capability/pkg-mssql-mcp.html) | 57 | 1k/wk | active |
| 11 | [Infrawise](https://tashan.sh/capability/pkg-infrawise.html) | 51 | 416/wk | active |
| 12 | [Mssql · vicagbasi](https://tashan.sh/capability/pkg-mssql-mcp-server.html) | 47 | 4k/wk | active |
| 13 | [Read Only Local Postgres](https://tashan.sh/capability/pkg-hovecapital-read-only-postgres-mcp-server.html) | 47 | 163/wk | active |
| 14 | [Infino AI](https://tashan.sh/capability/pkg-infino-ai-mcp-server.html) | 42 | 180/wk | active |
| 15 | [Postgres · kristofer84](https://tashan.sh/capability/pkg-mcp-postgres.html) | 38 | 367/wk | abandoned |
| 16 | [DB Access](https://tashan.sh/capability/pkg-rheopyrin-db-access-mcp.html) | 36 | 59/wk | active |
| 17 | [Run402](https://tashan.sh/capability/pkg-run402-mcp.html) | 65 | 3k/wk | active |
| 18 | [Postgres](https://tashan.sh/capability/pkg-henkey-postgres-mcp-server.html) | 59 | 954/wk | active |
| 19 | [SQLite](https://tashan.sh/capability/pkg-mcp-sqlite.html) | 53 | 488/wk | stable |
| 20 | [Read Only Local MySQL](https://tashan.sh/capability/pkg-hovecapital-read-only-mysql-mcp-server.html) | 53 | 203/wk | active |
| 21 | [Redash · seob717](https://tashan.sh/capability/pkg-redash-mcp.html) | 51 | 305/wk | active |
| 22 | [Sqemo](https://tashan.sh/capability/pkg-sqemo-mcp.html) | 48 | 316/wk | active |
| 23 | [Dm8](https://tashan.sh/capability/pkg-mcp-dm8-server.html) | 47 | 409/wk | active |
| 24 | [Mssql · connorbritain](https://tashan.sh/capability/pkg-connorbritain-mssql-mcp-server.html) | 47 | 251/wk | active |
| 25 | [PostgreSQL (hardened, read-only)](https://tashan.sh/capability/pkg-postgres-mcp-hardened.html) | 47 | 189/wk | active |
| 26 | [DB Connect](https://tashan.sh/capability/pkg-mcp-db-connect.html) | 44 | 142/wk | active |
| 27 | [Ainative Postgres](https://tashan.sh/capability/pkg-ainative-postgres-mcp.html) | 37 | 88/wk | active |
| 28 | [Spacetimedb](https://tashan.sh/capability/plugin-clockworklabs-spacetimedb-spacetimedb.html) | 74 | 25k ★ | active |
| 29 | [Monacloud](https://tashan.sh/capability/pkg-monacloud-mcp.html) | 55 | 419/wk | active |
| 30 | [Databases (read-only, switchable)](https://tashan.sh/capability/pkg-shibbirweb-mcp-db-read-only.html) | 51 | 537/wk | active |
| 31 | [Seedfast](https://tashan.sh/capability/pkg-seedfast.html) | 51 | 221/wk | active |
| 32 | [Postgres · kaiva](https://tashan.sh/capability/pkg-kaiva-postgres-mcp.html) | 51 | 203/wk | active |
| 33 | [Dev Error Explainers](https://tashan.sh/capability/pkg-dev-error-explainers.html) | 50 | 385/wk | active |
| 34 | [Jarroba Tools](https://tashan.sh/capability/pkg-jarroba-mcp.html) | 50 | 274/wk | active |
| 35 | [SQL Formatter](https://tashan.sh/capability/pkg-sql-formatter-mcp.html) | 49 | 294/wk | active |
| 36 | [Postgres (read-only)](https://tashan.sh/capability/pkg-contextflo-postgres-mcp.html) | 49 | 284/wk | active |
| 37 | [QuestDB Web Console](https://tashan.sh/capability/pkg-questdb-mcp-server-questdb.html) | 49 | 101/wk | active |
| 38 | [MySQL · berthojoris](https://tashan.sh/capability/pkg-berthojoris-mcp-mysql-server.html) | 48 | 482/wk | active |
| 39 | [Fauna](https://tashan.sh/capability/pkg-mrfentmen-fauna-mcp.html) | 48 | 343/wk | active |
| 40 | [Pg Migration Lock Lint](https://tashan.sh/capability/pkg-readystack-pg-migration-lock-lint.html) | 48 | 337/wk | active |

Showing the top 40 of 71. The full ranked shelf is at https://tashan.sh/task/database-access.html.

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
