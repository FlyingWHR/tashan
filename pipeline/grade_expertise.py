#!/usr/bin/env python3
"""Grade staged capability documents with the shared OpenAI grading allowance.

Run with --dry-run to inspect prompts, or --limit N to bound a live run.
Accepted grades are retained in data/readmes/scores_auto.json for replay.
"""
import json, os, sys
from pathlib import Path

import grade_evidence
import openai_grading
from merge_expertise import validate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "data", "readmes", "manifest.json")
OUT = os.path.join(ROOT, "data", "readmes", "scores_auto.json")
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
4. Differing tool counts in one file are usually NOT a contradiction — a per-sub-server inventory
   ("8 tools for dns, 62 for vps") or a table of deployment modes ("9 remote / 114 local") is the
   document being precise. Mention it in the note; do not cap the grade for it. Both times this
   rule fired automatically on the real corpus it was wrong, and both times it was wrong about the
   best-documented capability in the batch.
5. Tool documentation that lives in a linked file IS documentation. Splitting a large tool reference
   out of the README is better practice, not worse. Linked in-repo docs are appended below the
   README when they could be fetched; if the document hands off to a page that is not here, treat
   per-tool docs as UNVERIFIED — that rules out deep, which needs all four confirmed, and it is not
   a reason to grade down.
Also write a `note`: ONE sentence (<=200 chars), specific and evidence-based — cite what IS and ISN'T in the docs, and flag any real risk (e.g. a prompt-injection surface, a dangerous-op tool). No praise, no fluff.

Respond with ONLY this JSON object, nothing else:
{"verdict": "<deep|solid|thin>", "expertise": <integer in the verdict band>, "note": "<one sentence>",
"evidence":"<one short verbatim passage from the documentation supporting the note>"}. If you cannot grade this capability, return {"verdict": null}."""

# THE SCALABLE PATH WAS GRADING A PREFIX. The manifest stores a 14,000-character slice, and this
# builder cut it again at exactly that length — so the automated grader, which is the only path that
# can ever cover the corpus, read the opening of every long document and nothing else. The bias runs
# one way: tool references, troubleshooting and stated limitations live at the BOTTOM of a thorough
# README, so the documents most likely to earn `deep` were the ones most likely to be truncated out
# of it. Measured on the first top-demand queue, 36 of 57 hit the cap exactly, and reading them in
# full took firecrawl-mcp from 0 documented tools to 28 and figma-console-mcp from 0 to 70.
#
# grade_evidence.follow() re-reads the file at full length from the repo and appends the in-repo
# tool docs the README points at — chrome-devtools-mcp documents 47 tools in docs/tool-reference.md
# and none in its README. Both are cached on disk, so this costs network once per capability.
#
# The cap that remains is about model context and per-call cost, not about what counts as evidence,
# and it is set where a full README plus a tool reference fits comfortably underneath it.
PROMPT_CHARS = int(os.environ.get("GRADE_PROMPT_CHARS", "60000"))


def build_prompt(cap, cache=None):
    head = f"name: {cap.get('name')}\nrepo: {cap.get('repo')}\nnpm: {cap.get('npm_pkg')}\ndescription: {cap.get('description') or '(none)'}"
    readme, linked = cap.get("readme") or "", []
    try:
        readme, linked = grade_evidence.follow(cap, cache if cache is not None else {})
    except (ValueError, OSError):
        pass
    if (len(readme.strip()) < 400 or len(readme) > PROMPT_CHARS or
            (len(cap.get("readme") or "") == grade_evidence.MANIFEST_CAP and
             not any(" (full," in item for item in linked))):
        return ""
    note = ("\n(the sections below the README are its own linked docs: %s)" % ", ".join(linked)
            if linked else "")
    return f"{head}{note}\n\n--- DOCUMENTATION ---\n{readme[:PROMPT_CHARS]}\n--- END DOCUMENTATION ---"

def parse_grade(txt, document):
    obj = json.loads(txt)
    if obj["verdict"] is None:
        return None
    grade = {k: obj.get(k) for k in ("expertise", "verdict", "note")}
    if not grade["note"] or validate(dict(grade, id="candidate"), "OpenAI", None):
        raise ValueError("response does not satisfy the grading rubric")
    quote = obj.get("evidence")
    if not isinstance(quote, str) or not 8 <= len(quote.strip()) <= 300 or quote not in document:
        raise ValueError("missing supporting passage")
    return dict(grade, evidence=quote)


def save_scores(path, scores):
    if scores:
        target = Path(path)
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(list(scores.values()), indent=2) + "\n", encoding="utf-8")
        temp.replace(target)


def main():
    dry = "--dry-run" in sys.argv
    grade_all = "--all" in sys.argv
    limit = None
    if "--limit" in sys.argv:
        try: limit = int(sys.argv[sys.argv.index("--limit") + 1])
        except Exception: limit = None

    caps = json.load(open(MANIFEST))
    caps = [c for c in caps if not c["id"].startswith("skill:")]
    if not grade_all:
        # skip caps already graded (idempotent / incremental): merge existing outputs' ids
        done = set()
        for f in (OUT, *[os.path.join(ROOT, "data", "readmes", n) for n in os.listdir(os.path.join(ROOT, "data", "readmes")) if n.startswith("scores_")]):
            if os.path.exists(f):
                try: done |= {s["id"] for s in json.load(open(f))}
                except Exception: pass
        caps = [c for c in caps if c["id"] not in done]
    if limit is not None:
        caps = caps[:limit]

    # ONE fetch cache for the whole run, shared with grade_evidence and persisted between runs.
    # Without it every capability re-downloads its own linked docs from GitHub — 63 caps x up to
    # four files, every night, for text that never changes between publishes.
    linked_cache = (json.load(open(grade_evidence.LINKED, encoding="utf-8"))
                    if os.path.exists(grade_evidence.LINKED) else {})

    print(f"grading {len(caps)} caps with {openai_grading.MODEL}" + (" (dry-run)" if dry else ""))
    if dry:
        # prove prompt-building works with no key/network; assert the rubric is well-formed
        assert all(v in RUBRIC for v in VERDICTS), "rubric missing a verdict label"
        for c in caps[:2]:
            p = build_prompt(c, linked_cache)
            assert c["id"]
            print(f"  ✓ prompt for {c['id']} ({len(p)} chars)")
        # self-check the parser on a canned response
        g = parse_grade('{"verdict":"solid","expertise":72,"note":"Two examples.","evidence":"Example 2"}', "Example 2")
        assert g["expertise"] == 72
        assert parse_grade('{"verdict":null}', "") is None
        print("  ✓ parser + rubric self-check passed")
        return
    from merge_expertise import build
    con = build.db()
    scores = {s["id"]: s for s in json.loads(Path(OUT).read_text())} if Path(OUT).exists() else {}
    budget = None
    accepted = 0
    try:
        if not caps or not os.getenv("OPENAI_API_KEY"):
            raise openai_grading.StopGrading("empty queue or OPENAI_API_KEY unavailable")
        budget = openai_grading.Session("expertise")
        for c in caps:
            prompt = build_prompt(c, linked_cache)
            if not prompt:
                continue
            try:
                document = prompt.split("\n--- DOCUMENTATION ---\n", 1)[1].rsplit("\n--- END DOCUMENTATION ---", 1)[0]
                grade = parse_grade(budget.grade(RUBRIC, prompt, 400), document)
            except (TypeError, ValueError, KeyError, AttributeError):
                print(f"  {c['id']}: invalid grade")
                continue
            if grade:
                scores[c["id"]] = dict(grade, id=c["id"], model=openai_grading.MODEL)
                save_scores(OUT, scores)
                accepted += 1
            else:
                con.execute("UPDATE capabilities SET grade_withheld=? WHERE id=? AND expertise_verdict IS NULL",
                            ("The rubric could not establish a grade from this documentation.", c["id"]))
    except openai_grading.StopGrading as e:
        openai_grading.report(f"Expertise grading paused: {e}")
    finally:
        for score in scores.values():
            con.execute("UPDATE capabilities SET expertise=?, expertise_verdict=?, expertise_note=?, "
                        "grade_withheld=NULL WHERE id=? AND expertise_verdict IS NULL",
                        (score["expertise"], score["verdict"], score["note"], score["id"]))
        con.commit()
        con.close()
        if budget:
            target = Path(grade_evidence.LINKED)
            temp = target.with_suffix(".tmp")
            with temp.open("w", encoding="utf-8") as f:
                json.dump(linked_cache, f)
            temp.replace(target)
            budget.close()
    openai_grading.report(f"Accepted {accepted} documentation grades from {len(caps)} queued.")

if __name__ == "__main__":
    main()
