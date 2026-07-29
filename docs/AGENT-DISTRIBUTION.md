# Who actually browses this, and how the agent finds us

Four questions, answered from what the platform does today rather than from what we assumed when the
site was designed.

---

## 1. What Claude Code already handles automatically

More than the site's information architecture assumes.

| Step | Who does it today |
|---|---|
| Add the official marketplace | **Automatic** — `claude-plugins-official` is available on startup |
| Add other marketplaces | `/plugin marketplace add <repo>` — one command, no browsing |
| Load skills | **Automatic** — anything in `.claude/skills/` is available |
| Choose a skill mid-task | **Automatic** — the agent matches the job to a skill's own description |
| Connect MCP servers | **Automatic** — everything in `.mcp.json` connects at session start |
| Invoke a tool | **Automatic** |

Installation, loading, selection and invocation are all handled. Two things are not, and they are the
only two we should be building for:

- **deciding what to install in the first place**, and
- **knowing whether what you already installed is any good, or still alive.**

Everything else on the site is decoration.

## 2. What a human should actually browse

Almost nothing. Nobody's job is to read 5,791 rows.

There are three real moments, and only three:

1. **"I have a job and don't know what exists."** → the task hubs (`/task/<slug>`). This is browse, and
   it is why the axis is filed by work rather than by what a tool touches.
2. **"Is what I'm already running dead?"** → `npx tashan doctor`. No browsing at all; the answer comes
   to you, and nobody else in the field answers this question.
3. **"Which of these two?"** → a capability page, arrived at from a search engine or an agent, not from
   our nav.

The board — sortable, filterable, 5,791 rows — serves the third moment badly and the first two not at
all. It is a *proof surface*: it exists so a sceptic can check the arithmetic, and so crawlers have
something to index. It should not be the front door, and treating it as one is the mistake the task
axis is correcting.

**The implication is uncomfortable and worth stating: our primary consumer is not a human.** It is the
agent, at the moment it discovers it lacks a capability. Optimise for that and the human surfaces get
simpler, not richer.

## 3. Is Anthropic building this in-house?

**Yes, partly — and it does not close the position.**

There is a curated, reviewed Plugin Directory inside Claude, and the official marketplace loads without
being asked. Any capability directory that competes on *listing* is competing with a first-party
surface that ships with the product. That fight is unwinnable and we should not pick it.

But what a platform curates and what tashan measures are different things:

| | Platform directory | tashan |
|---|---|---|
| Question answered | *What is allowed in?* | *What do people keep?* |
| Direction | supply side | demand side |
| Can it say "this official plugin is abandoned"? | No | Yes |
| Can it say "this has three users"? | No | Yes |
| Can it be disinterested about its own platform? | Structurally, no | Yes |

A store cannot be a disinterested rater of its own shelves. That is the same reason tashan sells nothing
it measures — and it is why Consumer Reports exists alongside every retailer rather than instead of one.

The real platform risk is not curation. It is Anthropic publishing **usage telemetry** — install counts
per plugin. They have that data and we never will. If it ships, our adoption signal is outclassed
overnight for plugins.

Two things survive that, and both are why the roadmap points where it does:
- **Retention over time.** Install counts say what was added. `signal_history` says what was *kept* and
  what was quietly removed. That series cannot be backfilled by anyone, including them, from a standing
  start.
- **Expertise.** Nobody grades whether a capability is any good. 333k skills, zero published quality
  measurements. This is the largest open position and it is the one we have barely started.

## 4. Positioning

**Not a directory. The measurement layer over every directory — including Anthropic's.**

We should be indifferent to where a capability is listed and opinionated about whether it works. That
means listing count is explicitly not a goal, official marketplaces are an input rather than a rival,
and the sentence to lead with is closer to:

> Anthropic's directory tells you what you can install. tashan tells you what survives contact with
> real use — measured, with the arithmetic published, and nothing you can buy moves it.

## 5. How coding agents come to use us

An agent will never visit a website. It will call something. Five mechanisms, cheapest first:

1. **`llms.txt`** — built. Passive; answer engines read it. Table stakes, not distribution.
2. **Badges** — built. Human trust and backlinks, not agent consumption.
3. **Subregistry endpoint** — *the one to build.* The MCP registry spec anticipates aggregators that
   implement its OpenAPI shape and inject their own metadata under `_meta`; the registry's own worked
   example is literally `user_rating` and `download_count`. Serve `/v0.1/servers` with `sh.tashan/score`
   under `_meta`, and **every host that already speaks registry API gets our scores without integrating
   with us at all.** Sub-registries doing exactly this (capability routing over the base registry) are
   already an established pattern. `docs/SOURCING.md` §6 called this "a strategic priority, not a
   nice-to-have" and it is still unbuilt.
4. **A tashan MCP server** — the most direct. "Which capability should I use for X, and is it alive?"
   becomes a tool call at the moment of need. This is the shape that makes us infrastructure.
5. **`/capability/<slug>/skill.md`** — a real SKILL.md with frontmatter, per capability and at
   marketplace level, so an agent can install tashan as a capability. LobeHub already does this and
   `docs/COMPETITIVE-LOBEHUB.md` ranks adopting it #2. Ours differs by carrying the *evidence* — score,
   adoption, vitality, what is unrated and why — so an agent choosing between two servers gets the
   measurement, not just an install command.

**The order that matters: 3 → 4 → 5.** The endpoint reaches hosts that never heard of us; the MCP server
makes us callable; the skill makes us installable. All three are distribution *to machines*, which is
where the decision actually gets made.
