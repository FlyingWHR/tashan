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
| 4 | [Supabase · Cappahccino](https://tashan.sh/capability/pkg-supabase-mcp.html) | 23 | 3k/wk | abandoned |
| 5 | [Idmp Plugin](https://tashan.sh/capability/plugin-taosdata-agent-skills-idmp-plugin.html) | 43 | 2 ★ | active |
| 6 | [Ts Ddd Repository](https://tashan.sh/capability/plugin-llodev-skills-ts-ddd-repository.html) | 42 | 1 marketplaces | active |
| 7 | [Ts Query Cqrs](https://tashan.sh/capability/plugin-llodev-skills-ts-query-cqrs.html) | 42 | 1 marketplaces | active |
| 8 | [Sap Hana CLI](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-hana-cli.html) | 42 | 1 marketplaces | — |
| 9 | [Sap Sqlscript](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-sqlscript.html) | 42 | 1 marketplaces | — |
| 10 | [SQLite Npx](https://tashan.sh/capability/pkg-mcp-server-sqlite-npx.html) | 38 | 3k/wk | abandoned |
| 11 | [Snowflake Development](https://tashan.sh/capability/skill-alirezarezvani-snowflake-development.html) | not scored | 1 repos | active |
| 12 | [SQL Database Assistant](https://tashan.sh/capability/skill-alirezarezvani-sql-database-assistant.html) | not scored | 1 repos | active |
| 13 | [Postgres · modelcontextprotocol](https://tashan.sh/capability/pkg-modelcontextprotocol-server-postgres.html) | not scored | 121k/wk | abandoned |
| 14 | [MySQL](https://tashan.sh/capability/pkg-benborla29-mcp-server-mysql.html) | 69 | 12k/wk | active |
| 15 | [Mssql · vicagbasi](https://tashan.sh/capability/pkg-mssql-mcp-server.html) | 62 | 3k/wk | active |
| 16 | [Read Only Local Postgres](https://tashan.sh/capability/pkg-hovecapital-read-only-postgres-mcp-server.html) | 61 | 163/wk | active |
| 17 | [Snowflake · mikdanjey](https://tashan.sh/capability/pkg-snowflake-mcp-server.html) | 24 | 3k/wk | abandoned |
| 18 | [Postgres](https://tashan.sh/capability/pkg-henkey-postgres-mcp-server.html) | 73 | 2k/wk | active |
| 19 | [Run402](https://tashan.sh/capability/pkg-run402-mcp.html) | 71 | 4k/wk | active |
| 20 | [Read Only Local MySQL](https://tashan.sh/capability/pkg-hovecapital-read-only-mysql-mcp-server.html) | 67 | 203/wk | active |
| 21 | [Mssql](https://tashan.sh/capability/pkg-connorbritain-mssql-mcp-server.html) | 66 | 779/wk | active |
| 22 | [SQLite · jparkerweb](https://tashan.sh/capability/pkg-mcp-sqlite.html) | 60 | 896/wk | active |
| 23 | [Dynoxide](https://tashan.sh/capability/pkg-dynoxide.html) | 71 | 5k/wk | active |
| 24 | [SAP HANA CLI](https://tashan.sh/capability/pkg-hana-cli.html) | 66 | 1k/wk | active |
| 25 | [DB Connect](https://tashan.sh/capability/pkg-mcp-db-connect.html) | 66 | 769/wk | active |
| 26 | [Infrawise](https://tashan.sh/capability/pkg-infrawise.html) | 66 | 729/wk | active |
| 27 | [Mssql Reader](https://tashan.sh/capability/pkg-connorbritain-mssql-mcp-reader.html) | 65 | 1k/wk | active |
| 28 | [Wr Admin Mcp Connector](https://tashan.sh/capability/pkg-wr-admin-mcp-connector.html) | 65 | 992/wk | active |
| 29 | [Seedfast](https://tashan.sh/capability/pkg-seedfast.html) | 64 | 421/wk | active |
| 30 | [PostgreSQL (hardened, read-only)](https://tashan.sh/capability/pkg-postgres-mcp-hardened.html) | 63 | 734/wk | active |
| 31 | [Mongo](https://tashan.sh/capability/pkg-mcp-mongo-server.html) | 63 | 649/wk | active |
| 32 | [Sqemo](https://tashan.sh/capability/pkg-sqemo-mcp.html) | 63 | 477/wk | active |
| 33 | [Dm8](https://tashan.sh/capability/pkg-mcp-dm8-server.html) | 63 | 409/wk | active |
| 34 | [SSH Manager](https://tashan.sh/capability/pkg-mcp-ssh-manager.html) | 62 | 596/wk | active |
| 35 | [SQL Preview](https://tashan.sh/capability/pkg-sql-preview.html) | 62 | 345/wk | active |
| 36 | [Ainative Postgres](https://tashan.sh/capability/pkg-ainative-postgres-mcp.html) | 59 | 632/wk | active |
| 37 | [Mssql · BYMCS](https://tashan.sh/capability/pkg-mssql-mcp.html) | 58 | 664/wk | active |
| 38 | [Redash](https://tashan.sh/capability/pkg-redash-mcp.html) | 58 | 398/wk | active |
| 39 | [Infino AI](https://tashan.sh/capability/pkg-infino-ai-mcp-server.html) | 57 | 180/wk | active |
| 40 | [Schema Designer](https://tashan.sh/capability/pkg-mcp-schema-designer.html) | 53 | 132/wk | active |

Showing the top 40 of 58. The full ranked shelf is at https://tashan.sh/task/database-access.html.

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
