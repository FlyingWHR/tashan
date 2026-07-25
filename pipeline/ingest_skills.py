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

CAVEAT ON SCORING (read before trusting a skill's numbers): every skill in a repo shares that repo's
maintenance/freshness signals, because that is genuinely all the public evidence there is for a folder
inside a monorepo. So skill scores are REPO-LEVEL, not per-skill. The site must say so wherever a skill
score is shown, and skills are kept off the trust-ranked board for that reason — 800 same-scored rows
from one repo would bury every independently-measured MCP server.

Stdlib + `gh` only (no pip deps).  Env: SKILL_CAP (max skills ingested per repo, default 400).
"""
import json, os, re, subprocess, sys, urllib.request, urllib.error
import build  # reuse db()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "skills_cache.json")
CAP = int(os.environ.get("SKILL_CAP", "400"))

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

def upsert(con, cid, name, title, desc, repo, homepage, official):
    con.execute("""INSERT INTO capabilities (id, name, kind, title, description, source_repo, homepage, in_registry)
      VALUES (?,?, 'skill', ?, ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        title=COALESCE(excluded.title, capabilities.title),
        description=COALESCE(excluded.description, capabilities.description),
        source_repo=COALESCE(excluded.source_repo, capabilities.source_repo),
        homepage=COALESCE(excluded.homepage, capabilities.homepage), kind='skill'""",
      (cid, name, title, desc, repo, homepage, 1 if official else 0))

def main():
    con = build.db()
    cache = load_cache()
    seen, total, dupes, thin = set(), 0, 0, 0
    # pre-seed dedup with skills already in the DB so re-runs don't re-add a renamed duplicate
    for (n,) in con.execute("SELECT name FROM capabilities WHERE kind='skill'"):
        seen.add(norm(n))
    for repo, official in SKILL_REPOS:
        owner = repo.split("/")[0]
        paths = skill_paths(repo)
        added = 0
        for d, path, sha in paths:
            if added >= CAP:
                print(f"    (capped at {CAP}; {len(paths) - added} more in this repo not ingested)", flush=True)
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
            if not key or key in seen:
                dupes += 1
                continue
            if not desc or len(desc) < 20:
                # identity without a description is not a directory entry anyone can use
                thin += 1
                continue
            seen.add(key)
            home = f"https://github.com/{repo}/tree/HEAD/{d}" if d else f"https://github.com/{repo}"
            upsert(con, f"skill:{owner}/{key}", key, nm, desc, repo, home, official)
            total += 1; added += 1
        print(f"  {repo}: {len(paths)} SKILL.md found, {added} new", flush=True)
        con.commit()
    with open(CACHE, "w") as f:
        json.dump(cache, f)
    n = con.execute("SELECT COUNT(*) FROM capabilities WHERE kind='skill'").fetchone()[0]
    print(f"ingested {total} new; skipped {dupes} duplicate-name, {thin} without a usable description; "
          f"{n} skills total in DB")
    con.close()

if __name__ == "__main__":
    main()
