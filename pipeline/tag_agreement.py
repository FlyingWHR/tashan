#!/usr/bin/env python3
"""tashan — how much do two independent graders agree, and is the taxonomy converging?

WHY THIS EXISTS. Everything measured about the task axis so far compared labels to a reference written
by the same author, which proves consistency and nothing about correctness. `--eval` in
tag_capabilities.py is explicitly that: inter-rater agreement against an unvalidated reference. This
scores two genuinely independent gradings of the SAME rows, which is the only honest read available
without ground truth nobody has.

    python3 pipeline/tag_agreement.py

Inputs (both must cover the same capability ids):
  data/tags/round1_for_agreement.json   the production labels for a sampled slice
  data/tags/round2_blind.json           a second grader, told not to look at round 1

WHAT THE NUMBERS MEAN, because it is easy to over-read them:
  - EXACT      both graders produced the identical tag set. A harsh bar for a multi-label judgement:
               a capability genuinely does several jobs, so one grader adding a defensible fourth tag
               scores as total disagreement.
  - JACCARD    overlap / union, averaged per row. The honest headline for multi-label work.
  - ANY        the two sets share at least one tag. "Would a reader land in the right neighbourhood."
  - EMPTY      do they agree on the hard call — that a capability serves no single job (R3/R4)?
               Disagreement here usually means the bundle rule is being read differently.

CONVERGENCE is the trend across rounds, not a threshold. If Jaccard rises as the rubric is tightened and
the taxonomy's gaps are filled, the axis is settling; if it plateaus well below 1, what remains is
genuine ambiguity in the work itself, and the fix is a clearer task definition, not more grading.
Per-task disagreement below points at exactly which definitions are doing the damage.
"""
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R1 = os.path.join(ROOT, "data", "tags", "round1_for_agreement.json")
R2 = os.path.join(ROOT, "data", "tags", "round2_blind.json")


def load(path):
    if not os.path.exists(path):
        return None
    return {k: set(v) for k, v in json.load(open(path)).items() if not k.startswith("_")}


def main():
    a, b = load(R1), load(R2)
    if a is None or b is None:
        print("need both %s and %s" % (os.path.basename(R1), os.path.basename(R2)))
        return 1
    keys = sorted(set(a) & set(b))
    if not keys:
        print("no overlapping ids to compare")
        return 1

    exact = anyshare = both_empty = 0
    jac_total = 0.0
    disagree = collections.Counter()      # tag -> times one grader used it and the other did not
    pairs = []
    for k in keys:
        x, y = a[k], b[k]
        if x == y:
            exact += 1
        if x & y:
            anyshare += 1
        if not x and not y:
            both_empty += 1
        union = x | y
        jac_total += (len(x & y) / len(union)) if union else 1.0
        for t in x ^ y:
            disagree[t] += 1
        if x != y:
            pairs.append((k, sorted(x), sorted(y)))

    n = len(keys)
    empt_a = sum(1 for k in keys if not a[k])
    empt_b = sum(1 for k in keys if not b[k])
    print(f"two independent gradings of the same {n} capabilities\n")
    print(f"  exact set match      {exact:4}/{n}  {100*exact/n:5.1f}%   (harsh bar for multi-label)")
    print(f"  mean Jaccard         {jac_total/n:.3f}          <- the headline")
    print(f"  share >=1 tag        {anyshare:4}/{n}  {100*anyshare/n:5.1f}%   (right neighbourhood)")
    print(f"  empty calls          grader A {empt_a}, grader B {empt_b}, agreed on {both_empty}")

    print("\ntags that most often appear for one grader but not the other")
    print("(a task definition doing damage shows up here first):")
    for tag, c in disagree.most_common(12):
        print(f"  {tag:32} {c:3}")

    print("\nsample disagreements:")
    for k, x, y in pairs[:8]:
        print(f"  {k.split('/')[-1][:30]:32} A={x}  B={y}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
