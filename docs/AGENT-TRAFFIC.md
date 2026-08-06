# Optimising for agent traffic

*Written 6 Aug 2026. Every gap below was measured, not assumed; the measurement is printed beside it
so it can be re-run and so a fix can be checked rather than believed.*

**The premise.** This product's readers are mostly not people. An agent deciding what to install, an
answer engine asked "best MCP server for postgres", a CI scanner reading a config — those are the
consumers, and none of them run JavaScript, read a hero, or click a filter. The site was built for
the human first and the agent as an afterthought, and it showed in the measurements.

---

## The funnel, and where it leaked

An agent has to get through five stages. A leak at any stage makes the ones after it irrelevant, so
they are worked in order.

| # | Stage | Question | State when measured |
|---|---|---|---|
| 1 | **Reach** | does a request get a response? | **BROKEN** — 403 to any stdlib Python client |
| 2 | **Find** | does the agent know we exist? | partial — llms.txt yes, MCP registry no |
| 3 | **Fetch** | is the answer cheap to obtain? | **BROKEN** — the Index published nothing without JS |
| 4 | **Trust** | is it citable and attributable? | partial |
| 5 | **Use** | is the tool worth keeping? | good — 3 MCP tools, keyless endpoints |

---

## 1. Reach — the only blocker we cannot fix from here

Cloudflare Bot Fight Mode returns **403 to any request whose User-Agent is `Python-urllib/3.x`** —
the default of `urllib.request.urlopen(url)`. Re-measured 6 Aug 2026, 02:17: still failing on all
five advertised surfaces.

    /  ·  /llms.txt  ·  /v0.1/scores  ·  /v0.1/servers  ·  /data/index.json  ·  /capability/*.md

**There is no code workaround.** The obvious idea — serve the endpoints from a Pages Function so the
challenge does not apply to a static asset path — does not work: the block is zone-wide and runs
before Workers. Measured:

    default urllib UA    curl UA
    /v0.1/scores       403        200
    /badge/*.svg       403        200     <- already a Function
    /api/security      403        401     <- already a Function

An agent that gets 403 on its first request does not retry with a nicer header; it concludes the
service is down. `docs/NEXT.md` §1.2 has the two-minute fix; the deploy token carries `zone:read`,
not `zone:write`.

**But it is narrower than it first looked, and the distinction decides what to worry about.** Swept
6 Aug 2026 against every named crawler:

| user-agent | `/` | `/methodology.html` | `/llms.txt` | `/v0.1/scores` |
|---|---|---|---|---|
| Googlebot · Google-Extended | 200 | 200 | 200 | 200 |
| GPTBot · OAI-SearchBot | 200 | 200 | 200 | 200 |
| ClaudeBot · PerplexityBot · Bingbot | 200 | 200 | 200 | 200 |
| **`Python-urllib/3.x`** | **403** | **403** | **403** | **403** |

So **the citation path is not blocked** — every answer engine that would ground an answer in this
site can read all of it, including `llms.txt` and the JSON feeds. What is blocked is the
**decision-time path**: an agent running `urllib.request.urlopen()` inside a tool call, a CI script,
a `requests`-based integration someone writes after reading the outreach email. That is a real loss
and still worth two minutes, but it is not "nobody can see us" — an earlier version of this file
overstated it, and GEO work does not need to wait for it.

---

## 2. Find

- **`llms.txt`** — site summary, scoring method, top 40, categories, citation guidance, and now the
  per-axis coverage rates so an agent can weigh an absence instead of guessing at one. ✅
- **`robots.txt`** names every major AI crawler explicitly rather than leaving them to the wildcard. ✅
- **The MCP registry** — we ingest it as the spine of our coverage and were **absent from it**:

      curl "https://registry.modelcontextprotocol.io/v0/servers?search=tashan"
      → {"servers":[],"metadata":{"count":0}}

  `server.json` is now written and validated field-by-field against the official `2025-12-11` schema.
  Publishing needs a human identity — `docs/OUTREACH.md` §0. ⏳ *user*
- **`Dataset` JSON-LD** — already good: the homepage declares a Dataset with `measurementTechnique`,
  `variableMeasured` per axis, and a `distribution` listing the bulk feeds. What it lacked was a
  `dateModified` (an undated dataset is one an engine has to treat as undated) and any mention of the
  per-question endpoints. Both added, baked from the export so they cannot go stale. ✅

## 3. Fetch

- **The Index published no measurements.** `https://tashan.sh/` rendered 3,137 characters of nav,
  hero and footer; the ranked board lived entirely in `index.js`. Now the top 25 rows are
  server-rendered with an `ItemList` carrying each score as an `aggregateRating`. ✅
- **The ranked shelves had no markdown twin.** Capabilities had one; `/category/`, `/task/` and
  `/role/` — the pages that answer the actual queries — did not. 100 twins now, declared with
  `rel="alternate"`, allowed in `robots.txt`, served as `text/markdown`, announced in `llms.txt`. ✅
- **One question cost a whole file.** `/v0.1/scores` is 804 KB and `/v0.1/servers` is 6.9 MB; an
  agent asking about one package had to pull all of it, which in a tool call is both the latency and
  the context budget. `/v0.1/lookup?name=` and `/v0.1/search?q=` answer in a few hundred bytes. ✅

### The one that mattered most

The first version of `/v0.1/lookup` read `/v0.1/scores`, which is the obvious source and the wrong
one. `scores` is the **ranked, publishable** corpus: `junk()` has already removed from it everything
we refuse to recommend, including the two packages OSV's malicious-packages database confirms as
malware. So:

    GET /v0.1/lookup?name=mcp-server-fetch      →  { "measured": false,
                                                     "hint": "…we have no public evidence for it yet" }

That package carries **MAL-2026-5476**. Asked whether it was safe to install, the endpoint would have
said we had no opinion — the worst answer this service can give, produced by reading the
recommendation list to answer a safety question.

`lookup` now reads `/data/lookup.json`, which is the file that keeps those rows precisely so `doctor`
can warn someone already running one, and which carries the advisory ids and install-script text.
`search` still reads the ranked corpus. **We answer about malware; we never recommend it** — the same
policy the CLI has always had, now true of the public endpoint as well. A `MALICIOUS` row returns a
top-level `verdict: "DO NOT INSTALL"` rather than leaving it three levels down under
`security.max_severity`, because an agent skimming a JSON body should not have to find it.

## 4. Trust

An answer engine decides whether to cite partly on whether the claim is attributable and dated.

- Markdown twins end with `Measured <date> by tashan … Scorer s5`. ✅
- `/v0.1/*` carries `license: CC BY 4.0 — attribute tashan`. ✅
- Capability pages carried `SoftwareApplication` with a `review` but **no `aggregateRating`, no
  `dateModified`, and no statement of who did the measuring** — so the number was quotable without
  anything tying it to us or to a date. ✅
- Coverage is published per axis, so "we have not measured that" is a readable answer rather than
  silence. ✅

## 5. Use

- `npx tashan-cli mcp` exposes `find_capability`, `check_capability`, `audit_config`. The
  descriptions tell the agent *when* to call ("Use this BEFORE suggesting or installing any MCP
  server"), which is the part that decides whether a tool gets used at all. ✅
- Free, keyless, no signup: `/v0.1/*`, `/badge/*`, `/capability/*.md`. ✅

**Open, needs a publish cycle:** `check_capability` downloads `/data/lookup.json` — 3.9 MB — on
first use. It is correct (that file is the one carrying the malware rows) and cached for the life of
the process, so it is one download per session rather than per call, but it lands on the first tool
call, which is exactly when an agent is deciding whether this tool is worth keeping.
`/v0.1/lookup?name=` now returns the same fields in a few hundred bytes. Switching it means
republishing `tashan-cli`, so it waits for the next release rather than leaving the repo and npm
describing different software.

---

## Verify after the next deploy

The endpoints are a Pages Function at `functions/v0.1/[[route]].js`, and two things about it cannot
be proven from this machine: whether Pages routes a directory with a dot in its name (`v0.1`), and
whether `web/_headers` still applies to an asset served through `next()`. Both are handled
defensively — the Function re-asserts the content-type on fall-through, and an unrouted Function
leaves the static files exactly as they are — but check rather than assume:

```sh
curl -s "https://tashan.sh/v0.1/lookup?name=tavily-mcp" | head -c 200        # expect JSON
curl -s "https://tashan.sh/v0.1/lookup?name=mcp-server-fetch" | grep -o 'DO NOT INSTALL'
curl -sI "https://tashan.sh/v0.1/scores" | grep -i content-type              # expect application/json
curl -s "https://tashan.sh/v0.1/search?q=postgres&limit=3" | head -c 200
```

If the Function did not route, the first, second and fourth return the HTML 404 page and the third
still says `application/json` — i.e. nothing that worked before is broken, and the new surface is
simply absent.

## What is guarded

`tests/test_agent_surface.py` runs in the suite and fails the build on: an empty board tbody, a
missing or contradictory `ItemList`, a hub without a markdown twin, a `rel=alternate` pointing at a
file that was never written, a missing `robots.txt` allowance or `text/markdown` header, and a
`server.json` that has drifted from the version the CLI actually publishes.

`tests/test_agent_access.py` runs advisory (never blocks a deploy) and is the standing check on §1.

---

## Deliberately not done

- **Content negotiation on `Accept: text/markdown`.** Static assets cannot negotiate, and routing
  every page through a Function to do it costs more than the `rel=alternate` convention already
  delivers.
- **`/.well-known/` anything.** There is no settled convention for MCP discovery there; inventing
  one would publish a URL nobody looks for.
- **Per-capability static JSON.** 7,365 more files against Cloudflare's 20,000-file deployment
  ceiling, to duplicate what the markdown twin and `/v0.1/lookup` already answer.
- **`/llms-full.txt`.** The convention's "full content" companion to `llms.txt`. Here it would be a
  multi-megabyte markdown restatement of `/v0.1/servers`, which already exists in a better-typed
  form — and the per-page and per-hub twins already give a reader the same content in the size they
  actually want. A large duplicate file is not more discoverable, it is just larger.
- **`.md` twins in `sitemap.xml`.** `rel="alternate"` is the signal for an alternate representation;
  listing both forms as separate URLs invites them to be treated as separate pages.
