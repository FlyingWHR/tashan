#!/usr/bin/env python3
"""tashan — assign TASK tags: what work is this capability for?

The 15 domain categories say what a capability *touches* (browser, database, files). This axis says what
you are trying to *get done* (review code, write a PRD, edit video). Every other directory in this field
categorises by function — several literally label it "browse by use case" while the categories are
`search / databases / memory / cloud`. Nobody files by the job, which is how people actually search.

Taxonomy: web/data/tasks.json — the SINGLE definition. Do not mirror these slugs in Python or JS; the
15 domain categories are duplicated in six places and that is the mistake this avoids.

    python3 pipeline/tag_capabilities.py --declared     # free, deterministic, attributable
    ANTHROPIC_API_KEY=sk-... python3 pipeline/tag_capabilities.py --grade --limit 200
    python3 pipeline/tag_capabilities.py --grade --dry-run   # build prompts, no API call
    python3 pipeline/tag_capabilities.py --eval         # accuracy against data/tags/truth.json
    python3 pipeline/tag_capabilities.py --report       # coverage, no writes

TWO BASES, never blurred — `capability_tags.basis` records which, so any tag can answer "says who?":
  declared : the AUTHOR's own keyword/tag matched a task synonym EXACTLY. Attributable to them, not us.
  graded   : a model read the capability's full text against the rubric below. Our judgement, labelled.

Scope is deliberately skills + plugins. remote/npm/python/docker descriptions are capped at 100 chars by
the MCP REGISTRY upstream, and only 2% of them contain both a role and a stage word — tagging those from
one truncated sentence would manufacture precision we do not have. They stay "tool, not workflow-scoped"
until their READMEs are fetched.
"""
import json, os, re, sys, urllib.request, urllib.error
import build

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, "web", "data", "tasks.json")
OUTDIR = os.path.join(ROOT, "data", "tags")
GRADED = os.path.join(OUTDIR, "graded.json")
TRUTH = os.path.join(OUTDIR, "truth.json")
MODEL = os.environ.get("TAG_MODEL", "claude-sonnet-5")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MAX_TAGS = 4          # a capability that claims to do everything is telling you nothing
BODY_CHARS = 6000     # SKILL.md bodies reach 70 KB; the top of the doc carries the intent


def load_tasks():
    d = json.load(open(TASKS))
    return d["tasks"], {r["id"]: r["label"] for r in d["roles"]}


def norm(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")


def declared_index(tasks):
    """EXACT lookup from an author's own word to a task. Exact only — no substring, no stemming.

    Precision is the whole point of this pass: 'declared' means the author said it, so a fuzzy match
    would be us saying it while wearing their name. Ambiguous words that map to several tasks are
    dropped rather than guessed at.
    """
    idx = {}
    for t in tasks:
        for w in [t["slug"], t["label"]] + t.get("synonyms", []):
            k = norm(w)
            if not k or len(k) < 3:
                continue
            idx.setdefault(k, set()).add(t["slug"])
    return {k: next(iter(v)) for k, v in idx.items() if len(v) == 1}


def author_words(con, cap_id):
    """Author-supplied vocabulary: plugin manifest tags land in gh_topics (ingest_plugins writes them
    there), and skills carry repo topics. Repo-level GitHub topics are excluded — one repo publishing
    200 skills stamps all 200 identically, so they carry zero discriminative power within a repo."""
    r = con.execute("SELECT gh_topics, sources FROM capabilities WHERE id=?", (cap_id,)).fetchone()
    if not r or not r[0]:
        return []
    if (r[1] or "").startswith("plugin-marketplace"):     # these are the author's own manifest tags
        return [w.strip() for w in r[0].split(",") if w.strip()]
    return []


def rows_with_text(con, kinds=("skill", "plugin")):
    q = ("SELECT c.id, c.name, c.description, t.full_description, t.doc_body "
         "FROM capabilities c LEFT JOIN capability_text t ON t.cap_id = c.id "
         "WHERE c.kind IN (%s)" % ",".join("?" * len(kinds)))
    return con.execute(q, list(kinds)).fetchall()


def put_tags(con, cap_id, pairs, basis):
    """pairs: [(tag, confidence, evidence)]. Higher-confidence bases win on conflict."""
    for tag, conf, ev in pairs:
        con.execute(
            """INSERT INTO capability_tags (cap_id, tag, confidence, basis, evidence)
               VALUES (?,?,?,?,?)
               ON CONFLICT(cap_id, tag) DO UPDATE SET
                 confidence=MAX(capability_tags.confidence, excluded.confidence),
                 basis=CASE WHEN excluded.confidence > capability_tags.confidence
                            THEN excluded.basis ELSE capability_tags.basis END,
                 evidence=CASE WHEN excluded.confidence > capability_tags.confidence
                            THEN excluded.evidence ELSE capability_tags.evidence END""",
            (cap_id, tag, conf, basis, (ev or "")[:300]))


# ---------------------------------------------------------------- declared pass
def run_declared(con, tasks, dry=False):
    idx = declared_index(tasks)
    hit = miss = rows = 0
    for cap_id, name, desc, full, body in rows_with_text(con):
        rows += 1
        got = {}
        for w in author_words(con, cap_id):
            slug = idx.get(norm(w))
            if slug:
                got[slug] = w
        if not got:
            miss += 1
            continue
        hit += 1
        if not dry:
            put_tags(con, cap_id, [(s, 0.75, f'author keyword: "{w}"') for s, w in
                                   list(got.items())[:MAX_TAGS]], "declared")
    if not dry:
        con.commit()
    print(f"declared: {hit}/{rows} rows tagged from the author's own keywords "
          f"({miss} had none that map to a task)")
    return hit


# ---------------------------------------------------------------- graded pass
def rubric(tasks):
    lines = [f'  {t["slug"]}: {t["label"]} — {t["blurb"]}' for t in tasks]
    return (
        "You are filing an AI capability (an MCP server, agent skill or plugin) under the WORK someone "
        "would be doing when they reach for it.\n\n"
        "Pick the tasks from this list that the capability is genuinely FOR:\n" + "\n".join(lines) +
        "\n\nRules:\n"
        f"- At most {MAX_TAGS} tasks. Fewer is better. A capability tagged with everything says nothing.\n"
        "- Only tag what the text actually supports. Returning an EMPTY list is a correct and expected "
        "answer for generic infrastructure that serves no particular job.\n"
        "- Judge the work it does, not the technology it uses. A Postgres client used to pull numbers for "
        "a report is 'query-a-database', not 'analyze-a-dataset', unless it actually analyses.\n"
        "- For each tag give confidence 0-1 and a SHORT verbatim quote from the text as evidence. Never "
        "invent a quote.\n\n"
        'Respond with ONLY this JSON, nothing else:\n'
        '{"tags":[{"tag":"<slug>","confidence":0.0,"evidence":"<quote from the text>"}]}')


def prompt_for(name, desc, full, body):
    text = (full or desc or "")
    if body:
        text += "\n\n--- documentation ---\n" + body[:BODY_CHARS]
    return f"Capability name: {name}\n\nIts own description and docs:\n{text[:BODY_CHARS + 1200]}"


def call_api(system, user):
    body = json.dumps({"model": MODEL, "max_tokens": 700, "system": system,
                       "messages": [{"role": "user", "content": user}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
                                 headers={"x-api-key": API_KEY, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.load(r)
    return "".join(p.get("text", "") for p in d.get("content", []))


def run_grade(con, tasks, limit, dry=False):
    valid = {t["slug"] for t in tasks}
    sysmsg = rubric(tasks)
    os.makedirs(OUTDIR, exist_ok=True)
    done = {}
    if os.path.exists(GRADED):
        try:
            done = json.load(open(GRADED))
        except Exception:
            done = {}
    todo = [r for r in rows_with_text(con) if r[0] not in done and (r[3] or r[2])]
    todo = todo[:limit]
    print(f"grading {len(todo)} capabilities ({len(done)} already graded, resumable)")
    if dry:
        cap_id, name, desc, full, body = todo[0]
        print("\n--- system (first 700 chars) ---\n" + sysmsg[:700])
        print("\n--- user (first 700 chars) ---\n" + prompt_for(name, desc, full, body)[:700])
        print(f"\ndry run — nothing called. {len(todo)} would be graded.")
        return 0
    if not API_KEY:
        print("ANTHROPIC_API_KEY not set — cannot grade. Run --declared for the free pass, or "
              "--dry-run to inspect prompts.")
        return 1
    for i, (cap_id, name, desc, full, body) in enumerate(todo, 1):
        try:
            raw = call_api(sysmsg, prompt_for(name, desc, full, body))
            m = re.search(r"\{.*\}", raw, re.S)
            got = json.loads(m.group(0)) if m else {"tags": []}
            keep = [(t["tag"], float(t.get("confidence") or 0), t.get("evidence"))
                    for t in (got.get("tags") or []) if t.get("tag") in valid][:MAX_TAGS]
            done[cap_id] = keep
            put_tags(con, cap_id, keep, "graded")
        except Exception as e:
            print(f"  ! {cap_id}: {type(e).__name__} {e}")
            continue
        if i % 25 == 0:
            con.commit()
            json.dump(done, open(GRADED, "w"))
            print(f"  {i}/{len(todo)}", flush=True)
    con.commit()
    json.dump(done, open(GRADED, "w"))
    print(f"graded {len(todo)}; {sum(1 for v in done.values() if v)} carry at least one tag")
    return 0


# ---------------------------------------------------------------- eval + report
def run_eval(con, tasks):
    """Accuracy against hand labels. Multi-label, so we report precision/recall, not a single accuracy:
    a capability legitimately does several jobs and 'exactly right' is the wrong bar."""
    if not os.path.exists(TRUTH):
        print(f"no held-out labels at {TRUTH} — hand-label ~150 rows as "
              '{"<cap_id>": ["<task-slug>", ...]} to enable this')
        return 1
    truth = json.load(open(TRUTH))
    tp = fp = fn = 0
    for cap_id, want in truth.items():
        got = {r[0] for r in con.execute("SELECT tag FROM capability_tags WHERE cap_id=?", (cap_id,))}
        want = set(want)
        tp += len(got & want); fp += len(got - want); fn += len(want - got)
    prec = tp / max(1, tp + fp); rec = tp / max(1, tp + fn)
    f1 = 2 * prec * rec / max(1e-9, prec + rec)
    print(f"held-out n={len(truth)}  precision {prec*100:.1f}%  recall {rec*100:.1f}%  F1 {f1*100:.1f}%")
    return 0


def run_report(con, tasks):
    total = con.execute("SELECT COUNT(*) FROM capabilities WHERE kind IN ('skill','plugin')").fetchone()[0]
    tagged = con.execute("SELECT COUNT(DISTINCT cap_id) FROM capability_tags").fetchone()[0]
    print(f"tagged {tagged}/{total} skills+plugins ({100*tagged/max(1,total):.1f}%)")
    for basis, n in con.execute("SELECT basis, COUNT(*) FROM capability_tags GROUP BY basis"):
        print(f"  {basis:9} {n} assignments")
    print("\npopulated tasks (>=5 rated capabilities gets a page):")
    rows = con.execute(
        """SELECT t.tag, COUNT(*) n, SUM(CASE WHEN c.trust IS NOT NULL THEN 1 ELSE 0 END) rated
           FROM capability_tags t JOIN capabilities c ON c.id=t.cap_id
           GROUP BY t.tag ORDER BY rated DESC""").fetchall()
    for tag, n, rated in rows[:25]:
        print(f"  {tag:32} {rated:4} rated / {n:4} total{'' if rated >= 5 else '   (no page)'}")
    empty = [t["slug"] for t in tasks if t["slug"] not in {r[0] for r in rows}]
    print(f"\n{len(rows)} of {len(tasks)} tasks have at least one capability; {len(empty)} empty")
    if empty:
        print("  empty: " + ", ".join(empty[:12]) + (" …" if len(empty) > 12 else ""))
    return 0


def main():
    tasks, _ = load_tasks()
    con = build.db()
    dry = "--dry-run" in sys.argv
    limit = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--limit=")), 0) or
                (sys.argv[sys.argv.index("--limit") + 1] if "--limit" in sys.argv else 100000))
    rc = 0
    if "--declared" in sys.argv:
        run_declared(con, tasks, dry)
    elif "--grade" in sys.argv:
        rc = run_grade(con, tasks, limit, dry)
    elif "--eval" in sys.argv:
        rc = run_eval(con, tasks)
    else:
        rc = run_report(con, tasks)
    con.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
