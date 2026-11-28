# tashan CLI

The trusted directory for your agent's toolbox, in your terminal. Checks what you run against
[tashan.sh](https://tashan.sh), which measures every MCP server, plugin and skill it can find on public
evidence: npm, GitHub, OSV and the MCP registry. Nobody can pay for a position in it.

```bash
npx tashan-cli                 # check the toolbox you already have (the default)
npx tashan-cli info context7   # should I install this? The verdict first, then the evidence
npx tashan-cli search database # find capabilities, ranked on public evidence
```

Use `GET https://tashan.sh/v0.1/lookup?name=tavily-mcp` for a single remote check. The HTTP API needs no installation. The npm package adds local config inventory and a stdio MCP server.

In MCP, call `find_capability` with a task, a client and `quote_kit: true` for the HTTP request and current x402 terms. Your authorized wallet can use that request to buy the kit.

## What `tashan` (doctor) tells you

- **What needs attention.** Anything deprecated, archived, abandoned, removed from the registry,
  malicious, or carrying a known advisory. It gives the advisory id, the version that fixes it, and the
  exact command a package runs at install time.
- **Your stack, scored.** Each server, plugin and skill we measure gets its tashan score, where it
  stands in its category ("above 98% of browser"), and the evidence behind the score: publisher,
  downloads, stars, provenance, documentation grade.
- **What you use.** From your local Claude Code history: which servers were called in the last 30 days,
  which were never called, and how many skills you use. Only tool names and dates are read, and nothing
  leaves the machine. Cursor and Claude Desktop keep no such record, so they get no usage figure. That
  is not a zero.
- **What it can reach.** The permission surface your agent carries (files, network, browser, shell,
  credentials), and which tools can bring third-party text into the model's context. This comes from
  declared dependencies; nothing is executed.
- **What changed.** Ownership changes, new install scripts, widened permissions and abandonment in
  the last 30 days, for the things you run. These are the same events as [tashan.sh/changes.html](https://tashan.sh/changes.html).
- **What you have.** Counts across every project, what arrived since the last run, and which skills
  no plugin maintains.

Exit code 2 when something needs attention, so it can gate CI.

## tashan Pro

Every finding above is free, in full. Pro adds time: the daily score series behind each capability you
run, drawn as a sparkline with its direction. When something you depend on dies, Pro names the
measured replacement. $6/mo, 7 days free: [tashan.sh/pricing](https://tashan.sh/pricing). Sign in with
`tashan login`; in CI, set `TASHAN_KEY=<key>`.

## Automatic savings in Claude Code and Codex

Connect one local stdio MCP server at a time. In its existing configuration, set the command to the installed `tashan` binary and prepend `["wrap", "--", originalCommand]` to its original argument list. Keep its working directory and server-specific environment. For example, a server started with `node /path/server.js` becomes:

```json
{"command":"tashan","args":["wrap","--","node","/path/server.js"]}
```

Reconnect the server and use the tool as usual. Free mode measures JSON objects and arrays in text results. An active Pro licence automatically removes redundant JSON whitespace when that saves tokens. For a model that accepts tables, use `["wrap","--table","--", ...]` to write repeated field names once. Table mode changes the text representation. Structured MCP results, errors, images and other text pass through.

Run `tashan daily` or `tashan daily --json`. **Removed** counts tokens actually taken out of returned text. **Available** shows additional reductions seen in free mode. Counts cover measured JSON text in o200k_base. The local ledger beside your Tashan licence stores the date and counts only. For whole-task spend, compare paired runs with `tashan costs`.

## Use fewer tokens for tool results

Run `tashan tokens response.json` for a free before/after count in o200k_base. Use `-` to read stdin or `--json` for a machine-readable receipt. With `--table`, uniform arrays can become a JSON object containing columns and rows. Use this option only for a consumer that accepts that layout. The default preserves the JSON structure and numeric literals.

With an active Pro licence, `tashan tokens response.json --emit` writes the chosen payload to stdout. Add the same `--table` flag for a table export. The input stays on your machine. Only licence validation uses the network. Counts measure this text in the named encoding. Provider billing and Claude token counts require run usage.

## Flags

- `--all`: list every item, including the ones no public record describes
- `--json`: machine-readable output (pipe into `jq`)
- `--limit <n>`: cap the rows for `search` (default 20)
- `--client <c>`: `claude` · `cursor` · `desktop` · `codex` · `npx` (for `add`)

## How it works

Node ≥ 18. The token command loads a local tokenizer on demand. It reads the public index at `tashan.sh/data/index.json` and your local
config. Your config is never uploaded. Every score can be re-derived from public evidence.

`TASHAN_DATA=<path>` reads a local `index.json` instead of the network (dev/offline);
`TASHAN_SITE=<url>` points at a different deployment.

```bash
node tashan.test.mjs        # pure-logic tests, no network
```

### Send a shorter CI log

Save the log to a file the agent can open. Preview for free, then use the Pro export as the input to your existing prompt builder.

```sh
gh run view RUN_ID --log-failed > build.log
tashan tokens build.log --ci --json
tashan tokens build.log --ci --emit > agent-context.txt
```

Pro folds runs of passing tests. Errors, stack traces and unfamiliar output stay visible. Each fold names the original line range. The first line points back to the full log. Use a different output file. The count includes the pointer and fold markers and uses o200k_base. Other models may tokenize the text differently.

### Compare total tokens and cost for the same task

Run `tashan costs week.json` (or add `--json`). Enter what your provider charged, including cached input, output, retries and tool fees. Use a unique charge ID for each request or invoice line. Include all paired cases for the period and grade both runs against the same expected result. Set the fee to the subscription cost attributable to that period. For a token comparison, include the provider’s total input and output token count for each request as `total_tokens`. Include cache and reasoning tokens once according to the provider’s usage breakdown. Use zero for a separate non-model fee. Missing usage leaves that run’s total unknown. The example uses illustrative amounts.

```json
{"period":"pilot week 1","fee_usd":1.40,"cases":[
  {"id":"find-a-tool",
   "baseline":{"accepted":true,"charges":[{"id":"before-1","usd":0.08,"total_tokens":8200}]},
   "tashan":{"accepted":true,"charges":[{"id":"after-1","usd":0.05,"total_tokens":6100}]}}
]}
```

The report shows total tokens, spend, accepted tasks, cost per accepted task and the difference after the fee. A previously accepted task that now fails leaves savings unconfirmed. For a flat-rate plan, track quota use separately. This report reads your entries locally.

### Buy a kit over MCP

Call `find_capability` with `quote_kit: true` for a read-only quote. To purchase, call `get_tool_kit` with the same task and client through an x402-enabled MCP wallet. The wallet authorizes the price and retries with `_meta["x402/payment"]`. A successful tool result includes the checked config and `_meta["x402/payment-response"]`. If the response is lost, retry the identical request and signed proof before authorizing another payment. The server keeps the settled kit for up to 24 hours.
