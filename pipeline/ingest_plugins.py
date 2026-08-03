#!/usr/bin/env python3
"""tashan — ingest Claude Code PLUGINS, the channel where the good skills actually live.

THE DISCOVERY GAP THIS CLOSES
Crawling GitHub for `SKILL.md` finds ~333,000 files, 39% of which are one template with a vendor name
swapped. Meanwhile the skills people actually recommend to each other — impeccable (design), ponytail
(context discipline), SwiftUI-Agent-Skill (iOS) — were invisible to us, because they are not published
as bare skill folders. They are published as **plugins**, installed with
`/plugin marketplace add <owner>/<repo>`, and declared in a `.claude-plugin/marketplace.json` manifest.
`tashan doctor` proved the cost of missing this: 105 of 123 items on a real developer's machine were
absent from our index. Almost all of them arrived through this channel.

WHY THIS CORPUS IS BETTER THAN THE SKILL.md CRAWL
  - It is curated by construction. Someone wrote a manifest, named it, versioned it, and published it.
  - The manifest is a first-class schema (anthropic.com/claude-code/marketplace.schema.json) carrying
    name, description, version, author, category, homepage and tags — far more than SKILL.md frontmatter.
  - THE SIGNALS ARE PER-ITEM. A plugin usually owns its repository, so stars, push recency, contributor
    count and license describe *that plugin*, not a 400-skill monorepo it happens to sit inside. This is
    precisely the objection that forced us to withhold ratings for monorepo skills (854 of them scored an
    identical 42.0). Plugins do not have that problem, so plugins can be ranked honestly.
  - Stars are the closest public proxy for "the thing people keep recommending in videos and threads" —
    which is currently how this ecosystem's quality actually gets discovered.

Population: GitHub code search reports ~5,184 repositories carrying the manifest. Code search returns at
most 1,000 results per query, so several disjoint query shards are unioned and deduped.

    python3 pipeline/ingest_plugins.py            # incremental (cached manifests)
    python3 pipeline/ingest_plugins.py --refresh  # refetch every manifest

Env: PLUGIN_CAP (max repos processed, default 1200).  Stdlib + `gh` only.
"""
import json, os, re, subprocess, sys, time, urllib.parse, urllib.request
import build

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "plugins_cache.json")
CAP = int(os.environ.get("PLUGIN_CAP", "1200"))

# The two Anthropic-managed marketplaces first: curated, reviewed, and reachable in ONE fetch each.
# claude-plugins-official is the hand-curated directory shipped with every install; -community is the
# reviewed third-party catalogue. Together ~2,500 plugins whose inclusion is itself a quality signal —
# far better provenance than anything a code-search sweep turns up. Order here is provenance priority.
SEED_MARKETPLACES = [
    ("anthropics/claude-plugins-official", "official"),
    ("anthropics/claude-plugins-community", "community"),
    # Known-good standalone marketplaces. These are the ones people recommend to each other by name and
    # then install directly — the exact population that was invisible to us. Seeding them explicitly
    # means a rate-limited code search can never silently drop a capability we know is good; discovery
    # is best-effort, this list is not. Each owns its repo, so its stars are a true per-plugin signal.
    ("pbakaus/impeccable", "curated"),
    ("DietrichGebert/ponytail", "curated"),
    ("AvdLee/SwiftUI-Agent-Skill", "curated"),
    ("Shopify/shopify-ai-toolkit", "curated"),
    ("AgriciDaniel/claude-seo", "curated"),
    ("bradautomates/claude-video", "curated"),
    ("obra/superpowers", "curated"),
]

# Disjoint-ish shards, because code search caps at 1000 results per query. Unioned and deduped by repo.
QUERIES = [
    "filename:marketplace.json+path:.claude-plugin",
    "%22claude-code/marketplace.schema.json%22",
    "filename:marketplace.json+path:.claude-plugin+claude",
    "filename:marketplace.json+path:.claude-plugin+skills",
]


def gh(path):
    try:
        r = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
    except Exception:
        return None


def raw(repo, path="/.claude-plugin/marketplace.json"):
    url = "https://raw.githubusercontent.com/" + repo + "/HEAD" + path
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception:
        return None


def discover():
    """Repos carrying a REAL manifest. Code search happily returns .bak / .archived / .template /
    .license variants; those are not installable and must not become catalogue entries."""
    repos, pages = {}, 0
    for q in QUERIES:
        for page in range(1, 11):                       # 10 x 100 = the 1000-result ceiling
            d = gh(f"/search/code?q={q}&per_page=100&page={page}")
            pages += 1
            items = (d or {}).get("items") or []
            if not items:
                break
            for it in items:
                if (it.get("path") or "") != ".claude-plugin/marketplace.json":
                    continue
                full = (it.get("repository") or {}).get("full_name")
                if full:
                    repos.setdefault(full, True)
            time.sleep(2)                               # code search is rate-limited hard
            if len(items) < 100:
                break
    print(f"  discovery: {len(repos)} repos with a real manifest ({pages} search pages)", flush=True)
    return list(repos)


GH_RE = re.compile(r"github\.com[/:]([^/\s]+/[^/\s#?]+?)(?:\.git)?/?$")

def home_repo(src, marketplace_repo):
    """Where the plugin ACTUALLY lives — which is usually NOT the marketplace repo.

    This distinction is the whole ballgame. `anthropics/claude-plugins-community` has 32,734 stars and
    lists 2,269 plugins; attributing those stars to each plugin would repeat, at larger scale, exactly
    the error that forced us to withhold ratings for 854 monorepo skills (all scoring an identical 42.0).
    The manifest tells us the truth: 1,874 community plugins declare `source: {url: <own repo>}` and 391
    declare `git-subdir` against a vendor repo. Only the handful using a relative "./" path genuinely
    live in the marketplace repo."""
    if isinstance(src, str):
        return marketplace_repo if src.strip().startswith(".") else None
    if not isinstance(src, dict):
        return None
    u = (src.get("url") or "").strip()
    if not u:
        return marketplace_repo
    if re.match(r"^[\w.-]+/[\w.-]+$", u):        # already "owner/repo"
        return u
    m = GH_RE.search(u)
    return m.group(1) if m else None


def parse(manifest, repo):
    """A manifest declares one or more plugins. Returns [] on anything malformed — a broken manifest is
    not installable, so it is not a catalogue entry."""
    try:
        m = json.loads(manifest)
    except Exception:
        return []
    if not isinstance(m, dict):
        return []
    mkt_desc = m.get("description") or (m.get("metadata") or {}).get("description") or ""
    owner = m.get("owner") or {}
    out = []
    for p in (m.get("plugins") or []):
        if not isinstance(p, dict) or not p.get("name"):
            continue
        desc = (p.get("description") or mkt_desc or "").strip()
        if len(desc) < 20:                              # identity without a usable description
            continue
        auth = p.get("author") or owner
        out.append({
            "name": str(p["name"]).strip(),
            # `description` stays clipped — it is the card/table blurb and 500 chars is a display
            # decision. `description_full` is the untruncated original, written to capability_text for
            # the tagger and the expertise grader. 514 plugins were sitting exactly at the old cap,
            # i.e. their text was being cut mid-sentence and the remainder discarded entirely.
            "description": desc[:500],
            "description_full": desc,
            "version": p.get("version"),
            "category": (p.get("category") or "").strip().lower() or None,
            "tags": [str(t) for t in (p.get("tags") or [])][:12],
            "homepage": p.get("homepage") or (owner.get("url") if isinstance(owner, dict) else None),
            "author": (auth or {}).get("name") if isinstance(auth, dict) else None,
            "repo": repo,
            "home": home_repo(p.get("source"), repo),
            "marketplace": m.get("name") or repo.split("/")[-1],
        })
    return out


# The manifest's own category vocabulary -> our 15. Anything unmapped stays None and falls through to
# the name-anchored classifier, rather than being invented.
CATMAP = {
    "design": "design", "ui": "design", "frontend": "design",
    "productivity": "productivity", "workflow": "productivity", "project-management": "productivity",
    "development": "devtools", "developer": "devtools", "devtools": "devtools", "testing": "devtools",
    "code-quality": "devtools", "git": "devtools", "language": "devtools",
    "data": "data", "analytics": "data", "database": "database",
    "security": "security", "devops": "cloud", "infrastructure": "cloud", "cloud": "cloud",
    "documentation": "docs", "docs": "docs", "writing": "docs",
    "ai": "ai", "agents": "ai", "llm": "ai",
    "search": "search", "browser": "browser", "web": "browser",
    "communication": "comms", "marketing": "comms", "finance": "finance", "files": "files",
}


def plugin_id(p):
    """Identity is the plugin's OWN home, never the marketplace that happens to list it.

    Keying by marketplace produced one row per listing: impeccable appeared three times (its own
    marketplace, claude-plugins-community, and a third-party bundle), each with its own category and
    score. Worse, the solo-repo test counts declarations per home repo, so a plugin listed in two
    marketplaces looked like two plugins sharing one repo — and had its star count stripped as "shared".
    impeccable lost 51,323 stars and ponytail 90,263 exactly this way, dropping their trust from 65/63
    to 47/46. One plugin, one row, keyed by where it actually lives."""
    home = p.get("home") or p["repo"]
    return "plugin:" + home.lower() + "/" + re.sub(r"[^a-z0-9]+", "-", p["name"].lower()).strip("-")


def upsert(con, p, gh_meta, shared, reach):
    """shared=True means this repo hosts more than one plugin, so its stars are NOT a per-item signal.
    Those rows carry the metadata but no stars, so scoring cannot mistake a vendor's repo popularity
    for evidence about one plugin inside it."""
    cid = plugin_id(p)
    cat = CATMAP.get(p.get("category") or "", None)
    con.execute("""INSERT INTO capabilities
        (id, name, kind, title, description, source_repo, homepage, category, in_registry,
         gh_stars, gh_pushed, gh_license, gh_topics, sources, config_reach)
      VALUES (?,?, 'plugin', ?,?,?,?,?, 0, ?,?,?,?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        title=COALESCE(excluded.title, capabilities.title),
        description=COALESCE(excluded.description, capabilities.description),
        homepage=COALESCE(excluded.homepage, capabilities.homepage),
        category=COALESCE(capabilities.category, excluded.category),
        gh_stars=excluded.gh_stars, gh_pushed=excluded.gh_pushed,
        gh_license=COALESCE(excluded.gh_license, capabilities.gh_license),
        gh_topics=COALESCE(excluded.gh_topics, capabilities.gh_topics),
        sources=excluded.sources, config_reach=MAX(capabilities.config_reach, excluded.config_reach),
        kind='plugin'""",
      (cid, p["name"], p.get("marketplace"), p["description"], p.get("home") or p["repo"], p.get("homepage"), cat,
       (None if shared else gh_meta.get("stars")), gh_meta.get("pushed"), gh_meta.get("license"),
       ",".join(p.get("tags") or []),
       "plugin-marketplace:" + (p.get("tier") or "discovered"), reach))
    build.put_text(con, cid, full_description=p.get("description_full") or p["description"],
                   doc_source="marketplace_json")


def backfill_market_repo(con, cache):
    """Record WHICH REPO each plugin's marketplace lives in, so a page can print a real install.

    `title` already carries the marketplace NAME, but a name cannot be turned back into a repo:
    anthropics/claude-plugins-community publishes as "claude-community". Both halves are needed —
    `/plugin marketplace add <repo>` then `/plugin install <name>@<market>`.

    Matched on (marketplace name, plugin name) against the manifests already in the cache, so the repo
    ALWAYS agrees with the title that won the upsert; a row can never advertise adding one marketplace
    and installing from another. Pure cache read, no network — safe to re-run every ingest.
    """
    pairs = {}                                     # (market name, plugin name) -> marketplace repo
    for key, man in cache.items():
        if not key.startswith("man:") or not isinstance(man, str):
            continue
        repo = key[4:]
        try:
            m = json.loads(man)
        except Exception:
            continue
        market = m.get("name") or repo.split("/")[-1]
        for p in (m.get("plugins") or []):
            if isinstance(p, dict) and p.get("name"):
                pairs.setdefault((market, str(p["name"]).strip()), repo)

    rows = con.execute("SELECT id, name, title FROM capabilities WHERE kind='plugin'").fetchall()
    hits = [(pairs[(t, n)], i) for i, n, t in rows if (t, n) in pairs]
    con.executemany("UPDATE capabilities SET plugin_market_repo=? WHERE id=?", hits)
    con.commit()
    print(f"  marketplace repo resolved for {len(hits)}/{len(rows)} plugins")
    return len(hits)


def main():
    refresh = "--refresh" in sys.argv
    cache = {}
    if os.path.exists(CACHE) and not refresh:
        try: cache = json.load(open(CACHE))
        except Exception: cache = {}

    # ---- PASS 1: collect every plugin declaration, from seeds then the discovered tail ----
    found = []
    for repo, tier in SEED_MARKETPLACES:
        man = cache.get("man:" + repo) or raw(repo)
        if not man:
            print(f"  {repo}: unreachable", flush=True); continue
        cache["man:" + repo] = man
        got = parse(man, repo)
        for pl in got: pl["tier"] = tier
        found += got
        print(f"  {repo} [{tier}]: {len(got)} plugins", flush=True)

    for repo in discover()[:CAP]:
        man = cache.get("man:" + repo) or raw(repo)
        if not man:
            continue
        cache["man:" + repo] = man
        got = parse(man, repo)
        for pl in got: pl["tier"] = "discovered"
        found += got

    # ---- PASS 2: how many plugins share each home repo? ----
    # A repo hosting exactly one plugin gives per-item signals. A repo hosting several does not, and
    # publishing its stars against each of them would be the marketplace-stars error in miniature.
    # count DISTINCT plugins per home repo — not declarations. The same plugin listed by three
    # marketplaces is still one plugin, and its repo is still its own.
    per_home, listings = {}, {}
    for p in found:
        pid = plugin_id(p)
        listings[pid] = listings.get(pid, 0) + 1
        if p.get("home"):
            per_home.setdefault(p["home"], set()).add(pid)
    solo = {r for r, ids in per_home.items() if len(ids) == 1}
    print(f"  {len(found)} plugin declarations across {len(per_home)} home repos "
          f"({len(solo)} own their repo outright -> ratable); "
          f"{len(listings)} distinct plugins", flush=True)

    # ---- PASS 3: fetch stars ONLY where they mean something, then upsert ----
    con = build.db()
    fetched = rated = 0
    for i, p in enumerate(found):
        home, is_solo = p.get("home"), p.get("home") in solo
        meta = cache.get("meta:" + home) if home else None
        if is_solo and meta is None:
            r = gh("/repos/" + home) or {}
            meta = {"stars": r.get("stargazers_count"), "pushed": (r.get("pushed_at") or "")[:10] or None,
                    "license": ((r.get("license") or {}) or {}).get("spdx_id")}
            cache["meta:" + home] = meta
            fetched += 1
            if fetched % 150 == 0:
                print(f"    {fetched} repos fetched…", flush=True)
                con.commit(); json.dump(cache, open(CACHE, "w"))
        upsert(con, p, meta or {}, shared=not is_solo, reach=listings.get(plugin_id(p), 1))
        rated += 1 if (is_solo and (meta or {}).get("stars") is not None) else 0
    con.commit()
    json.dump(cache, open(CACHE, "w"))
    backfill_market_repo(con, cache)

    n = con.execute("SELECT COUNT(*) FROM capabilities WHERE kind='plugin'").fetchone()[0]
    top = con.execute("SELECT name, gh_stars, source_repo FROM capabilities WHERE kind='plugin' "
                      "AND gh_stars IS NOT NULL ORDER BY gh_stars DESC LIMIT 10").fetchall()
    print(f"ingested {len(found)} declarations -> {n} plugins in DB; "
          f"{rated} carry a per-plugin star count, {len(found)-rated} left unstarred (shared repo)")
    for name, st, repo in top:
        print(f"    {st:>7} \u2605  {name:32} {repo}")
    con.close()


if __name__ == "__main__":
    main()
