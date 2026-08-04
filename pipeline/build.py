#!/usr/bin/env python3
"""
tashan — v2 data pipeline.  Public signal → SQLite → scores → site JSON.

Answers the three v2 needs:
  1. COVERAGE — ingest the official MCP registry (thousands of capabilities), not just our config sample.
  2. QUALITY  — enrich with npm signals (downloads, freshness, maintainers, deprecated) beyond adoption.
  3. DB       — SQLite store (data/tashan.db); site JSON is an *export*, not the source of truth.

Sources, all public / no telemetry:
  - data/capabilities.json  : config-adoption (reach/repos/stars/co-use) from the scraper
  - MCP registry            : registry.modelcontextprotocol.io (name/desc/status/repo/npm pkg)
  - npm registry + downloads: quality (weekly downloads, last publish, maintainers, versions, deprecated)

Scores are transparent, labelled, and computed here — never a black box.
Roadmap (next passes, not here yet): GitHub repo-health, git-history retention/churn, LLM expertise eval.
"""
import collections, json, os, sqlite3, urllib.request, urllib.error, urllib.parse, time, math, re, subprocess
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "tashan.db")
NPM_CACHE = os.path.join(ROOT, "data", "npm_cache.json")
GH_CACHE = os.path.join(ROOT, "data", "github_cache.json")
REG_CAP = int(os.environ.get("REG_CAP", "4000"))     # max registry servers to ingest
NPM_CAP = int(os.environ.get("NPM_CAP", "1200"))      # max npm packages to enrich this run
GH_CAP = int(os.environ.get("GH_CAP", "1200"))        # max capability source-repos to enrich this run

SCHEMA = """
CREATE TABLE IF NOT EXISTS capabilities (
  id TEXT PRIMARY KEY, name TEXT, kind TEXT, title TEXT, description TEXT,
  npm_pkg TEXT, source_repo TEXT, homepage TEXT,
  registry_name TEXT, registry_status TEXT, registry_updated TEXT,
  config_reach INTEGER DEFAULT 0, config_repos INTEGER DEFAULT 0,
  stars_median INTEGER DEFAULT 0, stars_max INTEGER DEFAULT 0, last_seen TEXT,
  npm_downloads INTEGER, npm_last_publish TEXT, npm_created TEXT,
  npm_maintainers INTEGER, npm_versions INTEGER, npm_deprecated INTEGER,
  co_used TEXT,
  adoption REAL, upkeep REAL, freshness REAL, tashan_score REAL,
  expertise REAL, expertise_verdict TEXT, expertise_note TEXT,
  retention REAL, retention_note TEXT,
  in_registry INTEGER DEFAULT 0, in_configs INTEGER DEFAULT 0,
  updated_at TEXT
);
CREATE TABLE IF NOT EXISTS signal_history (
  cap_id TEXT, metric TEXT, value REAL, at TEXT,
  -- WHICH RULER MEASURED THIS. Without it the series is uninterpretable: the scorer was rewritten four
  -- times inside the first week of history (gate floor, adoption anchors, calibration curve), so
  -- pkg:3dstreet-mcp reads 43,43,43,43,42,40 and every one of those steps is US, not the capability.
  -- A trend that spans two scorer versions measures our own recalibration and reports it to a paying
  -- customer as decline. Comparisons are only ever made within one version.
  scorer TEXT
);
-- one row per source: where the last incremental sync got to. A catalog is a clock, not a snapshot;
-- without this every run is a full crawl and coverage stays capped by however long we are willing to wait.
CREATE TABLE IF NOT EXISTS sync_state (
  source TEXT PRIMARY KEY, last_synced TEXT, last_cursor TEXT, seen INTEGER DEFAULT 0, note TEXT
);
-- FULL text, deliberately in its own table. `capabilities` is already 52 columns wide and every
-- scoring pass SELECTs across it; SKILL.md bodies run to 70 KB (5.6 MB across the corpus) and would
-- make every unrelated query drag them along. Kept here, joined only by the things that read prose:
-- the tagger, the expertise grader, prerender.
--   doc_source ∈ 'skill_md' | 'marketplace_json' | 'readme'
-- Note what this does NOT fix: remote/npm descriptions are capped at 100 chars by the MCP REGISTRY
-- itself, upstream of us. Those need a README fetch, not a truncation fix.
CREATE TABLE IF NOT EXISTS capability_text (
  cap_id TEXT PRIMARY KEY, full_description TEXT, doc_body TEXT, doc_source TEXT, fetched_at TEXT
);
-- The task axis: multi-valued, queryable, and every assignment carries its own justification.
-- A capability does several jobs, so this cannot be a column on `capabilities` the way `category` is
-- (single-valued by design). `basis` + `evidence` exist so a tag can always answer "says who?" —
-- the same standard expertise_verdict already meets. NOT a repeat of the gh_topics CSV mistake
-- (docs/ARCHITECTURE-RISKS.md risk #8: unqueryable blob columns).
--   basis ∈ 'declared'  (the author's own keyword/category — attributable)
--         | 'graded'    (LLM read the text against the published rubric)
--         | 'alongside' (measured: appears in the same real configs as other capabilities for this task)
CREATE TABLE IF NOT EXISTS capability_tags (
  cap_id TEXT, tag TEXT, confidence REAL, basis TEXT, evidence TEXT,
  PRIMARY KEY (cap_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_score ON capabilities(tashan_score DESC);
CREATE INDEX IF NOT EXISTS idx_captag_tag ON capability_tags(tag);
CREATE INDEX IF NOT EXISTS idx_captag_cap ON capability_tags(cap_id);
"""

# columns added after the first DBs were created — ALTER them in on open (SQLite has no ADD COLUMN IF NOT EXISTS)
MIGRATE = ["expertise REAL", "expertise_verdict TEXT", "expertise_note TEXT",
           "retention REAL", "retention_note TEXT", "category TEXT",
           # capability's OWN source-repo health (GitHub) + derived vitality/bus-factor
           "gh_stars INTEGER", "gh_forks INTEGER", "gh_open_issues INTEGER", "gh_pushed TEXT",
           "gh_contributors INTEGER", "gh_last_release TEXT", "gh_license TEXT", "gh_topics TEXT",
           "gh_has_discussions INTEGER", "gh_archived INTEGER",
           "vitality TEXT", "single_maintainer INTEGER",
           # product-specific community/support signals (the project's own Discord + homepage/docs)
           "discord_url TEXT", "gh_homepage TEXT",
           # which source(s) asserted this row — provenance is publishable evidence and lets a bad
           # source be retracted wholesale (docs/SOURCING.md §4)
           "sources TEXT",
           # The published `latest` semver. It was fetched on every enrichment pass and discarded twice
           # (here and in enrich_meta), so nothing could answer "is the version I pinned out of date" —
           # npm_versions is a COUNT of releases, not a version.
           "npm_latest_version TEXT",
           # Host of a remote server's endpoint, from the registry's remotes[].url. Without it a config
           # entry {url:"https://mcp.exa.ai/mcp"} — which identify() reduces to the HOST — can never
           # resolve, and remote is the second-largest kind we track (4,215 rows, 0 resolvable before).
           "remote_host TEXT",
           # The marketplace REPO a plugin can actually be installed from. `title` already holds the
           # marketplace NAME, and the two are not derivable from each other — anthropics/
           # claude-plugins-community publishes under the name "claude-community" — so `/plugin
           # marketplace add <repo>` + `/plugin install <name>@<market>` needs both halves. Without it
           # every plugin page fell through to the npm-less branch and told 3,624 readers their Claude
           # Code plugin was a "Remote / registry server". Identity still keys on the plugin's own
           # home (see ingest_plugins.plugin_id) — this is a DISTRIBUTION fact, not an identity one.
           "plugin_market_repo TEXT",
           # ---- security audit (pipeline/scan_security.py) ----------------------------------
           # Public evidence only: OSV.dev advisories for the version you would install TODAY, plus
           # what the npm packument already tells us and we were throwing away. None of these feed
           # the score — tests/test_firewall.py still proves the scorer reads only its own columns.
           "sec_advisories TEXT",        # JSON [{id, severity, summary, fixed}]
           "sec_advisory_count INTEGER",
           "sec_max_severity TEXT",      # CRITICAL / HIGH / MODERATE / LOW
           "sec_install_script TEXT",    # postinstall|preinstall — arbitrary code at install time
           "sec_provenance INTEGER",     # signed / attested release
           "sec_permissions TEXT",       # JSON ["shell","network",…] from DECLARED dependencies
           "sec_remote_content INTEGER", # can carry third-party text into the model's context
           "sec_dep_count INTEGER",
           "sec_scanned_at TEXT",
           "npm_license TEXT",
           # Is the documentation actually ABOUT this capability? 79 of 836 staged rows ship a README
           # byte-identical to another capability's, and whole families are never named in the only
           # document they have. A grader reading that text sees competent docs — for something else.
           "doc_shared_with INTEGER",   # how many OTHER capabilities ship this exact README
           "doc_names_self INTEGER",    # does the text mention this capability at all
           # The author's OWN package.json keywords, comma-joined like gh_topics. Fetched on every
           # enrichment pass since the beginning and thrown away, which left npm the only kind with
           # no author vocabulary at all: plugins had manifest tags, skills had frontmatter, and
           # `pkg:` had nothing — so 0 of 1,398 npm rows carried a task tag and the job axis could
           # not see the half of the corpus where media, audio and video servers actually live.
           "npm_keywords TEXT",
           # The author's OWN statement that they stopped, quoted. NULL means no such statement was
           # found; a value is the sentence itself, so the site can always answer "says who?".
           #
           # The scorer already discounts maintenance by 0.7 when a maintainer declares a thing done —
           # but it only ever listened to three PLATFORM flags: npm's deprecated field, the registry's
           # deprecated status, and GitHub's Archive checkbox. wooyun-legacy opens its README with
           # "# 不维护决定 … 我们决定不维护了" (we have decided not to maintain this), never touched the
           # Archive checkbox, and so kept vitality=active, upkeep 79 and the #1 slot on the security
           # shelf. Our own expertise grader had already READ that line and written it into
           # expertise_note as prose, where nothing could act on it. A declaration in the README is the
           # same evidence as a checkbox and is now read as such.
           "self_unmaintained TEXT", "coverage REAL"]

SCHEMA_VERSION = 11  # bump when MIGRATE changes; PRAGMA user_version records the applied version

# v5 RENAMED the headline score. "Trust" claimed more than the SCORE measures: it is upkeep, freshness
# and adoption, and a number whose name needs walking back is misnamed. That still holds — the security
# audit added in v8 (pipeline/scan_security.py) is a SEPARATE column set, deliberately not folded into
# the score, so that "well maintained" and "nothing known is wrong with it" stay two different claims a
# reader can weigh independently. A popular, actively maintained package can still ship a CVE. `tashan_score` names what it is: our measurement, on public evidence. `maintenance`
# became `upkeep` in the same pass because the board had two words starting "main" in adjacent columns.
# Existing DBs are renamed in place here rather than rebuilt — signal_history is un-backfillable, so it
# is re-keyed, never dropped.
RENAMES = [("trust", "tashan_score"), ("maintenance", "upkeep")]

# indexes on the columns actually filtered/sorted — created AFTER MIGRATE so category/gh_* exist.
# At 100k+ rows these turn every facet/sort/history query from an O(N) scan into an index seek.
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_reach ON capabilities(config_reach DESC)",
    "CREATE INDEX IF NOT EXISTS idx_category ON capabilities(category)",
    "CREATE INDEX IF NOT EXISTS idx_npm ON capabilities(npm_pkg)",
    "CREATE INDEX IF NOT EXISTS idx_repo ON capabilities(source_repo)",
    "CREATE INDEX IF NOT EXISTS idx_hist ON signal_history(cap_id, metric, at)",
    "CREATE INDEX IF NOT EXISTS idx_hist_at ON signal_history(at)",
]

def db():
    # 60s busy timeout: pipeline stages legitimately overlap (a long npm enrichment still writing while
    # a plugin ingest opens), and the default behaviour is to fail instantly with "database is locked"
    # and lose the whole run. WAL lets a reader work while a writer commits.
    con = sqlite3.connect(DB, timeout=60)
    con.execute("PRAGMA busy_timeout = 60000")
    try:
        con.execute("PRAGMA journal_mode = WAL")
    except sqlite3.OperationalError:
        pass                      # a concurrent writer may hold it; the busy_timeout still applies
    con.executescript(SCHEMA)
    have = {r[1] for r in con.execute("PRAGMA table_info(capabilities)")}
    for old, new in RENAMES:
        if old in have and new not in have:
            con.execute(f"ALTER TABLE capabilities RENAME COLUMN {old} TO {new}")
            con.execute("UPDATE signal_history SET metric=? WHERE metric=?", (new, old))
            have.discard(old); have.add(new)
    for coldef in MIGRATE:
        if coldef.split()[0] not in have:
            con.execute(f"ALTER TABLE capabilities ADD COLUMN {coldef}")
    # signal_history is not covered by MIGRATE (which only ALTERs capabilities) and cannot be rebuilt —
    # it is the un-backfillable series. Add the column in place and label every pre-existing row `s1`,
    # the mixed pre-calibration era, so it can never be trended against anything.
    hist_cols = {r[1] for r in con.execute("PRAGMA table_info(signal_history)")}
    if "scorer" not in hist_cols:
        con.execute("ALTER TABLE signal_history ADD COLUMN scorer TEXT")
        con.execute("UPDATE signal_history SET scorer='s1' WHERE scorer IS NULL")
    for idx in INDEXES:
        con.execute(idx)
    con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    con.commit()
    return con

def put_text(con, cap_id, full_description=None, doc_body=None, doc_source=None):
    """Record a capability's UNTRUNCATED prose. Ingests call this with whatever they already hold.

    Every ingest was clipping text on the way in — plugins at 500 chars — and the full SKILL.md bodies
    (1,322 of them, up to 70 KB) were fetched, cached, and then thrown away without ever reaching the
    DB. That text is the only thing a workflow tagger has to read, so the quality ceiling for the whole
    task axis was set by a truncation nobody needed. COALESCE keeps a later partial write from erasing
    prose an earlier one captured.
    """
    if not (full_description or doc_body):
        return
    con.execute(
        """INSERT INTO capability_text (cap_id, full_description, doc_body, doc_source, fetched_at)
           VALUES (?,?,?,?,?)
           ON CONFLICT(cap_id) DO UPDATE SET
             full_description=COALESCE(excluded.full_description, capability_text.full_description),
             doc_body=COALESCE(excluded.doc_body, capability_text.doc_body),
             doc_source=COALESCE(excluded.doc_source, capability_text.doc_source),
             fetched_at=excluded.fetched_at""",
        (cap_id, full_description or None, doc_body or None, doc_source,
         datetime.now(timezone.utc).isoformat()))


def get_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "tashan-pipeline"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

# A valid npm package name never contains a backslash, colon, or whitespace, never starts with `.`/`/`, and
# doesn't end in `.js` — those are the fingerprints of a local filesystem path (e.g. a Windows
# "C:\Users\...\dist\index.js") that leaked out of a public config and got mistaken for a package. Guard the
# ingest trust boundary so this garbage never becomes an id or wastes an npm API round-trip 404ing.
_BAD_PKG = re.compile(r"[\\:\s]|^[./]|\.js$")
def bad_pkg(pkg):
    return bool(pkg) and bool(_BAD_PKG.search(pkg))

# ---------- phase A: load config-adoption ----------
def load_configs(con):
    path = os.path.join(ROOT, "data", "capabilities.json")
    if not os.path.exists(path):
        print("  (no capabilities.json — run the scraper first)"); return 0
    d = json.load(open(path))
    n = 0
    for c in d["capabilities"]:
        if c["id"].startswith("key:"):
            continue
        npm_pkg = c["id"][4:] if c["id"].startswith("pkg:") else None
        if bad_pkg(npm_pkg):                              # local path, not a package — never let it in
            continue
        con.execute("""INSERT INTO capabilities (id,name,kind,config_reach,config_repos,stars_median,stars_max,last_seen,co_used,npm_pkg,in_configs)
          VALUES (?,?,?,?,?,?,?,?,?,?,1)
          ON CONFLICT(id) DO UPDATE SET config_reach=excluded.config_reach, config_repos=excluded.config_repos,
            stars_median=excluded.stars_median, stars_max=excluded.stars_max, last_seen=excluded.last_seen,
            co_used=excluded.co_used, in_configs=1""",
          (c["id"], c["name"], c["kind"], c["owners"], c["repos"], c["stars_median"], c["stars_max"],
           c.get("last_seen"), json.dumps(c.get("co_used", [])), npm_pkg))
        n += 1
    con.commit(); return n

# ---------- phase B: ingest MCP registry (coverage) ----------
def ingest_registry(con, full=False):
    """Incremental sync of the official registry via the Generic MCP Registry API.

    Three fixes over the previous version (all measured — see docs/SOURCING.md §2):
      - /v0.1, not /v0. v0.1 is the documented spec; /v0 still answers but isn't what the docs describe.
      - `updated_since` delta. A full walk of 6,000 servers took 562s, which is why REG_CAP existed and
        why we held only 1,717 of >=6,000. The delta is seconds, so the cap stops being load-bearing.
      - `status` is honoured. The registry marks servers `deprecated` or `deleted`, and the moderation
        policy says `deleted` typically means spam, malware or illegal content. An index whose product
        is trust must not be the last place a known-bad server stays listed, so those are DELISTED —
      kept as evidence so `doctor` can warn, but refused a score so they can never rank.

    Pass full=True (or REG_FULL=1) to force a complete reconcile — run weekly to catch anything the
    delta feed missed. State lives in sync_state so a run can resume rather than restart.
    """
    SRC = "mcp-registry"
    base = "https://registry.modelcontextprotocol.io/v0.1/servers?limit=100"
    row = con.execute("SELECT last_synced FROM sync_state WHERE source=?", (SRC,)).fetchone()
    since = None if (full or os.environ.get("REG_FULL")) else (row[0] if row else None)
    if since:
        base += "&updated_since=" + urllib.parse.quote(since)
        print(f"  registry: incremental since {since}", flush=True)
    else:
        print("  registry: FULL reconcile (no prior sync state)", flush=True)
    started = datetime.now(timezone.utc).isoformat()
    cursor, seen, removed, deprecated = None, 0, 0, 0
    while seen < REG_CAP:
        url = base + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else "")
        try:
            d = get_json(url)
        except Exception as e:
            print(f"  registry stop: {e}"); break
        servers = d.get("servers") or []
        if not servers:
            break
        for s in servers:
            srv = s.get("server", s)
            meta = (s.get("_meta") or {}).get("io.modelcontextprotocol.registry/official", {})
            name = srv.get("name")
            if not name:
                continue
            npm_pkg, repo, kind = None, None, "remote"
            for p in (srv.get("packages") or []):
                rt = (p.get("registryType") or p.get("registry_name") or "").lower()
                ident = p.get("identifier") or p.get("name")
                if rt in ("npm",) and ident:
                    npm_pkg, kind = ident, "npm"; break
                if rt in ("pypi", "pip") and ident and not npm_pkg:
                    kind = "python"
                if rt in ("oci", "docker") and not npm_pkg:
                    kind = "docker"
            # A remote server has no packages[]; its endpoint lives in remotes[]. We read packages and
            # threw remotes away, which is the whole reason a hosted MCP server in someone's config
            # came back "not in the tashan index".
            rhost = None
            for rm in (srv.get("remotes") or []):
                u = rm.get("url") or ""
                m2 = re.match(r"https?://([^/:?#]+)", u)
                if m2:
                    rhost = m2.group(1).lower(); break
            repo = (srv.get("repository") or {}).get("url")
            if repo:
                m = re.search(r"github\.com[/:]([\w.-]+/[\w.-]+?)(?:\.git|/|$)", repo)
                repo = m.group(1) if m else repo
            cid = f"pkg:{npm_pkg}" if npm_pkg else f"registry:{name}"
            status = meta.get("status")
            if status == "deleted":
                # Spam / malware / illegal content, per the registry's own moderation policy.
                #
                # This used to DELETE the row, which is right for the board and badly wrong for the
                # user. `doctor` answers from what it can find, so a deleted row meant a person running
                # a server the registry had pulled for malware was told "not in the tashan index —
                # unmeasured, not necessarily bad". That reads as reassurance. Deleting the evidence is
                # the one thing that turns a warning we could give into silence.
                #
                # So the row STAYS, delisted: it keeps registry_status='deleted', compute_scores refuses
                # it a score so it can never rank or be recommended, and export() puts it in the lookup
                # table anyway so doctor and the MCP server can raise an alert on it.
                con.execute("""INSERT INTO capabilities (id,name,kind,registry_name,registry_status,registry_updated,in_registry)
                  VALUES (?,?,?,?,'deleted',?,1)
                  ON CONFLICT(id) DO UPDATE SET registry_status='deleted',
                    registry_updated=excluded.registry_updated, tashan_score=NULL""",
                  (cid, name.split("/")[-1], kind, name, meta.get("updatedAt")))
                removed += 1
                continue
            if status == "deprecated":
                deprecated += 1
            con.execute("""INSERT INTO capabilities (id,name,kind,title,description,npm_pkg,source_repo,registry_name,registry_status,registry_updated,remote_host,in_registry)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,1)
              ON CONFLICT(id) DO UPDATE SET title=COALESCE(excluded.title,capabilities.title),
                description=COALESCE(excluded.description,capabilities.description),
                source_repo=COALESCE(excluded.source_repo,capabilities.source_repo),
                registry_name=excluded.registry_name, registry_status=excluded.registry_status,
                registry_updated=excluded.registry_updated, in_registry=1,
                npm_pkg=COALESCE(capabilities.npm_pkg,excluded.npm_pkg),
                remote_host=COALESCE(excluded.remote_host,capabilities.remote_host)""",
              (cid, name.split("/")[-1], kind, srv.get("title"), srv.get("description"),
               npm_pkg, repo, name, meta.get("status"), meta.get("updatedAt"), rhost))
            seen += 1
        con.commit()
        cursor = (d.get("metadata") or {}).get("nextCursor")
        if seen % 1000 < 100:
            print(f"  registry: {seen} servers...", flush=True)
        if not cursor:
            break
    # only advance the watermark on a clean finish; a crash must re-read the same window next time
    con.execute("INSERT INTO sync_state (source,last_synced,last_cursor,seen,note) VALUES (?,?,?,?,?) "
                "ON CONFLICT(source) DO UPDATE SET last_synced=excluded.last_synced, "
                "last_cursor=excluded.last_cursor, seen=excluded.seen, note=excluded.note",
                (SRC, started, cursor, seen,
                 f"{seen} seen, {deprecated} deprecated, {removed} delisted (registry status=deleted)"))
    con.commit()
    print(f"  registry: {seen} servers ({deprecated} deprecated, {removed} delisted as deleted/spam)",
          flush=True)
    return seen

# ---------- phase C: npm enrichment (quality) ----------
def enrich_npm(con):
    cache = json.load(open(NPM_CACHE)) if os.path.exists(NPM_CACHE) else {}
    # never-enriched first (advance coverage past the cap over runs), then by adoption proxy
    rows = con.execute("SELECT id, npm_pkg FROM capabilities WHERE npm_pkg IS NOT NULL "
                       "ORDER BY (npm_downloads IS NULL) DESC, config_reach DESC, in_registry DESC "
                       "LIMIT ?", (NPM_CAP,)).fetchall()
    print(f"  enriching {len(rows)} npm packages...", flush=True)
    done = 0
    for cid, pkg in rows:
        if bad_pkg(pkg):                                  # skip local-path junk — don't waste an API 404
            continue
        # "keywords" not in the entry means it predates that field, not that the package has none —
        # an absent key is a cache miss, a present-but-empty one is a measured answer. Without this
        # the 1,588 already-cached entries would keep serving their keyword-less selves forever and
        # the new column would populate only for packages nobody had looked at yet.
        if pkg in cache and "keywords" in cache[pkg]:
            info = cache[pkg]
        else:
            info = {}
            # A FETCH THAT FAILED IS NOT A MEASUREMENT OF ZERO. This used to write
            # `info["downloads"] = None` on any exception and then cache the entry, so one bad run
            # poisoned the package permanently: the cache-miss rule below treats a present "keywords"
            # key as a hit, so the null was served on every future run and never re-requested.
            #
            # A run on 2026-08-01 did exactly that to 1,751 packages. npm download counts in the DB
            # fell from 1,412 rows to 505, adoption evaporated for most of the npm corpus, and 655
            # capabilities dropped off the board — from a network failure, not from anything changing
            # in the world. enrich_github already documents this rule ("DON'T cache a transient
            # failure — retry next run, never poison"); this is the same rule, here.
            #
            # 404 is an answer (the package is gone). Anything else is the network having a bad day.
            transient = False
            try:
                dl = get_json(f"https://api.npmjs.org/downloads/point/last-week/{urllib.parse.quote(pkg, safe='@/')}")
                info["downloads"] = dl.get("downloads")
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    info["downloads"] = None       # really has no downloads / no longer published
                else:
                    transient = True
            except Exception:
                transient = True
            try:
                meta = get_json(f"https://registry.npmjs.org/{urllib.parse.quote(pkg, safe='@/')}")
                latest = (meta.get("dist-tags") or {}).get("latest")
                t = meta.get("time") or {}
                info["last_publish"] = (t.get(latest) or "")[:10] or None
                info["created"] = (t.get("created") or "")[:10] or None
                # ABSENT != ZERO. `len(meta.get(k) or [])` read a missing key as a measured 0, and a
                # published npm package can never truly have 0 maintainers or 0 versions — so every 0
                # here really meant "the packument did not carry this field". It then entered the scorer
                # as evidence: people=0 scores the bus-factor axis at 0/40 AND asserts the axis is
                # measured, so upkeep collapsed to 0. This file promises unknown inputs stay None and are
                # never faked to 0; this was the leak.
                info["latest_version"] = latest or None
                info["maintainers"] = len(meta["maintainers"]) if meta.get("maintainers") else None
                info["versions"] = len(meta["versions"]) if meta.get("versions") else None
                # UNPUBLISHED IS NOT UNKNOWN. npm answers a removed package with a tombstone packument —
                # `_id`, `_rev`, `name`, `time` and nothing else: no dist-tags, no versions, no
                # maintainers. All three rows carrying the faked 0s above (netlify-mcp, mcp-server-time,
                # marketintell) are this, not a fetch failure. Nulling those fields alone would REGRESS
                # them: with no maintainer or version axis they would be scored on freshness alone and
                # climb onto the board, when the truth is the package cannot be installed at all. npm
                # refusing to serve a version IS npm saying do not use this, which is what npm_deprecated
                # already means to the scorer and the dossier, so it is recorded there.
                unpublished = not latest and not meta.get("versions")
                info["deprecated"] = 1 if (unpublished or "deprecated" in
                                           ((meta.get("versions") or {}).get(latest) or {})) else 0
                if not info.get("repo"):
                    ru = (meta.get("repository") or {}).get("url") or ""
                    m = re.search(r"github\.com[/:]([\w.-]+/[\w.-]+?)(?:\.git|/|$)", ru)
                    info["repo"] = m.group(1) if m else None
                # The author's own vocabulary. Packuments carry keywords at the root OR only on the
                # latest version depending on how the package was published, and reading just the
                # root misses the second group entirely.
                kw = meta.get("keywords") or ((meta.get("versions") or {}).get(latest) or {}).get("keywords") or []
                info["keywords"] = [str(k).strip() for k in kw if str(k).strip()][:30] if isinstance(kw, list) else []
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    transient = True
            except Exception:
                transient = True
            if transient:
                # Leave the row exactly as the last good run measured it and try again next time.
                time.sleep(0.05)
                continue
            # record the key even when the package is genuinely gone, so a dead package is not
            # re-requested on every run for the rest of time by the cache-miss rule above
            info.setdefault("keywords", [])
            cache[pkg] = info
            time.sleep(0.05)
        # COALESCE every measured field: a partial answer must never delete a whole one. Belt and
        # braces with the transient guard above — a stale-but-real download count is strictly better
        # than a null, because null reads to the scorer as "no adoption evidence".
        con.execute("""UPDATE capabilities SET
              npm_downloads=COALESCE(?, npm_downloads),
              npm_last_publish=COALESCE(?, npm_last_publish),
              npm_created=COALESCE(?, npm_created),
              npm_maintainers=COALESCE(?, npm_maintainers),
              npm_versions=COALESCE(?, npm_versions),
              npm_deprecated=COALESCE(?, npm_deprecated),
              npm_latest_version=COALESCE(?, npm_latest_version),
              npm_keywords=COALESCE(?, npm_keywords),
              source_repo=COALESCE(source_repo,?) WHERE id=?""",
          (info.get("downloads"), info.get("last_publish"), info.get("created"),
           info.get("maintainers"), info.get("versions"), info.get("deprecated"),
           info.get("latest_version"), ",".join(info.get("keywords") or []) or None,
           info.get("repo"), cid))
        done += 1
        if done % 200 == 0:
            con.commit(); json.dump(cache, open(NPM_CACHE, "w")); print(f"    npm {done}/{len(rows)}", flush=True)
    con.commit(); json.dump(cache, open(NPM_CACHE, "w"))
    return done

# ---------- phase C2: GitHub repo health (the capability's OWN source repo) ----------
# Uses the `gh` CLI (already authenticated, 5,000 req/hr) like scraper/scrape.py — not urllib.
# Cached in github_cache.json (mirrors npm_cache.json); ~3 calls/repo. This is repo-native health
# (stars/contributors/releases/archived of the server itself), distinct from scrape.py's HOST-repo meta.
def gh_api(path, jq=None):
    """Returns (status, data). status ∈ 'ok' | 'notfound' | 'transient'.
    Only a genuine HTTP 404 is cacheable-as-missing; rate-limits (403), timeouts, 5xx and network errors are
    TRANSIENT and must never be cached — caching them is what poisoned github_cache with false 'missing' entries."""
    args = ["gh", "api", path] + (["--jq", jq] if jq else [])
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=40)
    except Exception:
        return ("transient", None)                          # timeout / spawn failure — retry next run
    if out.returncode == 0:
        try:
            return ("ok", json.loads(out.stdout) if out.stdout.strip() else None)
        except Exception:
            return ("transient", None)                      # malformed output — don't cache
    err = (out.stderr or "").lower()
    if "http 404" in err or "not found" in err:
        return ("notfound", None)                           # genuine 404 / moved / private — safe to remember
    return ("transient", None)                              # 403 rate-limit / 5xx / network — resolve on a later run

REPO_RE = re.compile(r"^[\w.-]+/[\w.-]+$")
GH_MISSING_TTL_DAYS = 30

def _stale(at, days):
    if not at:
        return True                                          # no timestamp (legacy/poisoned entry) → re-verify
    try:
        return (datetime.now(timezone.utc).date() - datetime.fromisoformat(at).date()).days >= days
    except Exception:
        return True

def enrich_github(con):
    cache = json.load(open(GH_CACHE)) if os.path.exists(GH_CACHE) else {}
    today = datetime.now(timezone.utc).date().isoformat()
    # Order: never-enriched first (advance coverage across runs), then adoption proxies that exist PRE-scoring.
    # (trust is computed in phase D, AFTER this phase — ordering on it pushed every fresh row to the bottom
    #  forever, so new caps never got enriched: the circular-dependency bug.)
    #
    # "Never enriched" is keyed on gh_contributors, NOT gh_pushed. ingest_plugins.py writes gh_pushed and
    # gh_stars itself, so once plugins arrived every plugin repo LOOKED enriched to this query and sorted
    # to the bottom forever — while still missing the contributor and release counts that only this
    # function fetches. That is the entire reason 0% of 3,961 plugins had a maintainer or cadence signal,
    # which in turn made Maintenance for every rated plugin a copy of Freshness. Key the test on the
    # column this function alone populates, and it cannot drift again when another ingest adds a source.
    rows = con.execute("SELECT id, source_repo FROM capabilities WHERE source_repo IS NOT NULL "
                       "ORDER BY (gh_contributors IS NULL) DESC, config_reach DESC, npm_downloads DESC NULLS LAST "
                       "LIMIT ?", (GH_CAP,)).fetchall()

    # A REPO'S STARS ARE A PER-ITEM SIGNAL ONLY WHERE THE REPO IS THE ITEM.
    #
    # ingest_plugins.py is careful about this — it computes `solo` and refuses to attach stars to a
    # plugin whose repo hosts several. Then THIS function ran afterwards (run.py: plugins →
    # registry+npm), selected every row with a source_repo, and wrote gh_stars back unconditionally.
    # The guard was undone minutes after it was applied and nothing restored it, so chujianyun/skills
    # gave each of its 25 plugins the same 700 stars, the same adoption of 44, and the same score of
    # 70.0; across the corpus 593 artifacts carried a star count they shared with their siblings, and
    # 336 skills each displayed one repo's 23,181 as their own evidence.
    #
    # Only the star count is per-item. pushed/contributors/licence/archived ARE repo-level facts and
    # stay shared, which is why this nulls one column rather than skipping the row.
    shared_star_ids = {r[0] for r in con.execute(
        """SELECT c.id FROM capabilities c JOIN (
               SELECT source_repo, kind FROM capabilities
               WHERE source_repo IS NOT NULL AND kind IN ('plugin','skill','remote')
               GROUP BY source_repo, kind HAVING COUNT(*) > 1
           ) m ON m.source_repo = c.source_repo AND m.kind = c.kind""")}
    if shared_star_ids:
        print(f"  {len(shared_star_ids):,} plugin/skill rows share a repo — stars are not theirs, held null")
    print(f"  enriching {len(rows)} source repos via gh...", flush=True)
    done = 0
    for cid, repo in rows:
        repo = (repo or "").strip().strip("/")
        if not REPO_RE.match(repo):          # only owner/name (skip full URLs / junk)
            continue
        cached = cache.get(repo)
        # cache hit — unless it's a 'missing' entry old enough to re-verify (a 404 today may be a real repo later;
        # this also auto-purges legacy poisoned entries, which have no 'at' timestamp → treated as stale)
        if cached is not None and not (cached.get("missing") and _stale(cached.get("at"), GH_MISSING_TTL_DAYS)):
            info = cached
        else:
            st, r = gh_api(f"/repos/{repo}", "{stars:.stargazers_count, forks:.forks_count, "
                       "open_issues:.open_issues_count, pushed:.pushed_at, license:.license.spdx_id, "
                       "topics:.topics, has_discussions:.has_discussions, archived:.archived}")
            if st == "transient":
                done += 1; continue          # DON'T cache a transient failure — retry next run, never poison
            if st == "notfound" or r is None:
                info = {"missing": 1, "at": today}
            else:
                info = r
                info["at"] = today
                info["topics"] = ",".join(info.get("topics") or []) or None
                # contributor count (bus factor) + latest release. If EITHER is transient, skip caching the
                # whole repo this run rather than store silently-wrong (0-contributor / no-release) health.
                st2, contribs = gh_api(f"/repos/{repo}/contributors?per_page=30&anon=true")
                st3, rel = gh_api(f"/repos/{repo}/releases/latest", "{at:.published_at}")
                if st2 == "transient" or st3 == "transient":
                    done += 1; continue
                info["contributors"] = len(contribs) if isinstance(contribs, list) else None
                info["last_release"] = (rel or {}).get("at")
            cache[repo] = info
            time.sleep(0.02)
        if info.get("missing"):
            done += 1; continue
        con.execute("""UPDATE capabilities SET gh_stars=?, gh_forks=?, gh_open_issues=?, gh_pushed=?,
              gh_contributors=?, gh_last_release=?, gh_license=?, gh_topics=?,
              gh_has_discussions=?, gh_archived=? WHERE id=?""",
          (info["stars"] if cid not in shared_star_ids else None,
           info.get("forks"), info.get("open_issues"), info.get("pushed"),
           info.get("contributors"), info.get("last_release"), info.get("license"), info.get("topics"),
           1 if info.get("has_discussions") else 0, 1 if info.get("archived") else 0, cid))
        done += 1
        if done % 100 == 0:
            con.commit(); json.dump(cache, open(GH_CACHE, "w")); print(f"    gh {done}/{len(rows)}", flush=True)
    con.commit(); json.dump(cache, open(GH_CACHE, "w"))
    return done

# ---------- phase C3: repo-linked Discord — the project's OWN chat, from its README (product-specific) ----------
# (HN mention-counts were tried and dropped: even quoted, common-word product names — raven, soma — collect
#  false-positive threads that outrank real products like context7. Unreliable => not shown. Honest > padded.)
DISCORD_RE = re.compile(r"https?://(?:discord\.gg|discord\.com/invite)/[A-Za-z0-9]+")

def enrich_discord(con):
    """Pull the project's own Discord invite out of its cached README (0 API cost). Only where it exists."""
    man_path = os.path.join(ROOT, "data", "readmes", "manifest.json")
    if not os.path.exists(man_path):
        return 0
    n = 0
    for r in json.load(open(man_path)):
        m = DISCORD_RE.search(r.get("readme") or "")
        if m:
            con.execute("UPDATE capabilities SET discord_url=? WHERE id=?", (m.group(0), r["id"])); n += 1
    con.commit(); return n

def enrich_homepage(con):
    """The project's own homepage/docs (repo.homepage) — a reliable, per-product resource. Cached in
    github_cache alongside repo health; only a real http(s) URL that isn't just the repo itself is kept."""
    cache = json.load(open(GH_CACHE)) if os.path.exists(GH_CACHE) else {}
    rows = con.execute("SELECT id, source_repo FROM capabilities WHERE source_repo IS NOT NULL "
                       "AND tashan_score IS NOT NULL ORDER BY tashan_score DESC LIMIT ?",
                       (int(os.environ.get("HP_CAP", "300")),)).fetchall()
    print(f"  homepage for {len(rows)} repos...", flush=True)
    done = 0
    for cid, repo in rows:
        repo = (repo or "").strip().strip("/")
        if not REPO_RE.match(repo):
            continue
        ent = cache.setdefault(repo, {})
        if not ent.get("homepage"):                       # wrap in an object — a bare-string jq isn't valid JSON
            # gh_api returns (status, data). This was the ONE caller that read the tuple as a dict,
            # and a non-empty tuple is truthy so `or {}` never caught it — .get() on it killed the
            # whole daily run for 7 days straight, taking phases D and E (scores + export) with it.
            # A miss stays None, which the `if not ...` above retries next run; nothing is cached as
            # missing here, so a transient 403 costs one re-query, never a poisoned entry.
            _st, _r = gh_api("/repos/" + repo, "{h: .homepage}")
            ent["homepage"] = (_r or {}).get("h") or None
            time.sleep(0.02)
        hp = ent.get("homepage")
        # keep only a real external URL that isn't just a link back to the repo
        if hp and hp.startswith("http") and "github.com/" + repo.lower() not in hp.lower():
            con.execute("UPDATE capabilities SET gh_homepage=? WHERE id=?", (hp, cid))
        done += 1
        if done % 100 == 0:
            con.commit(); json.dump(cache, open(GH_CACHE, "w")); print(f"    hp {done}/{len(rows)}", flush=True)
    con.commit(); json.dump(cache, open(GH_CACHE, "w"))
    return done

# ---------- phase D: scores (transparent, labelled) ----------
def months_since(iso):
    if not iso: return None
    try: return (datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00") if "T" in iso else iso + "T00:00:00+00:00")).days / 30.4
    except Exception: return None

# How hard thin evidence discounts Trust. 0 = coverage ignored (a one-axis read can score as high as a
# fully-measured one); 1 ≈ the old behaviour, where a capability measured on 35% of the axes lost ~65%.
# SWEPT on real board composition (top-200 mix, and whether the 51,323★ plugin outranks a 422-downloads/wk
# package), not chosen by feel:
#     0.00  → plugins take 177 of the top 200; renormalising alone overshoots
#     0.20  → 93 of 200; still lopsided
#     0.30  → 78 npm / 61 remote / 52 plugin; impeccable 72 (#22) vs vaaya 64        <- chosen
#     0.45  → impeccable 63 vs vaaya 64; the inversion this whole fix exists to kill is BACK
#     0.60  → plugins gone from the top 200 entirely; the original pathology
# Re-run the sweep before changing it: TASHAN_COVERAGE_W=x python3 -c "...compute_scores(db())".
# This is a stopgap for missing inputs, not a permanent knob — every contributor/release count we fetch
# for non-npm repos raises real coverage and shrinks the discount toward nothing on its own.
COVERAGE_W = float(os.environ.get("TASHAN_COVERAGE_W", "0.30"))
# Weight of the adoption axis inside coverage, relative to the 100 points of maintenance axes. Adoption
# is the single most informative signal we have, so missing it should cost about as much as missing the
# maintainer count and release cadence together.
ADOPT_W = 60.0
# Discount on star-derived adoption vs download-derived adoption. A weekly download is recurring use; a
# star is a one-time bookmark that never decays — and this site's own hero copy promises "what people
# KEEP … not stars". Treating them as identical (1.0) contradicted that and handed plugins 138 of the
# top 200 purely because plugin repos carry huge star counts. Swept on board mix:
#     1.0 -> 138 plugins in the top 200 (impeccable 78)
#     0.9 -> 125 (76)
#     0.8 -> 110 (73)   <- chosen: plugins well represented, neither channel dominating
#     0.7 ->  95 (71)
# Not a thumb on the scale for any capability: it is one weight applied to one evidence TYPE, stated
# here and on the methodology page, and it moves no individual row relative to its peers.
STAR_W = float(os.environ.get("TASHAN_STAR_W", "0.8"))
# How much of Trust survives when NOTHING uses a capability. This is the single most consequential
# number in the file: Maintenance and Freshness both saturate near 100 for any recently-pushed repo, so
# (1 - GATE_FLOOR) is the entire range adoption has to separate "people keep this" from "nobody does".
# At the original 0.6, Trust was ~60% "is the repo alive" and a 30-star plugin outranked packages with
# thousands of weekly downloads — which contradicts the hero claim that we measure what people KEEP.
# Swept on the Design hub, where the contrast is sharpest (figma-developer-mcp: 87k downloads/wk over a
# 530-day track record, vs impeccable: 51k stars, no usage signal at all):
#     0.60 -> huggingface 76, impeccable 73, figma 70, and amplitude (30 stars!) at 66
#     0.45 -> huggingface 69, impeccable 67, figma 66
#     0.30 -> figma 62 leads, huggingface 62, impeccable 61        <- chosen: usage-led
#     0.20 -> figma 59, impeccable 58
# Lowering it compresses every score on the site downward; that is correct, not a regression — the old
# band was 60-100 because 60 was free.
GATE_FLOOR = float(os.environ.get("TASHAN_GATE_FLOOR", "0.30"))
# SCORER VERSION — bump this whenever ANY input, weight, gate or calibration below changes, because
# every stored history point is only comparable to points sharing this string. It is not decoration:
# trend() in cli/doctor.mjs refuses to compare across versions, so forgetting to bump it publishes a
# fake trend, and bumping it needlessly only costs a short gap in trend availability. Cheap mistake in
# one direction, a lie to a customer in the other.
#   s1  the pre-2026-07-30 era. Four rewrites inside one week (usage rebalance, inversion fixes,
#       contributor rescore, distribution recalibration) all share this label, which is exactly why
#       nothing labelled s1 may be trended — it is a mixed bag, not a baseline.
#   s2  first version under the calibrated scale (absolute adoption anchors + _calibrate).
# s3: a capability whose OWN AUTHOR says it is over is no longer ranked at all — same treatment as a
# registry-deleted row. It applies to self_unmaintained (the declaration quoted from their README or
# description, see pipeline/doc_signals.py) alongside npm's deprecated flag and the registry's
# deprecated status, which previously only cost a 0.3 maintenance discount and still left them on the
# board. wooyun-legacy is why: it held #1 on the security shelf at Trust 70 with vitality "active",
# because its README says 不维护决定 in prose and GitHub's Archive box was never ticked.
#
# The scale changed, so signal_history has to tell s2 points from s3 ones rather than reading the drop
# as decay. Safe to redefine in place today: s3 has never been snapshotted (2026-08-01 is s2, and
# snapshot_history writes a day once), so no stored point carries this label yet.
# s4: eligibility now overrides score. A capability whose author, npm or the registry has declared
# it over is refused a score outright rather than scored and ranked low, so the population a score is
# drawn from changed — pkg:docfork held 55 under s3 and holds nothing under s4. That is a different
# rule, not a different dataset, which is exactly the boundary this string exists to mark: trend()
# must not read a capability's removal from the board as its score declining.
# (The coverage column added alongside is pure persistence and moves no number; it does not need a
# version of its own, but it rides this one.)
# s5 (3 Aug 2026): an archived repository now KEEPS the 'abandoned' vitality the archive flag gives it.
# It was being overwritten by the `recent` branch below, and the push that made an archived repo look
# recent is usually the commit that closed it — 20 archived capabilities read "active" on the board.
# Vitality feeds the stable-freshness floor and the gate, so scores moved: a new ruler, not a new
# reading of the old one, which is exactly what trend() must not compare across.
SCORER_VERSION = os.environ.get("TASHAN_SCORER_VERSION", "s5")
# ADOPTION ANCHORS — the value on each evidence channel that reads as fully adopted (axis = 1.0).
#
# THE BUG THIS FIXES: these used to be the CORPUS MAX. On power-law data that puts the median at the
# bottom of the log scale, and it made the headline score stop discriminating. Measured before the fix,
# across all 6,200 scored capabilities: p25=20, p50=27, p75=32, p90=39 — half the board inside a
# 12-point band and 98% below 50. Adoption itself read p50=7, p90=25, so `gate` spanned 0.33-0.48 for
# nine rows in ten: Maintenance and Freshness spread perfectly well and were then multiplied down by a
# gate with no range left. The compression was arithmetic, not a fact about the corpus.
# It was also unstable and unfair in a second way: one new 2M-downloads package rescales every other
# row's adoption downward, so a badge minted last week silently means something different this week.
# An absolute anchor makes the score a function of the capability's own evidence, which is what the
# methodology page claims and what a public badge needs.
#
# Chosen where each channel stops carrying information, then swept (see the table in `_adopt_axis`):
DL_FULL    = float(os.environ.get("TASHAN_DL_FULL", "100000"))  # weekly npm downloads = broad daily use
REACH_FULL = float(os.environ.get("TASHAN_REACH_FULL", "10"))   # distinct public configs; corpus max is 23
STAR_FULL  = float(os.environ.get("TASHAN_STAR_FULL", "20000"))  # stars on a plugin's own repo


def _adopt_axis(x, full):
    """One adoption channel, log-scaled to 0-1, reading 1.0 at `full` and clamped there.

    Log because adoption is multiplicative — 10 -> 100 downloads is the same kind of jump as
    1,000 -> 10,000. Clamped because above `full` the channel has said all it can: the difference
    between 100k and 2M weekly downloads is not four times the difference between 10 and 100.
    Swept on the resulting board (DL_FULL / STAR_FULL, spread = p90 - p25 of the published score):
        corpus max      -> p25 20  p50 27  p75 32  p90 39   spread 19   (the defect)
        1M / 100k       -> p25 24  p50 31  p75 38  p90 46   spread 22
        250k / 50k      -> p25 27  p50 35  p75 43  p90 52   spread 25
        100k / 20k      -> p25 30  p50 39  p75 48  p90 57   spread 27   <- chosen
        25k  / 5k       -> p25 34  p50 43  p75 53  p90 62   spread 28, but 1,696 dl/wk already saturates
    Tighter anchors keep buying spread and start buying it dishonestly: at 25k a top-5-percentile
    package reads the same as one with 40x its usage. 100k/20k is the last rung where the busiest
    capabilities are still separated from the merely popular ones.
    """
    return min(1.0, math.log1p(x or 0) / math.log1p(full))


# CALIBRATION — the raw arithmetic decides the ORDER; this decides the RANGE. They are different jobs
# and conflating them is what broke the headline number.
#
# Trust is a product of three factors that are each <= 1: base x gate x coverage. Every prior sweep in
# this file tuned the ORDER that product produces (usage-led ranking, plugins neither dominating nor
# absent, unknown adoption never beating known-poor adoption) and those results are good. What was
# never checked is the RANGE it lands in, and the range is unusable:
#
#   A capability with NO adoption evidence has gate == GATE_FLOOR == 0.30. With perfect maintenance,
#   perfect freshness and every other axis measured, its raw ceiling is 100 * 0.30 * 0.89 = 26.6.
#   38% of the board (2,361 of 6,200) has neither a download count nor a star count, so more than a
#   third of everything we publish is structurally incapable of exceeding 27 out of 100 no matter how
#   good it is. The measured result: p25=21, p50=29, p75=34 — half the corpus inside 13 points, 95%
#   below 50, and "well-kept but unproven" rendered as a number that reads to a user as "bad".
#
# The tempting fix is to raise GATE_FLOOR, but the floor sets ordering too (it is the entire weight of
# adoption relative to upkeep), and raising it re-introduces the inversion the 0.30 sweep exists to
# kill — a 30-star plugin outranking a package with 87k weekly downloads. So the floor stays where the
# ordering sweep put it, and the range is fixed here instead, by a STRICTLY MONOTONE map: it cannot
# reorder two capabilities, which means it cannot resurrect any inversion this file already fixed.
#
# Knees are fixed constants, not corpus percentiles. A percentile map would spread perfectly and
# re-baseline every night as the corpus grows — a badge minted today would mean something else next
# week without the capability changing at all. These are stated on the methodology page and move only
# when swept:
#     raw 50 -> 68   below the knee the field is dense and gets stretched; above it the field is thin
#                    (only 280 of 6,200 rows exceed raw 50) and gets compressed into the last 32 points.
# Swept on the published distribution, with the sanity rows the sweeps above already argue about
# (spread = p90 - p25; `inversions` counts pairs the map reorders, and must be 0 for every candidate):
#     none (raw) -> p25 21 p50 29 p75 34 p90 43 | spread 22 | figma 83  impeccable 73  vaaya 50
#     50:85      -> p25 36 p50 49 p75 58 p90 73 | spread 37 | figma 95  impeccable 92  vaaya 85
#     50:75      -> p25 32 p50 44 p75 51 p90 64 | spread 32 | figma 92  impeccable 86  vaaya 75
#     50:68      -> p25 29 p50 39 p75 46 p90 58 | spread 29 | figma 89  impeccable 83  vaaya 68  <- chosen
#     50:62      -> p25 26 p50 36 p75 42 p90 53 | spread 27 | figma 87  impeccable 79  vaaya 62
# Chosen on the TOP of the curve, not the middle. @vaaya/mcp is this file's running example of a
# thinly-used package (422 downloads/wk, 31 stars) and 50:85 publishes it as 85 — the overstatement a
# neutrality product cannot afford. 50:68 keeps it mid-pack while still separating the proven head
# (supabase 99, figma 89) from it.
#
# The middle of the field lands near 39, not the 50 the audit asked for, and that is deliberate: 38% of
# the corpus has neither a download count nor a star count, so a median of 50 would claim we think half
# of it is proven when we have no evidence either way. Spread stops at 29 for the same reason — beyond
# this the map would be manufacturing distinctions the evidence does not support. The remaining
# flatness is an evidence problem (more measured axes), not an arithmetic one.
CAL_KNEES = tuple(tuple(float(n) for n in p.split(":"))
                  for p in os.environ.get("TASHAN_CAL_KNEES", "50:68").split(","))


def _calibrate(raw):
    """Monotone piecewise-linear stretch of the raw 0-100 product onto the published 0-100 scale."""
    pts = ((0.0, 0.0),) + CAL_KNEES + ((100.0, 100.0),)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if raw <= x1:
            return y0 + (y1 - y0) * (raw - x0) / (x1 - x0)
    return 100.0


def compute_scores(con):
    rows = con.execute("SELECT id, config_reach, npm_downloads, npm_last_publish, npm_maintainers, "
                       "npm_versions, npm_deprecated, registry_status, gh_pushed, gh_last_release, "
                       "gh_archived, gh_stars, gh_open_issues, gh_contributors, gh_has_discussions, kind, "
                       "self_unmaintained "
                       "FROM capabilities").fetchall()
    now_iso = datetime.now(timezone.utc).isoformat()
    for (cid, reach, dl, lastpub, maint, vers, dep, rstatus, gh_pushed, gh_release,
         gh_arch, gh_stars, gh_issues, gh_contrib, gh_disc, kind, self_unmaint) in rows:
        # ADOPTION: blend real npm downloads (log) + config reach (log), 0-100
        a_dl = _adopt_axis(dl, DL_FULL)
        a_reach = _adopt_axis(reach, REACH_FULL)
        adoption = round(100 * (0.7 * a_dl + 0.3 * a_reach)) if (dl or reach) else None
        # PLUGINS have no public download telemetry — the channel simply does not publish one. Stars on
        # the plugin's OWN repository are the only public popularity signal, so they stand in for
        # DOWNLOADS here and NOWHERE else, in the same 0.7/0.3 blend. Two guards make this honest:
        # gh_stars is only populated when the repo hosts exactly one plugin (see ingest_plugins.py), so
        # this can never be a marketplace's popularity wearing a plugin's name; and the methodology page
        # states the substitution outright.
        #
        # This MUST be a branch, not an `if adoption is None` fallback. As a fallback it was dead code the
        # moment config_reach started counting marketplace manifests that reference the plugin: one
        # referenced by 2 marketplaces got a non-None reach-only adoption of 10, so the star path never
        # ran and impeccable (51,323★) scored the same as an unknown. Reach alone is a 1-3 valued signal
        # here; it cannot carry adoption by itself.
        if kind == "plugin":
            # STAR_W discounts star-derived adoption against download-derived adoption. They are not the
            # same evidence: a weekly download is recurring use, a star is a one-time bookmark that never
            # decays — and this site's own claim is "what people KEEP … not stars". 1.0 treats them as
            # equal, which is what the raw log-normalisation does.
            a_star = _adopt_axis(gh_stars, STAR_FULL)
            adoption = round(100 * STAR_W * (0.7 * a_star + 0.3 * a_reach)) if (gh_stars or reach) else None
        # FRESHNESS: recency of the MOST RECENT public activity — npm publish OR git push OR release.
        # (a repo can be active on git but stale on npm, and vice-versa — take the freshest signal)
        acts = [months_since(x) for x in (lastpub, gh_pushed, gh_release)]
        ms = min([a for a in acts if a is not None], default=None)
        freshness = None if ms is None else round(max(0, min(100, 100 * math.exp(-ms / 9))))
        # SINGLE-MAINTAINER (bus factor): real contributor count when known, else npm-maintainers proxy
        single = 1 if (gh_contrib is not None and gh_contrib <= 1) else \
                 (1 if (gh_contrib is None and maint is not None and maint <= 1) else 0)
        # VITALITY (methodology fix): "not updated" != "abandoned". A finished, loved tool with no
        # recent commits but healthy demand + low unresolved-issue pressure stays "stable" (not penalized).
        # ponytail: point-in-time heuristic (issue/star ratio + stars floor); true velocity comes from
        # signal_history as it accrues — refine the thresholds then.
        recent = ms is not None and ms <= 6
        vitality = None
        if rstatus == "deleted":
            # Delisted by the registry for spam/malware/illegal content. Never scored, so it can never
            # rank, be recommended, or appear on a hub — but the row survives so doctor can warn.
            con.execute("UPDATE capabilities SET adoption=?, freshness=?, upkeep=?, tashan_score=NULL, "
                        "vitality='abandoned', single_maintainer=?, updated_at=? WHERE id=?",
                        (None, None, None, 0, now_iso, cid))
            continue
        if gh_arch or dep or rstatus == "deprecated" or self_unmaint:
            # A README saying "we stopped" outranks a recent push date. The push is a PROXY for whether
            # anyone is still looking after this; the sentence is the maintainer answering directly.
            # wooyun-legacy was pushed 18 days ago (freshness 94) BECAUSE the commit that landed was the
            # one announcing the project was over.
            vitality = "abandoned"

        # ELIGIBILITY OVERRIDES SCORE. Where the AUTHOR or the REGISTRY has declared the thing should
        # not be used any more, it stops being ranked at all — the same treatment rstatus='deleted'
        # already gets above, for the same reason: a score is a recommendation, and recommending
        # something we have been told is over is worse than having no opinion.
        #
        # docfork scored 55, sat at rank 19 in Docs & Knowledge, and shipped a working install command
        # while its own description said "DEPRECATED: Use io.github.docfork/docfork instead" and our
        # grader's note read "shut down 2026-06-14, endpoints offline, keys dead, setup fails". No
        # amount of copy elsewhere on the site survives one page telling a reader to install a server
        # that has been switched off.
        #
        # Deliberately NOT gh_archived on its own: an archived repository is a statement about the
        # repo, not about whether the published package still works, and plenty of finished tools are
        # archived and fine. This is only the declarations that say "do not use this": the author's
        # own notice, npm's deprecation flag, and the registry's.
        discontinued = bool(self_unmaint or dep or rstatus == "deprecated")
        if discontinued:
            con.execute("UPDATE capabilities SET adoption=?, freshness=?, upkeep=?, tashan_score=NULL, "
                        "vitality='abandoned', single_maintainer=?, updated_at=? WHERE id=?",
                        (adoption, freshness, None, single, now_iso, cid))
            continue
        elif vitality == "abandoned":
            # ALREADY DECIDED, UPSTREAM, BY THE ARCHIVE FLAG — leave it. `discontinued` deliberately
            # excludes gh_archived (an archived repo is a statement about the repo, not about whether
            # the package still works), so an archived row falls through to here still carrying the
            # 'abandoned' set above. Without this branch `recent` overwrote it with "active", and the
            # push that made it look recent is usually the commit that CLOSED the project — the exact
            # wooyun-legacy failure this file already documents, back in a second form. 19 archived
            # capabilities were reading "active" on the board.
            pass
        elif recent:
            vitality = "active"
        elif ms is not None or gh_stars is not None:
            loved = (gh_stars or 0) >= 50 or gh_disc == 1
            pressure = gh_stars and gh_issues is not None and (gh_issues / max(gh_stars, 1)) > 0.15
            vitality = "stable" if (loved and not pressure) else "abandoned"
        # finished != dead: don't let staleness alone bury a stable, still-loved tool
        if vitality == "stable" and freshness is not None:
            freshness = max(freshness, 55)
        # MAINTENANCE: people + release cadence + freshness, RENORMALISED over the axes we can actually
        # measure for this capability.
        #
        # THE BUG THIS FIXES. The three weights were fixed at 40/25/35 and a missing input scored 0, so
        # anything not published to npm was capped at 35 however well maintained it was. impeccable
        # (51,323★, pushed yesterday, listed by 2 marketplaces) scored exactly 35 and ranked BELOW
        # @vaaya/mcp (422 downloads/wk, 31★), which reached 80 purely by having npm metadata to read.
        # That is "not on npm" being scored as "badly maintained" — the exact thing this file promises
        # never to do: unknown inputs stay unknown, they are never faked to 0.
        #
        # Renormalising ALONE overshoots the other way: one perfect axis would read 100/100 and every
        # recently-pushed plugin would outrank properly-measured packages. So the fix is two-sided —
        # renormalise the score over known weight, then discount TRUST by how much evidence backs it.
        # Thin evidence costs a little; it no longer costs 65 points, and it cannot buy the top either.
        m = w = 0.0
        # PEOPLE: how many humans are behind this. npm maintainers are publish rights; GitHub
        # contributors are who actually writes it. Preferring npm and DISCARDING the other punished
        # projects for being on npm at all: figma-developer-mcp has 1 npm publisher and 30 contributors,
        # so it scored the bus-factor axis as a one-person project and landed at Maint 70, BELOW a plugin
        # with the same 30 contributors and no npm metadata at all (Maint 100). More evidence must never
        # produce a worse score. 100 of 181 rows carrying both were throwing away the larger number.
        # (single_maintainer is computed separately and still reports publish-rights bus factor honestly.)
        people = max([x for x in (maint, gh_contrib) if x is not None], default=None)
        if people is not None: m += min(1.0, people / 3) * 40; w += 40
        if vers is not None: m += min(1.0, math.log1p(vers) / math.log1p(30)) * 25; w += 25
        if freshness is not None: m += freshness / 100 * 35; w += 35
        if dep: m *= 0.3
        if rstatus == "deprecated": m *= 0.3
        if gh_arch: m *= 0.3
        if self_unmaint: m *= 0.3      # the author's own words, same weight as the platform's flag
        # FRESHNESS ALONE IS NOT MAINTENANCE. We already publish recency as its own Freshness column, so
        # a Maintenance built only from freshness is the same signal wearing a second name — and Trust,
        # which averages the two, then counted it twice. Measured: all 2,531 rated plugins had Maint
        # within 2 points of Freshness, and the resulting "Maint 100" for a plugin sat beside a genuinely
        # three-axis "Maint 71" as if it were the stronger number. Maintenance means people are keeping
        # it alive, so it requires at least one people-or-cadence axis; without that it is unmeasured and
        # says so, and Trust rests on freshness alone with coverage reflecting exactly that.
        has_upkeep_axis = people is not None or vers is not None
        upkeep = round(100 * m / w) if (w and has_upkeep_axis) else None
        # TRUST (v2, transparent): mostly maintenance+freshness gated by adoption; labelled, not final
        parts = [x for x in (upkeep, freshness) if x is not None]
        score = None
        if parts:
            base = sum(parts) / len(parts)
            # UNKNOWN ADOPTION MUST NOT BEAT KNOWN-POOR ADOPTION. The gate used to read 0.7 when adoption
            # was None but 0.6 + 0.4*a/100 when it was measured — so a capability we knew nothing about
            # outscored one we had measured as barely used. A 2-star registry server with no adoption
            # signal tied @vaaya/mcp at Trust 64 exactly this way. Absence of evidence now sits at the
            # same floor as evidence of absence, and costs coverage on top.
            gate = GATE_FLOOR + (1 - GATE_FLOOR) * (adoption or 0) / 100
            # Coverage spans every axis Trust rests on — adoption included, since "we never found an
            # adoption signal" is missing evidence in precisely the sense this discount exists for.
            cov = (w + (ADOPT_W if adoption is not None else 0)) / (100.0 + ADOPT_W)
            # raw decides the ranking; _calibrate only decides the range it is published on (see above)
            score = round(_calibrate(base * gate * (1 - COVERAGE_W * (1 - cov))))
        # COVERAGE IS PERSISTED, because it is published arithmetic. It is a multiplier on every
        # score — `base * gate * (1 - COVERAGE_W * (1 - cov))` — and it was computed here, applied,
        # and then discarded, so the methodology's promise that "every input is shown on the
        # capability page" was impossible to keep for this one: the number did not survive the
        # function that produced it. A discount a reader cannot see is a black box the size of 30%.
        con.execute("UPDATE capabilities SET adoption=?, freshness=?, upkeep=?, tashan_score=?, "
                    "vitality=?, single_maintainer=?, coverage=?, updated_at=? WHERE id=?",
                    (adoption, freshness, upkeep, score, vitality, single,
                     round(cov, 3) if score is not None else None, now_iso, cid))
    con.commit()
    snapshot_history(con)

# ---------- signal_history: one trust/adoption snapshot per day (the un-backfillable retention moat) ----------
def snapshot_history(con):
    today = datetime.now(timezone.utc).date().isoformat()
    if con.execute("SELECT 1 FROM signal_history WHERE at=? LIMIT 1", (today,)).fetchone():
        return  # already snapshotted today — keep it daily-granular and bounded
    n = 0
    for cid, score, adoption in con.execute(
            "SELECT id, tashan_score, adoption FROM capabilities WHERE tashan_score IS NOT NULL"):
        con.execute("INSERT INTO signal_history (cap_id, metric, value, at, scorer) VALUES (?,?,?,?,?)",
                    (cid, "tashan_score", score, today, SCORER_VERSION))
        if adoption is not None:
            con.execute("INSERT INTO signal_history (cap_id, metric, value, at, scorer) VALUES (?,?,?,?,?)",
                        (cid, "adoption", adoption, today, SCORER_VERSION))
        n += 1
    con.commit()
    print(f"  signal_history: snapshotted {n} caps for {today}", flush=True)

# ---------- phase E: export site JSON ----------
def slugify(cid):
    return re.sub(r"[^a-z0-9]+", "-", cid.lower()).strip("-")


# Ownership is a NAMESPACE fact, not a substring one. This matched anywhere in the concatenated
# package+repo string, so @atomicmail/mcp-modelcontextprotocol was published to the world as
# "✓ Official from Anthropic" — an endorsement neither we nor Anthropic ever gave, on a package
# whose only qualification was containing the protocol's name. @perplexity-ai/mcp-server got the
# same badge via its source_repo. That is the reverse of the typosquat problem we already guard
# against in similar_official: there we refuse to accuse, here we were happy to vouch.
#
# A package is official iff it lives in the organisation's own npm scope, or its repository is
# owned by the organisation's own GitHub account. Both are checked on the exact namespace
# segment — the scope before the first "/", and the owner before the first "/".
OFFICIAL_NS = {
    "Anthropic": {"npm": ("@modelcontextprotocol", "@anthropic-ai"),
                  "gh": ("modelcontextprotocol", "anthropics")},
    "OpenAI":    {"npm": ("@openai",), "gh": ("openai",)},
    "Google":    {"npm": ("@google-cloud", "@google", "@google-gemini"),
                  "gh": ("google", "googleapis", "google-gemini", "googlecloudplatform",
                         "gemini-cli-extensions", "google-labs-code", "googlechrome",
                         "chromedevtools")},
    "Microsoft": {"npm": ("@microsoft", "@azure"),
                  "gh": ("microsoft", "azure", "azure-samples", "azurecosmosdb", "microsoftdocs")},
}

def official_of(pkg, repo):
    scope = (pkg or "").lower().split("/")[0] if (pkg or "").startswith("@") else ""
    owner = (repo or "").lower().split("/")[0]
    for org, ns in OFFICIAL_NS.items():
        if scope and scope in ns["npm"]:
            return org
        if owner and owner in ns["gh"]:
            return org
    return None


def export(con):
    cols = ["id","name","kind","title","description","npm_pkg","source_repo","registry_status",
            "config_reach","config_repos","stars_median","stars_max","last_seen",
            "npm_downloads","npm_last_publish","npm_created","npm_maintainers","npm_versions","npm_deprecated","npm_latest_version","remote_host",
            # with `title` (the marketplace NAME) this is what makes a plugin's install printable
            "plugin_market_repo",
            "co_used","adoption","freshness","upkeep","tashan_score",
            "expertise","expertise_verdict","expertise_note","retention","retention_note",
            "category","in_registry","in_configs",
            "gh_stars","gh_forks","gh_open_issues","gh_pushed","gh_contributors","gh_last_release",
            "gh_license","gh_topics","gh_has_discussions","gh_archived","vitality","single_maintainer",
            # the author's own sentence behind an "abandoned" vitality — exported so the page can
            # answer "says who?" by quoting them, rather than asserting it on our own authority
            "self_unmaintained", "coverage",
            # security audit — the detail page and the CLI both read these. sec_advisories carries the
            # full finding list; the page decides what a free reader sees and what needs a licence.
            "sec_advisory_count","sec_max_severity","sec_install_script","sec_permissions",
            "sec_provenance","sec_remote_content","sec_dep_count","sec_scanned_at","sec_advisories",
            # sec_advisories is fetched so redact_paid() can strip it; it never reaches a public file.
            "npm_license",
            "discord_url","gh_homepage"]
    # Only trust-ranked caps are ever exported (ranked = trust-not-null, capped below), so fetch just the top
    # slice via idx_score instead of materializing the whole table. LIMIT is a buffer above the 800 board cap
    # so junk-filtering still leaves ≥800. At 1M rows this reads ~1500 rows, not all of them.
    # Everything the user can act on belongs in ONE catalog — a skill and an MCP server answer the same
    # question ("make my agent do X"), so splitting them by artifact type organises the site around our
    # pipeline instead of their job. Unrated rows come along; they are simply not ranked (see below).
    # TWO queries, deliberately. A single "tashan_score IS NOT NULL OR kind='skill'" query ordered by trust and
    # capped silently deleted an entire tier the moment enough rows gained a score: registry rows filled
    # the slice and every unrated skill fell off the end, taking `catalogued` to zero. The ranked set and
    # the catalogued set are different populations and must be selected separately.
    # TWO PROJECTIONS OF ONE STORE — this is the fix for "the data is siloed".
    #
    # Everything (board, category rail, search) used to read ONE capped payload, so a hard limit set by
    # the interactive board's download weight silently decided what existed for the whole product:
    # 4,429 capabilities had a computed trust score and only 1,669 were reachable. We were doing the
    # work and discarding it at the gate.
    #
    #   BULK  (capabilities.json) — every scored capability. Nothing fetches it at runtime; it feeds
    #         prerender and the hubs, which are static HTML and therefore have NO payload budget, and it
    #         is the public export. Size here costs a user nothing.
    #   SLIM  (index.json)        — the interactive board only. Stays capped, because this one IS
    #         downloaded on first paint.
    # Every scored capability gets a page and a place on its category hub — that is the INTENT, and
    # a bare LIMIT quietly stopped honouring it. npm discovery took the scored population from ~5,900
    # to 7,175 overnight, so 1,175 capabilities were cut lowest-score-first with nothing said: plugins
    # thinned from 3,627 to 2,969 and the only way to notice was to count them. The population is
    # still growing (4,684 npm packages are discovered but not yet enriched, and each one scores once
    # it is), so this will keep biting. Raised to fit, and it now REPORTS when it truncates — the file
    # already warns about silent tier deletion twenty lines below, in a comment about the same bug one
    # layer down.
    BULK_CAP = int(os.environ.get("BULK_CAP", "12000"))
    RANK_CAP = 1080   # board only: the largest that fits the 45 KB gz index budget (test_site asserts it)
    rows = con.execute(f"SELECT {','.join(cols)} FROM capabilities WHERE tashan_score IS NOT NULL "
                       "ORDER BY tashan_score DESC, config_reach DESC, npm_downloads DESC "
                       f"LIMIT {BULK_CAP}").fetchall()
    scored_total = con.execute("SELECT COUNT(*) FROM capabilities WHERE tashan_score IS NOT NULL").fetchone()[0]
    if scored_total > len(rows):
        print(f"  !! BULK_CAP {BULK_CAP}: {scored_total - len(rows)} scored capabilities got NO page "
              f"(cut lowest-score-first of {scored_total}). Raise BULK_CAP or say so on the site.", flush=True)
    # Catalogued: things we deliberately list without a score (skills and plugins with no per-item
    # evidence). They are browsable and installable; they simply are not ranked.
    # Each tier gets its OWN quota. Ordering one combined query by stars filled all 1400 slots with
    # starred plugins, so skills (stars NULL, sorted last) never made the cut and `catalogued` went to
    # zero — the same class of silent-tier-deletion bug as before, one layer down. Populations that are
    # selected against different signals must not share a LIMIT.
    seen_ids = {r[0] for r in rows}
    def take(where, order, limit):
        out = [r for r in con.execute(
            f"SELECT {','.join(cols)} FROM capabilities WHERE {where} "
            f"ORDER BY {order} LIMIT {limit}").fetchall() if r[0] not in seen_ids]
        seen_ids.update(r[0] for r in out)
        return out

    DESC_OK = "description IS NOT NULL AND description != ''"
    rows += take(f"kind='plugin' AND {DESC_OK}", "gh_stars DESC NULLS LAST", 700)
    rows += take(f"kind='skill'  AND {DESC_OK}", "config_reach DESC, name", 700)
    # DISCONTINUED: listed, never recommended. compute_scores refuses a score to anything the author,
    # npm or the registry has declared over, which is what keeps it off the board and out of every
    # hub. But dropping it from the export entirely is a different mistake: pkg:docfork went from
    # "ranked 19th with a working install command" to "no page at all", so an indexed URL started
    # 404ing and anyone who had already installed it learned nothing. A page that says DISCONTINUED,
    # with the author's own notice and no install command, is the useful answer — the same shape as
    # the catalogued tier above, which is browsable without being ranked.
    rows += take(f"(self_unmaintained IS NOT NULL OR npm_deprecated=1 OR registry_status='deprecated') "
                 f"AND tashan_score IS NULL AND {DESC_OK}", "config_reach DESC NULLS LAST, name", 400)
    # bare single-word generic names carry no identity in a ranking (registry ingest skips the scraper's filter)
    DENY = {"mcp", "server", "mcp-server", "run", "serve", "cli", "app", "main", "index",
            "stdio", "tools", "mcp-serve", "client", "core", "test", "demo"}
    # Tutorial/homework servers published to the registry: "Send personalized greetings", "Pirate Mode",
    # dad jokes, MIT-course hw3 submissions. They score like any low-adoption server and were ranking on
    # the board, which undercuts the whole claim to measure what works. Patterns are deliberately
    # unambiguous — "template repository"/"boilerplate" are included (a scaffold is not a capability you
    # install to do work) but bare "template" is not, since real tools describe themselves that way.
    DEMO = re.compile(r"\bgreet(ing)?s?\b|hello,?\s*world|pirate mode|swashbuckling|dad joke"
                      r"|add two numbers|template repository|boilerplate", re.I)
    DEMO_NAME = re.compile(r"(^|[-_])(hw\d|test_m|hello|hellomcp|smithery-exam)([-_]|\d|$)", re.I)
    # Self-declared non-capabilities. `mcp-server-fetch` and `mcp-server-git` are dependency-confusion
    # CANARIES — unscoped npm names shadowing the official @modelcontextprotocol/server-* packages,
    # picking up thousands of weekly installs from people who assume the unscoped name is the real one.
    # They scored Trust 54 and 51 here, and the install snippet was telling readers to npx them. An index
    # that exists to say what is trustworthy must not rank a typosquat, so anything that declares itself
    # a canary/placeholder/not-for-production is not a capability and does not belong on the board.
    CANARY = re.compile(r"security research canary|\bcanary\b.*not for production"
                        r"|not for production use|placeholder package|name reservation|reserved name"
                        r"|do not (install|use) this package", re.I)
    # Local paths and shell fragments scraped into the corpus as capability names — "/home/blyons/
    # finances/main.ledger", "C:\\Users\\david\\OneDrive - Qolcom\\...", "cd cmd/mcp-server && go".
    # None currently reach the export because they carry no trust, but that is luck, not a rule: one
    # enrichment pass away from a score and they would be on the board.
    PATHY = re.compile(r"^[/~]|^[A-Za-z]:[\\/]|\\\\|^(cd|source|export|sudo|bash|sh|python|node|go)\s"
                       r"|&&|\.(jar|exe|ledger)$|/etc/|OneDrive", re.I)

    def junk(o):
        n = (o["npm_pkg"] or o["id"].split(":", 1)[-1] or "")
        if PATHY.search(n) or PATHY.search(o.get("name") or ""):
            return True
        # CONFIRMED MALWARE. OSV's malicious-packages database (MAL-* ids) is authoritative and, unlike
        # the CANARY rule below it, does not depend on the package DESCRIBING itself as a canary — real
        # malware will not self-declare. The two shadows of @modelcontextprotocol/server-* that CANARY
        # catches today are both independently confirmed as MAL-2026-5476 and MAL-2026-5478; this catches
        # the next one, which will not be so polite. The row survives in the lookup table so `doctor`
        # can still warn someone who already installed it — it is only refused a place on the board.
        if o.get("sec_max_severity") == "MALICIOUS":
            return True
        blurb = (o.get("description") or "") + " " + (o.get("title") or "")
        if DEMO.search(blurb) or DEMO_NAME.search(n.split("/")[-1]) or CANARY.search(blurb):
            return True
        if n.startswith("@"):
            return False  # scoped = real identity
        leaf = n.split("/")[-1].lower()
        return leaf in DENY
    # Descriptions come from READMEs and manifests and arrive full of markup. One row on the Database hub
    # rendered as a raw markdown image link — "[![smithery badge](https://…)](https://…)" — straight into
    # the "what it does" column. Clean once here so every surface (board, hubs, dossiers, llms.txt, CLI,
    # badges) benefits, rather than patching each renderer.
    MD_IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)")
    MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
    # MOJIBAKE. Ten shipped descriptions read "Pare Git \u05d2\u20ac\u201d Structured git operations" — a UTF-8
    # em-dash that some upstream decoded as a single-byte codepage before we ever saw it. It survives
    # into the board, the hubs, the agent endpoints and now the search token bag, where it also
    # produces junk tokens. Repairing is a round trip through the codepage that mangled it, kept ONLY
    # when the result is valid UTF-8 and contains fewer suspicious characters than the original —
    # otherwise text that legitimately uses those letters (Hebrew, Cyrillic) would be destroyed.
    SUSPECT = re.compile(r"[\u00c2-\u00c3\u05d0-\u05ea\u00e2][\u2013\u2014\u20ac\u2122\u201c\u201d]")
    def demojibake(d):
        if not d or not SUSPECT.search(d):
            return d
        for enc in ("cp1255", "cp1252", "latin-1"):
            try:
                fixed = d.encode(enc).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            if len(SUSPECT.findall(fixed)) < len(SUSPECT.findall(d)):
                return fixed
        return d

    def clean_desc(d):
        d = demojibake(d)
        if not d:
            return d
        d = MD_IMG.sub("", d)                 # images carry no meaning in a one-line summary
        d = MD_LINK.sub(r"\1", d)             # keep link text, drop the URL
        d = re.sub(r"[`*_#>]+", "", d)        # inline emphasis / heading marks
        d = re.sub(r"\s+", " ", d).strip()
        return d or None

    # `name` is whatever KEY a person typed in their config JSON, and a lot of people just type "mcp".
    # A SCOPED package whose leaf is generic has all of its identity in the scope: junk() rightly keeps
    # @vaaya/mcp, but the stored name is the bare leaf, so the Design hub listed "mcp" and "mcp-server"
    # as if they were nameless. The same is true UNSCOPED and was never handled — pkg:justdrop-mcp
    # shipped to the board labelled "mcp", pkg:drengr as "server", 30 rows in all, each with its real
    # identity sitting unused in npm_pkg. junk() is right to keep them (justdrop-mcp is a real package,
    # not junk); only the label was wrong. Prefer npm_pkg over title because the board's job is to let a
    # reader identify and install the thing, and the package name is the unambiguous form of that. Same
    # reasoning as clean_desc above: resolve it once here so the board, hubs, dossiers, llms.txt, CLI and
    # badges all get the real name rather than each renderer guessing.
    # DELIBERATELY NOT `DENY`. junk() uses DENY to DROP rows, so a word added there deletes capabilities:
    # "api" as a display name is meaningless, but registry:com.contrastcyber/api is a real, scored,
    # described capability whose id leaf is "api" — putting "api" in DENY would erase it from the site.
    # Bad label and not-a-capability are different judgements and need different lists.
    GENERIC_LABEL = DENY | {"api"}

    # ---- the human label -------------------------------------------------------------------------
    # The board read like a package manager: "@supabase/mcp-server-supabase" over
    # "pkg:@supabase/mcp-server-supabase" over a category chip — the npm coordinate twice and the
    # product name nowhere. This derives the name a person would say.
    #
    # COMPUTED HERE, ONCE, FOR THE WHOLE CORPUS, for two reasons. First, pretty() existed in FOUR
    # copies (index.js, capability.js, terminal.js, cli/tashan.mjs) and none of them handled a scope,
    # so "@upstash/context7-mcp" rendered as "@upstash/context7" on every surface. Second, and the
    # reason it CANNOT be a per-row function: two of the decisions below need to see every other row.
    #
    # THE TRAP THAT MAKES `title` UNUSABLE ALONE. `title` looks like the human name and often is —
    # but for an agent skill it is the CONTAINING repo's title, so 364 distinct skills on the board
    # share the title "claude-community". Rendering that would have collapsed a quarter of the board
    # into one name. It is the same defect as keying a plugin by the marketplace that listed it: the
    # artifact's name must come from the artifact. So a title is used only when no other capability
    # claims it.
    ACRONYM = set("api ai ui ux cli sql aws gcp db sdk http https url id io pdf csv json xml yaml "
                  "s3 ci cd seo crm erp gui ide os vm k8s ftp ssh dns rss llm npm qa bi 3d rag jwt "
                  "oauth ocr tts stt sms cms cdn dom ast orm rpc grpc tcp udp ip iot ar vr nlp".split())
    BRAND = {"devtools": "DevTools", "github": "GitHub", "gitlab": "GitLab", "postgresql": "PostgreSQL",
             "postgres": "Postgres", "mysql": "MySQL", "mongodb": "MongoDB", "openai": "OpenAI",
             "youtube": "YouTube", "javascript": "JavaScript", "typescript": "TypeScript",
             "graphql": "GraphQL", "wordpress": "WordPress", "bigquery": "BigQuery", "notionhq": "Notion",
             "dynamodb": "DynamoDB", "clickhouse": "ClickHouse", "duckdb": "DuckDB", "paypal": "PayPal",
             "linkedin": "LinkedIn", "deepseek": "DeepSeek", "huggingface": "HuggingFace",
             "cloudflare": "Cloudflare", "elevenlabs": "ElevenLabs", "sqlite": "SQLite"}
    # Only the affixes that mean "this is an MCP server" — never a word that carries meaning.
    AFFIX_RE = re.compile(r"^(mcp[-_]server|mcp|server)[-_]|[-_](mcp[-_]server|mcp|server)$")

    def _strip_affixes(t):
        for _ in range(3):
            nxt = AFFIX_RE.sub("", t)
            if nxt == t:
                break
            t = nxt
        return t

    def _titlecase(t):
        out = []
        for w in re.split(r"[-_\s.]+", t):
            if not w:
                continue
            lw = w.lower()
            if lw in BRAND:
                out.append(BRAND[lw])
            elif lw in ACRONYM:
                out.append(lw.upper())
            elif w[:1].isupper() and any(c.isupper() for c in w[1:]):
                out.append(w)                       # already cased by its author: DevTools, GraphQL
            else:
                out.append(w[:1].upper() + w[1:])
        return " ".join(out)

    def looks_authored(t, o):
        """A title is only worth preferring over the derived name when a human wrote it as a name.

        Half of them are just the slug again ("impeccable", "ponytail") or the repo path with the
        owner glued on ("agricidaniel-claude-seo") — using those threw away the title-casing and, in
        the second case, published a coordinate as a product name. Require a space or an internal
        capital, and reject anything that is merely the name/repo restated.
        """
        if not t or t.lower() in GENERIC_LABEL:
            return False
        if not (" " in t or any(c.isupper() for c in t[1:])):
            return False                                    # slug-shaped: all lowercase, no spaces
        flat = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
        ft = flat(t)
        return ft and ft != flat(o.get("name")) and ft not in flat(o.get("source_repo"))

    def label_of(o, title_owned):
        t = (o.get("title") or "").strip()
        if t and title_owned.get(t.lower()) == o["id"]:
            t = re.sub(r"\s*[-—:]?\s*MCP(\s+Server)?$", "", t, flags=re.I).strip()
            if looks_authored(t, o):
                return t
        n = (o.get("name") or "").strip()
        m = re.match(r"^@([^/]+)/(.+)$", n)
        scope, n = (m.group(1), m.group(2)) if m else ("", n)
        n = _strip_affixes(n)
        # "@acme/mcp-server" leaves nothing to say; the scope is the only identity there is.
        if not n or n.lower() in GENERIC_LABEL:
            n = _strip_affixes(scope) or n
        return _titlecase(n) or (o.get("name") or o["id"])

    def apply_labels(objs):
        """Second pass: a label is only correct in the context of every other label."""
        owner = {}
        for o in objs:
            t = (o.get("title") or "").strip().lower()
            if t:
                owner[t] = None if t in owner else o["id"]       # shared title -> owned by nobody
        for o in objs:
            o["label"] = label_of(o, owner)
        # Two real products can share a name — @notionhq/notion-mcp-server and @suekou/mcp-notion-server
        # are both "Notion", and there are many honest "Filesystem" servers. Showing identical rows is
        # worse than showing the publisher, so collisions get qualified.
        #
        # BUT NOT ALL OF THEM. The same principle the dedup uses: the highest-signal row in a colliding
        # group keeps the clean name and everyone else is qualified against it. Anthropic's Filesystem
        # is "Filesystem"; a clone of it is "Filesystem · someone". Qualifying every member produced
        # "Filesystem · modelcontextprotocol" at rank 3, which reads like the package name we just
        # removed.
        def vendor(o):
            m = re.match(r"^@([^/]+)/", (o.get("npm_pkg") or o.get("name") or ""))
            if m:
                return m.group(1)
            if o.get("source_repo") and "/" in o["source_repo"]:
                return o["source_repo"].split("/")[0]
            return ""

        flat = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
        groups = collections.defaultdict(list)
        for o in objs:
            groups[o["label"]].append(o)
        for label, group in groups.items():
            if len(group) < 2:
                continue
            # official first, then measured signal, then the id so the choice is deterministic
            # SCORE FIRST, official only as a tiebreak. Official-first handed "Context7" to a
            # score-42 marketplace listing over @upstash/context7-mcp, which scores 98 and has 1.1M
            # weekly downloads — the row anyone typing "Context7" actually means.
            group.sort(key=lambda o: (-(o.get("tashan_score") or 0),
                                      0 if o.get("official") else 1, o["id"]))
            for o in group[1:]:
                v = vendor(o)
                # A vendor that merely restates the name ("Tavily · tavily-ai") disambiguates nothing;
                # fall back to the package or the id, which always differ or they would be one row.
                if not v or flat(v) in flat(label) or flat(label) in flat(v):
                    # "Notion · makenotion/claude-code-notion-plugin/notion" is a path, not a name.
                    tail = (o.get("npm_pkg") or o["id"].split(":", 1)[-1]).split("/")
                    v = tail[0] if len(tail) > 1 else tail[-1]
                o["label"] = label + " · " + v
        return objs

    def display_name(o):
        n = (o.get("name") or "").strip()
        if n.lower() not in GENERIC_LABEL:
            return n
        return o.get("npm_pkg") or (o.get("title") or "").strip() or o["id"].split(":", 1)[-1] or n

    # Resolve the publisher ONCE here instead of re-deriving it in index.js, prerender.py and the CLI
    # from a source_repo string each of them had to carry. Shipping the answer costs a short token;
    # shipping the input cost 9 KB gzipped in the board index, which is 20% of its whole budget.
    caps = []
    # Task tags, fetched ONCE for the whole export rather than per row — 4,900 single-row lookups inside
    # the loop below is the shape that turns a 2-second export into a minute.
    #
    # FIT LEVEL AND ITS EVIDENCE. The job axis is the differentiated half of this product and it was
    # the only measurement shipping with no evidence attached: the export carried a bare task slug,
    # so a role page could say a capability is "for" contract review and offer nothing to check that
    # against — while the score, the least differentiated number here, had a whole methodology page.
    #
    # Fit is derived from BASIS, not from confidence. Confidence is bimodal (declared 0.75, graded
    # 0.90) so a numeric threshold would re-derive basis while looking finer than it is, and ranking
    # the ties inside a capability would order them arbitrarily and then call the first one "primary".
    # What the two bases actually mean:
    #   graded    a model read this capability's full text against the published rubric and assigned
    #             the task  -> PRIMARY, the capability is for this work
    #   declared  the AUTHOR's own keyword matched a task synonym exactly -> SUPPORTING, attributable
    #             to them, but a keyword is a label, not a statement of purpose
    #   inferred  the rejected lexical pass (37% precision, kept as evidence, never wired) would land
    #             here as INCIDENTAL if it were ever turned on
    # Recommendation surfaces should lead with primary and may list supporting; incidental never
    # belongs in a recommendation.
    FIT_BY_BASIS = {"graded": "primary", "declared": "supporting", "inferred": "incidental"}
    tags_by_cap = {}
    for cap_id, tag, basis, evidence in con.execute(
            "SELECT cap_id, tag, basis, evidence FROM capability_tags ORDER BY confidence DESC"):
        tags_by_cap.setdefault(cap_id, []).append({
            "t": tag, "b": basis,
            "f": FIT_BY_BASIS.get(basis, "incidental"),
            "e": (evidence or "")[:160] or None})

    for r in rows:
        o = dict(zip(cols, r))
        o["tasks"] = tags_by_cap.get(o["id"], [])
        o["description"] = clean_desc(o.get("description"))
        o["official"] = official_of(o.get("npm_pkg"), o.get("source_repo"))
        o["name"] = display_name(o)          # see display_name: a generic config key is not a name
        if junk(o):
            continue
        o["co_used"] = json.loads(o["co_used"]) if o["co_used"] else []
        o["gh_topics"] = o["gh_topics"].split(",") if o["gh_topics"] else []
        o["slug"] = slugify(o["id"])                     # stable per-cap slug (matches gen_badges + prerender)
        caps.append(o)

    # TWO CAPABILITIES, ONE PAGE. slugify() maps every non-alphanumeric run to "-", so `@stripe/mcp`
    # and `stripe-mcp` both become `pkg-stripe-mcp`: prerender writes one file twice, the second wins,
    # and a reader who clicks the OFFICIAL Stripe row can land on the unofficial package's dossier
    # wearing the official one's URL. It reported 6,326 pages while 6,324 files existed — the only
    # visible symptom, and only if you counted.
    #
    # The unscoped id keeps the bare slug: it is the one whose natural slug that is, and it is the
    # incumbent whose URL is already indexed. The scoped twin takes an `-at-<scope>` form. Chosen over
    # always-encoding "@" because that is the correct long-term rule but moves ~1,400 live URLs, which
    # is a migration with redirects, not a bug fix.
    seen = {}
    for o in caps:
        seen.setdefault(o["slug"], []).append(o)
    for s, group in sorted(seen.items()):
        if len(group) < 2:
            continue
        # unscoped first, then by id, so the winner never depends on export ordering
        group.sort(key=lambda o: (o["id"].startswith("pkg:@"), o["id"]))
        for o in group[1:]:
            scope = re.match(r"pkg:@([^/]+)/", o["id"])
            o["slug"] = slugify(f"pkg-at-{scope.group(1)}-{o['id'].split('/',1)[1]}") if scope \
                        else slugify(o["id"] + "-" + o["kind"])
        print("  slug collision: %s -> %s (kept by %s)"
              % (s, ", ".join(x["slug"] for x in group[1:]), group[0]["id"]), flush=True)

    # The board is trust-RANKED: only caps with a real trust score belong on it. This is also the exact
    # set prerender turns into pages, so capabilities.json, index.json, and /capability/*.html stay aligned
    # (no board row or co-use link can point at a page that doesn't exist).
    # NAME-CONFUSION NOTE (the Agensi "security scan" answered with public evidence instead of a claim).
    # We cannot audit anyone's code, so we don't pretend to. What we CAN show from public data is when an
    # unscoped package normalises to the same name as an official scoped one — the exact shape that let
    # two dependency-confusion canaries pull thousands of installs. This is stated as a neutral fact
    # ("an official package with a similar name exists"), never as an accusation: an unscoped package
    # having a similar name is not by itself evidence of bad intent, and calling it a typosquat would be
    # a claim we cannot support. Exact normalised-name equality only, so it stays conservative.
    def norm_name(p):
        leaf = (p or "").split("/")[-1].lower()
        return re.sub(r"[^a-z0-9]", "", re.sub(r"\b(mcp|server)\b", "", leaf.replace("-", " ")))
    # The reference set was two hardcoded npm scopes, which is why this matched 0 rows: it could only
    # ever catch a shadow of @modelcontextprotocol/* or @anthropic-ai/*. official_of() already resolves
    # first-party ownership across Anthropic, OpenAI, Google and Microsoft from the namespace, so use
    # it — a package impersonating @openai/* or @azure/* is the same hazard and was invisible.
    official = {}
    for c in caps:
        p = c.get("npm_pkg") or ""
        # An empty normalised name is a landmine, not a match: @azure/mcp reduces to "" because the
        # normaliser strips "mcp", so every unscoped package that also reduced to "" would be
        # published as a shadow of it. A name with no distinguishing characters left cannot be
        # confused with anything.
        if p.startswith("@") and c.get("official") and norm_name(p):
            official.setdefault(norm_name(p), (p, c.get("npm_created")))
    shadowed = 0
    for c in caps:
        p = c.get("npm_pkg") or ""
        if not p or p.startswith("@"):
            continue
        key = norm_name(p)
        twin, twin_born = (official.get(key) or (None, None)) if key else (None, None)
        # YOU CANNOT SHADOW SOMETHING THAT DID NOT EXIST YET. The first time this detector ever fired
        # on live data it flagged fastify-mcp (14,194 downloads/wk, first published 2025-03-03) and
        # fastify-mcp-server (2025-06-18) as shadows of @modelcontextprotocol/fastify — which was not
        # published until 2026-04-01, ten and thirteen months LATER. Both are ordinary community
        # packages that happened to pick the obvious name first; the normaliser strips "mcp", so
        # `fastify-mcp` collapses to `fastify` and collides.
        #
        # Publication order is a fact, not a judgement, and it disqualifies the accusation outright.
        # Unknown dates do NOT flag: this note is one step from an accusation of typosquatting, which
        # this file already says is "a claim we cannot support", so absent evidence it stays silent.
        born = c.get("npm_created")
        if twin and twin != p and born and twin_born and born > twin_born:
            c["similar_official"] = twin
            shadowed += 1
    if shadowed:
        print("  name-confusion: %d unscoped package(s) share a normalised name with an official one" % shadowed)

    # Same product listed twice (usually a pkg: row and its registry: twin, e.g. @codescene/codehealth-mcp
    # vs com.codescene/codescene-mcp-server). Two genuinely different capabilities essentially never ship
    # byte-identical descriptions, so an exact match on a non-trivial description means one product — keep
    # the row with the most signal behind it and drop the echo. A ranking that lists the same thing twice
    # is telling the reader something false about the field.
    # TWO collisions, one mechanism — the same product listed more than once:
    #   (1) byte-identical descriptions (the same author republishing under two names);
    #   (2) the same name from the same repo reached through two DISTRIBUTION CHANNELS. chrome-devtools-mcp
    #       is on npm and also ships as a plugin, and it ranked at both T93 and T60 — one product wearing
    #       two scores, which is worse for a reader than either score alone.
    # Keep the highest-trust row and fold the loser's channel into `also_via`, so the fact that it is
    # installable both ways survives while the duplicate listing does not.
    def collapse(caps, key, label):
        best = {}
        for c in caps:
            k = key(c)
            if k is None:
                continue
            prev = best.get(k)
            if prev is None or (c.get("tashan_score") or 0) > (prev.get("tashan_score") or 0):
                best[k] = c
        keep = {c["id"] for c in best.values()}
        out, dropped = [], 0
        for c in caps:
            k = key(c)
            if k is not None and c["id"] not in keep:
                dropped += 1
                via = best[k].setdefault("also_via", [])
                if c.get("kind") and c["kind"] not in via:
                    via.append(c["kind"])
                continue
            out.append(c)
        if dropped:
            print(f"  dedup: dropped {dropped} duplicate listing(s) sharing {label} with a higher-signal row")
        return out

    def by_desc(c):
        d = (c.get("description") or "").strip().lower()
        return d if len(d) > 25 else None

    def by_repo(c):
        return ((c["name"].lower(), c["source_repo"].lower())
                if c.get("name") and c.get("source_repo") else None)

    # A CLONE IS NOT A SECOND PRODUCT. by_desc keys on the WHOLE description, so it misses the copy that
    # is the original TRUNCATED — and that is the common shape, because a plugin republished under
    # someone else's repo carries an older/shorter version of the original blurb. Measured:
    # anthropics/claude-plugins-official/code-review and an unattributed copy in varaku1012/aditi.code
    # both reached the board at exactly 42, side by side, with nothing telling a reader which is the
    # original. That is the failure this whole gate exists to prevent.
    #
    # Bucketing on the description OPENING alone would be wrong: generic boilerplate collides honestly.
    # "A comprehensive Model Context Protocol (MCP) server that enables AI assistants to …" opens both an
    # Unreal Engine server and a Nextcloud one, which are different products and must both survive. So
    # the opening only nominates candidates, and a bucket collapses only if its members form a true
    # PREFIX CHAIN — each description literally a prefix of the next. That test verifies the relationship
    # instead of trusting the heuristic, so boilerplate cannot trigger it.
    def prefix_chain_keys(caps):
        buckets = {}
        for c in caps:
            d = (c.get("description") or "").strip().lower()
            if len(d) >= 80:
                buckets.setdefault(d[:80], []).append((d, c["id"]))
        keys = {}
        for k, members in buckets.items():
            if len(members) < 2:
                continue
            members.sort(key=lambda m: len(m[0]))
            if all(b[0].startswith(a[0]) for a, b in zip(members, members[1:])):
                for _, cid in members:
                    keys[cid] = k
        return keys

    caps = collapse(caps, by_desc, "a description")
    chain = prefix_chain_keys(caps)
    caps = collapse(caps, lambda c: chain.get(c["id"]), "a truncated copy of one description")
    caps = collapse(caps, by_repo, "a name and repo")

    # ---- an endorsement we cannot attribute is not an endorsement ---------------------------------
    # official_of() reads the namespace of source_repo. For a PLUGIN that repo is often the marketplace
    # that vendored it, not the author — so 52 plugins carried "✓ ANTHROPIC · OFFICIAL" for the sole
    # reason of being listed in anthropics/claude-plugins-official. Among them: asana (Asana's own
    # integration), context7 (Upstash's), testdino (TestDino's) and one that describes itself in its
    # own text as "the first official TRES Finance plugin". Crediting the curator as the author is a
    # false claim about two real companies at once, and it is the same defect as keying a plugin by
    # the marketplace that listed it — the artifact's identity is its own home.
    #
    # The manifest DOES carry an `author`, and ingest_plugins.py parses it, but there is no column to
    # put it in so it is discarded. Persisting that is the real fix and needs a migration plus a
    # re-ingest. Until then, withhold rather than guess: a repo that is home to several unrelated
    # plugins is a marketplace, and a listing there attributes nothing.
    #
    # COUNT DISTINCT PLUGINS, NOT LISTINGS. Counting listings is what once decided impeccable's repo
    # was "shared" and nulled its 51,323 stars. This touches ONLY the official badge — never a score,
    # never stars.
    MARKETPLACE_MIN = 4
    homed = collections.Counter(
        c.get("source_repo") for c in caps if c.get("kind") == "plugin" and c.get("source_repo"))
    unattributed = 0
    for c in caps:
        if c.get("kind") == "plugin" and c.get("official") and homed[c.get("source_repo")] >= MARKETPLACE_MIN:
            c["official"] = None
            unattributed += 1
    if unattributed:
        print(f"  official: withheld from {unattributed} plugin(s) vendored in a multi-plugin "
              f"marketplace — a listing is not an authorship claim")

    # ---- what we sell must not be in the file anyone can curl -------------------------------------
    # The audit's DETAIL is the paid feature. It was being written straight into the public export and
    # into lookup.json, so /data/capabilities.json served, to anyone, the exact three things the page
    # offers an "unlock detail" link for:
    #
    #   sec_advisories      the GHSA id, severity, summary and fixed version   (1 row today)
    #   sec_install_script  the literal command a package runs at install time (132 rows)
    #   sec_permissions     the FULL permission list; free shows only the first (287 rows)
    #
    # The paywall was decorative. Nothing was delivering that detail to a paying customer either —
    # there is no endpoint and no CLI path that reads sec_advisories — so the same curl was both the
    # leak and the only way to get what Pro advertises.
    #
    # Fixed by REMOVAL, not by building a gate: the free tier's copy is unchanged because the free
    # tier never showed the detail. It names every finding — how many advisories, at what severity,
    # that an install script exists, that a permission surface exists — which is the firewall this
    # project promises: the EXISTENCE of a risk is never hidden, only the detail needed to act.
    # Fields the pipeline needs but no surface renders. They were shipped anyway — 605 KB of a file
    # that is committed on every nightly run, for data nothing reads. The DB keeps every one of them;
    # only the public export stops carrying them. (test_firewall.py reads build.py's SCHEMA text, not
    # this export, so the firewall's list of public-signal columns is unaffected.)
    UNRENDERED = ("also_via", "retention_note", "in_configs", "npm_versions", "stars_max",
                  "stars_median", "config_repos", "in_registry", "npm_license", "sec_dep_count")

    def redact_paid(o):
        for _k in UNRENDERED:
            o.pop(_k, None)
        # ADVISORY DETAIL AND THE INSTALL COMMAND ARE FREE, and ship in the public export.
        #
        # They used to be stripped here and sold for $6/mo. Three of the four things Pro listed were
        # the identity of a vulnerability, its fixing version, and the command a package runs on your
        # machine before you have agreed to anything — i.e. the facts a person needs precisely when
        # they cannot yet act, withheld until they pay. A rater whose whole claim is independence
        # cannot make the remediation the upsell; naming a risk and then charging to say which risk
        # is a worse position than not scanning at all.
        #
        # This is the same call already made for sec_permissions two paragraphs down, for the same
        # reason, and it is now the rule rather than the exception. What stays paid is TIME —
        # history, monitoring, and being told when any of this CHANGES — never the current state.
        # Also cheap: 3 rows carry an advisory and 159 an install script, so the export barely moves.
        # sec_permissions stays PUBLIC IN FULL. An earlier version of this truncated it to the first
        # entry, which quietly broke a free-tier promise: the pricing page's free column says "what
        # it can reach on your machine", and the paid column said "the full permission list" — the
        # same fact sold twice, once as free and once as paid. It is the safety-relevant one, so it
        # is free, and the paid claim was cut rather than the data. The visible symptom was a page
        # reading "Worth a look — deep, real domain work" above "Handles credentials or secrets",
        # because the summary could no longer see the credentials permission to warn about it.
        perms = o.get("sec_permissions")
        if perms:
            try:
                lst = json.loads(perms) if isinstance(perms, str) else list(perms)
            except Exception:
                lst = []
            o["sec_perm_n"] = len(lst)
        return o

    for _c in caps:
        redact_paid(_c)

    # The human label, LAST — after dedup, over the set that actually ships. Run before it, every row
    # collided with the duplicate listing about to be dropped, so survivors were qualified against
    # twins that no longer exist: "Filesystem · modelcontextprotocol", "Memory · modelcontextprotocol".
    # A disambiguator is only correct against the rows a reader can actually see.
    apply_labels(caps)
    # RATED vs CATALOGUED. A skill lives inside a repository, so repo maintenance is shared by every skill
    # in it: measured just now, 854 skills scored 42.0 with a within-repo spread of 42.0-42.0. That number
    # says "the repo is alive", not "this skill is good", and publishing it per-skill would be a claim we
    # cannot support. So it is withheld rather than shown — the row stays fully browsable, searchable and
    # installable, it just isn't ranked until there is per-skill evidence (an expertise grade of its own
    # SKILL.md, or real cross-repo adoption). Saying "not rated yet" is the honest version of not knowing.
    for c in caps:
        per_item = (c.get("expertise") is not None) or ((c.get("config_reach") or 0) > 1) \
                   or (c.get("npm_downloads") is not None)
        if c.get("kind") == "skill" and not per_item:
            c["tashan_score"] = None
            c["rated"] = False
            c["rating_basis"] = ("Catalogued, not rated. Its only upkeep evidence is the repository "
                                 "it lives in, which every skill in that repo shares — so a per-skill "
                                 "score would carry no information. A grade of its own SKILL.md is what "
                                 "makes it rankable.")
        else:
            c["rated"] = c.get("tashan_score") is not None
        # One flag, resolved once here, so no renderer re-derives "is this thing over?" — that rule
        # already lives in compute_scores and a second copy would drift from it.
        c["discontinued"] = bool(c.get("self_unmaintained") or c.get("npm_deprecated")
                                 or c.get("registry_status") == "deprecated")
        # Every exported row must land in a category — the hubs are built by grouping on it, so an
        # uncategorised row is a page nothing links to. Discontinued rows can arrive without one
        # because classify.py only ever ran over scored capabilities, and these lost their score.
        # "other" is what merge_categories.py already coerces an unknown category to, and it is the
        # honest label: we never classified it. Dropping the row instead would delete the warning,
        # which is the only reason it is still exported.
        if not c.get("category"):
            c["category"] = "other"
    ranked = [c for c in caps if c.get("tashan_score") is not None]
    catalogued = [c for c in caps if c.get("tashan_score") is None]
    tot = con.execute("SELECT COUNT(*) FROM capabilities").fetchone()[0]
    enriched = con.execute("SELECT COUNT(*) FROM capabilities WHERE npm_downloads IS NOT NULL").fetchone()[0]
    graded = con.execute("SELECT COUNT(*) FROM capabilities WHERE expertise IS NOT NULL").fetchone()[0]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "public signal: MCP registry + config-adoption + npm quality + LLM expertise-eval (SQLite pipeline)",
        "total_capabilities": tot,
        "enriched_npm": enriched,
        "expertise_graded": graded,
        # WHAT WE HAVE ACTUALLY CHECKED, as a fraction of what we rank. The homepage said "Audited
        # first" over a corpus where 76% of ranked capabilities had never been risk-scanned at all,
        # and sold "we read the actual expertise" while 84% were ungraded. Coverage is more
        # persuasive than a claim and it is the one number that cannot flatter us: it moves only when
        # we do the work. Shipped so the page renders it instead of asserting anything.
        "risk_scanned": sum(1 for c in ranked if c.get("sec_scanned_at")),
        "job_mapped": sum(1 for c in ranked if c.get("tasks")),
        # The denominator, named explicitly. "ranked" cannot be it: the slim index overwrites that key
        # with the length of its own board slice (1,080), so a percentage taken against it read 119%
        # risk-scanned. A coverage figure with the wrong denominator is worse than no figure.
        "coverage_of": len(ranked),
        # The ruler these numbers were produced with. signal_history already records it per point so
        # trend() never compares across two of them; the export did not carry it at all, so a reader
        # holding a number had no way to know which scorer produced it.
        "scorer": SCORER_VERSION,
        "ranked": len(ranked),
        "catalogued": len(catalogued),
        # ONE number a reader can act on: how many capabilities carry evidence and have a page. The old
        # trio (tracked / npm-enriched / ranked) was pipeline telemetry — three figures that did not
        # nest, one of them mislabelled "quality-measured" when it counted npm enrichment, and none of
        # which answered "what can I actually look at?".
        "measured": len(ranked) + len(catalogued),
        # This string ships inside capabilities.json and index.json — it is public copy, and it kept
        # the name the product retired in SCHEMA_VERSION 5. "Trust" claimed an audit we do not perform.
        "note": "Ranked by the tashan score: upkeep and freshness, gated by real adoption, on public "
                "evidence only. Security: OSV advisories for the current release, install-time scripts, "
                "build provenance and declared permission surface. We do not review source or "
                "execute the capability. Expertise is a "
                "separate LLM-graded read of the capability itself. Method: https://tashan.sh/methodology.html",
        # ONE catalog: ranked first, then catalogued-but-unrated. Both are installable and searchable;
        # only the ranked ones carry a trust number, and `rated` says which is which.
        "capabilities": ranked + catalogued,
    }
    out = os.path.join(ROOT, "web", "data", "capabilities.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(payload, open(out, "w"), indent=2)

    # SLIM index — only the ~15 fields the board / ticker / ⌘K palette actually render. The heavy per-cap
    # fields (co_used, description, expertise_note, gh_topics, install, repo-health, community) are dropped;
    # detail pages carry those INLINE (prerender), so nothing downloads the 1.2 MB dossier at runtime.
    # `adoption` and `gh_stars` are here so the board can show the SCORE with its evidence underneath.
    # Without them the Adoption column could only print raw downloads, which is not comparable across
    # kinds and made a 422-downloads/wk package look bigger than a 51,323-star plugin.
    # NO `slug`: it is exactly slugify(id), so the board derives it (see js capHref) instead of paying
    # ~9 KB gz to ship a second copy of every id.
    # single_maintainer and similar_official are here for the CLI, not the board. `assess()` in
    # cli/doctor.mjs branches on both, the CLI reads THIS file, and neither field was in it — so two
    # of doctor's seven verdicts were dead code, including the only anti-typosquat warning we have.
    # similar_official matches 0 rows today (the CANARY description filter removes the two known
    # shadows before the detector runs) and must ship anyway, so the verdict can fire the day a real
    # typosquat appears — which, unlike a canary, will not announce itself.
    SLIM = ["id", "name", "label", "kind", "category", "npm_pkg", "official", "registry_status", "slug",
            "config_reach", "npm_downloads", "gh_stars", "adoption", "tashan_score", "upkeep", "vitality",
            "expertise", "expertise_verdict", "npm_deprecated", "gh_archived", "rated",
            "single_maintainer", "similar_official",
            # Security is the headline of the product, so the board must show it. Only the summary —
            # a count and a severity — never the advisory list, which is 30x the size and belongs on
            # the dossier. Emitted sparsely, so the ~76% of rows with no npm package cost nothing.
            "sec_advisory_count", "sec_max_severity", "sec_install_script"]  # NOT description: it is 104 KB gz of the index and the board never reads it
    slim = {k: payload[k] for k in ("generated_at", "method", "total_capabilities", "enriched_npm",
                                    "expertise_graded", "risk_scanned", "job_mapped", "coverage_of",
                                    "scorer", "ranked", "catalogued", "measured", "note")}
    # the board is capped; the bulk export above is not.
    # DISCONTINUED ROWS ARE NOT ON THE BOARD, so they have no business in the board's payload — this
    # is the one file every visitor downloads on first paint, and adding 139 rows nobody can see
    # pushed it from 54 KB to 56 KB gz and broke the budget test_site enforces. They stay in the bulk
    # export (so their dossier is generated) and in lookup.json (so doctor can warn); the board is
    # simply not where they belong.
    board = ranked[:RANK_CAP] + [c for c in catalogued if not c.get("discontinued")]
    # SPARSE: omit keys whose value is None. The index sits at ~90% of its 45 KB gz budget and every
    # new field competes with first paint; dropping nulls buys back ~2 KB, which is how the two CLI
    # fields above fit with room to spare. Only None is dropped — `false` and `0` are real
    # measurements, and `assess()` in cli/doctor.mjs tests `row.rated === false` specifically, so
    # dropping false would silently turn "catalogued but unrated" into "fine". Nothing in the board JS
    # or the CLI compares to null strictly, so an absent key reads identically to a null one.
    def _slim(c):
        rec = {k: c[k] for k in SLIM if c.get(k) is not None}
        # SLUG: shipped ONLY when it is not derivable. Clients compute slugify(id) themselves (the
        # comment above SLIM explains why — a full copy costs ~9 KB gz on first paint), which is right
        # for 6,323 of 6,326 rows and WRONG for the handful that lost a slug collision: the board
        # would keep linking `@stripe/mcp` to /capability/pkg-stripe-mcp, which is now the UNOFFICIAL
        # package's dossier. Three exception rows cost nothing; the derivation stays the default.
        if rec.get("slug") == slugify(c["id"]):
            rec.pop("slug", None)
        # The install command can be 300 characters and the board only needs the FACT that one
        # exists; the dossier reads the full value from the bulk export. Shipping the command here
        # would be pure weight on the file every visitor downloads.
        if rec.get("sec_install_script"):
            rec["sec_install_script"] = 1
        return rec

    slim["capabilities"] = [_slim(c) for c in board]
    slim["ranked"] = len(ranked[:RANK_CAP])
    # TASK INDEX — the browse axis, kept OUT of the board payload on purpose. index.json is fetched on
    # first paint and sits at 39.8 KB of a 45 KB budget; this map is 3.6 KB gz and is fetched only when
    # someone actually filters by task. Putting it in SLIM would spend first-paint weight on a filter
    # most visitors never touch.
    tag_map = {}
    for c in ranked + catalogued:
        for t in (c.get("tasks") or []):
            tag_map.setdefault(t["t"], []).append(c["id"])
    json.dump({"generated_at": payload["generated_at"], "tasks": tag_map},
              open(os.path.join(ROOT, "web", "data", "tags.json"), "w"))
    print(f"Task index ({len(tag_map)} tasks) -> web/data/tags.json")

    # LOOKUP — the CLI and the MCP server read THIS, not the board.
    #
    # index.json is a ranked slice sized for the web's first paint (1,080 + 510 rows, 45 KB gz budget).
    # The CLI was reading it as if it were a lookup table, and the consequences were invisible: the board
    # carries ZERO remote, docker or python rows, and only 522 of the 1,380 npm packages we measure. So
    # `doctor` answered "not in the tashan index — unmeasured" for capabilities we had measured and
    # scored, which is the worst possible answer: it reads as reassurance.
    #
    # A board and a lookup are different shapes and both are needed. This one is keyed by every identity
    # a config can produce, carries only the fields assess() and the MCP risk lines actually branch on,
    # and has no first-paint budget because nothing renders it — 5,787 rows, ~200 KB gz, fetched by a
    # terminal, once.
    LOOKUP = ["id", "name", "label", "kind", "npm_pkg", "category", "official", "slug", "tashan_score",
              "npm_latest_version", "remote_host",
              "vitality", "expertise_verdict", "npm_downloads", "gh_stars", "npm_deprecated",
              "gh_archived", "registry_status", "single_maintainer", "similar_official", "rated",
              # the security audit, so `doctor` can warn about something already installed
              "sec_advisory_count", "sec_max_severity", "sec_install_script", "sec_permissions",
              "sec_perm_n", "sec_provenance", "sec_remote_content", "sec_scanned_at",
              # the author's own "we stopped" sentence — doctor quotes it rather than asserting it
              "self_unmaintained"]
    # DELISTED ROWS BELONG IN THE LOOKUP, and nowhere else. A capability the registry pulled for
    # spam/malware/illegal content has no score (compute_scores refuses it one), so it is correctly
    # absent from the board, the bulk export and every hub — we must never recommend it. But `doctor`
    # answers from what it can find, so if it is missing here too, a user running it is told
    # "unmeasured, not necessarily bad". The row is the only thing that lets us warn.
    delisted = [dict(zip(("id", "name", "kind", "registry_status"), r)) for r in con.execute(
        "SELECT id, name, kind, registry_status FROM capabilities WHERE registry_status='deleted'")]
    # Same reasoning for confirmed malware: junk() keeps it off the board, but a user who already ran
    # `npx mcp-server-fetch` needs to be told, and doctor can only tell them if the row is reachable.
    malicious = [dict(zip(("id", "name", "kind", "sec_max_severity", "sec_advisory_count",
                           "sec_advisories", "sec_install_script"), r)) for r in con.execute(
        "SELECT id, name, kind, sec_max_severity, sec_advisory_count, sec_advisories, "
        "sec_install_script FROM capabilities WHERE sec_max_severity='MALICIOUS'")]
    # NO SEPARATE discontinued FETCH HERE. There used to be one, on the same reasoning as `delisted`
    # and `malicious` above — but those two are absent from `caps` and these are not: the export now
    # carries discontinued rows so their dossier still gets built. Fetching them again appended a
    # SECOND copy of all 141 to the lookup, and a name that resolves to two records resolves to
    # whichever landed first, which is how `chrome-devtools-mcp` started answering with a downgraded
    # row. They are already in `caps`; that is enough.
    by_key, recs = {}, []
    # `malicious` and `delisted` are fetched fresh from SQL, AFTER caps were redacted — so they
    # arrived carrying the raw install command and full advisory blob into a public file. Redact on
    # the way in, where every row passes, rather than at each source.
    for c in caps + delisted + malicious:
        rec = redact_paid({k: c[k] for k in LOOKUP + ["sec_advisories"] if c.get(k) is not None})
        i = len(recs); recs.append(rec)
        # Every way a config entry can name this thing points at the same record. `identify()` in
        # cli/doctor.mjs yields an npm package, a python package, a docker image or a remote host, so all
        # four have to be keys — matching on `name` alone is what limited this to npm and skills.
        for k in (c.get("npm_pkg"), c.get("name"), c.get("id"),
                  c.get("remote_host"),          # a hosted server is named by its host in a config
                  (c.get("id") or "").split(":", 1)[-1] or None):
            if k:
                by_key.setdefault(str(k).lower(), i)
    # SEARCH TERMS — a token bag per record, parallel to `records`, so find_capability can match what a
    # capability DOES rather than only what it is called.
    #
    # Name matching alone put web-search (57, 112 downloads/wk) above tavily (86, 32k/wk) for "search
    # the web", because tavily's NAME contains none of those words while its DESCRIPTION contains all
    # of them. Descriptions are the signal and were dropped from every file the CLI reads, to protect
    # the board's first-paint budget — a budget the CLI does not share.
    #
    # Prose would add ~387 KB gz. The matcher only needs tokens, so tokens are what ships: ~198 KB gz.
    # Tokens seen once are noise and tokens in more than 8% of the corpus are topic words; both are
    # dropped, which is what stops a capability winning by echoing the user's own words.
    STOP = set("""the a an and or of for to in on with your you it is are be this that from as at by
        not mcp server servers cli api tool tools app agent agents plugin skill skills claude ai using
        use uses support supports allows enables provides provide via into can will more other any
        all""".split())
    bags = []
    for c in caps + delisted:
        txt = ((c.get("name") or "") + " " + (c.get("description") or "")).lower()
        toks = [w for w in re.split(r"[^a-z0-9+]+", txt) if len(w) > 2 and w not in STOP]
        bags.append(sorted(set(toks))[:24])
    tdf = {}
    for b in bags:
        for t in b:
            tdf[t] = tdf.get(t, 0) + 1
    hi = len(bags) * 0.08
    terms = [" ".join(t for t in b if 2 <= tdf[t] <= hi) for b in bags]

    lookup_out = os.path.join(ROOT, "web", "data", "lookup.json")
    json.dump({"generated_at": payload["generated_at"], "scorer": SCORER_VERSION,
               "records": recs, "keys": by_key, "terms": terms}, open(lookup_out, "w"),
              separators=(",", ":"))
    print(f"Lookup ({len(recs)} caps, {len(by_key)} keys) -> web/data/lookup.json")

    slim_out = os.path.join(ROOT, "web", "data", "index.json")
    json.dump(slim, open(slim_out, "w"))
    print(f"\nExported {len(ranked)} rated + {len(catalogued)} catalogued / {tot} total "
          f"({enriched} npm-enriched) -> {out}")
    print(f"Slim index ({len(SLIM)} fields/cap) -> {slim_out}")
    print("Top 12 by Trust:")
    for c in caps[:12]:
        print(f"  T{c['tashan_score'] or 0:>3}  A{c['adoption'] or 0:>3}  M{c['upkeep'] or 0:>3}  F{c['freshness'] or 0:>3}  "
              f"{(c['npm_downloads'] or 0):>8}dl  {c['name']}")

def main():
    con = db()
    print("A. config-adoption..."); print("   loaded", load_configs(con))
    print("B. MCP registry (coverage)..."); ingest_registry(con)
    print("C. npm enrichment (quality)..."); enrich_npm(con)
    print("C2. github repo health..."); enrich_github(con)
    print("C3. community/support (Discord + homepage)..."); print("   discord", enrich_discord(con)); enrich_homepage(con)
    print("D. scores..."); compute_scores(con)
    print("E. export..."); export(con)
    con.close()

if __name__ == "__main__":
    main()
