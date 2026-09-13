# What a devops / sre should install

> Capabilities measured for the work a devops / sre does.

Source: https://tashan.sh/role/devops.html
Ranked by fit for the task, then how well it documents itself, then the tashan score
  (upkeep and freshness, gated by real adoption). Public evidence only — nothing paid can
  change a rank. Method: https://tashan.sh/methodology.html

## The short answer

- **Infrastructure and deployment** — [Argocd](https://tashan.sh/capability/pkg-argocd-mcp.html) · tashan score 77
- **Observability** — [Smartbear](https://tashan.sh/capability/pkg-smartbear-mcp.html) · tashan score 79
- **Incident response** — [Sentry CLI](https://tashan.sh/capability/plugin-getsentry-cli-sentry-cli.html) · tashan score 67

## Ranked

| # | Capability | tashan score | Adoption evidence | Activity |
|---|---|---|---|---|
| 1 | [Argocd](https://tashan.sh/capability/pkg-argocd-mcp.html) | 77 | 13k/wk | active |
| 2 | [Auth0](https://tashan.sh/capability/pkg-auth0-auth0-mcp-server.html) | 74 | 4k/wk | active |
| 3 | [Vercel](https://tashan.sh/capability/plugin-vercel-vercel-plugin-vercel.html) | 70 | 246 ★ | active |
| 4 | [Zscaler](https://tashan.sh/capability/plugin-zscaler-zscaler-mcp-server-zscaler.html) | 63 | 41 ★ | active |
| 5 | [Langfuse Observability](https://tashan.sh/capability/plugin-langfuse-claude-observability-plugin-langfuse-observability.html) | 58 | 15 ★ | active |
| 6 | [Cockroachdb](https://tashan.sh/capability/plugin-cockroachdb-claude-plugin-cockroachdb.html) | 53 | 3 ★ | active |
| 7 | [Jfrog](https://tashan.sh/capability/plugin-jfrog-claude-plugin-jfrog.html) | 47 | 4 ★ | active |
| 8 | [Local CI](https://tashan.sh/capability/plugin-mrpuls-local-ci-local-ci.html) | 41 | 3 ★ | active |
| 9 | [Smartbear](https://tashan.sh/capability/pkg-smartbear-mcp.html) | 79 | 10k/wk | active |
| 10 | [Expo](https://tashan.sh/capability/plugin-expo-skills-expo.html) | 75 | 2k ★ | active |
| 11 | [SSH — policy-gated remote access](https://tashan.sh/capability/pkg-ssh-mcp.html) | 74 | 12k/wk | active |
| 12 | [Azure · microsoft](https://tashan.sh/capability/plugin-microsoft-azure-skills-azure.html) | 73 | 1k ★ | active |
| 13 | [Dokploy](https://tashan.sh/capability/pkg-dokploy-mcp.html) | 73 | 9k/wk | active |
| 14 | [Rustunnel](https://tashan.sh/capability/plugin-joaoh82-rustunnel-rustunnel.html) | 69 | 643 ★ | active |
| 15 | [Sentry CLI](https://tashan.sh/capability/plugin-getsentry-cli-sentry-cli.html) | 67 | 101 ★ | active |
| 16 | [Neon](https://tashan.sh/capability/plugin-neondatabase-agent-skills-neon.html) | 66 | 81 ★ | active |
| 17 | [Motus](https://tashan.sh/capability/plugin-lithos-ai-motus-motus.html) | 66 | 482 ★ | active |
| 18 | [Dynatrace Managed](https://tashan.sh/capability/pkg-dynatrace-oss-dynatrace-managed-mcp-server.html) | 66 | 425/wk | active |
| 19 | [Teamcity CLI](https://tashan.sh/capability/plugin-jetbrains-teamcity-cli-teamcity-cli.html) | 65 | 119 ★ | active |
| 20 | [Posthog](https://tashan.sh/capability/plugin-posthog-ai-plugin-posthog.html) | 64 | 64 ★ | active |
| 21 | [Defang](https://tashan.sh/capability/plugin-defanglabs-defang-defang.html) | 63 | 163 ★ | active |
| 22 | [Mlflow](https://tashan.sh/capability/plugin-mlflow-skills-mlflow.html) | 61 | 61 ★ | active |
| 23 | [Cloud SQL PostgreSQL](https://tashan.sh/capability/plugin-gemini-cli-extensions-cloud-sql-postgresql-cloud-sql-postgresql.html) | 60 | 41 ★ | active |
| 24 | [Alloydb](https://tashan.sh/capability/plugin-gemini-cli-extensions-alloydb-alloydb.html) | 59 | 22 ★ | active |
| 25 | [Autocode](https://tashan.sh/capability/plugin-ilang-ai-autocode-autocode.html) | 56 | 85 ★ | active |
| 26 | [Insforge](https://tashan.sh/capability/plugin-insforge-insforge-skills-insforge.html) | 56 | 33 ★ | active |
| 27 | [Crowdsec](https://tashan.sh/capability/plugin-crowdsecurity-crowdsec-skill-crowdsec.html) | 55 | 21 ★ | active |
| 28 | [Mine](https://tashan.sh/capability/plugin-anipotts-claude-code-tips-mine.html) | 55 | 27 ★ | active |
| 29 | [Launchdarkly · launchdarkly](https://tashan.sh/capability/plugin-launchdarkly-ai-tooling-launchdarkly.html) | 54 | 20 ★ | active |
| 30 | [Mirrord Agent Skills](https://tashan.sh/capability/plugin-metalbear-co-skills-mirrord-agent-skills.html) | 54 | 21 ★ | active |
| 31 | [Datadog · datadog-labs](https://tashan.sh/capability/plugin-datadog-labs-claude-code-plugin-datadog.html) | 54 | 8 ★ | active |
| 32 | [Confidence](https://tashan.sh/capability/plugin-spotify-confidence-ai-plugins-confidence.html) | 53 | 7 ★ | active |
| 33 | [Azure Cost Calculator](https://tashan.sh/capability/plugin-ahmadabdalla-azure-cost-calculator-azure-cost-calculator.html) | 52 | 17 ★ | active |
| 34 | [Parseable](https://tashan.sh/capability/pkg-parseable-parseable-mcp-server.html) | 51 | 91/wk | active |
| 35 | [AWS Dev Toolkit](https://tashan.sh/capability/plugin-aws-samples-sample-claude-code-plugins-for-startups-aws-dev-toolkit.html) | 50 | 12 ★ | active |
| 36 | [Teamcity](https://tashan.sh/capability/pkg-daghis-teamcity-mcp.html) | 50 | 1k/wk | active |
| 37 | [Basicdeploy](https://tashan.sh/capability/pkg-basicdeploy-mcp.html) | 50 | 97/wk | active |
| 38 | [Base44](https://tashan.sh/capability/plugin-base44-skills-base44.html) | 49 | 4 marketplaces | active |
| 39 | [Itential Builder](https://tashan.sh/capability/plugin-itential-builder-skills-itential-builder.html) | 48 | 12 ★ | active |
| 40 | [Dataproc](https://tashan.sh/capability/plugin-gemini-cli-extensions-dataproc-dataproc.html) | 47 | 1 ★ | active |

Showing the top 40 of 281. The full ranked shelf is at https://tashan.sh/role/devops.html.

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
