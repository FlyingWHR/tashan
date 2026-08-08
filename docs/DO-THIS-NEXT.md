# Do this next — the four things only you can do

*Written 6 Aug 2026. Everything that could be done from a keyboard has been. These four need an
identity, a dashboard, or a human on the other end. They are ordered by effect, and each one states
exactly what is already prepared so the step is short.*

**All four are done.** One new item has taken their place, and it is the one that matters most.

---

## 0 · Publish `tashan-cli@0.1.4` — the currently published version defames Microsoft

**Do this before anything else launches.** `tashan-cli@0.1.3` is live on npm right now, and it tells
every user who has Microsoft's official Playwright MCP server installed:

> `! playwright` — **REMOVED from the MCP registry** — its policy lists spam, malware or illegal
> content as the usual reasons. Stop using it and verify the source.

`@playwright/mcp` was never removed from anything. `doctor` fell back to matching the bare leaf name
`mcp` after the scoped lookup missed, and `mcp` resolves to a different, delisted package. Every
Playwright user running `tashan doctor` sees this. It is reproducible in one command:

```sh
npm install --prefix /tmp/t tashan-cli@0.1.3
# with @playwright/mcp in your Claude config:
/tmp/t/node_modules/.bin/tashan doctor
```

**0.1.4 fixes it** (`cli/doctor.mjs` refuses generic leaves: `mcp`, `server`, `cli`, `core`, …) and
was verified the way the bug was found — packed, installed from the tarball, and run against a real
config, not called as a function in a test. It also gives `--version` an answer; every form of it
replied "unknown command" up to 0.1.3.

**Do** — GitHub → Actions → **publish cli** → *Run workflow*:

| field | value |
|---|---|
| `dry_run` | **unchecked** — checked is a pack-and-verify rehearsal that publishes nothing |

Trusted publishing is already configured (§2), so there is no token to supply. Then move the MCP
registry entry to 0.1.4 (§3 has the command). Verify with `npx tashan-cli@latest --version` → `0.1.4`.

*Why you and not me: publishing is outward-facing and irreversible — npm restricts unpublish after
72 hours — so it happens when a human says so. That is also why the workflow is `workflow_dispatch`
and not a push trigger.*

---

## 1 · Nothing to do — it was never our setting ✅ resolved 8 Aug 2026

Two days were spent turning off Bot Fight Mode and Browser Integrity Check because `/llms.txt` and
`/v0.1/*` answered `403 error 1010` to a stdlib Python client. Neither was the cause. Measured
against third parties, which is the test that should have been run first:

| user-agent | tashan.sh | pages.dev | cloudflare.com | discord.com |
|---|---|---|---|---|
| `Python-urllib/3.14` | 403 | 403 | **403** | **403** |
| `python-requests/2.31` | 200 | 200 | — | — |
| `curl/8.4.0` | 200 | 200 | 200 | 200 |

Cloudflare refuses the literal string `Python-urllib` everywhere it sits in front of. No setting on
this account changes it, and `error 1010` was diagnosed as Browser Integrity Check from the code
alone — wrongly.

**The real scope is tiny:** only `urllib.request.urlopen()` with its default header. `requests` —
what nearly every Python integration uses — works, as do curl, node-fetch, Go and every named AI
crawler. `llms.txt` now tells callers to send a User-Agent, which is the actual fix and is one line.

Verify: `python3 tests/test_agent_access.py` → AGENT ACCESS OK.

## 2 · npm Trusted Publishing — ✅ DONE 7 Aug 2026 (`tashan-cli@0.1.3`)

*Published over OIDC with no token. Provenance did NOT land and cannot: npm builds the
attestation from a public source repo and this one is private. `start.html` says so
plainly rather than claiming a fix; making the CLI attestable means publishing it from a
public repository, which is a decision, not a task.*

<details><summary>original instructions</summary>

**What it costs today:** `tashan-cli@0.1.2` was published from a laptop and has **no build
provenance** — it is inside the 75% we point at in every outreach message. Fixing it is the
difference between "75% of packages have this problem" and "…and here's how we got out of it."

**Use trusted publishing, not a token.** It is better on three counts:

- **No long-lived credential.** npm trusts this repo and this workflow file over OIDC, so there is
  no secret to leak, rotate, or scope wrong.
- **Provenance is automatic** — no `--provenance` flag, and no way to publish unattested by
  forgetting one.
- **It survives 2FA enforcement.** npm's *"Require two-factor authentication and disallow tokens"*
  blocks token auth and leaves OIDC working, so you can lock the account down without breaking
  releases.

**Do** — npmjs.com → the `tashan-cli` package → Settings → **Trusted Publisher** → Select your
publisher:

| Field | Value |
|---|---|
| Publisher | GitHub Actions |
| Organization or user | `FlyingWHR` |
| Repository | `tashan` |
| **Workflow filename** | `publish-cli.yml` — filename only, case-sensitive, keep the `.yml` |
| Environment name | *(leave blank)* |
| Allowed actions | `npm publish` |

Every field is matched exactly; `publish-cli` or `.github/workflows/publish-cli.yml` both fail.

Then: Actions → **publish cli** → Run workflow. Leave `dry_run` **checked** the first time — it
tests, packs, and verifies without publishing. If green, run it again with `dry_run` unchecked.

**Verify:** the last step prints `tashan-cli@0.1.3 attestations: true`.

*One thing the workflow settles for you: trusted publishing needs **npm ≥ 11.5.1**, and no Node 22
release ever ships it — the whole 22.x line tops out at npm 10.9.x. The first Node bundling a new
enough npm is **24.5.0**, so the publish job runs on Node 24 (current LTS "Krypton", npm 11.17.0)
rather than installing npm globally over the top of the wrong runtime. The CLI is still tested on
Node 18, 22 and 24, because `engines: ">=18"` is a promise to whoever runs `npx tashan-cli` on an
older machine.*

---

## 3 · Publish to the MCP registry — ✅ DONE 7 Aug 2026 (`sh.tashan/tashan@0.1.3`, active)

**What it costs today:** we ingest `registry.modelcontextprotocol.io` as the spine of our coverage
and are absent from it. It is where every MCP client with a "browse servers" view looks.

```sh
curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=tashan"
# {"servers":[],"metadata":{"count":0}}
```

**Already prepared, including one thing that would have failed the publish:** `server.json` is
written and validated field-by-field against the official `2025-12-11` schema. The registry also
requires an **`mcpName` in `package.json`** equal to `server.json`'s `name`, or it rejects the
publish — both files are individually valid, so it is invisible until you try. That is now in
`cli/package.json` (`sh.tashan/tashan`), both files are at `0.1.3`, and
`tests/test_agent_surface.py` fails the build if they ever drift apart.

**Order matters: step 2 must land first.** The registry verifies the metadata against the npm
package, so `tashan-cli@0.1.3` has to exist on npm before this will work.

```sh
brew install mcp-publisher        # or the tarball from the registry's releases page
```

Then, from the repo root — the namespace `sh.tashan/*` is claimed by proving you control the domain:

```sh
openssl genpkey -algorithm Ed25519 -out key.pem
PUBLIC_KEY="$(openssl pkey -in key.pem -pubout -outform DER | tail -c 32 | base64)"
echo "tashan.sh. IN TXT \"v=MCPv1; k=ed25519; p=${PUBLIC_KEY}\""
```

Add that TXT record in Cloudflare DNS. **It must sit on the apex (`tashan.sh`), not under a selector
like `_mcp-auth`** — the registry follows SPF-style placement, and a record under a selector fails
with a generic signature error that tells you nothing.

The registry JWT from `login` is short-lived, so run the login and the publish as one chain rather
than as two steps you come back to — a pause between them returns
`401 … Registry JWT token … token is expired`, which reads like an auth problem and is only a clock.

```sh
PRIVATE_KEY="$(openssl pkey -in key.pem -noout -text | grep -A3 "priv:" | tail -n +2 | tr -d ' :\n')" \
  && mcp-publisher login dns --domain tashan.sh --private-key "$PRIVATE_KEY" \
  && mcp-publisher publish
```

If it does expire, only the two commands above need repeating — `key.pem` and the TXT record stay
valid, so there is nothing to regenerate and no DNS to touch.

`key.pem` is the private half of the key that proves we own the namespace — anyone holding it can
publish as `sh.tashan/*`. It is in `.gitignore` (`*.pem`); keep it out of the repo and out of chat.

**Simpler alternative if you would rather not touch DNS:** `mcp-publisher login github` works
immediately, but the namespace must become `io.github.FlyingWHR/tashan` — change `name` in
`server.json` **and** `mcpName` in `cli/package.json` to match, or the publish is rejected.

**Verify:** re-run the curl above; expect `count: 1`.

---

</details>

## 4 · Post one Discussion — ✅ DONE 7 Aug 2026

*Posted to [Cline](https://github.com/cline/cline/discussions/13027) and
[Goose](https://github.com/aaif-goose/goose/discussions/11029). Continue was not found in
a search — worth checking, since three beats two for the reason one non-reply is not a
signal.*

<details><summary>original instructions</summary>

Distribution has scored **10/100 at the heaviest weight** across five consecutive audits. Nothing
engineering-side moves it. This is the whole gap.

**Post a Discussion, do not email.** Cline and Continue both set `blank_issues_enabled: false` and
route non-bug messages to Discussions. It is the channel they asked for, it is public — which suits
a company whose claim is public evidence — and other users can upvote it, which an inbox cannot.

| Project | Link |
|---|---|
| **Cline** (65.7k ★) | [new Feature Request discussion](https://github.com/cline/cline/discussions/new?category=feature-requests) |
| **Continue** (35.3k ★) | [new discussion](https://github.com/continuedev/continue/discussions/new) |
| **Goose** (52.4k ★) | [new discussion](https://github.com/aaif-goose/goose/discussions/new) |

The title and body are written and ready to paste: **`docs/OUTREACH.md` §1.** Post to all three —
one non-reply is not a signal, three is.

**Then post #4 the same week** (`docs/OUTREACH.md` §4, the Show HN / r/mcp post). The thread and the
post compound: someone who has seen the name twice replies at a different rate.

**Before posting, re-check the numbers.** They went stale within four hours last time:
```sh
python3 tests/test_outreach_numbers.py
```

---

</details>

## What I will do while you do that

- **The file ceiling.** `web/` is at 18,759 files against Cloudflare Pages' hard **20,000** — about
  620 more capabilities before a deploy is *refused*, not degraded. It has been hit once already.
  `docs/SCALE.md` has the move (prerendered pages behind an SSR Function); the suite now fails at
  19,000 so it cannot surprise a deploy.
- **Expertise and task coverage.** 29% and 36% on the top 1,000 — the honest weak spot. Both need
  `ANTHROPIC_API_KEY` as a repo secret; the nightly stages are wired and skip loudly without it.
