# Do this next — the four things only you can do

*Written 6 Aug 2026. Everything that could be done from a keyboard has been. These four need an
identity, a dashboard, or a human on the other end. They are ordered by effect, and each one states
exactly what is already prepared so the step is short.*

Time: **~25 minutes total.** Steps 1 and 2 are two minutes each.

---

## 1 · Turn off Bot Fight Mode — 2 minutes

**What it costs today:** Cloudflare returns **403** to any request whose User-Agent is
`Python-urllib/3.x` — the default of `urllib.request.urlopen(url)`. Every endpoint the outreach post
points at is refused to anyone who tries it from a Python script.

**Narrower than it sounds, and worth knowing which half:** every named crawler reads the site fine
(Googlebot, Google-Extended, GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, Bingbot all return
200). So AI citation is unobstructed. What is blocked is the **decision-time** path — a tool call, a
CI check, the integration someone writes after reading step 3.

**Do:**
1. [dash.cloudflare.com](https://dash.cloudflare.com) → **tashan.sh** → Security → Bots
2. Turn **Bot Fight Mode** off.
   (Free-tier Bot Fight Mode cannot be scoped by path. Super Bot Fight Mode can, if you want
   protection elsewhere — allow `/v0.1/*` and `/data/*`.)

**Verify:**
```sh
python3 tests/test_agent_access.py     # every line should read ok
```

*Not automatable: the deploy token carries `zone:read`, not `zone:write`.*

---

## 2 · Add the npm token so the CLI publishes with provenance — 3 minutes

**What it costs today:** `tashan-cli@0.1.2` was published from a laptop and has **no build
provenance** — it is inside the 75% we point at in every outreach message. Fixing it is the
difference between "75% of packages have this problem" and "…and here's how we got out of it."

**Already prepared:** `.github/workflows/publish-cli.yml` — tests, packs, verifies every `bin` ships,
publishes with `--provenance`, then reads npm back and **fails if the attestation did not land**
(the usual cause is a missing `id-token` permission, which otherwise looks identical to success).

**Do:**
1. [npmjs.com](https://www.npmjs.com) → Access Tokens → Generate → **Granular Access**,
   read+write on `tashan-cli` only.
2. GitHub → tashan → Settings → Secrets and variables → Actions → **New repository secret**
   `NPM_TOKEN` = the token.
3. Actions → **publish cli** → Run workflow. Leave `dry_run` **checked** the first time — it packs
   and verifies without publishing. If green, run it again with `dry_run` unchecked.

**Verify:** the workflow's last step prints `tashan-cli@0.1.3 attestations: true`.

---

## 3 · Publish to the MCP registry — 10 minutes

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

```sh
PRIVATE_KEY="$(openssl pkey -in key.pem -noout -text | grep -A3 "priv:" | tail -n +2 | tr -d ' :\n')"
mcp-publisher login dns --domain tashan.sh --private-key "${PRIVATE_KEY}"
mcp-publisher publish
```

`key.pem` is the private half of the key that proves we own the namespace — anyone holding it can
publish as `sh.tashan/*`. It is in `.gitignore` (`*.pem`); keep it out of the repo and out of chat.

**Simpler alternative if you would rather not touch DNS:** `mcp-publisher login github` works
immediately, but the namespace must become `io.github.FlyingWHR/tashan` — change `name` in
`server.json` **and** `mcpName` in `cli/package.json` to match, or the publish is rejected.

**Verify:** re-run the curl above; expect `count: 1`.

---

## 4 · Post one Discussion — 10 minutes, and the only one that moves the number

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

## What I will do while you do that

- **The file ceiling.** `web/` is at 18,759 files against Cloudflare Pages' hard **20,000** — about
  620 more capabilities before a deploy is *refused*, not degraded. It has been hit once already.
  `docs/SCALE.md` has the move (prerendered pages behind an SSR Function); the suite now fails at
  19,000 so it cannot surprise a deploy.
- **Expertise and task coverage.** 29% and 36% on the top 1,000 — the honest weak spot. Both need
  `ANTHROPIC_API_KEY` as a repo secret; the nightly stages are wired and skip loudly without it.
