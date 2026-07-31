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

- [~] **6. Pro visual identity.** (nav mark shipped; `doctor` + `/account` header remain) Nav mark, `/account` header, `doctor` output, and the favicon-adjacent
      brand lockup. Must read as status, not as a badge we award ourselves. Accent colour is reserved
      for measured data — pick a treatment that does not break that rule.
- [x] **7. Upsell in the security block** (`prerender.py`) — the one place the reader has a problem we
      solve. Never hide that a finding EXISTS. Offer only the part Pro buys: which advisory, the
      fixed version, what the install script runs. One offer, per page, earned.
- [ ] **8. Upsell on the Index** — only against a real state (e.g. the board filtered to
      deprecated/archived), never a standing banner.
- [ ] **9. Upsell in `doctor`** — already partly there; make it name the count of actionable findings.
- [ ] **10. `/welcome` rewritten** as a state page, and reachable: linked from `/account`, from the
      nav when signed in, and from the CLI's success output.

### P2 — the rest of the lifecycle

- [ ] **11. Cancel / renewal** surfaced in `/account` without bouncing to Polar unexplained.
- [ ] **12. Machines list** — `/account` shows the count; show the devices and let one be released.
- [ ] **13. Agent surface.** The MCP server should report licence state so a coding agent can say
      "this needs Pro to get the fixed version" instead of failing opaquely.
- [ ] **14. Expired / refunded / revoked** states render as themselves everywhere, not as signed-out.

### P3 — SEO / GEO, alongside

- [ ] **15. Head-to-head `/compare/<a>-vs-<b>`** — 212 pages at top-8-per-category, both sides
      measured, free-tier data only. Estimated in-session; gate: same category, scored, ≥1k wk dl.
- [ ] **16. Per-page OG images** for capability + role + category hubs.
- [ ] **17. `Dataset` JSON-LD** for the export, so the corpus is citable as a dataset.
- [ ] **18. Sweep every page** for title/description/heading quality at the standard the homepage now
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
