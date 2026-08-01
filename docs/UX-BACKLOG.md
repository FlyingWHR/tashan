# The purchase funnel and the signed-in product — journey map + backlog

Durable state for the overnight UX loop. **Every wake-up: read this file, do the top unstarted item,
tick it, commit, move on.** Status: `[ ]` todo · `[~]` in progress · `[x]` done · `[-]` dropped (say why).

---

## Who is walking through this

**A. The vibe coder.** Runs Claude Code or Codex in the app. Does not read docs. Found us because an
agent cited us, or because they googled "is X mcp server safe". Will never paste a key from an email
into a terminal without resenting it. Their whole relationship with a terminal is `npx <thing>`.

**B. The engineer.** Has 40 MCP servers across three machines. Cares about the audit. Will read
`/methodology`. Will absolutely notice if the CLI auth is non-standard, and will judge us for it.

Both must reach Pro without ever being asked to be a database administrator of their own licence.

---

## The journey, end to end

```
   DISCOVER            EVALUATE             ADOPT              PAY               LIVE AS PRO
   ────────            ────────             ─────              ───               ───────────
   agent cites us      /capability/<x>      npx tashan-cli     /pricing          nav shows Pro
   google "best        the audit block      doctor             checkout          doctor says Pro
     mcp for <job>"    /role/<job>          "17 findings,      ↓                 CLI names the fix
   /llms.txt           the board            8 have detail      SIGN IN  ← THE HOLE
                                              behind Pro"      ↓
                                                               every machine     cancel / sign out
                                                               after: one cmd    browser + CLI
```

### Where it breaks today

| # | Break | Evidence |
|---|---|---|
| 1 | **The key must be pasted on every machine.** `tashan activate <key>` is the only way in. | `cli/tashan.mjs:510` |
| 2 | **No browser-first login.** Handoff is CLI→browser only, and presupposes the key. | `functions/api/account.js` header |
| 3 | **`/welcome` is unreachable after you close the tab.** Not in nav, not in footer, not in the sitemap (noindex, correctly) — but nothing links to it. | `web/welcome.html` |
| 4 | **The site never shows signed-in state.** Nav account glyph is static on all ~5,900 pages. | `pipeline/chrome.py` nav is static HTML |
| 5 | **Pro is invisible.** Nothing anywhere says "you are Pro". | no consumer of `/api/account` outside `/account` |
| 6 | **No upsell where the value is.** The security block names findings but never offers the fix. | `pipeline/prerender.py` `security_block()` |
| 7 | **`/welcome` content is a manual.** Two numbered steps, shell snippets, "copy your licence key". | `web/welcome.html` |

---

## Backlog, in dependency order

### P0 — the funnel must function

- [x] **1. Device-authorisation login (`npx tashan-cli login`).** The OAuth device-grant shape every
      developer already knows from `gh auth login` / `wrangler login` / `stripe login`.
      - `POST /api/device` → `{device_code, user_code, verify_url, interval}`; store in KV, TTL 600s
      - CLI opens `/activate?code=<user_code>`, polls `POST /api/device {device_code}`
      - browser approves (session cookie → binds key to the device code)
      - CLI receives the key, calls Polar `/activate`, writes `~/.config/tashan/key`
      - poll states must be explicit: `pending` / `slow_down` / `denied` / `expired` / `ok`
      - **the key is typed ONCE, in a browser, ever** — never once per machine
- [x] **2. `/activate` page.** The browser half of the above. Shows the user code for confirmation,
      approves with one click when a session exists, and when it does not offers exactly two doors:
      *buy Pro* or *paste the key from your email once*.
- [~] **3. Post-checkout auto sign-in.** Polar success URL → land signed in, not holding homework.
      **Verify first** what Polar's success URL can carry (`checkout_id`, customer session token) —
      do not guess at their API. If nothing is verifiable, fall back to: `/welcome` gets one
      "Sign in with your key" field that sets the cookie, and the CLI never needs it again.
- [x] **4. Session state in the nav, on every page.** `chrome.py` emits the shell; `site.js` fills it
      from `/api/account`. Signed out → "Sign in". Signed in → the account glyph, marked. Pro → the
      Pro mark. Must not flash the wrong state on load, and must degrade to signed-out if the API
      is unreachable — never to a false Pro.
- [x] **5. Sign out, in both places.** `DELETE /api/account` exists and nothing calls it from the nav.
      CLI: `tashan logout` (alias of `activate --forget`, which nobody will guess).

### P1 — make Pro felt, and sell it where the value is

- [x] **6. Pro visual identity.** nav mark + `doctor` state line + `/account` badge. Nav mark, `/account` header, `doctor` output, and the favicon-adjacent
      brand lockup. Must read as status, not as a badge we award ourselves. Accent colour is reserved
      for measured data — pick a treatment that does not break that rule.
- [x] **7. Upsell in the security block** (`prerender.py`) — the one place the reader has a problem we
      solve. Never hide that a finding EXISTS. Offer only the part Pro buys: which advisory, the
      fixed version, what the install script runs. One offer, per page, earned.
- [-] **8. Upsell on the Index** — DROPPED, see iteration 4. — only against a real state (e.g. the board filtered to
      deprecated/archived), never a standing banner.
- [x] **9. Upsell in `doctor`** — already partly there; make it name the count of actionable findings.
- [x] **10. `/welcome` rewritten** as a state page, and reachable: linked from `/account`, from the
      nav when signed in, and from the CLI's success output.

### P2 — the rest of the lifecycle

- [x] **11. Cancel / renewal** surfaced in `/account` without bouncing to Polar unexplained.
- [-] **12. Machines list** — count shipped; the DEVICE LIST needs Polar's customer session (org token), same blocker as item 3. `tashan logout` releases a seat from the machine itself.
- [x] **12b. Machines count** — `/account` shows the count; show the devices and let one be released.
- [x] **13. Agent surface.** The MCP server should report licence state so a coding agent can say
      "this needs Pro to get the fixed version" instead of failing opaquely.
- [x] **14. Expired / refunded / revoked** states render as themselves everywhere, not as signed-out.

### P3 — SEO / GEO, alongside

- [x] **15. Head-to-head `/compare/<a>-vs-<b>`** — 212 pages at top-8-per-category, both sides
      measured, free-tier data only. Estimated in-session; gate: same category, scored, ≥1k wk dl.
- [-] **16. Per-page OG images** — DROPPED, see iteration 8. for capability + role + category hubs.
- [x] **17. `Dataset` JSON-LD** for the export, so the corpus is citable as a dataset.
- [x] **18. Sweep every page** for title/description/heading quality at the standard the homepage now
      holds — several were written before the current voice.

---

## Rules for this loop

1. **Nothing ships that is not verified in a real browser against the live origin.** curl proves the
   file, not the pixel. The CSP class of bug shipped 33,000 times because of exactly this.
2. **The firewall is absolute.** Nobody pays to change a score, rank or listing. Upsell sells depth,
   never position. `tests/test_firewall.py` governs.
3. **Free always names the existence of a finding.** Pro buys which one and the fix. Hiding the
   existence would make the audit a hostage situation.
4. **Run the suite before every deploy**, and `bump_assets.py` AFTER the last edit, never before.
5. **A session must never be faked.** Unreachable API → signed out. Never optimistic Pro.
6. Log what was dropped and why. A silent cap reads as coverage.


---

## Iteration log

**Iteration 1 — items 1 & 2 shipped.**
`functions/api/device.js` (RFC 8628 grant, KV-backed, 10-min TTL, single-use device code, approval
requires a live session AND a re-validated licence), `web/activate.html` + `web/js/activate.js`
(three states, never optimistic about a session), `tashan login` / `tashan logout` in the CLI,
14 tests in `functions/api/device.test.mjs` wired into `tests/run.sh`. `/welcome` rewritten from a
two-step key-paste manual into one command. Verified against the live origin: start → pending →
lookup → **approve without a session returns 401**, and the page renders the signed-out two-door
state at `?code=`. Deploy `a79a5372`.

Note for item 3: `activate <key>` is retained deliberately for CI, where there is no browser.

**Iteration 2 — item 3 partially, items 4 & 5 shipped.**

*Item 3 is deliberately parked at the fallback, with evidence.* Polar's `success_url` does support
`?checkout_id={CHECKOUT_ID}`. Exchanging that for a licence key needs
`customer-portal/license-keys/list`, which needs a customer session, which is created by a
server-side endpoint requiring the **organisation access token** — a credential that can read every
customer's record, which `wrangler.toml` says is deliberately absent. Putting it in an edge function
behind a path keyed only by an id that travels in URLs, history and Referer headers is a bigger trust
surface than this product has asked for, so it is the founder's call, not a 2am one.
**Fallback shipped instead:** `/welcome` is now a state page — signed out it is one autofocused key
field ("One paste, once"), signed in it greets you by email and hands you `tashan login`. The key is
still typed at most once in a lifetime; this only decides whether that once is here or on machine
one. *If the org token is ever added, `/welcome` becomes a redirect and nothing else changes.*

*Items 4 & 5.* `chrome.py` now bakes a neutral session shell into all ~5,900 pages and `site.js`
paints it from `/api/account`: signed out → "Sign in"; signed in → marked glyph; Pro → a hairline
`PRO` pill. It starts neutral and only ever ADDS, so no page flashes a wrong state, and an
unreachable API stays signed out — never an optimistic Pro. Cached per tab for 60s so browsing the
Index does not put a Polar call in the critical path; sign-out drops that cache first, so the mark
cannot outlive the session. The Pro pill deliberately does **not** use jade — the accent is reserved
for measured data, so status uses a hairline outline instead.

Found and fixed while verifying: `.nav__acct` is a fixed 2rem circle, so the new pill squeezed the
account glyph to `width: 0`. Guarded at the class level with `flex:none` on the glyph rather than
patching this one instance. Deploys `ecc1290d`, `8264126a`.

**Iteration 3 — item 7 shipped.**
The security audit now carries an EARNED offer: rendered only where detail is genuinely gated
(advisory / install script / remote content), naming the withheld part for that specific capability
and the count. **276 of 5,788 pages carry it; 1,121 scanned-and-clean pages carry none**, and the
sub-line no longer promises "detail needed to act" on a page where nothing is withheld. Two new
checks in `tests/test_site.py` hold the rule: no upsell where nothing is gated, and every offer names
a finding the page already showed for free.

`capability.js::revealPaid` removes the offer entirely once `/api/security` answers — a customer must
never be shown an ad for the thing they already bought.

**The bug worth remembering:** the offer shipped server-side first and was *invisible in the browser*.
`capability.js` replaces the whole prerendered dossier via `el.innerHTML`, so anything the server
renders inside the audit that the client does not render simply disappears for every reader with JS.
Caught only by looking at the live page — the served HTML contained `.secoffer` while the DOM did
not. Same one-concept-two-copies failure this codebase keeps finding. Deploys `5b443f3a`, `ab76c793`.

**Iteration 4 — item 9 done, item 8 dropped, and a dead control removed.**

*Item 8 is dropped, not deferred.* The only honest trigger for an Index offer is a reader looking at
something broken. The board carries **1,590 rows: 0 with advisories, 0 deprecated, 0 archived, 0
abandoned** — it is the healthy head of the corpus by construction. I built the offer against the
`abandoned` facet, deployed it, and it correctly never fired, because that facet matches nothing.
Shipping it would have been dead code wearing the costume of a feature. The alternative — a standing
banner — is what the backlog forbids and what readers train themselves not to see. So: no offer on
the Index. The 276 capability pages that *do* have something wrong carry it, which is where the
reader actually has the problem.

*What that exposed.* "Hide deprecated/archived" was rendered unconditionally on a board holding zero
of them, so the control could only ever do nothing. A filter that never changes the result teaches a
reader that none of the filters work. It is now gated on a real count, like every other facet.

*Item 9* was already right — `doctor` counts findings whose detail is withheld, says nothing on a
clean run, and prints the licence state every run. Added only the missing next step: the offer now
ends `already bought? tashan login`, because the answer to "I paid, now what" must be a command, not
a price. Deploys `66766aaa`, `1e0e5e23`.

**Iteration 5 — items 6, 10, 11 closed; the site stopped teaching the old flow.**

Every page still told customers to `tashan activate <key>` — the flow item 1 replaced. Six places
fixed: `/pricing` FAQ (twice), `/support`, `/account`'s signed-in note, `/welcome`. `activate` now
appears only where it is still correct: CI, where there is no browser to open. `activate --forget`
became `tashan logout` in the copy too.

**The signed-out `/account` was a dead end** — it offered only `npx tashan-cli account`, which needs
a machine that ALREADY holds a licence. For the exact person that page is for (closed the welcome
tab, came back later, has nothing set up) it could not help. It now leads with the direct way in.

*That would have been the third copy of one credential form* (/activate, /welcome, /account), so it
is now **`web/js/signin.js`, defined once** — markup, POST, error strings, and the rule that a failed
submit keeps the value rather than making someone retype a 40-character key over one stray space.
This codebase has been bitten twice this week by two-copies-that-drift; a credential form is the last
place to allow a third. Verified live on all three pages, including a real rejection round trip
against the API: error shown, value kept, button re-enabled.

*Item 12 is split.* The machines COUNT ships. The device LIST with per-device release needs Polar's
customer-session API — the same organisation-token blocker as item 3. `tashan logout` already
releases a seat from the machine itself, which is the case that matters. Deploy `efe44140`.

**Iteration 6 — items 13 & 14. P2 closed except the org-token-blocked device list.**

*Item 13.* The MCP server told an agent "2 known advisories" and stopped. An agent is the last
checkpoint before something is installed on a machine, and one that can warn but not act will either
paraphrase vaguely or invent a remedy. `renderCheck` now names the gate and the command that opens
it — and when a licence IS present on the machine, points at `/api/security` so the agent can fetch
the real advisory ids and fixed versions. Clean capabilities get no pitch, asserted in
`cli/mcp.test.mjs`.

*Item 14.* An expired licence was rendering as a quieter "signed in" — the nav said "Your account"
over a lapsed subscription, so someone would discover it lapsed by having a command fail rather than
by reading their own header. It now says `tashan — licence expired`, keeps `is-in`, and drops the Pro
mark. Verified live through the real paint path for all three states. Deploy `fb101b26`.

**Next: P3.** Item 15 (`/compare`) is going ahead — the instruction was to finish without asking.

**Iteration 7 — item 15. 212 head-to-head pages, sitemap now 6,107 URLs.**

`pipeline/gen_compare.py`. Gate: same category, both scored, both ≥1,000 weekly downloads, top 8 per
category → 28 pairs each, 212 total. Without a floor this is 5,788² pages of doorway spam, which
earns a manual action rather than traffic.

**The URL is alphabetical and the content is ranked, deliberately.** A slug ordered by score would
change the day two capabilities crossed, churning the one asset that takes months to earn.
Alphabetical is stable for the life of the pair.

**The verdict is derived, never editorial** — ≥10 points is "a real separation rather than noise",
3–9 is "a narrow lead, read the evidence", <3 says the score does not decide it. Saying so on the
close ones is what makes the decisive ones worth believing.

Free-tier data only: both scores, the raw evidence, freshness, upkeep, expertise grade and the
EXISTENCE of findings. Never the paid detail. Each category hub adopts its own comparisons from
`web/data/compare.json` — one definition of which pairs exist, so a hub can never link to a page
that was not written.

**Caught by the suite:** `bump_assets.py` had a hardcoded generator list, so all 212 pages froze at
the previous `?v=`. That list is now ordered to mirror `run.py`, and the `--check` assertion is what
found it — 24,134 references now agree. Deploy `f993aa79`.

**Iteration 8 — items 17 & 18 shipped, item 16 dropped. Backlog closed.**

*Item 16 dropped.* Social platforms do not accept SVG for `og:image`, so per-page cards need a
rasteriser — PIL, cairo, or Cloudflare's paid Browser Rendering binding. None is available and
"stdlib only, no pip deps, no build step" is a stated feature of this project, not an accident. The
shared card stays. Revisit only if a rendering binding is already being paid for.

*Item 17.* The homepage now declares the corpus as a schema.org `Dataset` — 6 `variableMeasured`
entries naming what each number means, `measurementTechnique`, licence, and 4 `DataDownload`
distributions. **Every declared URL was verified to serve 200 with the right content type**, because
a Dataset pointing at a 404 is worse than no Dataset. This is the entity an answer engine reads to
learn that the numbers it is about to quote come from a maintained machine-readable source rather
than from scraped prose.

*Item 18.* Two titles were being truncated mid-phrase in a result (65 and 64 chars) and five
descriptions were either over 160 or under 70. All rewritten to keep the claim and drop the padding.
Two new suite checks hold it: titles ≤62, descriptions present and ≤165, noindex pages exempt — and
the check immediately caught my own replacement homepage description at 166. Deploy `c913ce55`.


---

## P4 — the polish the first pass never looked at

The original 18 items are closed. These are the surfaces that were never examined at all, which is a
different thing from being finished. Same rules apply.

- [x] **19. Mobile and small viewports.** Every verification this session was done at desktop width.
      The board is a 5-column table, the comparison table is 4 columns, the job grid is 23 cards and
      the nav is 4 links plus a pill. At 390px at least one of those is wrong. Check the real
      breakpoints in a real viewport, not by reading the CSS.
- [x] **20. Keyboard and screen-reader pass.** The palette (`/`, ⌘K), the job picker buttons, the
      facet toggles, the sign-in forms, the comparison table. Focus order, visible focus rings,
      `aria-pressed` correctness, table header association. One unlabelled control was already found
      and fixed this session by accident — do it deliberately.
- [x] **21. Core Web Vitals on a real page.** `tests/test_site.py` holds a TTFB and HTML budget, but
      nothing measures LCP, CLS or INP. The board renders 100 rows client-side after two fetches;
      the hero runs a canvas animation. Measure before assuming either is fine.
- [x] **22. Walk the whole funnel as a stranger.** Not component checks — one continuous journey:
      land from a search result on a capability page, follow the audit, hit the offer, reach pricing,
      come back via `/account` signed out, sign in, and confirm every link on that path resolves and
      says the same thing. The pieces are verified; the *path* is not.
- [x] **23. Spot-check the generated tiers at scale.** 5,788 dossiers, 212 comparisons, 20 role hubs
      all got template changes tonight. Sample across kinds (npm / registry / plugin / skill, scored
      and unscored, clean and flagged) and confirm none of tonight's edits produced a broken page for
      a shape I did not have in front of me.

**Iteration 9 — item 19. Mobile checked in a real 390px viewport, not by reading CSS.**

*What held.* No horizontal page scroll anywhere. Nothing overflows outside its designated scroller —
the board table and the comparison table both scroll inside their own containers, which is the
pattern the rest of the site already uses. Role cards reflow to 2 per row. The comparison table's
"what it means" column correctly drops out below 46rem.

*What was broken.* **55 tap targets under 32px, including the header links at 22px** — which fails
WCAG 2.5.8's 24px minimum outright, on the primary navigation, on every page. Fixed with
`padding-block` rather than type size: the hit area grew to 42px inside a nav bar that was already
tall enough, so nothing moved visually. Brand likewise.

*What was deliberately left.* Left-rail rows stay at 30px — that clears the 24px minimum, and the
rail height has already been tuned against the viewport once (at 33px the two lists ran past the
fold and reintroduced the nested scrollbar the truncation exists to remove). Board row links are
18px but the whole 64px row is the click target, which is the real affordance. `Methodology` is
`display:none` in the mobile header by an existing documented decision — longest label, one tap away
in the footer, and dropping it keeps brand + three links + glyph on one row down to 375px. Verified
that reasoning still holds; the padding change is vertical only. Deploy `b184454c`.

**Iteration 10 — item 20. Four real findings, all fixed.**

1. **The homepage was the only page in the site with no `<main>` landmark.** Every other page had
   one; index.html put its sections straight in `<body>`. A screen-reader user had no way to jump to
   the content.
2. **No skip link, anywhere.** Reaching the board on the Index meant tabbing past the brand, four
   nav links, the account glyph, 28 tag chips, 15 category chips and every facet toggle. Added to
   `chrome.py` so it lands on all ~5,900 pages, visually hidden until focused. `NAV_RE` was widened
   to swallow it too — otherwise every chrome re-run would have stacked another copy. Verified
   idempotent: second run rewrites 0 pages, exactly one skip link on the page.
3. **Table headers carried no `scope`.** Now `scope="col"` on the board, the hub boards, the learn
   tables and the comparison table. 5/5 on the Index.
4. Every `<main>` now carries `id="main"`; prerender's kept its hydration hook by moving the skip
   target onto the element rather than renaming `#cap`.

*Checked and found already correct:* a global `:focus-visible { outline: 2px solid var(--jade) }`
covers every control; the two `outline:none` rules both replace it with a visible border, which
satisfies WCAG rather than defeating it. One `h1` per page. No unlabelled SVG. Heading order clean.
Role cards are real `<button>`s carrying `aria-pressed`. Deploy `01aa5d92`.

**Iteration 11 — item 21. Measured, not assumed. All three vitals good with room to spare.**

| | homepage | capability dossier | threshold |
|---|---|---|---|
| LCP | 720 ms | 540 ms | < 2500 ms |
| CLS | 0.0225 | 0.0211 | < 0.1 |
| INP | < 16 ms | — | < 200 ms |
| long tasks | none | none | — |
| TTFB | 190 ms | 346 ms | |

INP measured with real interactions, not proxied: picking a job re-ranked the board to 26 rows and
`/` opened the palette, and **no event entry crossed the 16 ms observer threshold at all**.

*What the small CLS actually is, since a number without a cause is not a measurement.* On the
homepage, one 0.0225 shift at 719 ms — `#rolegrid` ships empty and JS inserts 23 cards above the
board. On a dossier, two shifts totalling 0.0211 — `capability.js` replacing the prerendered summary
with the taller full render. Both are inherent to the hydrate-after-paint design, both are a fifth of
the "good" threshold, and both fixes (a min-height that would be wrong at some breakpoint, or
server-rendering the job grid) cost more than 0.02 of CLS is worth. **Left alone deliberately.**

*Locked instead:* a check that the board still opens as a teaser. At 100 rows it was a 7,500px table
and 75% of page height — that decision is what bought these numbers, and it is the one a future edit
could quietly undo.

**Iteration 12 — item 22. The path walks clean; one silent defect found in the middle of it.**

Walked as one continuous session, clicking real links rather than typing URLs:
1. **Dossier** — all 16 internal links resolve 200, the earned offer is present, nav reads "Sign in".
2. **Clicked the offer** → `/pricing?ref=…` — `ref` preserved through the navigation, `$6/mo` matches
   the offer, page says `tashan login`, and says `activate` only in its CI sentence.
3. **Footer → Account**, arriving cold as someone who closed the tab — two ways in, the key field,
   both help texts correct, portal and pricing both linked.

**The defect: `?ref=` was unencoded server-side and percent-encoded client-side.** The same
capability arrived at `/pricing` as `pkg:@ansvar/qatari-law-mcp` from the prerendered page and
`pkg%3A%40ansvar%2Fqatari-law-mcp` once `capability.js` replaced it — and since capability.js
replaces the whole dossier, which one a reader clicked depended purely on whether JS had finished.
Attribution split in half, silently, on the one measurement that says which dossiers earn money.

Both encode now, verified byte-identical on the live page. A check asserts no `?ref=` contains a raw
`:`, `@` or `/` — and it earned itself immediately: my first fix patched only one of the two call
sites and the check caught the other 183 pages. Deploy `927e50d3`.

**Iteration 13 — item 23. 41 pages, 17 shapes, 3 tiers, zero problems. P4 closed.**

Sampled deliberately across shapes never personally opened: registry-only, plugin, skill, unscored,
no description, no source repo, deprecated, archived, unscanned, carrying advisories, remote kind,
single-maintainer, graded deep, graded slop, no tasks — plus 6 comparison pages and 6 role hubs.
Checked each for literal `None`/`undefined`/`NaN`, empty titles, double-escaped entities, missing
`h1`, unparseable JSON-LD, missing `#main`, missing skip link, raw `?ref=`, and surviving inline
styles. **All 41 clean.** Tonight's template edits held on every shape.

---

## ⚠ FOR THE FOUNDER — a live defect I cannot fix from here

**Cloudflare Bot Fight Mode 403s `Python-urllib`, and only `Python-urllib`.** Verified live:

| client | result |
|---|---|
| `curl`, `python-requests`, `node-fetch`, `Go-http-client`, GPTBot, ClaudeBot | **200** |
| `Python-urllib/3.x` | **403** |

That 403 covers `/v0.1/scores`, `/v0.1/servers`, `/data/capabilities.json` and `/llms.txt` — every
endpoint `llms.txt` advertises and every `DataDownload` the new `Dataset` schema declares. The site
publishes a machine-readable corpus and blocks the most common zero-dependency way to fetch it from
Python — an idiom this project's own pipeline is built on.

Same **Security → Bots → Bot Fight Mode** toggle that is still injecting a CSP-blocked script into
every page. One switch fixes both. I cannot reach the dashboard.

---

## ⚠ UNCOMMITTED WORK FROM A PARALLEL SESSION — do not commit until these two clear

The working tree carries an in-progress scoring/tagging change (`npm_keywords`, doc-signals,
`tag_capabilities`, plus a full regenerate). **It fails two guardrails**, and both are alarms this
project installed deliberately:

1. **`tests/test_scorer_version.py`** — the scoring changed again AFTER `s2 → s3` was accepted, so
   the fingerprint no longer matches `pipeline/scorer.lock`. Every stored `signal_history` point
   would claim comparability with points measured by a different ruler, and `trend()` would report
   *our* recalibration as a customer's capability declining. That is the exact failure the column
   exists to prevent (`pkg:3dstreet-mcp` once read 43,43,43,43,42,40 — every step down a rewrite).
   **Fix:** bump `SCORER_VERSION` to `s4` in `pipeline/build.py`, then
   `python3 tests/test_scorer_version.py --accept`. Never `--accept` without the bump.

2. **`tests/test_classify.py`** — the two largest categories now hold **65.7%** of the board against
   a 62% ceiling (devtools + productivity). The taxonomy has stopped sorting.

Whoever owns that change should land it. It is not mine to bump a scorer version for — the version
string is a claim about comparability of published numbers, and only the author of the change knows
whether it is one.
