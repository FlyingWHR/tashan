# The story, for builders

How to talk about tashan to someone who builds with agents. Not a pitch deck — the argument, in the
order it actually convinces, with the numbers that carry it. Everything here is true today and
checkable on the site; if a number below stops matching `/paid.html` or the board, the number below
is the one that is wrong.

---

## The one sentence

**Everything anyone tells you about an AI capability is claimed. We measure it — and the newest
measurement is the only one that isn't a proxy: money.**

## The thirty seconds

> You are about to add an MCP server to your agent. What do you actually know about it? A star
> count, a download number, and a README written by the person who wants you to install it.
>
> tashan measures the field instead: 11,584 capabilities scored on upkeep, freshness and real
> adoption, audited against OSV at the version you would install today. Nobody can pay to move a
> rank — that is a test in the repo, not a promise on an about page.
>
> And now the part nobody else publishes. Of the 1,079 x402 payment addresses we could resolve,
> 997 have been paid at least once — and the median service has earned **fifty-one cents** in its
> entire life. Two thirds of all volume is one receiver. If you are about to build for the agent
> economy, that is the number you needed before you started.

---

## Why a builder should care, in the order they will ask

**1. "I have to choose dependencies I won't regret."**
Downloads measure how many machines ran `npm install`, which is mostly CI. Stars measure how many
people liked a tweet. Neither survives contact with "is this maintained, and will it still be here
in six months?" tashan answers that with upkeep, freshness, vitality and a bus-factor flag, each
linked back to the public source it came from. An unmeasured capability is published as unmeasured,
never as zero — because absence of evidence is not a finding.

**2. "I need to know what's already rotting in my stack."**
`npx tashan-cli doctor` reads the agent config on your machine — Claude Code, Desktop, Cursor, VS
Code, Windsurf, `~/.claude/skills/` — and names what is deprecated, archived, abandoned, running an
install-time script, or shadowing an official package name. Local only: no account, no key, no
upload. On a real machine it finds things the owner did not know were there; the one that lands is
usually "113 of your skills are owned by no plugin — nothing will ever update them but you."

**3. "My agent should check before it installs, not after."**
Four MCP tools — find, check, audit, and *has anyone actually paid for this*. The answers carry
their own caveats, because an agent cannot ask a follow-up question: a malicious package is refused
outright, a clean scan says "nothing known is wrong" rather than "safe", and a name we have never
seen comes back as *unmeasured, not necessarily bad — do not present absence as a warning*.

**4. "Is there any money in building for agents?"**
This is the one only we can answer, and the honest answer is more useful than the hopeful one:
$247k has settled across 10.4 million x402 payments, 997 of 1,079 listed services have been paid at
least once — and the median one has made $0.51. 592 have earned under a dollar; nine have earned
over a thousand. The top receiver alone is 67% of all volume. That is not a market yet. It is a
real, measurable, growing signal, and knowing its shape is worth more to a builder than a forecast.

---

## The three proofs that we mean it

These are what turn a directory into an instrument, and they are the part to say out loud.

- **Nobody can buy a rank.** `tests/test_firewall.py` reads the scorer's source and fails if it
  touches a column that is not public signal. Payment buys depth and tooling, never position.
- **Absence is published as absence.** Unscored capabilities are missing from the board rather than
  scored zero; `paid_seen_at` exists so a measured zero ("this address has never been paid") can
  never be confused with "we did not look".
- **We are in our own table.** tashan publishes an x402 price, so it appears on `/paid.html` like
  every other row — last, $0.00, never paid. Nobody put it there and nobody exempted it. An
  instrument that leaves itself out of its own measurement is not an instrument.

## The line that lands

> Downloads tell you a machine installed it. Payment tells you someone needed it.

## What we do not claim

Say these before anyone finds them, because they are the questions a good builder asks second:

- **Not a security audit.** We read public advisories, declared dependencies and install scripts. We
  do not run the code, read the source, or test for prompt injection. A clean result means nothing
  *known* is wrong.
- **The grade reads documentation, not quality.** Instruction depth is a read of what the docs
  cover — per-tool docs, worked examples, setup, a stated limitation — against a published rubric.
  It is not a judgment of the software, and we withdrew two grading bands (`wrapper`, `slop`)
  precisely because they claimed more than reading a README can support.
- **Payment is not quality, and unpaid is not bad.** Almost every MCP server is free by design.
  Being unpaid is the normal case; it is never a defect, and payment is deliberately not an input to
  the score.
- **The paid data is Base, and x402 only.** Other chains, other rails and private billing are
  invisible to us. We publish what is on the ledger we can read.
- **Coverage is uneven and stated.** The aggregate measured/tracked ratio falls every time discovery
  succeeds, so we report it and never target it. The commitment is over the top 100 and top 1,000 by
  adoption evidence, because what costs a reader is an absence on the thing they looked up.

---

## Where to send them

| they want | send them to |
|---|---|
| to see the ranking | `tashan.sh` |
| to check their own machine | `npx tashan-cli doctor` |
| to let their agent check | `npx tashan-cli mcp`, or `curl tashan.sh/v0.1/scores` |
| to see the money | `tashan.sh/paid.html` — and the query is printed on the page, so they can re-run it |
| to argue with a number | `tashan.sh/methodology.html`, then the repo |
