#!/usr/bin/env python3
"""Everything an agent reads must be reachable, current, and true.

Agents are not a nice-to-have audience here — they are the audience. This project's whole thesis is
that a model deciding what to install should be able to check first, and every one of those checks
happens without a browser. So the surfaces below get the same treatment the human pages get: a test
that fails the build when a claim stops being true.

WHAT THIS CAUGHT WHEN IT WAS WRITTEN (6 Aug 2026):

  - **The Index published no measurements.** https://tashan.sh/ rendered 3,137 characters of nav,
    hero copy and footer, and `<tbody id="rows">` shipped a "Loading measured data…" spinner that
    only index.js could fill. The site's most-crawled URL — the ranked board the entire product is —
    showed a crawler zero capabilities, zero scores, zero ranks. Every category and task hub was
    server-rendered; the board was the one page that needed JavaScript.
  - **The hubs had no markdown twin.** Every individual capability had had one for weeks. The hubs
    are where the questions live ("best MCP server for X", "what should a data engineer install"),
    and they were the tier without one.
  - **We were not in the MCP registry.** We ingest it as the spine of coverage and were absent from
    it, so the one place an MCP client looks for servers did not know we existed.

Run: python3 tests/test_agent_surface.py
"""
import glob, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
ok = fail = 0


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print("  ok   " + name)
    else:
        fail += 1
        print("  FAIL " + name + (("  — " + detail) if detail else ""))


def rendered(path):
    """What a reader that does not run JavaScript actually gets."""
    h = open(path, encoding="utf-8").read()
    h = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", h)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()


print("# the Index publishes measurements without JavaScript")
idx = os.path.join(WEB, "index.html")
src = open(idx, encoding="utf-8").read()
tbody = re.search(r'<tbody id="rows">([\s\S]*?)</tbody>', src)
check("index.html still has the board tbody to bake into", bool(tbody))
rows = tbody.group(1).count("<tr>") if tbody else 0
# 5 is arbitrary but the failure it guards is not: any regression here empties the tbody back to a
# spinner, and the whole page reverts to publishing nothing.
check(f"the top of the board is server-rendered ({rows} rows)", rows >= 5,
      "tbody is empty or holds only a loading state — run pipeline/prerender.py")
if tbody:
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", tbody.group(1)))
    check("those rows carry real scores, not placeholders",
          len(re.findall(r"\b\d{1,3}\b", txt)) >= rows,
          "no numbers in the baked rows")
    check("every baked row links to a page that exists",
          all(os.path.exists(os.path.join(WEB, h.lstrip("/")))
              for h in re.findall(r'href="(/capability/[^"]+)"', tbody.group(1))),
          "a baked row points at a missing dossier")

lds = [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', src, re.S)]
items = [x for x in lds if x.get("@type") == "ItemList"]
check("the Index carries an ItemList of the ranked capabilities", bool(items),
      "category hubs have had one since they were built; the Index is the ranked list")
if items:
    el = items[0].get("itemListElement") or []
    check(f"the ItemList is populated and ordered ({len(el)} items)",
          len(el) >= 5 and [x.get("position") for x in el] == list(range(1, len(el) + 1)))
    rated = [x for x in el if (x.get("item") or {}).get("review")]
    check("each rated entry carries its score as an attributed Review", bool(rated))
    # NOT aggregateRating. One rating with ratingCount:1 claims a crowd of reviewers that does not
    # exist, and it was deliberately removed from 6,586 capability pages as the self-serving-rating
    # pattern Google's structured-data policy rejects. It must not creep back in via the Index.
    check("no entry claims an aggregateRating",
          not any((x.get("item") or {}).get("aggregateRating") for x in el),
          "one party's measurement is a Review, not the mean of a crowd")
    check("the review names who did the measuring",
          all(((x.get("item") or {}).get("review") or {}).get("author", {}).get("name") == "tashan"
              for x in rated))
    # An ItemList that disagrees with the table under it is worse than none: the structured data is
    # what gets quoted, and it would be quoting a different ranking than the page shows.
    first_ld = el[0].get("name") if el else None
    first_row = None
    if tbody:
        m = re.search(r'<a class="cap__link"[^>]*>([^<]+)</a>', tbody.group(1))
        first_row = m.group(1) if m else None
    check("the ItemList and the rendered table agree on what ranks first",
          first_ld and first_row and first_ld.strip() == first_row.strip(),
          f"JSON-LD says {first_ld!r}, the table says {first_row!r}")

ds = [x for x in lds if x.get("@type") == "Dataset"]
check("the Index declares itself a Dataset", bool(ds))
if ds:
    d0 = ds[0]
    # An undated dataset is one an engine has to treat as undated, and "measured this week" is most
    # of why our number beats a directory's. It was the only date on the page a human could read and
    # a parser could not.
    check("the Dataset carries a dateModified",
          bool(re.fullmatch(r"\d{4}-\d\d-\d\d", str(d0.get("dateModified") or ""))),
          f"got {d0.get('dateModified')!r} — run pipeline/prerender.py")
    urls = [x.get("contentUrl", "") for x in (d0.get("distribution") or [])]
    check("the distribution offers the per-question endpoints",
          any("/v0.1/lookup" in u for u in urls) and any("/v0.1/search" in u for u in urls),
          "a crawler was pointed only at the 420 KB and 5.6 MB bulk files")
    # Order is a recommendation. Pointing a reader at 5.6 MB because it was declared first is the
    # same defect as having no cheap endpoint at all.
    check("the cheap endpoints are listed before the bulk feeds",
          urls and "/v0.1/lookup" in urls[0],
          f"first distribution is {urls[0] if urls else None!r}")
    check("exactly one Dataset block (the baker replaces, never appends)", len(ds) == 1)

print()
print("# the ranked shelves have machine-readable twins")
for kind in ("category", "task", "role"):
    twins = glob.glob(os.path.join(WEB, kind, "*.md"))
    check(f"/{kind}/*.md exists ({len(twins)} twins)", bool(twins),
          "the hub that answers the query has no markdown tier")
    if twins:
        # Whitespace-normalised: the disclaimer is wrapped across lines in the source, and matching
        # the raw text made this fail on formatting rather than on meaning.
        body = re.sub(r"\s+", " ", open(sorted(twins)[0], encoding="utf-8").read())
        # Ranking IS the claim on these pages, so the ordering rule has to be stated rather than
        # left for a summariser to infer — it is not the obvious one on task and role shelves.
        check(f"/{kind} twins state the rule they are ranked by", "Ranked by" in body)
        # A summariser quoting a ranking without this turns "well maintained" into "safe", which is
        # the exact conflation the score is named to avoid.
        check(f"/{kind} twins say what the score is not",
              re.search(r"not\*{0,2} a security verdict", body) is not None)

print()
print("# every page type carries structured data, and it is well-formed")
# An answer engine sources a number before it quotes one, and the page that explains where the
# numbers come from carried NO structured data at all — every hub had an ItemList, every dossier a
# Review, and the document behind all of them was unstructured.
PAGES = {
    "index.html": {"Organization", "WebSite", "FAQPage", "Dataset", "ItemList"},
    "methodology.html": {"TechArticle"},
    "browse.html": {"CollectionPage", "BreadcrumbList"},
}
for pg, want in PAGES.items():
    p = os.path.join(WEB, pg)
    if not os.path.exists(p):
        continue
    got = set()
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                        open(p, encoding="utf-8").read(), re.S):
        try:
            o = json.loads(m)
        except ValueError as e:
            check(f"{pg} JSON-LD parses", False, str(e)[:70])
            continue
        for x in (o if isinstance(o, list) else [o]):
            got.add(x.get("@type"))
    check(f"{pg} carries {', '.join(sorted(want))}", want <= got, f"missing {sorted(want - got)}")

# The self-serving-rating pattern, wherever it tries to come back. It has now had to be removed
# three times: capability pages, the Index ItemList, and the learn articles' ranked lists.
rogue = []
for p in ([os.path.join(WEB, f) for f in ("index.html",)]
          + sorted(glob.glob(os.path.join(WEB, "learn", "*.html")))
          + sorted(glob.glob(os.path.join(WEB, "capability", "*.html")))[:40]):
    if "aggregateRating" in open(p, encoding="utf-8").read():
        rogue.append(os.path.relpath(p, WEB))
check("no page claims an aggregateRating for a one-party measurement", not rogue,
      f"{len(rogue)} page(s), e.g. {rogue[:3]} — use an attributed Review")

print()
print("# the conventions are announced where a crawler looks")
robots = open(os.path.join(WEB, "robots.txt"), encoding="utf-8").read()
for p in ("/capability/*.md", "/category/*.md", "/task/*.md", "/role/*.md"):
    check(f"robots.txt allows {p}", f"Allow: {p}" in robots)
hdrs = open(os.path.join(WEB, "_headers"), encoding="utf-8").read()
for p in ("/capability/*.md", "/category/*.md", "/task/*.md", "/role/*.md"):
    # Without an explicit Content-Type a .md downloads instead of rendering, and several crawlers
    # skip an attachment outright.
    blk = re.search(re.escape(p) + r"\n((?:  .*\n)+)", hdrs)
    check(f"_headers serves {p} as text/markdown",
          bool(blk) and "text/markdown" in blk.group(1))

print()
print("# the markdown dossiers survived the move off the filesystem")
# 9,013 .md files became 64 shards + a Function so the site could keep being deployable at all. The
# risk that move introduced is a hash that disagrees across languages: the Function computes which
# shard to fetch, so a divergence 404s EVERY dossier at once rather than one. Checked against real
# slugs, in both languages, not by inspection.
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import prerender as _P

shards = sorted(glob.glob(os.path.join(WEB, "data", "md", "*.json")))
check(f"the dossier shards exist ({len(shards)} of {_P.MD_SHARDS})", len(shards) == _P.MD_SHARDS,
      "run pipeline/prerender.py")
pages = [os.path.basename(f)[:-5] for f in glob.glob(os.path.join(WEB, "capability", "*.html"))]
check("no per-capability .md files remain (they are what blew the file budget)",
      not glob.glob(os.path.join(WEB, "capability", "*.md")))
if shards and pages:
    loaded, placed = {}, 0
    for f in shards:
        loaded[int(os.path.basename(f)[:-5])] = json.load(open(f, encoding="utf-8"))
    missing, misplaced = [], []
    for slug in pages:
        i = _P.md_shard(slug)
        if slug not in loaded.get(i, {}):
            # in the wrong shard, or absent entirely — distinguish, because the causes differ
            (misplaced if any(slug in m for m in loaded.values()) else missing).append(slug)
        else:
            placed += 1
    check(f"every prerendered page has a dossier in the shard its hash names ({placed:,})",
          not missing and not misplaced,
          f"{len(missing)} absent e.g. {missing[:2]}; {len(misplaced)} in the wrong shard e.g. {misplaced[:2]}")
    empty = [s for s, t in ((s, m.get(s)) for m in loaded.values() for s in m) if not t or len(t) < 50]
    check("no dossier is empty or a stub", not empty, f"{len(empty)} e.g. {empty[:3]}")

# The JS half of the hash, run for real rather than eyeballed.
js = subprocess.run(
    ["node", "--input-type=module", "-e",
     "import {shard} from './functions/capability/[[path]].js';"
     "const s=JSON.parse(process.argv[1]);"
     "console.log(JSON.stringify(s.map(x=>shard(x))));"],
    input="", capture_output=True, text=True, cwd=ROOT,
    args=None) if False else subprocess.run(
    ["node", "--input-type=module", "-e",
     "import {shard} from './functions/capability/[[path]].js';"
     "const s=JSON.parse(process.argv[1]);console.log(JSON.stringify(s.map(x=>shard(x))));",
     json.dumps(sorted(pages)[:300])],
    capture_output=True, text=True, cwd=ROOT)
if js.returncode != 0:
    check("the JS shard function is importable", False, (js.stderr or "")[-160:])
else:
    got = json.loads(js.stdout.strip().split("\n")[-1])
    want = [_P.md_shard(s) for s in sorted(pages)[:300]]
    check(f"python and js agree on the shard for {len(want)} real slugs", got == want,
          "a divergence 404s every dossier at once — "
          f"first mismatch at {next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), None)}")

print()
print("# the deployment still fits")
# CLOUDFLARE PAGES REFUSES ANY DEPLOYMENT OVER 20,000 FILES. Not degrades — refuses. It has already
# happened once here: one .svg per capability took the site to 21,782 and badges had to move into a
# Function to publish at all. The markdown tier doubles the per-capability cost (an .html AND an .md
# each), so the ceiling now arrives about twice as fast, and the failure mode is a deploy that dies
# after the work is done rather than a number anyone was watching.
total = sum(len(fs) for _, _, fs in os.walk(WEB))
CEILING, WARN = 20000, 19000
check(f"web/ is under Cloudflare's 20,000-file deployment ceiling ({total:,} files)",
      total < CEILING, "the deploy will be REFUSED — move a tier behind a Function, as /badge/ was")
check(f"…with room to grow ({CEILING - total:,} files of headroom)", total < WARN,
      f"{CEILING - total:,} files left ≈ {(CEILING - total) // 2:,} more capabilities. Plan the next "
      f"move now: prerendered pages behind an SSR Function is the documented path (docs/SCALE.md).")

print()
print("# the MCP registry entry stays in step with what we publish")
sj = os.path.join(ROOT, "server.json")
check("server.json exists at the repo root", os.path.exists(sj),
      "the official registry is where MCP clients look; see docs/OUTREACH.md §0")
if os.path.exists(sj):
    m = json.load(open(sj, encoding="utf-8"))
    cli = json.load(open(os.path.join(ROOT, "cli", "package.json"), encoding="utf-8"))
    check("the manifest name is reverse-DNS with exactly one slash",
          bool(re.fullmatch(r"[a-zA-Z0-9.-]+/[a-zA-Z0-9._-]+", m.get("name", ""))),
          f"{m.get('name')!r} would be rejected by the registry")
    pkg = (m.get("packages") or [{}])[0]
    check("the manifest points at the package we actually publish",
          pkg.get("identifier") == cli.get("name"),
          f"server.json says {pkg.get('identifier')!r}, cli/package.json says {cli.get('name')!r}")
    # THE BLOCKER THAT WOULD HAVE FAILED THE PUBLISH. The registry verifies that the npm package and
    # the registry entry are the same thing by requiring an `mcpName` in package.json equal to
    # server.json's `name`. Without it the publish is rejected — and it is invisible until you try,
    # because both files are individually valid. Found by reading the registry's own quickstart.
    check("cli/package.json carries the mcpName the registry verifies against",
          cli.get("mcpName") == m.get("name"),
          f"package.json mcpName={cli.get('mcpName')!r}, server.json name={m.get('name')!r} — "
          f"the registry rejects a publish where these differ")
    # A domain namespace is only claimable with DNS auth on that apex. `sh.tashan/*` requires a TXT
    # record on tashan.sh; switching to GitHub auth means renaming to io.github.<user>/*.
    ns = str(m.get("name", "")).split("/")[0]
    check(f"the namespace {ns!r} matches a domain we control",
          ns == "sh.tashan" or ns.startswith("io.github."),
          "a namespace we cannot authenticate for will be refused at publish time")
    # A registry entry pinned to a version nobody can install is worse than no entry — the client
    # resolves it, fails, and the user concludes the server is broken.
    check("the manifest version matches the published CLI version",
          m.get("version") == cli.get("version") == pkg.get("version"),
          f"manifest {m.get('version')} / package {pkg.get('version')} / cli {cli.get('version')}")
    args = [a.get("value") for a in (pkg.get("runtimeArguments") or [])]
    plug = json.load(open(os.path.join(ROOT, "plugin", ".claude-plugin", "plugin.json"), encoding="utf-8"))
    want = ((plug.get("mcpServers") or {}).get("tashan") or {}).get("args") or []
    # The plugin and the registry entry are two published ways to start the same server. If they
    # disagree about the command, one of them starts something that is not our MCP server.
    check("the registry entry starts the server the same way the plugin does",
          args == [a for a in want if a not in ("-y", cli.get("name"))],
          f"registry runs `npx {cli.get('name')} {' '.join(args)}`, plugin runs `npx {' '.join(want)}`")

print()
print("=" * 46)
print("agent surface: %d/%d passed%s" % (ok, ok + fail, " · all green" if not fail else ""))
sys.exit(1 if fail else 0)
