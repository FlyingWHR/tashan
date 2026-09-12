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
| 3 | [Dbhub](https://tashan.sh/capability/pkg-bytebase-dbhub.html) | 80 | 16k/wk | active |
| 4 | [NexQL Postgres](https://tashan.sh/capability/pkg-nexql-mcp.html) | 60 | 367/wk | active |
| 5 | [Snowflake Development](https://tashan.sh/capability/skill-alirezarezvani-snowflake-development.html) | 44 | 2 repos | active |
| 6 | [SQL Database Assistant](https://tashan.sh/capability/skill-alirezarezvani-sql-database-assistant.html) | 44 | 2 repos | active |
| 7 | [Postgres · modelcontextprotocol](https://tashan.sh/capability/pkg-modelcontextprotocol-server-postgres.html) | not scored | 95k/wk | abandoned |
| 8 | [MySQL](https://tashan.sh/capability/pkg-benborla29-mcp-server-mysql.html) | 65 | 11k/wk | active |
| 9 | [Infrawise](https://tashan.sh/capability/pkg-infrawise.html) | 61 | 416/wk | active |
| 10 | [Mssql · vicagbasi](https://tashan.sh/capability/pkg-mssql-mcp-server.html) | 56 | 2k/wk | active |
| 11 | [Read Only Local Postgres](https://tashan.sh/capability/pkg-hovecapital-read-only-postgres-mcp-server.html) | 56 | 163/wk | active |
| 12 | [Mssql · BYMCS](https://tashan.sh/capability/pkg-mssql-mcp.html) | 53 | 664/wk | active |
| 13 | [Infino AI](https://tashan.sh/capability/pkg-infino-ai-mcp-server.html) | 52 | 180/wk | active |
| 14 | [Postgres · kristofer84](https://tashan.sh/capability/pkg-mcp-postgres.html) | 49 | 793/wk | active |
| 15 | [Run402](https://tashan.sh/capability/pkg-run402-mcp.html) | 72 | 4k/wk | active |
| 16 | [Postgres · henkey](https://tashan.sh/capability/pkg-henkey-postgres-mcp-server.html) | 69 | 1k/wk | active |
| 17 | [PostgreSQL (hardened, read-only)](https://tashan.sh/capability/pkg-postgres-mcp-hardened.html) | 61 | 799/wk | active |
| 18 | [Read Only Local MySQL](https://tashan.sh/capability/pkg-hovecapital-read-only-mysql-mcp-server.html) | 61 | 203/wk | active |
| 19 | [Mssql](https://tashan.sh/capability/pkg-connorbritain-mssql-mcp-server.html) | 60 | 516/wk | active |
| 20 | [Sqemo](https://tashan.sh/capability/pkg-sqemo-mcp.html) | 58 | 316/wk | active |
| 21 | [Dm8](https://tashan.sh/capability/pkg-mcp-dm8-server.html) | 57 | 409/wk | active |
| 22 | [SQLite · jparkerweb](https://tashan.sh/capability/pkg-mcp-sqlite.html) | 54 | 549/wk | active |
| 23 | [Ainative Postgres](https://tashan.sh/capability/pkg-ainative-postgres-mcp.html) | 53 | 632/wk | active |
| 24 | [Redash · seob717](https://tashan.sh/capability/pkg-redash-mcp.html) | 53 | 398/wk | active |
| 25 | [DB Connect](https://tashan.sh/capability/pkg-mcp-db-connect.html) | 53 | 142/wk | active |
| 26 | [Metaengine](https://tashan.sh/capability/pkg-metaengine-mcp-server.html) | 45 | 60/wk | active |
| 27 | [Runner](https://tashan.sh/capability/pkg-synapsor-runner.html) | 67 | 1k/wk | active |
| 28 | [SQL Preview](https://tashan.sh/capability/pkg-sql-preview.html) | 64 | 782/wk | active |
| 29 | [Data Studio](https://tashan.sh/capability/pkg-geek-fun-data-studio-mcp.html) | 63 | 460/wk | active |
| 30 | [SAP HANA CLI](https://tashan.sh/capability/pkg-hana-cli.html) | 60 | 1k/wk | active |
| 31 | [Seedfast](https://tashan.sh/capability/pkg-seedfast.html) | 59 | 421/wk | active |
| 32 | [Mongo](https://tashan.sh/capability/pkg-mcp-mongo-server.html) | 58 | 649/wk | active |
| 33 | [MySQL · berthojoris](https://tashan.sh/capability/pkg-berthojoris-mcp-mysql-server.html) | 58 | 509/wk | active |
| 34 | [DB](https://tashan.sh/capability/pkg-paretools-db.html) | 58 | 212/wk | active |
| 35 | [QuestDB Web Console](https://tashan.sh/capability/pkg-questdb-mcp-server-questdb.html) | 58 | 101/wk | active |
| 36 | [Mssql · piyapat](https://tashan.sh/capability/pkg-piyapat-mssql-mcp-server.html) | 57 | 370/wk | active |
| 37 | [Motherduck Skills](https://tashan.sh/capability/plugin-motherduckdb-agent-skills-motherduck-skills.html) | 56 | 53 ★ | active |
| 38 | [DB Gateway](https://tashan.sh/capability/pkg-db-gateway.html) | 56 | 533/wk | active |
| 39 | [Ae](https://tashan.sh/capability/pkg-ae-mcp-jkdg.html) | 56 | 394/wk | active |
| 40 | [Midplane](https://tashan.sh/capability/pkg-midplane.html) | 56 | 387/wk | active |

Showing the top 40 of 54. The full ranked shelf is at https://tashan.sh/task/database-access.html.

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
