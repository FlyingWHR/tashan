# tashan — the launch script

*Written 2026-08-01. Every number below is queried from `data/tashan.db`, and the query is printed
beside it. If a number can't be re-derived on demand, it doesn't go in the script — a marketing claim
we can't measure is the exact sin the product exists to point at.*

---

## The voice problem, and its resolution

A viral script wants punch. The brand wants restraint (`PROJECT.md` §12: plain grounded copy, accent
reserved for measured data). These look opposed and aren't.

**The numbers are the punch. The voice stays flat.** For a developer audience, understatement over
damning evidence travels further than enthusiasm ever does — and it's the only register that doesn't
undercut the thesis. A measurement company that oversells its own measurements has already lost the
argument. Read every line below deadpan. Nothing is exclaimed.

---

## Primary — 75s, screen recording + voiceover

**Hook has to land in 4 seconds or the rest never plays.**

| Time | Voiceover | On screen |
|---|---|---|
| 0:00–0:07 | "This was the top-ranked security tool on my own site. Its README opens with three words: *we've decided not to maintain this.*" | The dossier, Trust **70**, `#1`. Then the README scrolls to `# 不维护决定`. |
| 0:07–0:15 | "My scorer couldn't read it. It was checking whether GitHub's archive box was ticked. Nobody ticks the box. They just write it and walk away." | The GitHub repo page. Archive box: unticked. Last push: 18 days ago. |
| 0:15–0:24 | "That's the whole problem with picking an MCP server. Everything you can check quickly is a proxy, and every proxy has a way of being wrong." | Stars, downloads, last-commit badges — each greying out one by one. |
| 0:24–0:36 | "So: 12,638 capabilities tracked. 6,075 scored on public evidence — adoption, maintenance, freshness. The arithmetic is on the page. You can disagree with it." | The index scrolling. Hover a score → the methodology breakdown opens. |
| 0:36–0:52 | "Of the 1,859 npm-backed ones audited: 159 run a script on your machine at install time, before you ever call a tool. And only 381 can prove who built them." | Counter: `159`. Then `381 / 1,859`. Let the second number sit. |
| 0:52–1:03 | "Two were malicious. Those are delisted — but the CLI still warns you if you're already running one, because deleting the listing doesn't uninstall the package." | `npx tashan-cli doctor` → the warning line. |
| 1:03–1:12 | "Nobody can pay to change a score. There's nothing to buy — we don't sell, host, or run any of it. That's not a promise, it's a test that fails the build." | `tests/test_firewall.py` running. Green. |
| 1:12–1:15 | "tashan dot sh. It's free." | `tashan.sh` |

**The 0:52 line is the one that earns the share.** Everyone in this space announces a takedown.
Almost nobody admits that a takedown doesn't reach the machines that already installed it.

---

## Alternate hooks — same body, swap the first 15 seconds

**A. The provenance one** (best for a supply-chain audience)
> "npm signs every package it hosts. So if you check signatures to see whether a publisher really
> built the thing, 266 out of 266 come back verified. It's a meaningless check. The real one —
> did this get built in CI by its publisher — passes for 381 of 1,859."

**B. The bus-factor one** (widest reach, least technical)
> "3,199 of the tools people are wiring into their agents have exactly one maintainer. Not one
> company. One person. That's not an accusation — most good software starts there. It's just a
> number nobody was publishing."

**C. The self-own** (highest trust, slowest burn)
> "I built a thing that rates AI tools. Last week it ranked a dead project first, and the evidence
> that it was dead was sitting in a field I'd already collected and never read. Here's the fix, and
> here's why the failure was structural."

Hook C is the one to lead with if the audience is skeptical or the account is new. Admitting the
instrument was wrong is the fastest way to be believed about what it says now.

---

## Fact-check — regenerate before every recording

Numbers move daily. Re-run this and update the script; a stale figure in a video about measurement
is unrecoverable.

```sh
sqlite3 data/tashan.db "
select 'tracked',            count(*) from capabilities
union all select 'scored',   count(*) from capabilities where tashan_score is not null
union all select 'audited',  count(*) from capabilities where sec_scanned_at is not null and npm_pkg is not null
union all select 'install script', count(*) from capabilities where sec_scanned_at is not null and sec_install_script is not null
union all select 'provenance',     count(*) from capabilities where sec_scanned_at is not null and sec_provenance=1
union all select 'malicious',      count(*) from capabilities where sec_max_severity='MALICIOUS'
union all select 'one maintainer', count(*) from capabilities where single_maintainer=1
union all select 'declared dead',  count(*) from capabilities where self_unmaintained is not null;"
```

As of 2026-08-01: tracked 12,638 · scored 6,075 · audited 1,859 · install script 159 ·
provenance 381 · malicious 2 · one maintainer 3,199 · declared dead 9.

---

## Claims that must NOT go in, and why

- **"The only honest score."** Smithery, Glama and LobeHub all ship a score (`docs/MARKET.md`). The
  differentiator is *disinterest* — we don't sell what we rate — not novelty. Claiming novelty is
  both false and instantly falsifiable by anyone who looks.
- **"We cover the MCP ecosystem."** We hold 12,638 against a field of ~61–81k. `PROJECT.md` §1 is
  explicit: say the denominator. "Whole-field coverage" is the same sin as any unmeasured claim.
- **"Typosquatting."** Two packages normalise to an official scoped name. That is a fact about
  strings. Intent is not something we measured, and naming it is a legal claim we cannot support —
  the site says "an official package with a similar name exists" and the script says nothing more.
- **Anything from the Pro table in `GROWTH.md`.** Watch/alerts, compare and on-demand grading are
  unbuilt. That table is the plan. A visitor falsified three advertised rows in thirty seconds once
  already, and it had to be pulled.
- **A security score.** Security columns deliberately don't feed `tashan_score` — azure is
  Microsoft-official, scores 86, and runs an install script. Folding them would hide exactly that
  case, and implying we ship a safety rating oversells what the audit is.

---

## Distribution

Cast range beats reach here (`PROJECT.md` §2) — a rating nobody sees at install time changes nothing.
Rank the surfaces by whether they reach someone *at the moment they're choosing*:

1. **The badge in the maintainer's own README.** Highest intent, and it travels without us.
2. **`npx tashan-cli doctor`** on a config someone already has — it finds real problems in
   thirty seconds and needs no account. This is the demo; the video is only an advert for it.
3. **HN / r/mcp / X.** Lead with hook C, link the methodology page rather than the homepage.
   This audience checks arithmetic, which is the one thing we're built to survive.
