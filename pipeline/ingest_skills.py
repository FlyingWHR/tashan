#!/usr/bin/env python3
"""tashan — ingest agent-skills alongside MCP servers (one unified capability model).

A "skill" is a folder with a SKILL.md (YAML frontmatter: name, description, license) that an agent
loads on demand — the Anthropic Agent Skills format. This scans skill *monorepos* (a repo with a
skills/ dir of many skills, like anthropics/skills) and single-skill repos (SKILL.md at root),
reads each SKILL.md via the `gh` CLI (authenticated), and upserts them into the same `capabilities`
table with kind='skill', id='skill:<owner>/<name>'.

Run BEFORE build.py's registry/npm phases (or standalone) — it only writes identity + description;
build.py's github phase then enriches the source repo, and scoring/vitality/export treat skills like
any other capability. npm_pkg stays NULL (skills aren't published to npm); the install path differs
(drop the folder into ~/.claude/skills or .claude/skills), rendered client-side from kind.

Extend SKILL_REPOS to add community skill sources.  Stdlib + `gh` only (no pip deps).
"""
import json, os, re, subprocess, sqlite3
import build  # reuse db(), get_json is urllib; we use gh for private-rate headroom + auth

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (owner/repo, subdir-holding-skills or None for a single-skill repo at root, is_official)
SKILL_REPOS = [
    ("anthropics/skills", "skills", True),          # the official Agent Skills
    # community skill collections (same SKILL.md convention) — add as the ecosystem forms:
    # ("obra/superpowers", "skills", False),
]

def gh(path, jq=None):
    args = ["gh", "api", path] + (["--jq", jq] if jq else [])
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=40)
        return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else None
    except Exception:
        return None

def gh_text(repo, path):
    """Fetch a text file's contents via the contents API (base64-decoded)."""
    import base64
    d = gh(f"/repos/{repo}/contents/{path}")
    if isinstance(d, dict) and d.get("content"):
        try:
            return base64.b64decode(d["content"]).decode("utf-8", "ignore")
        except Exception:
            return None
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

def list_skill_dirs(repo, subdir):
    d = gh(f"/repos/{repo}/contents/{subdir}" if subdir else f"/repos/{repo}/contents")
    if not isinstance(d, list):
        return []
    return [it["name"] for it in d if it.get("type") == "dir"] if subdir else \
           ([""] if any(it.get("name") == "SKILL.md" for it in d) else [])

def upsert(con, cid, name, desc, repo, official):
    con.execute("""INSERT INTO capabilities (id, name, kind, description, source_repo, in_registry)
      VALUES (?,?, 'skill', ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET description=COALESCE(excluded.description, capabilities.description),
        source_repo=COALESCE(excluded.source_repo, capabilities.source_repo), kind='skill'""",
      (cid, name, desc, repo, 1 if official else 0))

def main():
    con = build.db()
    total = 0
    for repo, subdir, official in SKILL_REPOS:
        owner = repo.split("/")[0]
        dirs = list_skill_dirs(repo, subdir)
        print(f"  {repo}: {len(dirs)} skill dir(s)", flush=True)
        for name in dirs:
            path = (f"{subdir}/{name}/SKILL.md" if subdir else "SKILL.md") if name != "" else \
                   (f"{subdir}/SKILL.md" if subdir else "SKILL.md")
            md = gh_text(repo, path)
            fm = frontmatter(md)
            skill_name = fm.get("name") or name or repo.split("/")[-1]
            desc = fm.get("description")
            cid = f"skill:{owner}/{skill_name}"
            upsert(con, cid, skill_name, desc, repo, official)
            total += 1
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM capabilities WHERE kind='skill'").fetchone()[0]
    print(f"ingested {total} skills this run; {n} skills total in DB")
    con.close()

if __name__ == "__main__":
    main()
