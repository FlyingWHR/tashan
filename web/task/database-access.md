# What to use for database access

> Connecting to a database and getting data out — distinct from tuning it. Six independent graders all routed plain Postgres/Mongo/BigQuery connectors into `query-optimization`, whose label reads as EXPLAIN-plan work; that mismatch is what surfaced this gap.

Source: https://tashan.sh/task/database-access.html
Ranked by fit for the task, then how well it documents itself, then the tashan score
  (upkeep and freshness, gated by real adoption). Public evidence only — nothing paid can
  change a rank. Method: https://tashan.sh/methodology.html

## Ranked

| # | Capability | tashan score | Adoption evidence | Activity |
|---|---|---|---|---|
| 1 | [MongoDB](https://tashan.sh/capability/pkg-mongodb-mcp-server.html) | 84 | 73k/wk | active |
| 2 | [Supabase](https://tashan.sh/capability/pkg-supabase-mcp-server-supabase.html) | 99 | 115k/wk | active |
| 3 | [Dbhub](https://tashan.sh/capability/pkg-bytebase-dbhub.html) | 82 | 42k/wk | active |
| 4 | [Teable](https://tashan.sh/capability/pkg-teable-mcp.html) | 48 | 1k/wk | active |
| 5 | [NexQL Postgres](https://tashan.sh/capability/pkg-nexql-mcp.html) | 66 | 1k/wk | active |
| 6 | [Snowflake Development](https://tashan.sh/capability/skill-alirezarezvani-snowflake-development.html) | not scored | 1 repos | active |
| 7 | [SQL Database Assistant](https://tashan.sh/capability/skill-alirezarezvani-sql-database-assistant.html) | not scored | 1 repos | active |
| 8 | [Postgres · modelcontextprotocol](https://tashan.sh/capability/pkg-modelcontextprotocol-server-postgres.html) | not scored | 86k/wk | abandoned |
| 9 | [MySQL](https://tashan.sh/capability/pkg-benborla29-mcp-server-mysql.html) | 69 | 14k/wk | active |
| 10 | [Infrawise](https://tashan.sh/capability/pkg-infrawise.html) | 65 | 416/wk | active |
| 11 | [Mssql · vicagbasi](https://tashan.sh/capability/pkg-mssql-mcp-server.html) | 60 | 3k/wk | active |
| 12 | [SSH Manager](https://tashan.sh/capability/pkg-mcp-ssh-manager.html) | 60 | 596/wk | active |
| 13 | [Read Only Local Postgres](https://tashan.sh/capability/pkg-hovecapital-read-only-postgres-mcp-server.html) | 59 | 163/wk | active |
| 14 | [Mssql · BYMCS](https://tashan.sh/capability/pkg-mssql-mcp.html) | 56 | 664/wk | active |
| 15 | [Infino AI](https://tashan.sh/capability/pkg-infino-ai-mcp-server.html) | 55 | 180/wk | active |
| 16 | [Postgres · kristofer84](https://tashan.sh/capability/pkg-mcp-postgres.html) | 50 | 525/wk | active |
| 17 | [DB Access](https://tashan.sh/capability/pkg-rheopyrin-db-access-mcp.html) | 46 | 59/wk | active |
| 18 | [Postgres](https://tashan.sh/capability/pkg-henkey-postgres-mcp-server.html) | 71 | 1k/wk | active |
| 19 | [Run402](https://tashan.sh/capability/pkg-run402-mcp.html) | 70 | 4k/wk | active |
| 20 | [Read Only Local MySQL](https://tashan.sh/capability/pkg-hovecapital-read-only-mysql-mcp-server.html) | 65 | 203/wk | active |
| 21 | [DB Connect](https://tashan.sh/capability/pkg-mcp-db-connect.html) | 64 | 769/wk | active |
| 22 | [Mssql](https://tashan.sh/capability/pkg-connorbritain-mssql-mcp-server.html) | 63 | 516/wk | active |
| 23 | [PostgreSQL (hardened, read-only)](https://tashan.sh/capability/pkg-postgres-mcp-hardened.html) | 61 | 734/wk | active |
| 24 | [Sqemo](https://tashan.sh/capability/pkg-sqemo-mcp.html) | 61 | 316/wk | active |
| 25 | [Dm8](https://tashan.sh/capability/pkg-mcp-dm8-server.html) | 60 | 409/wk | active |
| 26 | [Ainative Postgres](https://tashan.sh/capability/pkg-ainative-postgres-mcp.html) | 57 | 632/wk | active |
| 27 | [SQLite · jparkerweb](https://tashan.sh/capability/pkg-mcp-sqlite.html) | 56 | 549/wk | active |
| 28 | [Redash](https://tashan.sh/capability/pkg-redash-mcp.html) | 56 | 398/wk | active |
| 29 | [Metaengine](https://tashan.sh/capability/pkg-metaengine-mcp-server.html) | 47 | 60/wk | active |
| 30 | [Androidapi](https://tashan.sh/capability/pkg-androidapi-mcp.html) | 44 | 55/wk | active |
| 31 | [Sqlike](https://tashan.sh/capability/pkg-sqlike-mcp.html) | 44 | 39/wk | active |
| 32 | [Dynoxide](https://tashan.sh/capability/pkg-dynoxide.html) | 70 | 5k/wk | active |
| 33 | [SQL Preview](https://tashan.sh/capability/pkg-sql-preview.html) | 68 | 782/wk | active |
| 34 | [Data Studio](https://tashan.sh/capability/pkg-geek-fun-data-studio-mcp.html) | 67 | 460/wk | active |
| 35 | [SAP HANA CLI](https://tashan.sh/capability/pkg-hana-cli.html) | 63 | 1k/wk | active |
| 36 | [Seedfast](https://tashan.sh/capability/pkg-seedfast.html) | 62 | 421/wk | active |
| 37 | [Mongo](https://tashan.sh/capability/pkg-mcp-mongo-server.html) | 61 | 649/wk | active |
| 38 | [MySQL · berthojoris](https://tashan.sh/capability/pkg-berthojoris-mcp-mysql-server.html) | 61 | 509/wk | active |
| 39 | [DB Gateway](https://tashan.sh/capability/pkg-db-gateway.html) | 60 | 533/wk | active |
| 40 | [Sap Abap SQL](https://tashan.sh/capability/pkg-sap-abap-sql-mcp.html) | 58 | 440/wk | active |

Showing the top 40 of 50. The full ranked shelf is at https://tashan.sh/task/database-access.html.

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
