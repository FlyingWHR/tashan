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
| 8 | [Aiven](https://tashan.sh/capability/pkg-mcp-aiven.html) | 69 | 289/wk | active |
| 9 | [Run402](https://tashan.sh/capability/pkg-run402-mcp.html) | 72 | 4k/wk | active |
| 10 | [Dynoxide](https://tashan.sh/capability/pkg-dynoxide.html) | 71 | 5k/wk | active |
| 11 | [SAP HANA CLI](https://tashan.sh/capability/pkg-hana-cli.html) | 67 | 1k/wk | active |
| 12 | [Wr Admin Mcp Connector](https://tashan.sh/capability/pkg-wr-admin-mcp-connector.html) | 66 | 992/wk | active |
| 13 | [Sqemo](https://tashan.sh/capability/pkg-sqemo-mcp.html) | 64 | 477/wk | active |
| 14 | [Stackql](https://tashan.sh/capability/pkg-stackql-mcp-server.html) | 61 | 179/wk | active |
| 15 | [Ravendb](https://tashan.sh/capability/pkg-ravendb-mcp.html) | 57 | 224/wk | active |
| 16 | [Metaengine](https://tashan.sh/capability/pkg-metaengine-mcp-server.html) | 52 | 86/wk | active |
| 17 | [Panini Connector](https://tashan.sh/capability/pkg-panini-connector-mcp.html) | 51 | 96/wk | active |
| 18 | [Lintbase](https://tashan.sh/capability/pkg-lintbase-mcp.html) | 50 | 68/wk | active |
| 19 | [DB Access](https://tashan.sh/capability/pkg-rheopyrin-db-access-mcp.html) | 49 | 57/wk | active |
| 20 | [Drawdb](https://tashan.sh/capability/pkg-drawdb-mcp.html) | 48 | 46/wk | active |
| 21 | [Dev Lifecycle](https://tashan.sh/capability/plugin-eblouin-development-eblouin-plugins-dev-lifecycle.html) | 47 | 1 ★ | active |
| 22 | [Ainative Zerodb](https://tashan.sh/capability/pkg-ainative-zerodb-mcp-server.html) | 47 | 30/wk | active |
| 23 | [Sqlike](https://tashan.sh/capability/pkg-sqlike-mcp.html) | 46 | 39/wk | active |
| 24 | [Kysely SQL](https://tashan.sh/capability/plugin-kingstinct-github-kysely-sql.html) | 45 | 1 marketplaces | active |
| 25 | [Alpacacloud](https://tashan.sh/capability/pkg-alpacacloud-mcp.html) | 45 | 52/wk | active |
| 26 | [Breezedeploy](https://tashan.sh/capability/pkg-breezedeploy-mcp.html) | 45 | 31/wk | active |
| 27 | [SQL · abhishekmcp](https://tashan.sh/capability/pkg-abhishekmcp-sql.html) | 44 | 52/wk | active |
| 28 | [Bach Snowflake](https://tashan.sh/capability/pkg-bach-snowflake-mcp.html) | 44 | 31/wk | active |
| 29 | [Taxonomy Creation](https://tashan.sh/capability/plugin-danielrosehill-claude-code-plugins-taxonomy-creation.html) | 41 | 1 marketplaces | active |
| 30 | [Supabase · lucasmccomb](https://tashan.sh/capability/plugin-lucasmccomb-ccgm-supabase.html) | 37 | 1 marketplaces | active |
| 31 | [Sqlfmt](https://tashan.sh/capability/pkg-mukundakatta-sqlfmt-mcp.html) | 36 | 36/wk | active |
| 32 | [Universal DB Client](https://tashan.sh/capability/pkg-izumisy-mcp-universal-db-client.html) | 31 | 17/wk | active |
| 33 | [Local Wp](https://tashan.sh/capability/pkg-verygoodplugins-mcp-local-wp.html) | 30 | 31/wk | abandoned |
| 34 | [Dynamo Expert](https://tashan.sh/capability/plugin-walis85300-marketplace-dynamo-expert.html) | 14 | 1 marketplaces | — |
| 35 | [Shopify Database Specialist](https://tashan.sh/capability/plugin-sarojpunde-shopify-dev-toolkit-claude-plugins-shopify-database-specialist.html) | 14 | 1 marketplaces | — |
| 36 | [Monitor](https://tashan.sh/capability/pkg-betterdb-mcp.html) | 60 | 247/wk | active |

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
