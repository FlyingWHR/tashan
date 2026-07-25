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
import json, os, sqlite3, urllib.request, urllib.error, urllib.parse, time, math, re, subprocess
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
  adoption REAL, maintenance REAL, freshness REAL, trust REAL,
  expertise REAL, expertise_verdict TEXT, expertise_note TEXT,
  retention REAL, retention_note TEXT,
  in_registry INTEGER DEFAULT 0, in_configs INTEGER DEFAULT 0,
  updated_at TEXT
);
CREATE TABLE IF NOT EXISTS signal_history (
  cap_id TEXT, metric TEXT, value REAL, at TEXT
);
CREATE INDEX IF NOT EXISTS idx_trust ON capabilities(trust DESC);
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
           "discord_url TEXT", "gh_homepage TEXT"]

SCHEMA_VERSION = 2  # bump when MIGRATE changes; PRAGMA user_version records the applied version

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
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    have = {r[1] for r in con.execute("PRAGMA table_info(capabilities)")}
    for coldef in MIGRATE:
        if coldef.split()[0] not in have:
            con.execute(f"ALTER TABLE capabilities ADD COLUMN {coldef}")
    for idx in INDEXES:
        con.execute(idx)
    con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    con.commit()
    return con

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
def ingest_registry(con):
    base = "https://registry.modelcontextprotocol.io/v0/servers?limit=100"
    cursor, seen = None, 0
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
            repo = (srv.get("repository") or {}).get("url")
            if repo:
                m = re.search(r"github\.com[/:]([\w.-]+/[\w.-]+?)(?:\.git|/|$)", repo)
                repo = m.group(1) if m else repo
            cid = f"pkg:{npm_pkg}" if npm_pkg else f"registry:{name}"
            con.execute("""INSERT INTO capabilities (id,name,kind,title,description,npm_pkg,source_repo,registry_name,registry_status,registry_updated,in_registry)
              VALUES (?,?,?,?,?,?,?,?,?,?,1)
              ON CONFLICT(id) DO UPDATE SET title=COALESCE(excluded.title,capabilities.title),
                description=COALESCE(excluded.description,capabilities.description),
                source_repo=COALESCE(excluded.source_repo,capabilities.source_repo),
                registry_name=excluded.registry_name, registry_status=excluded.registry_status,
                registry_updated=excluded.registry_updated, in_registry=1,
                npm_pkg=COALESCE(capabilities.npm_pkg,excluded.npm_pkg)""",
              (cid, name.split("/")[-1], kind, srv.get("title"), srv.get("description"),
               npm_pkg, repo, name, meta.get("status"), meta.get("updatedAt")))
            seen += 1
        con.commit()
        cursor = (d.get("metadata") or {}).get("nextCursor")
        print(f"  registry: {seen} servers ingested", flush=True)
        if not cursor:
            break
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
        if pkg in cache:
            info = cache[pkg]
        else:
            info = {}
            try:
                dl = get_json(f"https://api.npmjs.org/downloads/point/last-week/{urllib.parse.quote(pkg, safe='@/')}")
                info["downloads"] = dl.get("downloads")
            except Exception:
                info["downloads"] = None
            try:
                meta = get_json(f"https://registry.npmjs.org/{urllib.parse.quote(pkg, safe='@/')}")
                latest = (meta.get("dist-tags") or {}).get("latest")
                t = meta.get("time") or {}
                info["last_publish"] = (t.get(latest) or "")[:10] or None
                info["created"] = (t.get("created") or "")[:10] or None
                info["maintainers"] = len(meta.get("maintainers") or [])
                info["versions"] = len(meta.get("versions") or {})
                info["deprecated"] = 1 if "deprecated" in ((meta.get("versions") or {}).get(latest) or {}) else 0
                if not info.get("repo"):
                    ru = (meta.get("repository") or {}).get("url") or ""
                    m = re.search(r"github\.com[/:]([\w.-]+/[\w.-]+?)(?:\.git|/|$)", ru)
                    info["repo"] = m.group(1) if m else None
            except Exception:
                pass
            cache[pkg] = info
            time.sleep(0.05)
        con.execute("""UPDATE capabilities SET npm_downloads=?, npm_last_publish=?, npm_created=?,
              npm_maintainers=?, npm_versions=?, npm_deprecated=?,
              source_repo=COALESCE(source_repo,?) WHERE id=?""",
          (info.get("downloads"), info.get("last_publish"), info.get("created"),
           info.get("maintainers"), info.get("versions"), info.get("deprecated"), info.get("repo"), cid))
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
    rows = con.execute("SELECT id, source_repo FROM capabilities WHERE source_repo IS NOT NULL "
                       "ORDER BY (gh_pushed IS NULL) DESC, config_reach DESC, npm_downloads DESC NULLS LAST "
                       "LIMIT ?", (GH_CAP,)).fetchall()
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
          (info.get("stars"), info.get("forks"), info.get("open_issues"), info.get("pushed"),
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
                       "AND trust IS NOT NULL ORDER BY trust DESC LIMIT ?",
                       (int(os.environ.get("HP_CAP", "300")),)).fetchall()
    print(f"  homepage for {len(rows)} repos...", flush=True)
    done = 0
    for cid, repo in rows:
        repo = (repo or "").strip().strip("/")
        if not REPO_RE.match(repo):
            continue
        ent = cache.setdefault(repo, {})
        if not ent.get("homepage"):                       # wrap in an object — a bare-string jq isn't valid JSON
            ent["homepage"] = (gh_api("/repos/" + repo, "{h: .homepage}") or {}).get("h") or None
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

def compute_scores(con):
    rows = con.execute("SELECT id, config_reach, npm_downloads, npm_last_publish, npm_maintainers, "
                       "npm_versions, npm_deprecated, registry_status, gh_pushed, gh_last_release, "
                       "gh_archived, gh_stars, gh_open_issues, gh_contributors, gh_has_discussions "
                       "FROM capabilities").fetchall()
    max_dl = max((r[2] or 0) for r in rows) or 1
    max_reach = max((r[1] or 0) for r in rows) or 1
    now_iso = datetime.now(timezone.utc).isoformat()
    for (cid, reach, dl, lastpub, maint, vers, dep, rstatus, gh_pushed, gh_release,
         gh_arch, gh_stars, gh_issues, gh_contrib, gh_disc) in rows:
        # ADOPTION: blend real npm downloads (log) + config reach (log), 0-100
        a_dl = math.log1p(dl or 0) / math.log1p(max_dl)
        a_reach = math.log1p(reach or 0) / math.log1p(max_reach)
        adoption = round(100 * (0.7 * a_dl + 0.3 * a_reach)) if (dl or reach) else None
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
        if gh_arch or dep or rstatus == "deprecated":
            vitality = "abandoned"
        elif recent:
            vitality = "active"
        elif ms is not None or gh_stars is not None:
            loved = (gh_stars or 0) >= 50 or gh_disc == 1
            pressure = gh_stars and gh_issues is not None and (gh_issues / max(gh_stars, 1)) > 0.15
            vitality = "stable" if (loved and not pressure) else "abandoned"
        # finished != dead: don't let staleness alone bury a stable, still-loved tool
        if vitality == "stable" and freshness is not None:
            freshness = max(freshness, 55)
        # MAINTENANCE: maintainers(>=2 good) + version cadence + freshness − deprecated/archived
        m = 0.0; known = False
        if maint is not None: m += min(1.0, maint / 3) * 40; known = True
        if vers is not None: m += min(1.0, math.log1p(vers) / math.log1p(30)) * 25; known = True
        if freshness is not None: m += freshness / 100 * 35; known = True
        if dep: m *= 0.3
        if rstatus == "deprecated": m *= 0.3
        if gh_arch: m *= 0.3
        maintenance = round(m) if known else None
        # TRUST (v2, transparent): mostly maintenance+freshness gated by adoption; labelled, not final
        parts = [x for x in (maintenance, freshness) if x is not None]
        trust = None
        if parts:
            base = sum(parts) / len(parts)
            trust = round(base * (0.6 + 0.4 * (adoption or 0) / 100)) if adoption is not None else round(base * 0.7)
        con.execute("UPDATE capabilities SET adoption=?, freshness=?, maintenance=?, trust=?, "
                    "vitality=?, single_maintainer=?, updated_at=? WHERE id=?",
                    (adoption, freshness, maintenance, trust, vitality, single, now_iso, cid))
    con.commit()
    snapshot_history(con)

# ---------- signal_history: one trust/adoption snapshot per day (the un-backfillable retention moat) ----------
def snapshot_history(con):
    today = datetime.now(timezone.utc).date().isoformat()
    if con.execute("SELECT 1 FROM signal_history WHERE at=? LIMIT 1", (today,)).fetchone():
        return  # already snapshotted today — keep it daily-granular and bounded
    n = 0
    for cid, trust, adoption in con.execute(
            "SELECT id, trust, adoption FROM capabilities WHERE trust IS NOT NULL"):
        con.execute("INSERT INTO signal_history (cap_id, metric, value, at) VALUES (?,?,?,?)",
                    (cid, "trust", trust, today))
        if adoption is not None:
            con.execute("INSERT INTO signal_history (cap_id, metric, value, at) VALUES (?,?,?,?)",
                        (cid, "adoption", adoption, today))
        n += 1
    con.commit()
    print(f"  signal_history: snapshotted {n} caps for {today}", flush=True)

# ---------- phase E: export site JSON ----------
def slugify(cid):
    return re.sub(r"[^a-z0-9]+", "-", cid.lower()).strip("-")

def export(con):
    cols = ["id","name","kind","title","description","npm_pkg","source_repo","registry_status",
            "config_reach","config_repos","stars_median","stars_max","last_seen",
            "npm_downloads","npm_last_publish","npm_maintainers","npm_versions","npm_deprecated",
            "co_used","adoption","freshness","maintenance","trust",
            "expertise","expertise_verdict","expertise_note","retention","retention_note",
            "category","in_registry","in_configs",
            "gh_stars","gh_forks","gh_open_issues","gh_pushed","gh_contributors","gh_last_release",
            "gh_license","gh_topics","gh_has_discussions","gh_archived","vitality","single_maintainer",
            "discord_url","gh_homepage"]
    # Only trust-ranked caps are ever exported (ranked = trust-not-null, capped below), so fetch just the top
    # slice via idx_trust instead of materializing the whole table. LIMIT is a buffer above the 800 board cap
    # so junk-filtering still leaves ≥800. At 1M rows this reads ~1500 rows, not all of them.
    rows = con.execute(f"SELECT {','.join(cols)} FROM capabilities "
                       "WHERE trust IS NOT NULL "
                       "ORDER BY trust DESC, config_reach DESC, npm_downloads DESC "
                       "LIMIT 1500").fetchall()
    # bare single-word generic names carry no identity in a ranking (registry ingest skips the scraper's filter)
    DENY = {"mcp", "server", "mcp-server", "run", "serve", "cli", "app", "main", "index",
            "stdio", "tools", "mcp-serve", "client", "core", "test", "demo"}
    def junk(o):
        n = (o["npm_pkg"] or o["id"].split(":", 1)[-1] or "")
        if n.startswith("@"):
            return False  # scoped = real identity
        leaf = n.split("/")[-1].lower()
        return leaf in DENY
    caps = []
    for r in rows:
        o = dict(zip(cols, r))
        if junk(o):
            continue
        o["co_used"] = json.loads(o["co_used"]) if o["co_used"] else []
        o["gh_topics"] = o["gh_topics"].split(",") if o["gh_topics"] else []
        o["slug"] = slugify(o["id"])                     # stable per-cap slug (matches gen_badges + prerender)
        caps.append(o)
    # The board is trust-RANKED: only caps with a real trust score belong on it. This is also the exact
    # set prerender turns into pages, so capabilities.json, index.json, and /capability/*.html stay aligned
    # (no board row or co-use link can point at a page that doesn't exist).
    ranked = [c for c in caps if c.get("trust") is not None][:800]
    tot = con.execute("SELECT COUNT(*) FROM capabilities").fetchone()[0]
    enriched = con.execute("SELECT COUNT(*) FROM capabilities WHERE npm_downloads IS NOT NULL").fetchone()[0]
    graded = con.execute("SELECT COUNT(*) FROM capabilities WHERE expertise IS NOT NULL").fetchone()[0]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "public signal: MCP registry + config-adoption + npm quality + LLM expertise-eval (SQLite pipeline)",
        "total_capabilities": tot,
        "enriched_npm": enriched,
        "expertise_graded": graded,
        "ranked": len(ranked),
        "note": "V2. Ranked by a transparent Trust score (maintenance + freshness, gated by real adoption). "
                "Expertise is a separate, LLM-graded read of the actual capability — real depth vs. thin wrapper. "
                "Retention (added-then-removed from git history) is the next signal.",
        "capabilities": ranked,
    }
    out = os.path.join(ROOT, "web", "data", "capabilities.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(payload, open(out, "w"), indent=2)

    # SLIM index — only the ~15 fields the board / ticker / ⌘K palette actually render. The heavy per-cap
    # fields (co_used, description, expertise_note, gh_topics, install, repo-health, community) are dropped;
    # detail pages carry those INLINE (prerender), so nothing downloads the 1.2 MB dossier at runtime.
    SLIM = ["id", "slug", "name", "kind", "category", "npm_pkg", "source_repo", "registry_status",
            "config_reach", "npm_downloads", "trust", "maintenance", "vitality",
            "expertise", "expertise_verdict", "npm_deprecated", "gh_archived"]
    slim = {k: payload[k] for k in ("generated_at", "method", "total_capabilities", "enriched_npm",
                                    "expertise_graded", "ranked", "note")}
    slim["capabilities"] = [{k: c.get(k) for k in SLIM} for c in ranked]
    slim_out = os.path.join(ROOT, "web", "data", "index.json")
    json.dump(slim, open(slim_out, "w"))
    print(f"\nExported {len(caps)} ranked / {tot} total ({enriched} npm-enriched) -> {out}")
    print(f"Slim index ({len(SLIM)} fields/cap) -> {slim_out}")
    print("Top 12 by Trust:")
    for c in caps[:12]:
        print(f"  T{c['trust'] or 0:>3}  A{c['adoption'] or 0:>3}  M{c['maintenance'] or 0:>3}  F{c['freshness'] or 0:>3}  "
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
