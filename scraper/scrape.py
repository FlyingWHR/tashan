#!/usr/bin/env python3
"""
Mastered V1 — public-signal scraper.

Measures REAL adoption of MCP servers from public GitHub configs (mcp.json,
claude_desktop_config.json, .cursor mcp configs). No user instrumentation, no
opinions — just what people actually put in their configs, in public.

Signals per capability (all defined, reproducible, honest):
  - repos    : distinct public repos whose config references it (sample)
  - owners   : distinct owners (dedupes one person's many repos)
  - stars_*  : star distribution of the host repos (are serious projects using it?)
  - last_seen: most recent host-repo push (is it in *active* repos?)
  - co_used  : capabilities most often configured alongside it
NOT faked: retention/churn (needs git history) is intentionally left for a later pass.

Auth via the `gh` CLI token. Respectful of rate limits (code_search = 10/min).
Resumable: raw file contents cached under data/raw/.
"""
import json, subprocess, time, base64, re, os, sys, hashlib
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
os.makedirs(RAW, exist_ok=True)

# config file types to mine (query, human label)
QUERIES = [
    ('"mcpServers" filename:mcp.json', "mcp.json"),
    ('"mcpServers" filename:claude_desktop_config.json', "claude_desktop_config.json"),
    ('"mcpServers" filename:mcp.json path:.cursor', ".cursor/mcp.json"),
]
PAGES_PER_QUERY = 3          # 100 results/page
MAX_CONFIGS = 700            # cap on files we fetch+parse for V1
CODE_SEARCH_SLEEP = 7        # stay under 10/min


def gh(args, tolerant=True):
    """Call `gh api` and return parsed JSON (or None on error if tolerant)."""
    try:
        out = subprocess.run(["gh", "api", *args], capture_output=True, text=True, timeout=40)
        if out.returncode != 0:
            if not tolerant:
                sys.stderr.write(out.stderr[:300] + "\n")
            return None
        return json.loads(out.stdout) if out.stdout.strip() else None
    except Exception as e:
        if not tolerant:
            sys.stderr.write(f"{e}\n")
        return None


def strip_jsonc(text):
    """Tolerant parse of config files that use JSONC / trailing commas."""
    # remove /* */ and // comments (not inside strings — good enough for configs)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(?m)//.*?$", "", text)
    text = re.sub(r",\s*([}\]])", r"\1", text)  # trailing commas
    return text


PKG_RE = re.compile(r"^(@[\w.-]+/)?[\w.-]+$")

# generic tokens that are extraction artifacts, not real capability identities
DENY = {"mcp", "server", "mcp-server", "mcp-serve", "serve", "run", "start", "main", "index",
        "node", "npx", "uvx", "bunx", "bun", "python", "python3", "cli", "app", "run.py",
        "server.py", "main.py", "index.js", "app.py", "stdio", "."}

def strip_ver(pkg):
    """Drop the @version tag so name@latest and name@1.2.3 merge with name (scope-safe)."""
    if pkg.startswith("@"):
        rest = pkg[1:]
        return "@" + rest[:rest.rindex("@")] if "@" in rest else pkg
    return pkg.split("@")[0]

def _valid_pkg(base):
    name = base.split("/")[-1].lower()
    if name in DENY or base.lower() in DENY:
        return False
    # must be scoped, hyphenated, or dotted — kills bare generic words like "mcp"/"run"
    return base.startswith("@") or "-" in base or "/" in base

def is_junk(cid):
    kind, name = cid.split(":", 1)
    n = strip_ver(name).split("/")[-1].lower()
    if n in DENY or name.lower() in DENY:
        return True
    if kind in ("pkg", "npm", "py") and not name.startswith("@") \
       and "-" not in name and "/" not in name and "." not in name:
        return True
    return False


def capability_id(server_key, entry):
    """Derive a stable capability identifier from an mcpServers entry."""
    if not isinstance(entry, dict):
        return None, None
    # remote servers: url → hostname
    url = entry.get("url") or entry.get("serverUrl")
    if isinstance(url, str) and url.startswith(("http://", "https://")):
        host = re.sub(r"^https?://", "", url).split("/")[0].split("?")[0]
        return f"url:{host}", "remote"
    cmd = (entry.get("command") or "").lower()
    args = entry.get("args") or []
    args = [str(a) for a in args] if isinstance(args, list) else []
    # docker image
    if cmd == "docker":
        for a in args:
            if "/" in a and not a.startswith("-") and ":" not in a[:1]:
                if re.search(r"[a-z0-9]+/[a-z0-9._-]+", a) and "run" not in a:
                    return f"docker:{a.split(':')[0]}", "docker"
    # npm/py package in args (skip flags like -y, --key, paths)
    for a in args:
        if a.startswith(("-", "/", ".")):
            continue
        base = strip_ver(a)
        low = base.lower()
        if ("mcp" in low or "modelcontext" in low) and _valid_pkg(base):
            return f"pkg:{base}", ("npm" if cmd in ("npx", "node", "bunx", "pnpm", "yarn", "bun") else "pkg")
    # first non-flag arg for uvx/pip/python
    if cmd in ("uvx", "pipx", "uv"):
        for a in args:
            if not a.startswith("-"):
                return f"py:{a.split('@')[0].strip()}", "python"
    # fallback: the human server key (last resort — least reliable)
    key = str(server_key).strip().lower()
    if key:
        return f"key:{key}", "unknown"
    return None, None


def collect_files():
    """Code-search for config files; return list of contents-API urls + repo (cached)."""
    fcache = os.path.join(ROOT, "data", "files.json")
    if os.path.exists(fcache) and not os.environ.get("REFRESH"):
        files = json.load(open(fcache))
        print(f"  (cached file list: {len(files)} files — set REFRESH=1 to re-search)", flush=True)
        return files
    seen, files = set(), []
    for q, label in QUERIES:
        for page in range(1, PAGES_PER_QUERY + 1):
            if len(files) >= MAX_CONFIGS:
                break
            res = gh(["-X", "GET", "/search/code", "-f", f"q={q}",
                      "-F", "per_page=100", "-F", f"page={page}"])
            time.sleep(CODE_SEARCH_SLEEP)
            items = (res or {}).get("items") or []
            if not items:
                break
            for it in items:
                repo = (it.get("repository") or {}).get("full_name")
                url = it.get("url")  # contents API url for this exact file+ref
                path = it.get("path")
                if not (repo and url):
                    continue
                key = (repo, path)
                if key in seen:
                    continue
                seen.add(key)
                files.append({"repo": repo, "path": path, "url": url, "kind": label})
            print(f"  search[{label} p{page}] -> {len(files)} unique files so far", flush=True)
    files = files[:MAX_CONFIGS]
    json.dump(files, open(os.path.join(ROOT, "data", "files.json"), "w"))
    return files


def fetch_config(f):
    """Fetch + parse one config file; cache raw content. Return list of (server_key, entry)."""
    h = hashlib.sha1((f["repo"] + "/" + f["path"]).encode()).hexdigest()[:16]
    cache = os.path.join(RAW, h + ".json")
    content = None
    if os.path.exists(cache):
        content = open(cache, encoding="utf-8", errors="ignore").read()
    else:
        data = gh([f["url"]])
        if data and data.get("content"):
            try:
                content = base64.b64decode(data["content"]).decode("utf-8", "ignore")
                open(cache, "w", encoding="utf-8").write(content)
            except Exception:
                content = None
    if not content:
        return []
    try:
        obj = json.loads(strip_jsonc(content))
    except Exception:
        return []
    servers = obj.get("mcpServers") or obj.get("servers") or {}
    if not isinstance(servers, dict):
        return []
    return list(servers.items())


def repo_meta(full, cache):
    if full in cache:
        return cache[full]
    r = gh([f"/repos/{full}", "--jq",
            "{stars: .stargazers_count, pushed: .pushed_at, owner: .owner.login, archived: .archived}"])
    cache[full] = r or {}
    return cache[full]


def main():
    print("Mastered scraper — collecting public MCP configs...", flush=True)
    files = collect_files()
    print(f"Collected {len(files)} config files. Parsing...", flush=True)

    cap = defaultdict(lambda: {"repos": set(), "owners": set(), "kind": None,
                               "co": defaultdict(int), "types": defaultdict(int)})
    per_config_caps = []
    for i, f in enumerate(files):
        entries = fetch_config(f)
        owner = f["repo"].split("/")[0]
        ids = []
        for key, entry in entries:
            cid, ctype = capability_id(key, entry)
            if not cid or is_junk(cid):
                continue
            ids.append(cid)
            c = cap[cid]
            c["repos"].add(f["repo"])
            c["owners"].add(owner)
            if ctype:
                c["types"][ctype] += 1
        for a in set(ids):
            for b in set(ids):
                if a != b:
                    cap[a]["co"][b] += 1
        if (i + 1) % 50 == 0:
            print(f"  parsed {i+1}/{len(files)} configs, {len(cap)} capabilities", flush=True)

    # repo metadata for scoring (dedupe)
    all_repos = set()
    for c in cap.values():
        all_repos |= c["repos"]
    print(f"Fetching metadata for {len(all_repos)} unique repos...", flush=True)
    rmcache = os.path.join(ROOT, "data", "repo_meta.json")
    meta = json.load(open(rmcache)) if os.path.exists(rmcache) else {}
    for j, full in enumerate(sorted(all_repos)):
        repo_meta(full, meta)
        if (j + 1) % 100 == 0:
            print(f"  repo meta {j+1}/{len(all_repos)}", flush=True)
    json.dump(meta, open(rmcache, "w"))

    # build output
    def stars_list(repos):
        xs = [meta.get(r, {}).get("stars", 0) or 0 for r in repos]
        return sorted(xs)
    def median(xs):
        return xs[len(xs)//2] if xs else 0
    def last_seen(repos):
        ps = [meta.get(r, {}).get("pushed") for r in repos if meta.get(r, {}).get("pushed")]
        return max(ps) if ps else None

    out = []
    for cid, c in cap.items():
        repos = c["repos"]
        xs = stars_list(repos)
        co = sorted(c["co"].items(), key=lambda kv: -kv[1])[:5]
        out.append({
            "id": cid,
            "name": cid.split(":", 1)[1],
            "kind": max(c["types"].items(), key=lambda kv: kv[1])[0] if c["types"] else "unknown",
            "repos": len(repos),
            "owners": len(c["owners"]),
            "stars_sum": sum(xs),
            "stars_median": median(xs),
            "stars_max": xs[-1] if xs else 0,
            "last_seen": last_seen(repos),
            "co_used": [{"id": k, "n": v} for k, v in co],
        })
    # rank by owners (dedupes spammy monorepos) then repos
    out.sort(key=lambda x: (x["owners"], x["repos"], x["stars_sum"]), reverse=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "public GitHub config mining (mcp.json / claude_desktop_config.json / .cursor)",
        "sample_configs": len(files),
        "unique_repos": len(all_repos),
        "capabilities_found": len(out),
        "note": "V1 sample, not exhaustive. Adoption = distinct public repos in sample. "
                "Not an endorsement; retention/quality-eval layers are on the roadmap.",
        "capabilities": out,
    }
    path = os.path.join(ROOT, "data", "capabilities.json")
    json.dump(payload, open(path, "w"), indent=2)
    print(f"\nDONE. {len(out)} capabilities from {len(files)} configs / {len(all_repos)} repos -> {path}", flush=True)
    top = [c for c in out if not c["id"].startswith("key:")][:15]
    print("Top by owner-reach:")
    for c in top:
        print(f"  {c['owners']:4d} owners  {c['repos']:4d} repos  {c['stars_median']:6d}★med  {c['name']}")


if __name__ == "__main__":
    main()
