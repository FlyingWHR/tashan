# What to use for query optimisation

> 'Tuning'; the artifact is an EXPLAIN plan. NOT plain database access — see `database-access`.

Source: https://tashan.sh/task/query-optimization.html
Ranked by fit for the task, then how well it documents itself, then the tashan score
  (upkeep and freshness, gated by real adoption). Public evidence only — nothing paid can
  change a rank. Method: https://tashan.sh/methodology.html

## Ranked

| # | Capability | tashan score | Adoption evidence | Activity |
|---|---|---|---|---|
| 1 | [DuckDB Skills](https://tashan.sh/capability/plugin-duckdb-duckdb-skills-duckdb-skills.html) | 56 | 523 ★ | stable |
| 2 | [Cockroachdb](https://tashan.sh/capability/plugin-cockroachdb-claude-plugin-cockroachdb.html) | 44 | 3 ★ | active |
| 3 | [Whodb](https://tashan.sh/capability/plugin-clidey-whodb-whodb.html) | 65 | 5k ★ | active |
| 4 | [ClickHouse Best Practices](https://tashan.sh/capability/plugin-clickhouse-agent-skills-clickhouse-best-practices.html) | 61 | 498 ★ | active |
| 5 | [Codspeed](https://tashan.sh/capability/plugin-codspeedhq-codspeed-codspeed.html) | 59 | 235 ★ | active |
| 6 | [Data Agent Kit Starter Pack](https://tashan.sh/capability/plugin-gemini-cli-extensions-data-agent-kit-starter-pack-data-agent-kit-starter-pack.html) | 57 | 151 ★ | active |
| 7 | [Dataverse · microsoft](https://tashan.sh/capability/plugin-microsoft-dataverse-skills-dataverse.html) | 57 | 184 ★ | active |
| 8 | [Geosql](https://tashan.sh/capability/plugin-dekart-xyz-geosql-geosql.html) | 57 | 558 ★ | active |
| 9 | [Neon](https://tashan.sh/capability/plugin-neondatabase-agent-skills-neon.html) | 55 | 81 ★ | active |
| 10 | [Cloud SQL PostgreSQL](https://tashan.sh/capability/plugin-gemini-cli-extensions-cloud-sql-postgresql-cloud-sql-postgresql.html) | 51 | 41 ★ | active |
| 11 | [Alloydb](https://tashan.sh/capability/plugin-gemini-cli-extensions-alloydb-alloydb.html) | 50 | 22 ★ | active |
| 12 | [BigQuery Data Analytics](https://tashan.sh/capability/plugin-gemini-cli-extensions-bigquery-data-analytics-bigquery-data-analytics.html) | 50 | 47 ★ | active |
| 13 | [Cloud SQL MySQL](https://tashan.sh/capability/plugin-gemini-cli-extensions-cloud-sql-mysql-cloud-sql-mysql.html) | 46 | 11 ★ | active |
| 14 | [Cloud SQL Sqlserver](https://tashan.sh/capability/plugin-gemini-cli-extensions-cloud-sql-sqlserver-cloud-sql-sqlserver.html) | 44 | 7 ★ | active |
| 15 | [Alloydb Omni](https://tashan.sh/capability/plugin-gemini-cli-extensions-alloydb-omni-alloydb-omni.html) | 42 | 4 ★ | active |
| 16 | [Azure Cosmos DB Assistant](https://tashan.sh/capability/plugin-azurecosmosdb-cosmosdb-claude-code-plugin-azure-cosmos-db-assistant.html) | 40 | 2 ★ | active |
| 17 | [Sap Sqlscript](https://tashan.sh/capability/plugin-andreafusar-https-github-com-secondsky-sap-skills-sap-sqlscript.html) | 42 | 1 marketplaces | — |
| 18 | [MongoDB · mongodb](https://tashan.sh/capability/plugin-mongodb-agent-skills-mongodb.html) | 57 | 164 ★ | active |
| 19 | [Firestore Native](https://tashan.sh/capability/plugin-gemini-cli-extensions-firestore-native-firestore-native.html) | 50 | 30 ★ | active |
| 20 | [Spanner](https://tashan.sh/capability/plugin-gemini-cli-extensions-spanner-spanner.html) | 49 | 19 ★ | active |
| 21 | [Oracledb](https://tashan.sh/capability/plugin-gemini-cli-extensions-oracledb-oracledb.html) | 47 | 10 ★ | active |
| 22 | [ClickHouse · clickhouse](https://tashan.sh/capability/plugin-clickhouse-clickhouse-claude-code-plugin-clickhouse.html) | 45 | 5 ★ | active |
| 23 | [Bigtable](https://tashan.sh/capability/plugin-googlecloudplatform-cloud-bigtable-ecosystem-bigtable.html) | 44 | 20 ★ | active |
| 24 | [Azure SQL Developer](https://tashan.sh/capability/plugin-microsoft-azure-sql-database-container-azure-sql-developer.html) | 42 | 6 ★ | active |
| 25 | [Supabase · supabase-community](https://tashan.sh/capability/plugin-supabase-community-supabase-plugin-supabase.html) | 41 | 9 ★ | active |
| 26 | [Planetscale](https://tashan.sh/capability/plugin-planetscale-claude-plugin-planetscale.html) | 40 | 4 ★ | active |
| 27 | [Scylladb](https://tashan.sh/capability/plugin-scylladb-agent-skills-scylladb.html) | 40 | 6 ★ | active |
| 28 | [Altimate Code](https://tashan.sh/capability/plugin-altimateai-altimate-claude-plugin-altimate-code.html) | 36 | 3 ★ | active |
| 29 | [PostgreSQL](https://tashan.sh/capability/pkg-yawlabs-postgres-mcp.html) | 71 | 3k/wk | active |
| 30 | [Prodcheck](https://tashan.sh/capability/pkg-prodcheck.html) | 50 | 282/wk | active |
| 31 | [Sqlserver](https://tashan.sh/capability/pkg-cevelas-mcp-sqlserver.html) | 40 | 82/wk | active |

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
