#!/usr/bin/env python3
"""The category is a published claim, so its accuracy is a number we hold ourselves to.

Every other figure on a dossier is derived deterministically from public evidence. The category is
not — it comes from a naive-Bayes model — and that asymmetry is invisible to a reader, so the only
honest way to carry it is to measure it and to fail when it regresses.

TWO DEFECTS THIS EXISTS TO PREVENT, both of which shipped:

1. A CATEGORY THAT CAN NEVER BE PREDICTED. `ai` scored 0/16 on held-out labels while the hub for it
   was live and linked from every dossier that landed there. Two causes, found separately:
   the STOP list deleted `ai`, `agent`, `agents`, `model` and `context` as "generic", which is every
   discriminative word the class had — no other category had its own name stopped; and plain
   multinomial NB collapses toward whichever classes have the broadest vocabulary, because a class
   that has seen some count of nearly any word beats the smoothing floor a narrow class pays. Zero
   recall is a bug, not a tuning preference, so it fails here.

2. COLLAPSE INTO TWO BUCKETS. 40% of the board was `productivity` and 27% `devtools` — 67% of a
   15-category taxonomy in two shelves, with more browser-ish rows misfiled inside `productivity`
   (83) than the entire `browser` category held (32). A taxonomy that concentrates like that is not
   sorting anything.

MACRO, NOT MICRO. Overall accuracy is dominated by the two largest classes: a model that predicts
`productivity` and `devtools` for everything and nothing else would score respectably and be
worthless for browsing. Mean per-category recall is the number that reflects what a category hub
needs, so that is the one with a floor under it.

The floors are deliberately BELOW measured performance — they catch regressions, they do not certify
the model as good. It is not good; see the note at the bottom.

Run: python3 tests/test_classify.py
"""
import collections, hashlib, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import build, classify

# Measured 31 Jul 2026 with complement NB + the two feature fixes: macro 59.8%, micro 60.8%.
# Before those changes: macro 51.7%, micro 58.7%, with `ai` at 0/16.
# 3 Aug 2026, adding gh_topics as a feature: macro 62.2%, micro 62.9%. Topics are human-assigned
# repo labels ("database", "browser-automation"), present on 42% of the training set but only 10% of
# the corpus — so it lifts held-out accuracy without moving board concentration at all. Biggest
# movers: data 43.5%->65.2%, security 64.3%->78.6%. `ai` stayed 2/17, still the worst of the fifteen.
# The floors keep their deliberate slack rather than being ratcheted to the new measurement: the
# corpus grows daily, and a floor set at today's value fails tomorrow on drift rather than on a
# regression. CONCENTRATION_CEIL below is the one that sits AT its measured value, on purpose.
MACRO_FLOOR = 0.55
MICRO_FLOOR = 0.57

# A RATCHET, NOT A PASS MARK. 61% of the board in two of fifteen shelves is bad; the number is here
# at the measured value so it can only go down, and it is the honest record of where this stands.
# A taxonomy that sorts would be nearer 40%. Getting there is a decision about the taxonomy itself —
# `productivity` is a residual bucket, and in a corpus where every row is an AI tool `ai` is barely
# discriminative (11.8% recall, the worst of the fifteen) — not a threshold to tune.
#
# 3 Aug 2026 — WHERE THE CONCENTRATION ACTUALLY COMES FROM, measured per artifact kind:
#     plugin  n=3,627  74.8%      skill  n=518  79.5%
#     npm     n=1,378  32.3%      remote n=364  29.9%
# The classifier sorts MCP servers to ~30%, comfortably past the 40% this comment calls "a taxonomy
# that sorts". Every point of the breach comes from plugins and skills — 70% of the board — which are
# overwhelmingly "helps you write code" or "helps you work", and the fifteen shelves have nothing
# that separates them from each other. So this is NOT a classifier defect and cannot be fixed by
# better features: adding gh_topics lifted held-out accuracy 1.4pp and moved concentration by zero.
# It is the corpus composition shifting toward plugins faster than the taxonomy was designed for.
# The runner, whose corpus is fresher than any laptop's, reads 63.0% and is red on this line.
# Re-basing the ceiling is the owner's call and must come with the shelf change that earns it.
#
# 5 Aug 2026 — 65.4% -> 32.8%, AND THIS ONE IS REAL. The cause was never the taxonomy. Training data
# is hand-labelled rows PLUS the plugin author's own declared category, and the declared half had
# grown to 1,400 of 2,157 rows (65%) as plugin ingestion scaled. Authors overwhelmingly write
# "development" or "productivity": declared labels alone sit at 69.4% top-2 concentration against
# 23.4% for the hand set. The model was learning the authors' bias, not the taxonomy — macro recall
# fell through its floor to 52.8% and board concentration hit 65.4%.
#
# classify.DECL_CAP now caps declared labels at 80 per class. Swept against a FIXED held-out set of
# 152 hand-labelled rows (the earlier sweep was meaningless: varying the cap changed the test set too):
#     uncapped  macro 57.9%  micro 53.9%   655 declared rows
#     cap 80    macro 62.4%  micro 57.2%   207 declared rows   <- chosen
#     cap 300   macro 59.1%  micro 54.6%   460 declared rows
# +4.5pp macro recall from using LESS data. On the full corpus: macro 65.0%, and `other` FELL from
# 13.3% to 5.5%, so this is sorting rather than the abstention that flattered the number yesterday.
# Per kind, the actual problem halved: plugin 74.8% -> 40.5%, skill 67.9% -> 40.8%.
#
# Ratcheted 62% -> 45%, not to the measured 32.8%. The cap makes this stable against corpus growth
# (declared labels can no longer swamp anything), but 4,684 npm packages are still unenriched and will
# land real categories as they go; 45% locks in most of the gain without failing on ordinary drift.
# Tighten it once enrichment has settled.
CONCENTRATION_CEIL = 0.45

fail = 0


def ok(name, cond, detail=""):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  — " + detail) if detail and not cond else ""))


def held_out():
    """The same stable 80/20 split classify.evaluate() uses — md5, never hash(), which is salted."""
    con = build.db()
    try:
        gt = dict(classify.declared_labels())
        gt.update(classify.load_labels())
        rows = {r[0]: r for r in classify.rows_for(con, list(gt))}
        # [1:] not a hard-coded width: this said [1:6] and silently dropped whatever column was added
        # last, so a new feature could be added to classify.py and this suite would keep grading the
        # model WITHOUT it — reporting the old accuracy and calling the change a no-op.
        data = [(classify.features(*rows[i][1:]), c) for i, c in gt.items() if i in rows]
    finally:
        con.close()
    data.sort(key=lambda d: hashlib.md5(" ".join(d[0][:8]).encode()).hexdigest())
    cut = int(len(data) * 0.8)
    return data[:cut], data[cut:]


train, test = held_out()
model = classify.NB().fit(train)

right, total = collections.Counter(), collections.Counter()
for feats, truth in test:
    pred, _ = model.predict(feats, 0.0)
    total[truth] += 1
    if pred == truth:
        right[truth] += 1

recalls = {c: right[c] / total[c] for c in total}
macro = sum(recalls.values()) / max(1, len(recalls))
micro = sum(right.values()) / max(1, len(test))

print(f"  held-out n={len(test)} over {len(total)} categories")
ok(f"macro recall {macro*100:.1f}% >= {MACRO_FLOOR*100:.0f}% floor", macro >= MACRO_FLOOR,
   f"{macro*100:.1f}% — the small categories have collapsed again")
ok(f"micro accuracy {micro*100:.1f}% >= {MICRO_FLOOR*100:.0f}% floor", micro >= MICRO_FLOOR,
   f"{micro*100:.1f}%")

# A category with a live hub that the model never predicts is a page that can only ever be wrong.
dead = sorted(c for c, r in recalls.items() if r == 0 and total[c] >= 5)
ok("no category with >=5 held-out examples has zero recall", not dead,
   ", ".join(f"{c} 0/{total[c]}" for c in dead) + " — see the ai/STOP defect in this file's docstring")

# Whatever the model is, it must not shovel the corpus into two shelves.
import json
export = json.load(open(os.path.join(ROOT, "web", "data", "capabilities.json")))
caps = export["capabilities"] if isinstance(export, dict) else export
# TWO DISTINCT FAILURES, TWO DISTINCT CHECKS — and this was one check doing both jobs badly.
#
# Concentration asks "are the shelves being used". Abstention asks "how often do we decline to
# sort at all". They were conflated because `other` was the sink for both, so when the classifier
# gained a calibrated abstain threshold (NB.predict: 60.3% of labels were wrong before it) the
# ratchet fired at 47.3% — not because the taxonomy stopped sorting, but because 37.8% of rows now
# honestly say "we do not know".
#
# Splitting them is STRICTER, not laxer. Concentration is now measured over the rows we actually
# categorise, so it can no longer be diluted by abstaining; and the abstention rate is bounded
# separately, so a broken model cannot pass by declining to answer.
dist = collections.Counter(c.get("category") or "(none)" for c in caps)
ABSTAIN_CEIL = 0.42
abstained = sum(1 for c in caps if not c.get("category_basis"))
rate = abstained / max(1, len(caps))
ok(f"the classifier abstains on {rate*100:.1f}% of rows, under the {ABSTAIN_CEIL*100:.0f}% ceiling",
   rate <= ABSTAIN_CEIL,
   f"{abstained:,} of {len(caps):,} rows carry no category basis — either the threshold "
   f"(CLASSIFY_MARGIN) is too high or the model has stopped discriminating")

sorted_caps = [c for c in caps if c.get("category_basis")]
sdist = collections.Counter(c.get("category") or "(none)" for c in sorted_caps)
top2 = sum(v for _, v in sdist.most_common(2)) / max(1, sum(sdist.values()))
ok(f"the two largest categories hold {top2*100:.1f}% of what we DO categorise, under the "
   f"{CONCENTRATION_CEIL*100:.0f}% ceiling", top2 <= CONCENTRATION_CEIL,
   f"{top2*100:.1f}% in {', '.join(c for c, _ in sdist.most_common(2))} — the taxonomy is not sorting")

# Every category the site renders must be one the model can actually emit, or the hub is unreachable.
valid = set(classify.VALID)
shown = {c["id"] for c in json.load(
    open(os.path.join(ROOT, "web", "data", "categories.json")))["categories"]}
ok("the taxonomy the site renders matches the one the classifier writes", shown == valid,
   f"site-only: {sorted(shown - valid)}  classifier-only: {sorted(valid - shown)}")

print("\n  per-category recall:")
for c in sorted(total, key=lambda c: -total[c]):
    print(f"    {c:14} {right[c]:3}/{total[c]:3}  {recalls[c]*100:5.1f}%")

print()
print("  NOTE: ~61% is not good enough to present as measurement, and these floors do not say")
print("  otherwise. The real fix is the LLM classification path (classify_prep.py ->")
print("  merge_categories.py); this model is the stopgap that keeps the hubs populated meanwhile.")

print("CLASSIFY FAILED" if fail else "ok — classifier (macro recall, no dead category, no collapse)")
sys.exit(fail)
