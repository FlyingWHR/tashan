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
| 2 | [Supabase](https://tashan.sh/capability/pkg-supabase-mcp-server-supabase.html) | 94 | 78k/wk | active |
| 3 | [Dbhub](https://tashan.sh/capability/pkg-bytebase-dbhub.html) | 82 | 42k/wk | active |
| 4 | [Teable](https://tashan.sh/capability/pkg-teable-mcp.html) | 48 | 1k/wk | active |
| 5 | [NexQL Postgres](https://tashan.sh/capability/pkg-nexql-mcp.html) | 66 | 1k/wk | active |
| 6 | [Sap Hana CLI](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-hana-cli.html) | 42 | 1 marketplaces | — |
| 7 | [Sap Sqlscript](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-sqlscript.html) | 42 | 1 marketplaces | — |
| 8 | [Idmp Plugin](https://tashan.sh/capability/plugin-taosdata-agent-skills-idmp-plugin.html) | 41 | 2 ★ | active |
| 9 | [Ts Ddd Repository](https://tashan.sh/capability/plugin-llodev-skills-ts-ddd-repository.html) | 41 | 1 marketplaces | active |
| 10 | [Ts Query Cqrs](https://tashan.sh/capability/plugin-llodev-skills-ts-query-cqrs.html) | 41 | 1 marketplaces | active |
| 11 | [Snowflake Development](https://tashan.sh/capability/skill-alirezarezvani-snowflake-development.html) | not scored | 1 repos | active |
| 12 | [SQL Database Assistant](https://tashan.sh/capability/skill-alirezarezvani-sql-database-assistant.html) | not scored | 1 repos | active |
| 13 | [Postgres · modelcontextprotocol](https://tashan.sh/capability/pkg-modelcontextprotocol-server-postgres.html) | not scored | 86k/wk | abandoned |
| 14 | [MySQL](https://tashan.sh/capability/pkg-benborla29-mcp-server-mysql.html) | 68 | 12k/wk | active |
| 15 | [Infrawise](https://tashan.sh/capability/pkg-infrawise.html) | 65 | 416/wk | active |
| 16 | [Mssql · vicagbasi](https://tashan.sh/capability/pkg-mssql-mcp-server.html) | 60 | 3k/wk | active |
| 17 | [SSH Manager](https://tashan.sh/capability/pkg-mcp-ssh-manager.html) | 60 | 596/wk | active |
| 18 | [Read Only Local Postgres](https://tashan.sh/capability/pkg-hovecapital-read-only-postgres-mcp-server.html) | 59 | 163/wk | active |
| 19 | [Mssql · BYMCS](https://tashan.sh/capability/pkg-mssql-mcp.html) | 56 | 664/wk | active |
| 20 | [Infino AI](https://tashan.sh/capability/pkg-infino-ai-mcp-server.html) | 56 | 180/wk | active |
| 21 | [Postgres · kristofer84](https://tashan.sh/capability/pkg-mcp-postgres.html) | 50 | 525/wk | active |
| 22 | [DB Access](https://tashan.sh/capability/pkg-rheopyrin-db-access-mcp.html) | 47 | 59/wk | active |
| 23 | [Postgres](https://tashan.sh/capability/pkg-henkey-postgres-mcp-server.html) | 71 | 1k/wk | active |
| 24 | [Run402](https://tashan.sh/capability/pkg-run402-mcp.html) | 70 | 4k/wk | active |
| 25 | [Read Only Local MySQL](https://tashan.sh/capability/pkg-hovecapital-read-only-mysql-mcp-server.html) | 65 | 203/wk | active |
| 26 | [DB Connect](https://tashan.sh/capability/pkg-mcp-db-connect.html) | 64 | 769/wk | active |
| 27 | [Mssql](https://tashan.sh/capability/pkg-connorbritain-mssql-mcp-server.html) | 63 | 516/wk | active |
| 28 | [PostgreSQL (hardened, read-only)](https://tashan.sh/capability/pkg-postgres-mcp-hardened.html) | 62 | 734/wk | active |
| 29 | [Sqemo](https://tashan.sh/capability/pkg-sqemo-mcp.html) | 62 | 316/wk | active |
| 30 | [Dm8](https://tashan.sh/capability/pkg-mcp-dm8-server.html) | 60 | 409/wk | active |
| 31 | [Ainative Postgres](https://tashan.sh/capability/pkg-ainative-postgres-mcp.html) | 57 | 632/wk | active |
| 32 | [Redash](https://tashan.sh/capability/pkg-redash-mcp.html) | 57 | 398/wk | active |
| 33 | [SQLite · jparkerweb](https://tashan.sh/capability/pkg-mcp-sqlite.html) | 56 | 549/wk | active |
| 34 | [Metaengine](https://tashan.sh/capability/pkg-metaengine-mcp-server.html) | 48 | 60/wk | active |
| 35 | [Androidapi](https://tashan.sh/capability/pkg-androidapi-mcp.html) | 44 | 55/wk | active |
| 36 | [Sqlike](https://tashan.sh/capability/pkg-sqlike-mcp.html) | 44 | 39/wk | active |
| 37 | [Dynoxide](https://tashan.sh/capability/pkg-dynoxide.html) | 70 | 5k/wk | active |
| 38 | [SQL Preview](https://tashan.sh/capability/pkg-sql-preview.html) | 68 | 782/wk | active |
| 39 | [Data Studio](https://tashan.sh/capability/pkg-geek-fun-data-studio-mcp.html) | 67 | 460/wk | active |
| 40 | [SAP HANA CLI](https://tashan.sh/capability/pkg-hana-cli.html) | 64 | 1k/wk | active |

Showing the top 40 of 58. The full ranked shelf is at https://tashan.sh/task/database-access.html.

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
