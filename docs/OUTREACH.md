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

| Fact | Value (6 Aug 2026) | Query |
|---|---|---|
| npm packages scanned for advisories against the version you'd install today | 3,737 | `SELECT count(*) FROM capabilities WHERE sec_scanned_at IS NOT NULL` |
| …of those, **no build provenance** — nothing proves the publisher built it | **74%** (2,761) | `SELECT sec_provenance, count(*) FROM capabilities WHERE sec_scanned_at IS NOT NULL GROUP BY 1` |
| Servers running an **install-time script** (arbitrary code on `npm i`) | 301 | `WHERE sec_install_script IS NOT NULL` |
| Confirmed-malicious packages found, kept unranked so `doctor` still warns | 4 | `WHERE sec_max_severity='MALICIOUS'` |
| Scored capabilities whose maintainer has **stopped** (archived / declared / dormant) | 581 | `WHERE tashan_score IS NOT NULL AND vitality='abandoned'` |
| Library/SDK packages found so far that can't be launched at all | 226 | `WHERE npm_runnable=0` |

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

## 4. The launch post

*For HN Show / X / r/mcp. The register is flat on purpose: a measurement company that oversells its
own measurements has already lost the argument. The numbers are the punch.*

**Title:** Show HN: I scored 8,700 MCP servers on public evidence, and 74% have no build provenance

> I kept installing MCP servers with no way to tell which were maintained, so I built the measurement
> and left it running.
>
> tashan.sh scores them on public signal only — upkeep, freshness, real adoption, and an OSV advisory
> scan run against the version you'd actually install rather than the latest tagged one. Every score
> shows its inputs. Nothing paid can change a score, a rank, or a listing; that's the one line the
> whole thing rests on.
>
> Some of what fell out:
>
> - ~74% of scanned packages have **no build provenance** — npm signs every tarball it hosts, which
>   is a fact about npm and not about the publisher, and reading it as provenance marked 266 of 266
>   packages "verified" until I caught it.
> - 199 run a script at install time.
> - 2 were in OSV's malicious-packages database. They're kept in the lookup, unranked, so the CLI can
>   still warn someone who already installed one.
> - 409 scored capabilities are maintained by nobody — archived, deprecated, or the author saying so
>   in the README. One opened with "我们决定不维护了" and was still ranked #1 on its shelf.
> - The single highest-adoption package on the board was the SDK you *build* servers with, at 53M
>   downloads a week. Fixed the day I noticed: a package that declares no `bin` can't be launched by
>   a host, so it isn't a capability. That removed 30 rows, including 19 browser-extension plugins
>   listed as if you could install them.
>
> Free and keyless if you want the data: `/v0.1/scores`, `/v0.1/servers`, `/llms.txt`.
> `npx tashan-cli doctor` reads your local config and uploads nothing.
>
> The methodology page says what it doesn't measure, which is more than it does: no source review, no
> sandboxing, no prompt-injection testing. Corrections welcome — several of the fixes above came from
> someone telling me a number was wrong.

**The last line is the point.** Inviting correction is the only opening move available to something
claiming to be a rating agency, and it's the one that survives contact with a sceptical crowd.

---

## 0. List tashan in the official MCP registry (do this first — 10 minutes)

*Not outreach exactly, but it is the single highest-intent distribution surface for an MCP tool, and
we are absent from it while ingesting it as the spine of our own coverage. Measured 6 Aug 2026:*

```sh
curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=tashan"
# {"servers":[],"metadata":{"count":0}}
```

Every MCP client that offers a "browse servers" view reads that registry. `server.json` is written,
validated against the official schema (`2025-12-11`), and sits at the repo root. Publishing needs a
human because it needs an identity:

```sh
brew install mcp-publisher          # or: go install github.com/modelcontextprotocol/registry/cmd/publisher@latest
mcp-publisher login dns --domain tashan.sh        # prints a TXT record to add at Cloudflare
mcp-publisher publish
```

`login dns` proves control of `tashan.sh` and is what earns the `sh.tashan/*` namespace — the right
signal for a measurement company, and worth the extra DNS step. If you would rather not touch DNS,
`mcp-publisher login github` works immediately but the name has to become
`io.github.FlyingWHR/tashan`; change `name` in `server.json` to match before publishing, or the
publish is rejected.

Verify with the same curl above. `tests/test_agent_surface.py` checks the manifest stays in step with
what the CLI actually publishes, so the entry cannot drift from the package.

---

## Order of operations

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
