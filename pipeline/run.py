#!/usr/bin/env python3
"""tashan — the whole pipeline, one command.

There were 16 scripts and the correct order existed only as prose in CLAUDE.md. That is the kind of
weight that doesn't show up in a line count: every run needs a human to remember a sequence, and every
forgotten step is a silent data bug. This is the order, in code.

    python3 pipeline/run.py                 # the daily loop (incremental, cheap)
    python3 pipeline/run.py --full          # full reconcile: re-walk every source
    python3 pipeline/run.py --site          # site generation only (no network)
    python3 pipeline/run.py --list          # show the stages and exit

Every stage is idempotent and independently runnable — this schedules them, it does not hide them.
Stages that need a key or a human (LLM grading) are marked optional and skipped with a note rather
than failing the run.
"""
import argparse, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

# (name, argv, phase, why) — phase: source | enrich | score | site
STAGES = [
    ("config-adoption", ["scraper/scrape.py"], "source",
     "what people actually put in real public agent configs — the un-backfillable signal"),
    ("skills",          ["pipeline/ingest_skills.py"], "source",
     "every SKILL.md across the tracked source repos"),
    # Without this the daily run would never see a new plugin, and the plugin channel is where the
    # skills people actually recommend get published. Incremental: manifests are cached by repo.
    ("plugins",         ["pipeline/ingest_plugins.py"], "source",
     "Claude Code plugin marketplaces — the channel good skills are published through"),
    # BEFORE build.py, so anything discovered here is enriched and scored in the SAME run rather than
    # sitting unmeasured until tomorrow. Nothing searched npm until now: a package reached the board
    # only if the official registry listed it or the config scraper found it in someone's mcp.json,
    # which is how @playwright/mcp (Microsoft's own, 34k stars on its repo) was missing entirely while
    # a third-party alternative sat at 73. Cached per query+offset, so a re-run is free.
    ("npm-search",      ["pipeline/ingest_npm.py"], "source",
     "search npm for published MCP servers — the discovery step that never existed"),
    ("registry+npm",    ["pipeline/build.py"], "source",
     "official registry (incremental) + npm quality + scoring + export"),
    # IMMEDIATELY after scoring, deliberately. run.py keeps going past a failed stage, so putting the
    # snapshot first means a crash anywhere downstream can still never cost a day of the one series
    # that cannot be recomputed. Cheap, idempotent, reads only.
    ("history",         ["pipeline/snapshot_history.py"], "enrich",
     "signal_history -> committed daily shards, the only copy that survives this machine"),
    ("metadata",        ["pipeline/enrich_meta.py"], "enrich",
     "npm description / homepage / license backfill"),
    ("clean",           ["pipeline/clean.py"], "enrich",
     "drop rows that are not capabilities (local paths, shell fragments)"),
    ("categories",       ["pipeline/classify.py", "--all"], "enrich",
     "naive-Bayes categoriser trained on hand + author-declared labels (62.9% held-out)"),
    # The security audit belongs in the DAILY loop, not in a developer's hands: an advisory published
    # today is only useful if it reaches the board tomorrow. Cached and incremental, so a re-run costs
    # almost nothing and a new package is picked up the day it appears.
    ("security",        ["pipeline/scan_security.py"], "enrich",
     "OSV advisories for the current release + install scripts, provenance, permission surface"),
    # COVERAGE MUST COMPOUND NIGHTLY, not wait for someone to remember. Task mapping was a
    # developer-run script and never ran in the loop, so the axis that makes job and role pages
    # work simply stopped advancing as the corpus tripled. --declared is free and deterministic —
    # it matches the AUTHOR'S OWN keywords to a task synonym, so every tag it writes is attributable
    # to them rather than to us. One run recovered 575 mappings (1,749 -> 2,324).
    ("task-tags",       ["pipeline/tag_capabilities.py", "--declared"], "enrich",
     "map capabilities to the work they are for, from the author's own keywords"),
    # THE TWO AXES AN AGENT NOTICES MISSING. Measured 5 Aug on the top 20 capabilities by weekly
    # downloads — the ones anyone actually asks about: 18/20 had no expertise grade and 20/20 no task
    # mapping. Aggregate coverage read 41%, but coverage was not demand-weighted, so the absence rate
    # on POPULAR packages was far worse than the headline. "An agent hitting absences on popular
    # packages learns to stop querying" is the whole risk, and neither pass ran in the nightly loop.
    #
    # Both need ANTHROPIC_API_KEY and both no-op loudly without it, like the CF_* push stages — a
    # missing credential must never take down the measurement, and must never be silent either.
    # STAGING WAS NOT IN THE LOOP, so the grader ran nightly against a manifest only a human ever
    # refreshed. grade_expertise.py reads data/readmes/manifest.json and nothing wrote it on a
    # schedule — graded coverage could not advance past whatever was last staged by hand, however
    # many nights the grader ran. Cheap and self-limiting: the query excludes already-graded rows, so
    # each run stages the next TOP_N ungraded capabilities, in demand order.
    ("readmes",         ["pipeline/fetch_readmes.py"], "enrich",
     "stage the next ungraded READMEs, most-used first — the grader's input queue"),
    ("expertise",       ["pipeline/grade_expertise.py"], "enrich",
     "grade how well each capability documents itself, against the published rubric (needs a key)"),
    ("task-grade",      ["pipeline/tag_capabilities.py", "--grade", "--limit", "150"], "enrich",
     "map the most-used capabilities to the work they are for (needs a key)"),
    # Skills carry their own SKILL.md and no grade — the expertise rubric is server-shaped
    # and a skill has no tools. This reads the documents we already hold and states facts.
    ("skill-docs",       ["pipeline/skill_doc.py"], "enrich",
     "what each skill's own SKILL.md contains — facts, not a grade"),
    ("doc-signals",     ["pipeline/doc_signals.py"], "enrich",
     "is a capability's only documentation actually about that capability"),
    # LAST of the enrich stages, deliberately: it diffs the FINAL state of each capability against
    # the previous run, so anything that still mutates the row has to have run already. This is the
    # only stage whose output cannot be recomputed later — a change is observable exactly once, on
    # the day it happens, and a day nobody runs this is a day of alerts nobody can ever get back.
    ("changes",         ["pipeline/change_events.py"], "enrich",
     "what changed since the last run — advisories, install scripts, permissions, ownership"),
    # FIRST IN THE SITE PHASE, because every generator below reads its output. The export lives in
    # build.py, which is a `source` stage, so `--site` used to skip it and rebuild the whole site
    # from whatever capabilities.json was last written. Silent, and it shipped: the task tagger was
    # corrected, --site was run, and the hubs regenerated from the stale export.
    ("export",          ["pipeline/export_site.py"], "site",
     "re-export web/data/*.json from the DB, so the site is never built from a stale snapshot"),
    ("badges",          ["pipeline/gen_badges.py"], "site",
     "embeddable SVGs — cast range"),
    # NOT bump_assets here: a daily run must not increment the asset version. The data changes daily,
    # the CSS/JS does not, and bumping would rewrite all ~3,000 generated pages every night for nothing.
    # Bumping is a developer action for when assets actually change (pipeline/bump_assets.py).
    # ORDER MATTERS: hubs BEFORE pages. gen_hubs writes /category/ and /task/; prerender writes the
    # sitemap by walking those directories AND links each capability to the task hubs that exist. Run
    # the other way round and every task page added this run is missing from the sitemap (33 were) and
    # unlinked from the dossiers that should point at it.
    # FIRST in the site phase: prerender bakes the headline into methodology.html, so the measurement
    # has to exist before any page that quotes it. Reads only, no network.
    ("coverage",        ["pipeline/coverage.py"], "site",
     "coverage weighted by demand — the tiers we commit to, not the ratio that falls as we discover"),
    ("compare",         ["pipeline/gen_compare.py"], "site", "head-to-head X vs Y pages"),
    ("hubs",            ["pipeline/gen_hubs.py"], "site", "category + task + role hubs, llms.txt"),
    # A sitemap asks a crawler to come and look; a feed is PULLED — by readers, aggregators and the
    # answer engines that read a dated stream as a freshness signal. It is also the only content
    # here that is genuinely new rather than recomputed.
    ("feed",            ["pipeline/gen_feed.py"], "site",
     "Atom feed of what changed — the one thing that is new every day"),
    # THE SAME EVENTS, AS A PAGE A CRAWLER AND A READER CAN USE. The feed is pulled; this is
    # indexable, linked from the footer of every page, and rewritten nightly — the only surface we
    # have whose freshness a static catalogue cannot match, built from a series nobody can backfill.
    ("changes-page",    ["pipeline/gen_changes.py"], "site",
     "/changes.html — what moved in the ecosystem, dated, the one page rivals cannot reproduce"),
    # The numbers a writer would quote, in a form they can quote. Our deficit is authority and
    # authority comes from citation; a stats page is the classic thing people link to.
    ("stats-page",      ["pipeline/gen_stats.py"], "site",
     "/stats.html — the ecosystem in numbers, licensed CC BY and built to be cited"),
    # DRAFTS ONLY. Nothing here posts: publishing is outward-facing, needs credentials this repo
    # does not hold, and an automated account that gets one post wrong costs more than the traffic
    # it wins. A human reads data/social/<day>.json and sends it.
    ("social",          ["pipeline/gen_social.py"], "site",
     "draft the day's post for X / Threads / Farcaster from the day's most consequential finding"),
    ("pages",           ["pipeline/prerender.py"], "site", "capability pages + sitemap"),
    ("registry",        ["pipeline/gen_registry.py"], "site", "agent endpoints (/v0.1/servers, /v0.1/scores)"),
    ("content",         ["pipeline/gen_content.py"], "site", "learn articles"),
    # THE PAID DELIVERY PATH. redact_paid() strips the audit's detail from every public file, so this
    # is the only way it reaches the people who bought it. A day this does not run is a day paying
    # customers see "unlock detail" and get nothing — the exact defect the whole feature audit was
    # about. No-ops loudly without CF_* credentials rather than failing the run.
    # AFTER every page generator, because it counts what is ON DISK. It was a developer-run script
    # whose freshness tests/test_product_tree.py asserts — so the first pipeline run that changed a
    # page count failed the suite by construction, and the suite is what gates the daily commit. That
    # is exactly what happened the first time the pipeline got far enough to reach the tests: 5,933
    # pages recorded, 5,985 on disk. Regenerating a doc is cheaper than a red build nobody caused.
    ("product-tree",    ["pipeline/gen_product_tree.py"], "site",
     "docs/PRODUCT-TREE.md — every route, counted from disk"),
    ("push-paid",       ["pipeline/push_security.py"], "site",
     "the audit's paid half -> Cloudflare KV, where /api/security serves licence holders"),
    # /api/history is the OTHER paid endpoint and had no stage at all — Pro's headline promise is
    # "Free tells you what is true today, Pro tells you the day that changes", and nothing ever
    # uploaded the series that sentence sells. A licence holder got an empty store.
    ("push-history",    ["pipeline/push_history.py"], "site",
     "the retention series -> Cloudflare KV, where /api/history serves licence holders"),
]
SITE_ONLY = {"badges", "pages", "content", "hubs", "compare", "coverage", "registry", "product-tree",
             "push-paid", "push-history"}


def run(name, argv, full):
    cmd = [PY] + [os.path.join(ROOT, argv[0])] + argv[1:]
    env = dict(os.environ)
    if full:
        env["REG_FULL"] = "1"
    t0 = time.time()
    print(f"\n\033[1m▸ {name}\033[0m  ({' '.join(argv)})", flush=True)
    r = subprocess.run(cmd, cwd=ROOT, env=env)
    dt = time.time() - t0
    if r.returncode != 0:
        print(f"  ✗ {name} failed ({r.returncode}) after {dt:.0f}s", flush=True)
        return False
    print(f"  ✓ {name} in {dt:.0f}s", flush=True)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="full reconcile instead of incremental")
    ap.add_argument("--site", action="store_true", help="site generation only, no network")
    ap.add_argument("--list", action="store_true", help="print the stages and exit")
    a = ap.parse_args()

    stages = [s for s in STAGES if (s[0] in SITE_ONLY if a.site else True)]
    if a.list:
        for name, argv, phase, why in STAGES:
            print(f"  {phase:7} {name:16} {argv[0]:32} {why}")
        return 0

    print(f"tashan pipeline — {len(stages)} stages, {'FULL' if a.full else 'incremental'}")
    failed = [name for name, argv, _, _ in stages if not run(name, argv, a.full)]
    print()
    if failed:
        print(f"\033[31mfailed: {', '.join(failed)}\033[0m")
        return 1
    print("\033[32mall stages green\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
