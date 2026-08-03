#!/usr/bin/env python3
"""tashan — ingest agent-skills alongside MCP servers (one unified capability model).

A "skill" is a folder with a SKILL.md (YAML frontmatter: name, description, license) that an agent
loads on demand — the Anthropic Agent Skills format. This walks each source repo's git tree ONCE
(`/git/trees/HEAD?recursive=1`), finds every `**/SKILL.md` at any depth, and upserts them into the
same `capabilities` table with kind='skill', id='skill:<owner>/<name>'.

Why the tree API: the earlier version listed `contents/<subdir>` one level deep, which found 17 skills.
The large community collections nest two-to-three levels (category/subcategory/skill), so one-level
listing missed ~99% of them. One tree call per repo also costs 1 API request instead of N.

SKILL.md bodies are fetched from raw.githubusercontent (no API rate limit) and cached in
data/skills_cache.json keyed by the tree blob SHA, so re-runs are nearly free and only changed skills
refetch.

Run BEFORE build.py's github/scoring phases (or standalone) — it writes identity + description +
source URL; build.py's github phase then enriches the source repo, and scoring/export treat skills
like any other capability. npm_pkg stays NULL (skills aren't published to npm).

SCORING (read before trusting a skill's numbers): every skill in a repo shares that repo's
maintenance/freshness signals — that is genuinely all the public evidence there is for a folder inside a
monorepo. Measured: 854 skills scored 42.0 with a within-repo spread of 42.0-42.0, i.e. the number says
"the repo is alive", not "this skill is good". So skills live in the SAME catalog as everything else
(one capability model, filterable by type) but their trust is WITHHELD rather than faked: export marks
them rated=false with a reason. Per-skill evidence — an expertise grade of the SKILL.md itself, or real
cross-repo adoption (config_reach > 1) — is what promotes one into the ranking.

Stdlib + `gh` only (no pip deps).  Env: SKILL_CAP (max skills ingested per repo, default 400).
"""
import json, os, re, subprocess, sys, urllib.request, urllib.error
import build  # reuse db()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "skills_cache.json")
CAP = int(os.environ.get("SKILL_CAP", "400"))
TEMPLATE_MIN = int(os.environ.get("SKILL_TEMPLATE_MIN", "5"))  # shared-description count that marks a stub

# (owner/repo, is_official). Order matters: it is the DEDUP PRIORITY — the community "awesome" mirrors
# vendor copies of upstream skills, so upstream/official repos must come first to win the name.
SKILL_REPOS = [
    ("anthropics/skills", True),                       # the official Agent Skills
    ("anthropics/claude-plugins-official", True),      # official plugin bundle (ships skills)
    ("obra/superpowers", False),                       # widely-used community set
    ("Jeffallan/claude-skills", False),                # 66 full-stack dev skills
    ("multica-ai/andrej-karpathy-skills", False),
    ("alirezarezvani/claude-skills", False),           # large multi-category collection
    ("ComposioHQ/awesome-claude-skills", False),       # large curated mirror (dedups against the above)
]

def gh(path, jq=None):
    args = ["gh", "api", path] + (["--jq", jq] if jq else [])
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=60)
        return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else None
    except Exception:
        return None

def raw(repo, path):
    """SKILL.md body from raw.githubusercontent — public, and not subject to the API rate limit."""
    url = f"https://raw.githubusercontent.com/{repo}/HEAD/" + urllib.parse.quote(path)
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception:
        return None

def frontmatter(md):
    """Parse a leading `---`\\n...\\n`---` YAML frontmatter block. Stdlib line-parser (no yaml dep);
    handles the flat name/description/license keys SKILL.md uses — not arbitrary nested YAML."""
    if not md or not md.startswith("---"):
        return {}
    end = md.find("\n---", 3)
    if end < 0:
        return {}
    fm, out, key = md[3:end], {}, None
    for line in fm.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            key = m.group(1).strip().lower()
            out[key] = m.group(2).strip().strip('"').strip("'")
        elif key and line.strip():                       # folded continuation of the previous value
            out[key] += " " + line.strip()
    return out

def skill_paths(repo):
    """Every `**/SKILL.md` in the repo, as (dir, path, blob_sha). One API call."""
    t = gh(f"/repos/{repo}/git/trees/HEAD?recursive=1")
    if not isinstance(t, dict) or not isinstance(t.get("tree"), list):
        return []
    out = []
    for it in t["tree"]:
        p = it.get("path") or ""
        if it.get("type") == "blob" and (p == "SKILL.md" or p.endswith("/SKILL.md")):
            out.append((p.rsplit("/", 1)[0] if "/" in p else "", p, it.get("sha") or ""))
    return out

def load_cache():
    try:
        with open(CACHE) as f:
            return json.load(f)
    except Exception:
        return {}

def norm(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").strip().lower()).strip("-")

def upsert(con, cid, name, title, desc, repo, homepage, official, reach, repos):
    """reach = how many INDEPENDENT public repos carry this skill.

    This is the per-skill adoption signal, and it is why duplicates are counted rather than discarded.
    A skill vendored into six different collections has been chosen six times by six maintainers; that is
    the same kind of evidence as an MCP server appearing in many public agent configs, so it goes in the
    same column (config_reach) and means the same thing: independent adoption. Without it every skill in
    a monorepo scores identically and none of them can be ranked honestly."""
    con.execute("""INSERT INTO capabilities (id, name, kind, title, description, source_repo, homepage,
        in_registry, config_reach, config_repos)
      VALUES (?,?, 'skill', ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        title=COALESCE(excluded.title, capabilities.title),
        description=COALESCE(excluded.description, capabilities.description),
        source_repo=COALESCE(excluded.source_repo, capabilities.source_repo),
        homepage=COALESCE(excluded.homepage, capabilities.homepage),
        config_reach=excluded.config_reach, config_repos=excluded.config_repos, kind='skill'""",
      (cid, name, title, desc, repo, homepage, 1 if official else 0, reach, repos))

REPO_CAP = int(os.environ.get("SKILL_REPO_CAP", "300"))


def discovered_repos(con):
    """Repos to walk BEYOND the seven seeds, taken from sources we have already ingested.

    THE GAP THIS CLOSES. SKILL_REPOS was seven hand-picked repositories, and that was the entire
    discovery mechanism — so the skills corpus stalled at ~520 while a competing directory published
    12,634 skill pages. Skills were not being missed because they are hard to find; nothing was
    looking anywhere else.

    Deliberately NOT a GitHub crawl for `SKILL.md`: that returns ~333,000 files, 39% of them one
    template with a vendor name swapped (see ingest_plugins.py). These candidates are repos that
    already earned their way into the corpus by publishing a plugin or a marketplace manifest — a
    much stronger prior than "contains a file with this name", and it costs no new search API calls.

    Ordered never-scanned-first so REPO_CAP advances coverage across runs instead of re-walking the
    same head every night, the same way the registry and npm stages already work.
    """
    cand = {r[0] for r in con.execute(
        "SELECT DISTINCT source_repo FROM capabilities "
        "WHERE source_repo IS NOT NULL AND source_repo != '' AND kind IN ('plugin','skill')")}
    cand -= {r for r, _ in SKILL_REPOS}
    seen = {r[0][7:]: r[1] for r in con.execute(
        "SELECT source, last_synced FROM sync_state WHERE source LIKE 'skills:%'")}
    # never scanned (no state) first, then least-recently scanned
    ordered = sorted(cand, key=lambda r: (seen.get(r) is not None, seen.get(r) or ""))
    return ordered[:REPO_CAP]


def mark_scanned(con, repo, n):
    """Record the walk so the next run moves on. A repo with ZERO SKILL.md still gets a row — that is
    the whole point: without it 'scanned, empty' is indistinguishable from 'never scanned' and the cap
    would re-walk the same barren head every night."""
    from datetime import datetime, timezone
    con.execute("INSERT INTO sync_state (source,last_synced,last_cursor,seen,note) VALUES (?,?,?,?,?) "
                "ON CONFLICT(source) DO UPDATE SET last_synced=excluded.last_synced, seen=excluded.seen",
                ("skills:" + repo, datetime.now(timezone.utc).isoformat(), None, n, "skill walk"))


def main():
    con = build.db()
    cache = load_cache()
    found, thin, scanned = {}, 0, 0
    extra = [(r, False) for r in discovered_repos(con)]
    print(f"walking {len(SKILL_REPOS)} seed repos + {len(extra)} discovered "
          f"(cap {REPO_CAP}/run, never-scanned first)", flush=True)
    # PASS 1 — collect every occurrence of every skill across every repo. Duplicates are the point:
    # they are the adoption signal, so nothing is discarded here.
    for repo, official in SKILL_REPOS + extra:
        paths = skill_paths(repo)
        taken = 0
        for d, path, sha in paths:
            if taken >= CAP:
                print(f"    (capped at {CAP}; {len(paths) - taken} more in this repo not scanned)", flush=True)
                break
            md = cache.get(sha)
            if md is None:
                md = raw(repo, path)
                if md is None:
                    continue
                cache[sha] = md
            fm = frontmatter(md)
            nm = fm.get("name") or (d.rsplit("/", 1)[-1] if d else repo.split("/")[-1])
            desc = fm.get("description")
            key = norm(nm)
            if not key:
                continue
            if not desc or len(desc) < 20:
                thin += 1                       # identity without a description isn't a usable entry
                continue
            home = f"https://github.com/{repo}/tree/HEAD/{d}" if d else f"https://github.com/{repo}"
            found.setdefault(key, []).append(
                {"name": nm, "desc": desc, "repo": repo, "home": home, "official": official,
                 # carry the FULL SKILL.md body through to the DB. It was already fetched and cached
                 # here and then dropped on the floor; it is the richest prose in the whole corpus
                 # (p50 ~2,950 chars vs a 100-char registry blurb) and the task tagger reads it.
                 "body": md})
            taken += 1; scanned += 1
        mark_scanned(con, repo, taken)
        con.commit()          # per repo, NOT at the end of the walk: a 300-repo pass takes ~40 minutes
                              # and anything that interrupts it (ctrl-c, a CI timeout, a dropped proxy)
                              # would otherwise discard every repo already walked and re-walk them all
                              # next run — the cap would then never advance past the first slow batch.
        if taken or len(paths):
            print(f"  {repo}: {len(paths)} SKILL.md found, {taken} scanned", flush=True)

    # PASS 1b — drop auto-generated stubs. Measured on this corpus: 339 of 865 skills shared ONE
    # description template ("Automate {vendor} tasks via Rube MCP (Composio). Always search tools first
    # for current schemas.") with only the vendor name swapped — one entry per SaaS product, carrying no
    # per-skill information whatsoever. That is the skills equivalent of the "Send personalized greetings"
    # demo servers, and at 39% of the corpus it would have been the single largest thing in the catalog.
    # A description that is a fill-in-the-blank shared by hundreds of entries is not a description.
    def shape(name, desc):
        s = (desc or "").lower()
        for tok in re.split(r"[-_ ]", (name or "").lower()):
            if len(tok) > 2:
                s = s.replace(tok, "{}")
        return re.sub(r"\s+", " ", s).strip()[:120]

    shapes = {}
    for key, occ in found.items():
        shapes.setdefault(shape(occ[0]["name"], occ[0]["desc"]), []).append(key)
    boiler = {k for sh, keys in shapes.items() if len(keys) >= TEMPLATE_MIN for k in keys}
    for k in boiler:
        found.pop(k, None)
    if boiler:
        print(f"  dropped {len(boiler)} auto-generated stubs (description template shared by "
              f">={TEMPLATE_MIN} skills)", flush=True)

    # PASS 2 — one row per skill, carrying how many independent repos vendor it. SKILL_REPOS order is
    # the canonical-source priority, so the official copy wins identity and the rest become reach.
    prio = {r: i for i, (r, _) in enumerate(SKILL_REPOS)}
    total = multi = 0
    for key, occ in found.items():
        occ.sort(key=lambda o: prio.get(o["repo"], 99))
        best = occ[0]
        repos = sorted({o["repo"] for o in occ})
        reach = len(repos)
        if reach > 1:
            multi += 1
        owner = best["repo"].split("/")[0]
        cid = f"skill:{owner}/{key}"
        upsert(con, cid, key, best["name"], best["desc"], best["repo"],
               best["home"], best["official"], reach, ",".join(repos)[:500])
        build.put_text(con, cid, full_description=best["desc"], doc_body=best.get("body"),
                       doc_source="skill_md")
        total += 1
    con.commit()
    with open(CACHE, "w") as f:
        json.dump(cache, f)
    n = con.execute("SELECT COUNT(*) FROM capabilities WHERE kind='skill'").fetchone()[0]
    print(f"scanned {scanned} SKILL.md across {len(SKILL_REPOS) + len(extra)} repos "
          f"({len(SKILL_REPOS)} seed + {len(extra)} discovered) -> {total} distinct skills "
          f"({multi} vendored by more than one repo); skipped {thin} without a usable description; "
          f"{n} skills in DB")
    con.close()

if __name__ == "__main__":
    main()
