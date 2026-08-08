#!/usr/bin/env python3
"""Automated expertise grading — the moat as CODE, not a person.

Today expertise is graded by Claude Code subagents in an interactive session, so only ~24 of ~2,000 caps
are graded (~1%). That doesn't scale to a store adding thousands of listings. This runs the SAME rubric as
a pipeline stage against the Anthropic API, so grading keeps up with ingestion.

    ANTHROPIC_API_KEY=sk-... python3 pipeline/grade_expertise.py          # grade ungraded caps in the manifest
    python3 pipeline/grade_expertise.py --dry-run                          # build prompts, no API call (testable)
    ANTHROPIC_API_KEY=... GRADE_MODEL=claude-sonnet-5 python3 pipeline/grade_expertise.py --all --limit 50

Input : data/readmes/manifest.json  (staged by fetch_readmes.py — {id,name,repo,npm_pkg,description,readme})
Output: data/readmes/scores_auto.json  (the exact [{id,expertise,verdict,note}] shape merge_expertise.py reads)
Then  : python3 pipeline/merge_expertise.py   # folds grades into the DB + re-exports the site JSON

Stdlib only (urllib), no pip deps. Sequential Messages API is fine at today's scale (hundreds–low thousands);
at 10k+ swap the per-item call for the Message Batches API (POST /v1/messages/batches — 50% cheaper, async):
the prompt/parse code below is unchanged, only the transport batches. See docs/ARCHITECTURE-RISKS.md §1.3.
"""
import json, os, sys, re, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "data", "readmes", "manifest.json")
OUT = os.path.join(ROOT, "data", "readmes", "scores_auto.json")
MODEL = os.environ.get("GRADE_MODEL", "claude-sonnet-5")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# THREE BANDS, ONE QUESTION: how completely does this document explain how to use this thing?
# `wrapper` and `slop` were on this scale and did not belong. `wrapper` is a KIND of artifact — a
# well-documented shim ranked below a badly-documented original, which is a value judgment dressed
# as a measurement; it is now a separate fact carrying the author's own words. `slop` claimed
# "AI-generated filler", which a README read cannot establish; both rows carrying it turned out to
# be ordinary factual findings (an announced shutdown, a documentation inconsistency).
VERDICTS = ["deep", "solid", "thin"]

RUBRIC = """You are grading ONE THING: how completely a capability's own documentation explains how to use it. Not whether the software is good, not whether the team is expert, not whether the idea is original — only how well the documentation does its job. Judge on public evidence, never on hype. Output STRICT JSON only.

Assign a verdict (one of: deep, solid, thin) and a score 0-100:
- deep (80-100): per-tool documentation, >=2 worked examples with real arguments or output, setup/auth covered, and at least one stated limitation.
- solid (60-79): clear prose, at least one worked example, honest about scope. A real product with real docs that does not reach all four deep criteria.
- thin (35-59): reference-only, or install instructions with no worked example, or a wall of badges and client-config blocks where tool docs should be.

SEPARATELY, and NOT part of the verdict, answer whether the capability DESCRIBES ITSELF as a shim: a
bridge, proxy, adapter or wrapper whose work happens somewhere else. This is a fact about what the
thing IS, evidenced by the author's own words, and it is recorded beside the grade rather than
folded into it — a well-documented shim is not worse-documented than a badly-documented original,
and ranking it lower was a value judgment dressed as a measurement. Set "shim": true only when the
author says so, and put their sentence in "shim_note". Never infer it from the name or your own
reading of the architecture.

There is no verdict for "low quality", "AI-generated" or "non-functional". Reading a README cannot
establish any of those, and a published accusation we cannot support is the one thing this project
must never ship. If a document announces that the service is shut down, or contradicts itself, say
so in the note as a fact and grade the documentation on its own terms.

CALIBRATION RULES — these override the band descriptions above, and exist because six graders applied
the bands alone and returned "deep" anywhere from 1.5% to 22.9% of the time (see docs/GRADING-RUBRIC.md):
1. deep requires ALL FOUR of: per-tool docs, >=2 worked examples with real arguments, setup/auth
   covered, and at least one stated limitation. Cannot name all four? It is solid.
2. If the README never names this capability, DO NOT GRADE IT. Return verdict null. It is
   documented by a shared repo README about something else: a grade would borrow credit for
   another project's work, and a low grade would borrow blame for it. The export states the
   fact ("shares its documentation with N other capabilities") instead.
3. Length is not depth. A long README with no worked example is thin.
4. Internal contradictions (two different tool counts in one file) cap at thin.
5. A well-documented shim is still a wrapper.
Also write a `note`: ONE sentence (<=200 chars), specific and evidence-based — cite what IS and ISN'T in the docs, and flag any real risk (e.g. a prompt-injection surface, a dangerous-op tool). No praise, no fluff.

Respond with ONLY this JSON object, nothing else:
{"verdict": "<one of the five>", "expertise": <int 0-100>, "note": "<one sentence>"}"""

def build_prompt(cap):
    head = f"name: {cap.get('name')}\nrepo: {cap.get('repo')}\nnpm: {cap.get('npm_pkg')}\ndescription: {cap.get('description') or '(none)'}"
    readme = (cap.get("readme") or "")[:14000]   # cap the README so a huge one can't blow the context/cost
    return f"{head}\n\n--- README ---\n{readme}\n--- END README ---"

def call_api(prompt):
    body = json.dumps({
        "model": MODEL, "max_tokens": 400,
        "system": RUBRIC,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
        headers={"x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.load(r)
    txt = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    return txt

def parse_grade(txt):
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        return None
    try:
        o = json.loads(m.group(0))
    except Exception:
        return None
    v = str(o.get("verdict", "")).lower().strip()
    if v not in VERDICTS:
        return None
    try:
        e = max(0, min(100, int(round(float(o.get("expertise"))))))
    except Exception:
        return None
    return {"expertise": e, "verdict": v, "note": str(o.get("note", ""))[:240]}

def main():
    dry = "--dry-run" in sys.argv
    grade_all = "--all" in sys.argv
    limit = None
    if "--limit" in sys.argv:
        try: limit = int(sys.argv[sys.argv.index("--limit") + 1])
        except Exception: limit = None

    caps = json.load(open(MANIFEST))
    if not grade_all:
        # skip caps already graded (idempotent / incremental): merge existing outputs' ids
        done = set()
        for f in (OUT, *[os.path.join(ROOT, "data", "readmes", n) for n in os.listdir(os.path.join(ROOT, "data", "readmes")) if n.startswith("scores_")]):
            if os.path.exists(f):
                try: done |= {s["id"] for s in json.load(open(f))}
                except Exception: pass
        caps = [c for c in caps if c["id"] not in done]
    if limit:
        caps = caps[:limit]

    print(f"grading {len(caps)} caps with {MODEL}" + (" (dry-run)" if dry else ""))
    if dry:
        # prove prompt-building works with no key/network; assert the rubric is well-formed
        assert all(v in RUBRIC for v in VERDICTS), "rubric missing a verdict label"
        for c in caps[:2]:
            p = build_prompt(c)
            assert c["id"] and len(p) > 20
            print(f"  ✓ prompt for {c['id']} ({len(p)} chars)")
        # self-check the parser on a canned response
        g = parse_grade('noise {"verdict":"solid","expertise":72,"note":"clear docs, 2 examples"} tail')
        assert g == {"expertise": 72, "verdict": "solid", "note": "clear docs, 2 examples"}, g
        assert parse_grade('{"verdict":"bogus","expertise":50}') is None
        print("  ✓ parser + rubric self-check passed")
        return
    if not API_KEY:
        # SKIP, NOT FAIL: this runs in the nightly loop now. Loud, because 18 of the top 20
        # capabilities by downloads carry no grade, and silence here is why nobody noticed.
        print("SKIPPED — ANTHROPIC_API_KEY is not set, so no capability gets an expertise grade "
              "tonight. Coverage stays where it is: the axis an agent notices missing first.")
        return 0

    scores, fails = [], 0
    for i, c in enumerate(caps, 1):
        try:
            g = parse_grade(call_api(build_prompt(c)))
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:            # rate-limit / server — back off and retry once
                time.sleep(5)
                try: g = parse_grade(call_api(build_prompt(c)))
                except Exception: g = None
            else:
                g = None
        except Exception:
            g = None
        if g:
            g["id"] = c["id"]; scores.append(g)
            print(f"  [{i}/{len(caps)}] {c['id']}: {g['verdict']} ({g['expertise']})")
        else:
            fails += 1; print(f"  [{i}/{len(caps)}] {c['id']}: FAILED")
        if i % 20 == 0:
            json.dump(scores, open(OUT, "w"), indent=2)   # checkpoint
        time.sleep(0.1)
    json.dump(scores, open(OUT, "w"), indent=2)
    print(f"\nwrote {len(scores)} grades ({fails} failed) -> {OUT}\nnext: python3 pipeline/merge_expertise.py")

if __name__ == "__main__":
    main()
