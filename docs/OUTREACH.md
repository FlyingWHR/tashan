# Outreach — ready to send

*Written 6 Aug 2026. This file exists because the last four audits scored distribution 10/100 at the
heaviest weight on the sheet, and each time the response was another product sprint. The gap is not
that we don't know who to talk to; it is that "do outreach" is a task with no first line, and a task
with no first line loses to a task that has one. So here are the first lines.*

**Nothing here is sent by anyone but you.** Every message below is a draft in a file. Pick one,
paste it, change what sounds wrong, send it.

---

## The rule that makes these different from spam

Every message leads with **a fact about the recipient's own users that they do not have and we do**,
measured, with the query behind it. Not "we built a thing." Not "we'd love to chat."

If a draft below has lost its number by the time you send it, re-run the query. A stale number in an
outreach email is the same sin the product exists to point at.

---

## The facts, and how to re-derive them

Run `python3 pipeline/coverage.py` and the snippets below against `data/tashan.db`.

| Fact | Value (19 Aug 2026) | Query |
|---|---|---|
| npm packages scanned for advisories against the version you'd install today | 8,052 | `SELECT count(*) FROM capabilities WHERE sec_scanned_at IS NOT NULL` |
| …of those, **no build provenance** — nothing proves the publisher built it | **74%** (5,943) | `SELECT sec_provenance, count(*) FROM capabilities WHERE sec_scanned_at IS NOT NULL GROUP BY 1` |
| Servers running an **install-time script** (arbitrary code on `npm i`) | 495 | `WHERE sec_install_script IS NOT NULL` |
| Confirmed-malicious packages found, kept unranked so `doctor` still warns | 6 | `WHERE sec_max_severity='MALICIOUS'` |
| Scored capabilities whose maintainer has **stopped** (archived / declared / dormant) | 992 | `WHERE tashan_score IS NOT NULL AND vitality='abandoned'` |
| Library/SDK packages found so far that can't be launched at all | 798 | `WHERE npm_runnable=0` |

The 74% is the strongest single line in this file. It is not an accusation of anything — most
publishers have simply never turned on npm provenance — but it means that for three out of four MCP
servers your users install, **nobody can show that the tarball came from the source repo it claims**.

---

## 1. MCP client authors — Cline, Continue, Cursor, Windsurf, Zed

*Best fit. They own the install moment, which is the only moment a score changes a decision.*

**Post a Discussion, do not send an email.** Checked 6 Aug 2026: Cline and Continue both set
`blank_issues_enabled: false` and route every non-bug message to GitHub Discussions. That is the
channel they asked for, it is public — which suits a company whose whole claim is public evidence
better than a private pitch does — and it is one form, not a cold address you have to find.

| Project | Where | Notes |
|---|---|---|
| **Cline** (65.7k ★) | [Discussions → Feature Requests](https://github.com/cline/cline/discussions/new?category=feature-requests) | also [discord.gg/cline](https://discord.gg/cline) |
| **Continue** (35.3k ★) | [Discussions](https://github.com/continuedev/continue/discussions/new) | no separate category |
| **Goose** (52.4k ★) | [Discussions](https://github.com/aaif-goose/goose/discussions/new) | Block's client |

No existing MCP-trust thread to reply to — searched, nothing close — so a new post is correct.

**Title:** Show a maintenance + advisory score next to each MCP server (free, keyless endpoint)

> Cline/Continue users add MCP servers from a list that shows a name and a description. Nothing at
> that moment says whether the server is still maintained, whether its current release has an open
> advisory, or whether it runs a script at install time.
>
> I measure that publicly at [tashan.sh](https://tashan.sh) — public evidence only, nothing paid can
> change a score, no listings and no promoted slots. Of the npm-published MCP servers audited so far,
> about **75% ship with no build provenance** (no attestation tying the tarball to the repo it points
> at), **199 run a script at install time**, and **two turned out to be in OSV's malicious-packages
> database**.
>
> There is a free, keyless, CORS-open endpoint if this is useful:
>
>     GET https://tashan.sh/v0.1/lookup?name=<package>   # one package, a few hundred bytes
>     GET https://tashan.sh/v0.1/search?q=<query>        # ranked matches
>
> The response carries the score, what the score is **not** (it is not a security verdict), the
> advisory ids, and the licence terms for quoting it. An unmeasured package answers `measured:false`
> rather than 404, because "we have no evidence" is a real answer and shouldn't look like an outage.
>
> No account, no key, no rate limit to negotiate, and no ask on my side — attribution if you feel
> like it. If the shape is wrong for you, tell me what shape you'd want and I'll add it.

**Why this one is first:** it costs them one fetch and a column. No partnership, no contract, no
integration review. And a public thread other users can upvote is worth more than a reply in a
founder's inbox.

## 2. Registry and directory operators — Smithery, Glama, PulseMCP, mcp.so

*They have supply and traffic. They have no measurement. That is a fit, not a conflict — and saying
so plainly is more persuasive than pretending we're not adjacent.*

**Subject:** measurement layer for your listings — free, and I'm not building a directory

> Hi — tashan.sh scores MCP servers on public evidence: upkeep, freshness, adoption, plus an OSV
> advisory scan run against the version a user would install today. We're deliberately not a
> directory — no listings, no submissions, no promoted slots. The whole product is the measurement.
>
> That makes us complementary to [Smithery/Glama/…] rather than competitive: you have the catalogue
> and the traffic, and every catalogue eventually gets asked "which of these is any good."
>
> Free and keyless, today: `GET https://tashan.sh/v0.1/scores`, plus badge SVGs at
> `/badge/<slug>.svg` if you want it inline.
>
> Two things you'd be able to show that nobody in this space shows yet: whether a package's current
> release has an open advisory, and whether it has build provenance (~74% don't).
>
> Happy to add whatever field makes it drop into your schema.
>
> — [name]

---

## 3. CI and supply-chain security tooling — Socket, Snyk, Semgrep, Aikido, StepSecurity

*They already scan dependencies and have no answer for MCP servers, which are entering codebases
through `.mcp.json` rather than `package.json` — a file their scanners don't read.*

**Subject:** your scanners don't read .mcp.json

> Hi — MCP servers are arriving in repos through `.mcp.json` and `claude_desktop_config.json`, not
> through `package.json`, so they land inside the dependency boundary without passing the scanner
> that guards it. They're npm packages with the same install-time script surface as anything else —
> 199 of the ones we've audited run one.
>
> tashan.sh measures them: OSV advisories against the installed version, install scripts, provenance,
> declared permission surface. `GET https://tashan.sh/v0.1/lookup?name=<pkg>` is free, keyless and
> answers in a few hundred bytes.
>
> If a config-file parser plus our lookup is a week of work for you, it's a category you can claim
> before anyone asks for it. Not selling anything — I'd rather this got measured than that we owned it.
>
> — [name]

---

## 4. The launch post  — REWRITTEN 19 Aug 2026

*The previous draft led with "I scored 8,700 MCP servers". Two problems. Its numbers had gone stale
(199 install scripts -> 490, 2 malicious -> 6, 409 abandoned -> 727), which is the exact sin this
file warns about two sections up. And it asked the reader to read rather than to DO something —
/audit.html now exists, so the opening move can be a thing they try in ten seconds on their own
config. Every number below was re-derived 19 Aug; re-run them before posting.*

**Title:** Show HN: Paste your MCP config and see what is actually in it

> I kept adding MCP servers to Claude Code and Cursor without any way to tell which ones were
> maintained, so I built the measurement and left it running for a few months.
>
> https://tashan.sh/audit — paste your `mcpServers` block, get every risk I hold about each one.
> Free, no account. **The config is parsed in your browser and only the bare package names are sent**;
> an MCP config keeps API tokens and database URLs in the `env` block right next to the package name,
> so nothing else leaves the page.
>
> Some of what fell out of measuring 39,374 capabilities (14,419 scored, 7,862 scanned against the
> version you would actually install rather than the latest tag):
>
> - **74% have no build provenance.** npm signs every tarball it hosts, which is a fact about npm and
>   not about the publisher — reading it as provenance marked 266 of 266 packages "verified" until I
>   caught it. Only `dist.attestations` means the publisher built it in CI.
> - **490 run a script when you install them, and for 92% of those I cannot tell you what the script
>   does.** The hook delegates to a file inside the tarball (`postinstall.js`, `install.js`), and a
>   static check cannot read it without downloading and running the package. That is the honest limit
>   of every scanner including mine, and I would rather publish the limit than the implication.
> - **26% of resolved dependency trees carry a known advisory** — 85 of the 315 I have resolved so
>   far. Matching dependency *names* against OSV said 86%, which is a scare story: express and undici
>   carry advisories at *some* version and resolve to fixed ones. You have to resolve the tree and
>   query with the version that actually installs.
> - 6 packages are in OSV's malicious-packages database. They are kept in the lookup, unranked, so
>   the CLI can still warn someone who already installed one.
> - 727 scored capabilities are maintained by nobody. One README opened with "we have decided to stop
>   maintaining this" and it was still ranked #1 on its shelf.
> - The highest-adoption package on the board was once the SDK you *build* servers with, at 53M
>   downloads a week. A package that declares no `bin` cannot be launched by a host, so it is not a
>   capability. That removed 794 rows.
>
> Nothing paid can change a score, a rank, or a listing. That is the one line the whole thing rests
> on, and it has a test of its own that fails if the scorer ever reads a payment column.
>
> Keyless data if you want it: `/v0.1/scores`, `/v0.1/servers`, `/llms.txt`.
> `npx tashan-cli doctor` reads your local config and uploads nothing.
>
> The methodology page spends more space on what this does not measure than what it does: no source
> review, no sandboxing, no prompt-injection testing, and a package I have never measured is reported
> as unmeasured rather than as safe. Corrections welcome — several of the numbers above are different
> from what I first published because someone told me they were wrong.

**Why this one and not the old one.** The strongest line is the one that admits a limit: *for 92% of
install scripts I cannot tell you what the script does*. A measurement product that leads with its
blind spot is making the only claim a sceptical crowd cannot immediately puncture, and it happens to
be the most interesting fact in the set.

**Do not** post the same text to six places. One Show HN, one r/mcp post written differently, and
nothing else the same week. The failure mode is looking like a launch campaign instead of a person
who built a thing — and be there to answer for the first few hours, or do not post at all.

---

## 0. The official MCP registry — DONE, 7 Aug 2026

*This section used to open "we are absent from it while ingesting it as the spine of our own
coverage", citing a 6 Aug curl. That stopped being true the next day and the section sat here
unchanged, which is the exact failure this file warns about in "The facts, and how to re-derive
them". It was quoted back as an outstanding task twice before anyone re-ran the query.*

```sh
curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=tashan"
```

    sh.tashan/tashan  v0.1.3  published 2026-08-07  status=active
    sh.tashan/tashan  v0.1.4  published 2026-08-09  status=active  isLatest=true

Listed under the **DNS-verified `sh.tashan/*` namespace**, which is the namespace worth having for
a measurement company — it says the domain vouches for the entry. v0.1.4 matches `server.json` at
the repo root, so the published entry and the package agree today.

**What is left here is not publishing, it is re-publishing.** `mcp-publisher publish` again whenever
`server.json`'s version changes, or the registry keeps serving an older description of what the CLI
does. `tests/test_agent_surface.py` checks the manifest against what the CLI actually publishes, so
drift inside the repo is caught; drift between the repo and the *registry* is not, and nothing here
watches for it.

---

## Order of operations

0. ~~List in the MCP registry~~ — done 7 Aug, verify with the curl in §0 before repeating the claim.
1. **Send #1 to three clients.** Not one — three, so a single non-reply isn't a signal.
2. **Post #4 the same week.** The post and the emails compound: an integrator who has seen the
   thread twice replies at a different rate.
3. **Only then #2 and #3.** They're slower and they matter less than the install moment.

Track replies in this file. An email thread is the artifact the next audit is asking to score, and
`docs/NEXT.md` §1.3 has been open across four sprints.

---

## What must be true before any of this goes out

- [ ] **Bot Fight Mode off** (`docs/NEXT.md` §1.2). Cloudflare currently returns **403** to any
      request whose User-Agent is `Python-urllib/3.x`. Every email above ends in someone pasting a
      URL into a script. Verify: `python3 tests/test_agent_access.py`.
- [ ] The endpoints answer: `curl -s https://tashan.sh/v0.1/scores | head -c 200`
- [ ] The numbers in your draft match `python3 pipeline/coverage.py` on the day you send it.
