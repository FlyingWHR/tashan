# tashan CLI

The trusted directory for your agent's toolbox, in your terminal. Checks what you run against
[tashan.sh](https://tashan.sh), which measures every MCP server, plugin and skill it can find on public
evidence: npm, GitHub, OSV and the MCP registry. Nobody can pay for a position in it.

```bash
npx tashan-cli                 # check the toolbox you already have (the default)
npx tashan-cli info context7   # should I install this? The verdict first, then the evidence
npx tashan-cli search database # find capabilities, ranked on public evidence
```

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

## Flags

- `--all`: list every item, including the ones no public record describes
- `--json`: machine-readable output (pipe into `jq`)
- `--limit <n>`: cap the rows for `search` (default 20)
- `--client <c>`: `claude` · `cursor` · `desktop` · `codex` · `npx` (for `add`)

## How it works

Zero dependencies, Node ≥ 18. It reads the public index at `tashan.sh/data/lookup.json` and your local
config. Your config is never uploaded. Every score can be re-derived from public evidence.

`TASHAN_DATA=<path>` reads a local `index.json` instead of the network (dev/offline);
`TASHAN_SITE=<url>` points at a different deployment.

```bash
node tashan.test.mjs        # pure-logic tests, no network
```
