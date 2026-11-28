# What to use for database access

> Connecting to a database and getting data out — distinct from tuning it. Six independent graders all routed plain Postgres/Mongo/BigQuery connectors into `query-optimization`, whose label reads as EXPLAIN-plan work; that mismatch is what surfaced this gap.

Source: https://tashan.sh/task/database-access.html
Ranked by fit for the task, then how well it documents itself, then the tashan score
  (upkeep and freshness, gated by real adoption). Public evidence only — nothing paid can
  change a rank. Method: https://tashan.sh/methodology.html

## Ranked

| # | Capability | tashan score | Adoption evidence | Activity |
|---|---|---|---|---|
| 1 | [MongoDB](https://tashan.sh/capability/pkg-mongodb-mcp-server.html) | 86 | 168k/wk | active |
| 2 | [Supabase](https://tashan.sh/capability/pkg-supabase-mcp-server-supabase.html) | 98 | 239k/wk | active |
| 3 | [Dbhub](https://tashan.sh/capability/pkg-bytebase-dbhub.html) | 86 | 220k/wk | active |
| 4 | [Dbx App](https://tashan.sh/capability/pkg-dbx-app-mcp-server.html) | 73 | 6k/wk | active |
| 5 | [NexQL Postgres](https://tashan.sh/capability/pkg-nexql-mcp.html) | 49 | 367/wk | active |
| 6 | [Sap Hana CLI](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-hana-cli.html) | 42 | 1 marketplaces | — |
| 7 | [Sap Sqlscript](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-sqlscript.html) | 42 | 1 marketplaces | — |
| 8 | [Idmp Plugin](https://tashan.sh/capability/plugin-taosdata-agent-skills-idmp-plugin.html) | 35 | 2 ★ | active |
| 9 | [Postgres · modelcontextprotocol](https://tashan.sh/capability/pkg-modelcontextprotocol-server-postgres.html) | not scored | 122k/wk | abandoned |
| 10 | [MySQL](https://tashan.sh/capability/pkg-benborla29-mcp-server-mysql.html) | 54 | 12k/wk | active |
| 11 | [Mssql](https://tashan.sh/capability/pkg-mssql-mcp.html) | 56 | 1k/wk | active |
| 12 | [Infrawise](https://tashan.sh/capability/pkg-infrawise.html) | 50 | 416/wk | active |
| 13 | [Read Only Local Postgres](https://tashan.sh/capability/pkg-hovecapital-read-only-postgres-mcp-server.html) | 46 | 163/wk | active |
| 14 | [Mssql · vicagbasi](https://tashan.sh/capability/pkg-mssql-mcp-server.html) | 45 | 3k/wk | active |
| 15 | [Infino AI](https://tashan.sh/capability/pkg-infino-ai-mcp-server.html) | 42 | 180/wk | active |
| 16 | [Postgres · kristofer84](https://tashan.sh/capability/pkg-mcp-postgres.html) | 38 | 367/wk | abandoned |
| 17 | [Run402](https://tashan.sh/capability/pkg-run402-mcp.html) | 64 | 3k/wk | active |
| 18 | [Postgres](https://tashan.sh/capability/pkg-henkey-postgres-mcp-server.html) | 58 | 954/wk | active |
| 19 | [SQLite](https://tashan.sh/capability/pkg-mcp-sqlite.html) | 53 | 488/wk | stable |
| 20 | [Read Only Local MySQL](https://tashan.sh/capability/pkg-hovecapital-read-only-mysql-mcp-server.html) | 52 | 203/wk | active |
| 21 | [Redash · seob717](https://tashan.sh/capability/pkg-redash-mcp.html) | 50 | 305/wk | active |
| 22 | [Sqemo](https://tashan.sh/capability/pkg-sqemo-mcp.html) | 47 | 316/wk | active |
| 23 | [PostgreSQL (hardened, read-only)](https://tashan.sh/capability/pkg-postgres-mcp-hardened.html) | 47 | 189/wk | active |
| 24 | [Dm8](https://tashan.sh/capability/pkg-mcp-dm8-server.html) | 46 | 409/wk | active |
| 25 | [Mssql · connorbritain](https://tashan.sh/capability/pkg-connorbritain-mssql-mcp-server.html) | 46 | 251/wk | active |
| 26 | [DB Connect](https://tashan.sh/capability/pkg-mcp-db-connect.html) | 43 | 142/wk | active |
| 27 | [Ainative Postgres](https://tashan.sh/capability/pkg-ainative-postgres-mcp.html) | 36 | 88/wk | active |
| 28 | [Spacetimedb](https://tashan.sh/capability/plugin-clockworklabs-spacetimedb-spacetimedb.html) | 74 | 25k ★ | active |
| 29 | [Dbmastermind](https://tashan.sh/capability/pkg-dbmastermind-mcp.html) | 67 | 1k/wk | active |
| 30 | [Neosql](https://tashan.sh/capability/pkg-neosql-mcp.html) | 67 | 679/wk | active |
| 31 | [Dbmcp](https://tashan.sh/capability/pkg-haymon-ai-dbmcp.html) | 61 | 377/wk | active |
| 32 | [Rowstile](https://tashan.sh/capability/pkg-rowstile.html) | 60 | 319/wk | active |
| 33 | [Tusk](https://tashan.sh/capability/pkg-tusk-mcp.html) | 57 | 200/wk | active |
| 34 | [Monacloud](https://tashan.sh/capability/pkg-monacloud-mcp.html) | 54 | 419/wk | active |
| 35 | [Databases (read-only, switchable)](https://tashan.sh/capability/pkg-shibbirweb-mcp-db-read-only.html) | 51 | 537/wk | active |
| 36 | [Seedfast](https://tashan.sh/capability/pkg-seedfast.html) | 51 | 221/wk | active |
| 37 | [Jarroba Tools](https://tashan.sh/capability/pkg-jarroba-mcp.html) | 50 | 274/wk | active |
| 38 | [Postgres · kaiva](https://tashan.sh/capability/pkg-kaiva-postgres-mcp.html) | 50 | 203/wk | active |
| 39 | [Dev Error Explainers](https://tashan.sh/capability/pkg-dev-error-explainers.html) | 49 | 385/wk | active |
| 40 | [Postgres (read-only)](https://tashan.sh/capability/pkg-contextflo-postgres-mcp.html) | 49 | 284/wk | active |

Showing the top 40 of 77. The full ranked shelf is at https://tashan.sh/task/database-access.html.

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
