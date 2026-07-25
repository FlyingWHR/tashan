# tashan — brand & design system

> **tashan** — the intelligence layer for AI capabilities. *Measure what actually works.*

## The name
**tashan** (他山) is from the Chinese proverb **他山之石，可以攻玉** — *a stone from another
mountain can polish your jade.* It's the product thesis in three characters: we judge the
field using the field's **own public evidence** (its stones — registries, npm, git history,
the READMEs people wrote) to reveal which capabilities are jade and which are gravel. We bring
no stone of our own to sell; we only sharpen with what's already out there. Always lowercase —
it's a command you run (`tashan`, `tashan.sh`, `npx tashan`), not a company you shout.

## Positioning
Not a directory, not a store — an **instrument**. Closer to Bloomberg / Consumer Reports /
Michelin than to npm or the GPT Store: an institution people trust because it **measures**,
independently, and doesn't sell the answer. Trust is an *output of evidence*.

## Identity thesis — the terminal
The visual DNA is the **Bloomberg terminal**: **near-black + amber**. Amber is the one signal
color — it reads as a measurement readout, a standard, an authority (and it is *not* the
emerald every dev-tool and the blue every SaaS defaults to). All data renders in **monospace**,
like an instrument. Restraint is the point: no gradients, no blobs, no illustration — numbers,
hairlines, and black space.

## Color
| Token | Value | Use |
|---|---|---|
| `--bg` | `#09090b` | page — warm near-black, never pure #000 |
| `--surface` | `#111114` | cards / board |
| `--surface-2` | `#17171b` | hover / elevated |
| `--hairline` | `rgba(255,255,255,.08)` | borders, grid |
| `--text` | `#ededf0` | headings / primary |
| `--text-dim` | `#8a8a93` | body |
| `--text-faint` | `#5b5b63` | labels, meta |
| **`--amber`** | **`#e9a23b`** | **the one signal color** — scores, the mark, key data |
| `--green` | `#4fd08a` | "active / fresh" (used sparingly) |
| `--red` | `#f2604a` | "stale / churned" |

One accent, used *only* for measured signal. If everything's amber, nothing is.

## Type
Self-hosted, no external requests (privacy + speed):
- **Geist** (variable 100–900) — sans, headings, UI. Display = large, weight ~500, tight (`-0.03em`).
- **GeistMono** (variable) — **all data, numbers, scores, labels, the eyebrow/kicker.** Mono =
  instrument. `font-feature-settings: "tnum"` for aligned figures.
- `ui-serif` — reserved for the occasional editorial pull-quote (gravitas, the manifesto). Nothing else.

Rule: **numbers are mono, prose is sans, wisdom is serif.**

## Components
- **Wordmark:** amber rounded-square mark (`brand__mark`, glowing) + `tashan` in Geist 600, with a
  mono `v1 · public-signal` chip.
- **The Index (leaderboard):** hairline-bordered dark table, mono numerals, the headline metric
  ("Signal") in amber with a thin gradient bar. Rows are the product.
- **Chips:** mono pill filters; active = solid amber, black text.
- **Buttons:** white pill primary (act), ghost hairline secondary (with amber-tint hover).
- **Callouts:** amber-line box on amber-dim fill — for the honest caveats and the mission.
- **Freshness:** green `active` / grey `Nmo` / red `Ny` — a one-glance liveness read.

## Voice
Precise, evidence-first, quietly confident, **humble about the unknown**. Short declaratives.
No hype, no exclamation, no adjectives we can't measure. We say plainly what we *can't* yet
measure and call it the roadmap. Signature line: **"Measure what actually works."** Core stance:
**measured, not claimed.**

## What to never do
Pay-to-rank. Star-counting. Fabricated scores. A single black-box number. Illustration/gradients.
Any claim we can't derive from public evidence.
