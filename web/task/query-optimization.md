# What to use for query optimisation

> 'Tuning'; the artifact is an EXPLAIN plan. NOT plain database access — see `database-access`.

Source: https://tashan.sh/task/query-optimization.html
Ranked by fit for the task, then how well it documents itself, then the tashan score
  (upkeep and freshness, gated by real adoption). Public evidence only — nothing paid can
  change a rank. Method: https://tashan.sh/methodology.html

## Ranked

| # | Capability | tashan score | Adoption evidence | Activity |
|---|---|---|---|---|
| 1 | [DuckDB Skills](https://tashan.sh/capability/plugin-duckdb-duckdb-skills-duckdb-skills.html) | 59 | 523 ★ | active |
| 2 | [Cockroachdb](https://tashan.sh/capability/plugin-cockroachdb-claude-plugin-cockroachdb.html) | 53 | 3 ★ | active |
| 3 | [Whodb](https://tashan.sh/capability/plugin-clidey-whodb-whodb.html) | 73 | 5k ★ | active |
| 4 | [ClickHouse Best Practices](https://tashan.sh/capability/plugin-clickhouse-agent-skills-clickhouse-best-practices.html) | 71 | 498 ★ | active |
| 5 | [Codspeed](https://tashan.sh/capability/plugin-codspeedhq-codspeed-codspeed.html) | 69 | 235 ★ | active |
| 6 | [Dataverse · microsoft](https://tashan.sh/capability/plugin-microsoft-dataverse-skills-dataverse.html) | 69 | 184 ★ | active |
| 7 | [Data Agent Kit Starter Pack](https://tashan.sh/capability/plugin-gemini-cli-extensions-data-agent-kit-starter-pack-data-agent-kit-starter-pack.html) | 68 | 151 ★ | active |
| 8 | [Geosql](https://tashan.sh/capability/plugin-dekart-xyz-geosql-geosql.html) | 68 | 558 ★ | active |
| 9 | [Neon](https://tashan.sh/capability/plugin-neondatabase-agent-skills-neon.html) | 66 | 81 ★ | active |
| 10 | [BigQuery Data Analytics](https://tashan.sh/capability/plugin-gemini-cli-extensions-bigquery-data-analytics-bigquery-data-analytics.html) | 60 | 47 ★ | active |
| 11 | [Cloud SQL PostgreSQL](https://tashan.sh/capability/plugin-gemini-cli-extensions-cloud-sql-postgresql-cloud-sql-postgresql.html) | 60 | 41 ★ | active |
| 12 | [Alloydb](https://tashan.sh/capability/plugin-gemini-cli-extensions-alloydb-alloydb.html) | 59 | 22 ★ | active |
| 13 | [Cloud SQL MySQL](https://tashan.sh/capability/plugin-gemini-cli-extensions-cloud-sql-mysql-cloud-sql-mysql.html) | 55 | 11 ★ | active |
| 14 | [Cloud SQL Sqlserver](https://tashan.sh/capability/plugin-gemini-cli-extensions-cloud-sql-sqlserver-cloud-sql-sqlserver.html) | 53 | 7 ★ | active |
| 15 | [Alloydb Omni](https://tashan.sh/capability/plugin-gemini-cli-extensions-alloydb-omni-alloydb-omni.html) | 50 | 4 ★ | active |
| 16 | [Azure Cosmos DB Assistant](https://tashan.sh/capability/plugin-azurecosmosdb-cosmosdb-claude-code-plugin-azure-cosmos-db-assistant.html) | 48 | 2 ★ | active |
| 17 | [Database Designer](https://tashan.sh/capability/skill-alirezarezvani-database-designer.html) | 44 | 2 repos | active |
| 18 | [Performance Profiler](https://tashan.sh/capability/skill-alirezarezvani-performance-profiler.html) | 44 | 2 repos | active |
| 19 | [SQL Database Assistant](https://tashan.sh/capability/skill-alirezarezvani-sql-database-assistant.html) | 44 | 2 repos | active |
| 20 | [MongoDB · mongodb](https://tashan.sh/capability/plugin-mongodb-agent-skills-mongodb.html) | 68 | 164 ★ | active |
| 21 | [Firestore Native](https://tashan.sh/capability/plugin-gemini-cli-extensions-firestore-native-firestore-native.html) | 61 | 30 ★ | active |
| 22 | [Spanner](https://tashan.sh/capability/plugin-gemini-cli-extensions-spanner-spanner.html) | 58 | 19 ★ | active |
| 23 | [Oracledb](https://tashan.sh/capability/plugin-gemini-cli-extensions-oracledb-oracledb.html) | 56 | 10 ★ | active |
| 24 | [ClickHouse · clickhouse](https://tashan.sh/capability/plugin-clickhouse-clickhouse-claude-code-plugin-clickhouse.html) | 54 | 5 ★ | active |
| 25 | [Bigtable](https://tashan.sh/capability/plugin-googlecloudplatform-cloud-bigtable-ecosystem-bigtable.html) | 54 | 20 ★ | active |
| 26 | [Azure SQL Developer](https://tashan.sh/capability/plugin-microsoft-azure-sql-database-container-azure-sql-developer.html) | 51 | 6 ★ | active |
| 27 | [Supabase · supabase-community](https://tashan.sh/capability/plugin-supabase-community-supabase-plugin-supabase.html) | 50 | 9 ★ | active |
| 28 | [Planetscale](https://tashan.sh/capability/plugin-planetscale-claude-plugin-planetscale.html) | 49 | 4 ★ | active |
| 29 | [Scylladb](https://tashan.sh/capability/plugin-scylladb-agent-skills-scylladb.html) | 48 | 6 ★ | active |
| 30 | [Altimate Code](https://tashan.sh/capability/plugin-altimateai-altimate-claude-plugin-altimate-code.html) | 44 | 3 ★ | active |
| 31 | [Prodcheck](https://tashan.sh/capability/pkg-prodcheck.html) | 69 | 2k/wk | active |
| 32 | [Sqlserver](https://tashan.sh/capability/pkg-cevelas-mcp-sqlserver.html) | 51 | 82/wk | active |

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
