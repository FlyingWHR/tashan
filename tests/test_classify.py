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
# 4 Aug 2026 — NOW 53.0%, AND THAT IS NOT A WIN. Nothing about the taxonomy changed. npm discovery
# added ~5,000 packages the classifier does not recognise, so it ABSTAINED on them: `other` went from
# 3.0% of the board (176 rows) to 13.3% (981). Diluting two big shelves with a third big shelf called
# "we don't know" lowers this number without sorting anything, which is precisely the weakness noted
# in the competing directory studied on 3 Aug — its MCP top-2 is 34.6% and its LARGEST single shelf
# is "Other" at 18.2%.
#
# Per-kind, unchanged where it matters: plugin 74.8%, skill 67.9%, npm 38.7%, remote 30.1%. Plugins
# are still the problem and still have no shelves that separate them.
#
# DELIBERATELY NOT RATCHETED to 53%. 4,684 discovered npm packages are still unenriched; each gets
# real signal — and a real category — as enrichment reaches it, so `other` will shrink and this number
# will climb again. Ratcheting a transient mid-flight value would guarantee a red build for a change
# nobody made. Re-measure once enrichment has caught up, then set it at whatever it honestly is.
CONCENTRATION_CEIL = 0.62

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
dist = collections.Counter(c.get("category") or "(none)" for c in caps)
top2 = sum(v for _, v in dist.most_common(2)) / max(1, sum(dist.values()))
ok(f"the two largest categories hold {top2*100:.1f}% of the board, under the {CONCENTRATION_CEIL*100:.0f}% ceiling",
   top2 <= CONCENTRATION_CEIL,
   f"{top2*100:.1f}% in {', '.join(c for c, _ in dist.most_common(2))} — the taxonomy is not sorting")

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
