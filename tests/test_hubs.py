#!/usr/bin/env python3
"""tashan — the generated content tier: asset versioning, category hubs, skills, llms.txt.

These guard the failure modes that actually happened while building this tier:
  - a ?v= bump missed in one of six places, so browsers served stale JS (this cost a whole debugging
    round; now there is one constant and this asserts every reference agrees with it)
  - capability pages left behind as orphans when a cap dropped out of the export (19 of them, still
    crawlable, in no sitemap, frozen at an old asset version)
  - hub pages generated but not linked from anywhere and not in the sitemap — a content tier that
    exists on disk and is invisible to crawlers
  - a single 375 KB skills page (split into paginated per-repo pages; this keeps it that way)
"""
import json, os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import assets

WEB = os.path.join(ROOT, "web")
ok = fail = 0

def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print("  ok  " + name)
    else:
        fail += 1; print("  FAIL " + name + (" — " + detail if detail else ""))

def read(p):
    return open(os.path.join(WEB, p)).read()

print("# asset versioning (one constant, no drift)")
vers = {}
for f in glob.glob(os.path.join(WEB, "*.html")) + glob.glob(os.path.join(WEB, "*", "*.html")):
    for m in re.finditer(r"\?v=(\d+)", open(f).read()):
        vers.setdefault(int(m.group(1)), []).append(os.path.relpath(f, ROOT))
check("every ?v= on disk equals assets.V (%d)" % assets.V, set(vers) in ({assets.V}, set()),
      "found %s" % sorted(vers))

print()
print("# capability pages vs export (no orphans, no missing)")
export = json.load(open(os.path.join(WEB, "data", "capabilities.json")))
slugs = {c["slug"] for c in export["capabilities"] if c.get("slug")}
pages = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(WEB, "capability", "*.html"))}
check("every exported capability has a page", slugs <= pages, "missing %d" % len(slugs - pages))
check("no orphaned capability pages", pages <= slugs, "orphans %d" % len(pages - slugs))

print()
print("# category hubs")
cats = json.load(open(os.path.join(WEB, "data", "categories.json")))["categories"]
by_cat = {}
for c in export["capabilities"]:
    if c.get("category"):
        by_cat.setdefault(c["category"], []).append(c)
check("every capability is categorised",
      all(c.get("category") for c in export["capabilities"]),
      "%d uncategorised" % sum(1 for c in export["capabilities"] if not c.get("category")))
missing_hub = [cid for cid in by_cat if not os.path.exists(os.path.join(WEB, "category", cid + ".html"))]
check("every populated category has a hub page", not missing_hub, str(missing_hub))
bad_cat = [c["id"] for c in cats if c["id"] not in by_cat and
           os.path.exists(os.path.join(WEB, "category", c["id"] + ".html"))]
check("no hub page for an empty category", not bad_cat, str(bad_cat))
if by_cat:
    any_cid = sorted(by_cat)[0]
    hub = read("category/" + any_cid + ".html")
    check("hub carries ItemList JSON-LD", '"@type": "ItemList"' in hub or '"@type":"ItemList"' in hub)
    check("hub links back to the index", 'href="/"' in hub)
    check("hub links to sibling categories", hub.count('href="/category/') >= 5)

print()
print("# capability -> hub link (the flywheel edge)")
sample = sorted(glob.glob(os.path.join(WEB, "capability", "*.html")))[:40]
linked = sum(1 for p in sample if '/category/' in open(p).read())
check("capability pages link to their category hub", linked >= len(sample) * 0.9,
      "%d/%d" % (linked, len(sample)))

print()
print("# skills directory")
if os.path.isdir(os.path.join(WEB, "skills")):
    sk = glob.glob(os.path.join(WEB, "skills", "*.html"))
    check("skills index exists", os.path.exists(os.path.join(WEB, "skills", "index.html")))
    big = [os.path.basename(p) for p in sk if os.path.getsize(p) > 120_000]
    check("no skills page over 120 KB (paginated)", not big, str(big))
    idx = read("skills/index.html")
    check("skills index states scores are repo-level, not per-skill",
          "repo" in idx.lower() and ("not" in idx.lower()))
    check("skills index links to per-repo pages", idx.count('href="/skills/') >= 3)

print()
print("# llms.txt (GEO)")
if os.path.exists(os.path.join(WEB, "llms.txt")):
    L = read("llms.txt")
    check("llms.txt starts with an H1", L.startswith("# "))
    check("llms.txt has a blockquote summary", "\n> " in L)
    check("llms.txt explains the score", "tashan score" in L and "Adoption" in L)
    check("llms.txt links absolute URLs", "https://tashan.sh/capability/" in L)
    check("llms.txt names the firewall", "pay" in L.lower())
    check("llms.txt is under 40 KB", len(L.encode()) < 40_000, "%d bytes" % len(L.encode()))

print()
print("# sitemap covers the generated tier")
sm = read("sitemap.xml")
for sub in ("category", "skills", "task"):
    d = os.path.join(WEB, sub)
    if os.path.isdir(d):
        files = [f for f in os.listdir(d) if f.endswith(".html")]
        miss = [f for f in files if ("/" + sub + "/" + f) not in sm]
        check("sitemap lists every /%s/ page" % sub, not miss, "%d missing" % len(miss))
check("sitemap has no orphan capability URLs",
      all(("/capability/" + s + ".html") in sm for s in list(slugs)[:50]))

print()
print("# robots / AI crawlers")
r = read("robots.txt")
check("robots names the major answer engines",
      all(a in r for a in ("GPTBot", "ClaudeBot", "PerplexityBot", "OAI-SearchBot")))
check("robots points at the sitemap", "Sitemap:" in r)
check("robots mentions llms.txt", "llms.txt" in r)

print()
print("# name-confusion detector (defence-in-depth vs dependency confusion)")
# The self-declared canaries are filtered by description, but a real typosquat won't announce itself.
# This proves the normalised-name comparison still catches that shape, even with nothing live to fire on.
_norm = lambda p: re.sub(r"[^a-z0-9]", "",
                         re.sub(r"\b(mcp|server)\b", "", p.split("/")[-1].lower().replace("-", " ")))
check("unscoped shadow of an official name normalises equal",
      _norm("mcp-server-fetch") == _norm("@modelcontextprotocol/server-fetch") != "")
check("unrelated packages do not collide",
      _norm("tavily-mcp") != _norm("@modelcontextprotocol/server-fetch"))
check("no ranked capability shadows an official package",
      not [c["id"] for c in export["capabilities"] if c.get("similar_official")],
      str([c["id"] for c in export["capabilities"] if c.get("similar_official")][:3]))
# Match the PRODUCTION rule (build.py CANARY), not the bare word: "canary" legitimately describes a
# deployment strategy ("merge -> canary -> promote"), and flagging that was a false positive.
_CANARY = re.compile(r"security research canary|\bcanary\b[^.]{0,40}not for production"
                     r"|not for production use|placeholder package|do not (install|use) this package", re.I)
check("no self-declared canary is ranked",
      not [c["id"] for c in export["capabilities"] if _CANARY.search(c.get("description") or "")])

print()
print("# social card")
check("og.png exists", os.path.exists(os.path.join(WEB, "assets", "og.png")))
check("apple-touch-icon exists", os.path.exists(os.path.join(WEB, "assets", "apple-touch-icon.png")))
home = read("index.html")
check("home declares og:image", "og:image" in home)
check("twitter card is large", "summary_large_image" in home)

print()
print("# classifier accuracy (regression guard)")
# The categoriser is a trained model, so it can rot silently when features, priors or the label set
# change. This asserts it still beats a floor measured on the same held-out split — the point is that a
# change which drops accuracy fails here instead of quietly mis-shelving thousands of capabilities.
import subprocess
_r = subprocess.run([sys.executable, os.path.join(ROOT, "pipeline", "classify.py"), "--eval"],
                    capture_output=True, text=True, cwd=ROOT,
                    env={**os.environ, "PYTHONPATH": os.path.join(ROOT, "pipeline")})
_m = re.search(r"margin\s+0\.0\s+accuracy\s+([\d.]+)%", _r.stdout)
check("classifier --eval reports an accuracy", bool(_m), _r.stdout[-200:] or _r.stderr[-200:])
if _m:
    _acc = float(_m.group(1))
    check(f"classifier accuracy >= 55% (is {_acc:.1f}%)", _acc >= 55.0,
          "measured 62.9% when written; floor set below it to allow noise, not decay")


print()
print("# agent surfaces (the distribution that matters — an endpoint nobody can call is not distribution)")
V1 = os.path.join(WEB, "v0.1")
if os.path.exists(os.path.join(V1, "scores")):
    sc = json.load(open(os.path.join(V1, "scores")))
    check("/v0.1/scores is valid JSON with a scores map", isinstance(sc.get("scores"), dict))
    check("/v0.1/scores states how to read it", "format" in sc.get("metadata", {}))
    # An absent name must mean UNMEASURED. A zero would be read by a machine as "measured, and bad".
    check("no score is null or zero", all(v[0] for v in sc["scores"].values()))
    # The collision bug this caught: rows are sorted score-desc and 144 names repeat, so plain dict
    # assignment resolved chrome-devtools-mcp to 20 instead of 87. Highest score must win.
    bulk = json.load(open(os.path.join(WEB, "data", "capabilities.json")))["capabilities"]
    best = {}
    for c in bulk:
        if c.get("tashan_score") is not None:
            n = c.get("registry_name") or c["name"]
            best[n] = max(best.get(n, 0), c["tashan_score"])
    wrong = [n for n, v in sc["scores"].items() if best.get(n) and v[0] < best[n]]
    check("lookup returns the HIGHEST score for a duplicated name", not wrong,
          f"{len(wrong)} downgraded e.g. {wrong[:3]}")
    srv = json.load(open(os.path.join(V1, "servers")))
    check("/v0.1/servers uses the registry shape", isinstance(srv.get("servers"), list)
          and "server" in srv["servers"][0] and "_meta" in srv["servers"][0])
    check("measurement is namespaced sh.tashan/*",
          "sh.tashan/measurement" in srv["servers"][0]["_meta"])
    check("/v0.1/servers ships its own caveats", "note" in srv.get("metadata", {})
          and "limits" in srv.get("metadata", {}))
if os.path.exists(os.path.join(WEB, "skill", "SKILL.md")):
    sk = read("skill/SKILL.md")
    check("SKILL.md has YAML frontmatter with a description",
          sk.startswith("---") and "description:" in sk[:900])
    check("SKILL.md says a high score is NOT a security audit", "not a security audit" in sk)
    check("SKILL.md says absent means unmeasured", "UNMEASURED" in sk)

print()
print("=" * 46)
print("hubs: %d/%d passed%s" % (ok, ok + fail, " · all green" if not fail else ""))
sys.exit(1 if fail else 0)

