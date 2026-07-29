#!/usr/bin/env python3
"""tashan — derive the task taxonomy from what real occupations actually do.

WHY THIS REPLACES A HAND-WRITTEN TAXONOMY
The first task list was 105 entries invented by one person and named in that person's words. It could
not answer the only question that matters for a measurement product: *says who?* This derives the axis
from the O*NET 30.3 database (US Dept of Labor, CC BY 4.0) — 1,016 occupations, 18,796 surveyed task
statements, and 2,087 named Detailed Work Activities (DWAs), which are a formal, citable decomposition
of real jobs into the steps that make them up.

The payoff is provenance no competitor has: every task tag carries the O*NET DWA ids behind it and the
OCCUPATIONS that perform it, so a page can say "this is a step performed by Data Scientists, Financial
Analysts and Market Research Analysts" and cite the source, instead of asserting a category.

THREE LAYERS, AND ONLY THE FIRST IS EVIDENCE — the other two are judgement and are labelled as such:

  1. EXTRACT (this file, measured).  Occupations in knowledge-work SOC major groups, their CORE task
     statements only, resolved to DWAs, with occupation attribution and breadth counts.
  2. FILTER (judgement, disclosed).  Which steps can a software capability plausibly assist? O*NET maps
     all work, so "Serve on institutional committees" and "Order library materials" are in scope for it
     and out of scope for us. Every drop is recorded, not silently omitted.
  3. RENAME (judgement, disclosed).  O*NET writes in government register; practitioners do not. The tag
     people search for is the insider term, so "Analyze data to identify trends or relationships among
     variables" becomes "exploratory data analysis", keeping the DWA id as the receipt.

    python3 pipeline/onet_tasks.py --candidates      # ranked DWA candidates with their occupations
    python3 pipeline/onet_tasks.py --occupations     # the occupation set this is derived from
    python3 pipeline/onet_tasks.py --coverage        # which occupations our capabilities can serve

Data: data/onet/db_30_3_text/ (downloaded, CC BY 4.0 — attribution required wherever this is published).
"""
import collections
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ONET = os.path.join(ROOT, "data", "onet", "db_30_3_text")

# SOC major groups where work is done with information rather than with hands or bodies. Stated as a
# filter rather than applied silently: an MCP server can help a Financial Analyst and cannot help a
# Roofer, and pretending otherwise would put 500 unreachable occupations in the denominator.
KNOWLEDGE_GROUPS = {
    "11": "Management",
    "13": "Business & Financial",
    "15": "Computer & Mathematical",
    "17": "Architecture & Engineering",
    "19": "Life, Physical & Social Science",
    "23": "Legal",
    "25": "Education",
    "27": "Arts, Design, Entertainment & Media",
    "41": "Sales",
    "43": "Office & Administrative Support",
}

# O*NET carries 68 near-identical "Postsecondary Teachers, <subject>" occupations that share one DWA
# set, which alone would make "Maintain student records" and "Serve on departmental committees" look
# like the most universal work in the economy. They are ONE job for our purposes. Collapsed so breadth
# counts measure how many DIFFERENT kinds of work a step appears in, not how finely O*NET splits a field.
COLLAPSE_PREFIX = ("25-1",)   # postsecondary teachers


# LAYER 2 — the relevance filter, stated so it can be argued with. O*NET maps ALL work, including work
# no software can touch. A capability can help someone analyse data or draft a document; it cannot help
# them move a pallet, repair a compressor, or motivate a subordinate. Filtering by General Work Activity
# rather than by hand keeps the decision at 41 checkable calls instead of 1,159 invisible ones.
OUT_OF_SCOPE_GWA = {
    "Handling and Moving Objects",
    "Performing General Physical Activities",
    "Repairing and Maintaining Electronic Equipment",
    "Repairing and Maintaining Mechanical Equipment",
    "Controlling Machines and Processes",
    "Operating Vehicles, Mechanized Devices, or Equipment",
    "Assisting and Caring for Others",
    "Performing for or Working Directly with the Public",
    "Guiding, Directing, and Motivating Subordinates",
    "Developing and Building Teams",
    "Coaching and Developing Others",
    "Establishing and Maintaining Interpersonal Relationships",
    "Resolving Conflicts and Negotiating with Others",
    "Staffing Organizational Units",
    "Inspecting Equipment, Structures, or Materials",
}


def read(name):
    with open(os.path.join(ONET, name), encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load():
    occ = {o["O*NET-SOC Code"]: o["Title"] for o in read("Occupation Data.txt")
           if o["O*NET-SOC Code"][:2] in KNOWLEDGE_GROUPS}
    dwa_name, dwa_gwa = {}, {}
    for r in read("GWAs to IWAs to DWAs.txt"):
        dwa_name[r["DWA Element ID"]] = r["DWA Element Name"]
        dwa_gwa[r["DWA Element ID"]] = r["GWA Element ID"]
    core = {(r["O*NET-SOC Code"], r["Task ID"]) for r in read("Task Statements.txt")
            if r["Task Type"] == "Core"}
    return occ, dwa_name, dwa_gwa, core


def bucket(code, title):
    """One label per distinct kind of work — see COLLAPSE_PREFIX."""
    if code.startswith(COLLAPSE_PREFIX):
        return "Postsecondary Teachers"
    return title


def candidates():
    occ, dwa_name, dwa_gwa, core = load()
    who = collections.defaultdict(set)     # dwa id -> {occupation label}
    for r in read("Tasks to DWAs.txt"):
        code = r["O*NET-SOC Code"]
        if code not in occ or (code, r["Task ID"]) not in core:
            continue
        if r["DWA Element ID"] in dwa_name:
            who[r["DWA Element ID"]].add(bucket(code, occ[code]))
    return occ, dwa_name, dwa_gwa, who


def validate_terms():
    """Falsify the insider names against 5.9M chars of text practitioners actually wrote.

    The rename layer is the part most likely to be quietly wrong: a plausible-sounding name that nobody
    in the field says produces a tag nobody searches for. Every O*NET phrasing scores ZERO here, which is
    the whole reason the layer exists — but so did 8 of the first 22 names I proposed
    ("requirements discovery", "picture edit", "BI and reporting", "campaign measurement" …).

    Document frequency, not raw count: one vendor's auto-generated template repeats "rube search" 183
    times across hundreds of near-identical skills, and term frequency ranks that above every real word
    in the corpus.

    READ THE OUTPUT, DO NOT AUTOMATE IT. Frequency proves a term is USED, never that it MEANS the O*NET
    step. Measured examples of that trap: "transcription" (18 docs) beat every candidate for "Edit audio
    or video recordings" and is a different process; "copywriting" (35) beat every candidate for "Study
    scripts to determine project requirements" and is also a different process. Both would have been
    confident, popular, wrong. Where a domain is genuinely absent from our corpus — video post, finance —
    the honest answer is `unvalidated`, not the nearest popular word.
    """
    import sqlite3
    db = os.path.join(ROOT, "data", "tashan.db")
    con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    docs = [((n or "") + ". " + (fd or "") + " " + (b or "")).lower() for n, fd, b in con.execute(
        "SELECT c.name, t.full_description, t.doc_body "
        "FROM capabilities c JOIN capability_text t ON t.cap_id = c.id")]
    con.close()
    import json as _json
    import re as _re
    path = os.path.join(ROOT, "data", "onet", "mapping.json")
    mapping = _json.load(open(path))["mappings"]
    print(f"{len(docs)} practitioner-written documents\n")
    print(f"{'tag':<30}{'docs':>6}  status")
    for e in mapping:
        term = (e.get("term") or e["label"]).lower()
        pat = _re.compile(r"(?<![a-z])" + _re.escape(term) + r"(?![a-z])")
        n = sum(1 for d in docs if pat.search(d))
        state = e.get("validation", "")
        if n >= 5:
            status = "confirmed — practitioners use this term"
        elif n > 0:
            status = "weak — used, but thinly represented here"
        else:
            status = "UNVALIDATED — " + (state or "term not found in corpus; domain may be absent")
        print(f"{e['label'][:29]:<30}{n:>6}  {status}")
    return 0


ROLE_LABELS = {
    "engineer": "Software engineer", "web-dev": "Web / frontend developer",
    "mobile-dev": "Mobile developer", "devops": "DevOps / SRE", "security": "Security engineer",
    "data-analyst": "Data analyst", "data-engineer": "Data engineer", "ai-engineer": "AI engineer",
    "pm": "Product manager", "designer": "Designer", "creator": "Creator / video",
    "writer": "Writer / content", "marketer": "Marketer / growth", "sales": "Sales",
    "support": "Customer support", "finance": "Finance / accounting", "legal": "Legal / compliance",
    "hr": "HR / recruiting", "researcher": "Researcher", "ops": "Operations",
    "educator": "Educator", "scientist": "Scientist", "hardware": "Hardware / electronics",
    "agent-operator": "Agent operator",
}


def build_tasks_json():
    """Generate web/data/tasks.json — the single definition the site and generators read.

    Everything here is DERIVED: rerunning this regenerates the file, so the taxonomy cannot drift away
    from its evidence. Each task carries the O*NET steps behind it and the occupations that perform
    them, which is what lets a hub page cite its own basis instead of asserting a category.
    """
    import json
    occ, dwa_name, dwa_gwa, who = candidates()
    by_step = {}
    for did, people in who.items():
        by_step.setdefault(dwa_name[did], set()).update(people)

    src = json.load(open(os.path.join(ROOT, "data", "onet", "mapping.json")))
    tasks, roles_used = [], set()
    for e in src["mappings"]:
        # WEIGHT OCCUPATIONS BY OVERLAP, don't just union them. Some O*NET steps are performed by nearly
        # every technical occupation ("Recommend technical design or process changes to improve
        # efficiency, quality, or performance"), so a plain union made the Code review page cite
        # Automotive Engineering Technicians and Civil Engineers — true of the STEP, absurd for the TASK,
        # and it would discredit the one citation competitors cannot copy. An occupation that performs
        # several of a task's steps is a practitioner of it; one that performs a single generic step is
        # incidental. Keep the top overlap tier only.
        hits = collections.Counter()
        for s in e["onet"]:
            for p in by_step.get(s, set()):
                hits[p] += 1
        best = max(hits.values(), default=0)
        floor = best if best <= 1 else max(2, best - 1)
        people = {p for p, n in hits.items() if n >= floor}
        roles_used.update(e.get("roles", []))
        # Synonyms exist for ONE job: matching an author's own manifest keyword to a task, exactly
        # (tag_capabilities.py --declared). Derived from the names we already committed to, plus any
        # explicit extras in the mapping — never invented here, or "declared" would stop meaning the
        # author said it.
        syn = {e.get("term", "").lower(), e["label"].lower(), e["slug"].replace("-", " ")}
        syn.update(s.lower() for s in e.get("synonyms", []))
        tasks.append({
            "slug": e["slug"], "label": e["label"], "term": e.get("term", e["label"]).lower(),
            "blurb": e["insider"],
            "synonyms": sorted(x for x in syn if x and len(x) > 2),
            "roles": e.get("roles", []),
            "onet_steps": e["onet"],
            "occupations": sorted(people),
            "grounded": bool(e["onet"]),
            "validation": e.get("validation"),
        })

    out = {
        "version": 2,
        "source": "O*NET 30.3 Database, U.S. Department of Labor / Employment and Training "
                  "Administration, used under CC BY 4.0. Modified: process steps consolidated into "
                  "the terms practitioners use, and filtered to work software can assist.",
        "note": "Generated by pipeline/onet_tasks.py --build from data/onet/mapping.json. Do not hand "
                "edit and do not mirror these slugs in Python or JS — the 15 domain categories are "
                "duplicated in six places and that is the mistake this avoids. `occupations` is "
                "evidence (who performs this step, per O*NET); `label`/`term` are our naming, "
                "falsified against practitioner text with --validate.",
        "roles": [{"id": r, "label": ROLE_LABELS.get(r, r)} for r in sorted(roles_used)],
        "tasks": sorted(tasks, key=lambda t: t["label"]),
    }
    path = os.path.join(ROOT, "web", "data", "tasks.json")
    json.dump(out, open(path, "w"), indent=2, ensure_ascii=False)
    grounded = sum(1 for t in tasks if t["grounded"])
    cov = len({p for t in tasks for p in t["occupations"]})
    print(f"wrote {path}")
    print(f"  {len(tasks)} tasks · {grounded} O*NET-grounded · {len(tasks)-grounded} declared gaps")
    print(f"  {len(out['roles'])} roles · {cov} distinct kinds of knowledge work cited")
    return 0


def main():
    if "--validate" in sys.argv:
        return validate_terms()
    if "--build" in sys.argv:
        return build_tasks_json()
    occ, dwa_name, dwa_gwa, who = candidates()
    if "--occupations" in sys.argv:
        groups = collections.defaultdict(set)
        for code, title in occ.items():
            groups[KNOWLEDGE_GROUPS[code[:2]]].add(bucket(code, title))
        print(f"{sum(len(v) for v in groups.values())} distinct kinds of knowledge work "
              f"(from {len(occ)} O*NET occupations, postsecondary teaching collapsed)")
        for g in sorted(groups):
            print(f"\n## {g}  ({len(groups[g])})")
            for t in sorted(groups[g])[:200]:
                print("   " + t)
        return 0

    ranked = sorted(who.items(), key=lambda kv: (-len(kv[1]), dwa_name[kv[0]]))
    print(f"{len(who)} distinct process steps across {len({bucket(c, t) for c, t in occ.items()})} "
          f"kinds of knowledge work (O*NET 30.3, CORE tasks only)")
    print(f"{'occs':>5}  {'dwa id':<18} step / performed by")
    for did, people in ranked:
        n = len(people)
        if n < 2:
            continue
        print(f"{n:5}  {did:<18} {dwa_name[did]}")
        print(f"{'':5}  {'':<18}   {', '.join(sorted(people)[:6])}"
              + (" …" if n > 6 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
