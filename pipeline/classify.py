#!/usr/bin/env python3
"""tashan — categorise every capability, and be able to say how often it is right.

WHY THIS REPLACES THE REGEX CLASSIFIER
The hand-written rules abstained on 75% of the corpus. "Other" at that rate is not a classification, it
is a refusal, and it left category hubs — the whole browse-by-job surface — nearly empty. Worse, the
rules had no accuracy number attached, so every change was an opinion.

This is a small multinomial naive-Bayes trained on the 757 capabilities that were hand-labelled into
data/classify/cat_*.json. That file set stops being a one-off backfill and becomes a training set and a
regression suite: `--eval` holds out a fifth of it and reports accuracy per category, so any future
change to features, priors or the abstain threshold is measured rather than argued about.

Stdlib only, deterministic (fixed shuffle seed), no API key, ~2s over 12k rows.

    python3 pipeline/classify.py --eval        # accuracy on held-out labels, changes nothing
    python3 pipeline/classify.py --dry-run     # show the distribution it would write
    python3 pipeline/classify.py               # classify + re-export
    python3 pipeline/classify.py --all         # re-classify everything, not just uncategorised
"""
import collections, glob, hashlib, json, math, os, re, sys
import build

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALID = {"browser", "search", "database", "devtools", "cloud", "files", "data", "docs",
         "comms", "design", "ai", "finance", "productivity", "security", "other"}

# Words that appear across every category and carry no signal. Left in, they dominate the likelihoods
# ("mcp" and "server" occur in nearly every description) and everything collapses toward the largest class.
STOP = set("""a an the and or of for to in on with your you our this that it its is are be as at by from
into over via using use used uses can will not no any all more most other others new get set add
mcp server servers claude code agent agents ai tool tools skill skills plugin plugins model context
protocol api apis service services support supports provide provides provided allow allows enable
enables integration integrations access simple easy powerful advanced comprehensive various multiple
your their them then than when where which who what how why also just only very well best good
run runs running work works working make makes made create creates creating build builds building
""".split())

# ...but six of those "generic" words are the ONLY discriminative vocabulary the `ai` category has.
# `ai`, `agent`, `agents`, `model`, `context` and `protocol` were all stopped, so the one class whose
# subject IS agents had every feature naming its subject deleted before training — and scored 0/13
# recall on held-out labels while every other category kept its own name as a feature. A word being
# common is not a reason to stop it if it is also the thing a category is about; that is precisely
# the word you need. Boilerplate every MCP server says ("mcp", "server", "protocol" in the sense of
# "Model Context Protocol") still goes, but not the ones that carry topic.
KEEP = set("ai agent agents model context memory".split())
# Two-letter tokens worth keeping — each one names what some category is about.
SHORT = set("ai ml db bi ci qa s3 3d ui ux vm k8s api".split())
STOP -= KEEP

TOKEN = re.compile(r"[a-z][a-z0-9+#.]{1,}")


NAME_W = int(os.environ.get("CLASSIFY_NAME_W", "1"))   # swept: 1 beats 3 and 5 on the stable split
BINARY = os.environ.get("CLASSIFY_BINARY", "1") == "1"  # de-duplicating tokens is worth ~6 points

def features(name, title, desc, pkg=None, repo=None, topics=None):
    """Name weighting is swept, not assumed — measured best at 1x. An earlier sweep favoured 3x, but
    that comparison ran on a per-process-salted split and was noise.
    Package scope and repo owner are included because vendor identity is a strong category signal
    ("@supabase/..." is a database, "vercel/..." is cloud) and they were being thrown away.
    BINARY collapses repeated words to one occurrence — otherwise a description that says "data" six
    times outvotes a name that says it once."""
    def toks(s):
        # `len(t) > 2` silently dropped "ai" — two characters — so freeing it from STOP changed
        # nothing and the ai category still scored 0/16. Short tokens are mostly noise, but a handful
        # of them are the most discriminative words a category has, and every one of those is a
        # category's own subject: ai, ml, db, s3, 3d, ci, qa, bi. Keep those, drop the rest.
        return [t for t in TOKEN.findall((s or "").lower().replace("_", "-").replace("/", "-").replace("-", " "))
                if t not in STOP and (len(t) > 2 or t in SHORT)]
    body = toks(title) + toks(desc) + toks(pkg) + toks(repo) + toks(topics)
    if BINARY:
        body = list(dict.fromkeys(body))
    return toks(name) * NAME_W + body


class NB:
    # Swept, like NAME_W and BINARY — see fit_complement for why the default flipped.
    complement = os.environ.get("CLASSIFY_CNB", "1") == "1"

    def __init__(self):
        self.logprior = {}
        self.loglik = {}
        self.vocab = set()

    def fit(self, samples):
        if self.complement:
            return self.fit_complement(samples)
        by_cat = collections.defaultdict(collections.Counter)
        n_cat = collections.Counter()
        for feats, cat in samples:
            n_cat[cat] += 1
            by_cat[cat].update(feats)
            self.vocab.update(feats)
        total = sum(n_cat.values())
        V = len(self.vocab) or 1
        # UNIFORM priors by default. The training set is dominated by two classes (declared labels
        # skew "development" and "productivity"), and with empirical priors the model pushed 72% of the
        # whole corpus into those two while ai/files/browser scored 0% recall. A prior that reflects our
        # labelling effort is not evidence about the world.
        uniform = os.environ.get("CLASSIFY_UNIFORM", "1") == "1"
        for cat, cnt in by_cat.items():
            denom = sum(cnt.values()) + V
            self.logprior[cat] = 0.0 if uniform else math.log(n_cat[cat] / total)
            self.loglik[cat] = {w: math.log((cnt[w] + 1) / denom) for w in self.vocab}
            self.loglik[cat]["__unseen__"] = math.log(1 / denom)
        return self

    def fit_complement(self, samples):
        """Complement Naive Bayes (Rennie et al. 2003), because plain multinomial NB collapses here.

        THE MECHANISM, since "try a different model" is not a reason. MNB scores a document as
        sum(log P(w|c)). A class trained on a BROAD vocabulary has seen some count of nearly any word,
        so it pays log((n+1)/denom); a narrow class pays the smoothing floor log(1/denom) for the same
        word. With 757 training docs the vocabulary is far larger than any class's token total, so the
        broad class wins by a fixed margin on EVERY word it happens to have seen, multiplied by
        document length. That is why `productivity` and `devtools` took 67% of the corpus while `ai`
        scored 0/16 recall — not because those documents look like productivity, but because those two
        classes had seen more words. Uniform priors do not touch this: the bias is in the likelihoods.

        CNB estimates each class's weights from every OTHER class's counts, which inverts the asymmetry
        (a broad class now makes its COMPLEMENT broad), then normalises the weight vectors so no class
        can win on magnitude alone. Lowest complement score wins, so scores() negates to keep one
        "higher is better" convention for predict().
        """
        by_cat = collections.defaultdict(collections.Counter)
        for feats, cat in samples:
            by_cat[cat].update(feats)
            self.vocab.update(feats)
        V = len(self.vocab) or 1
        total = collections.Counter()
        for cnt in by_cat.values():
            total.update(cnt)
        grand = sum(total.values())

        for cat, cnt in by_cat.items():
            own = sum(cnt.values())
            denom = (grand - own) + V              # every token NOT in this class, smoothed
            w = {t: math.log((total[t] - cnt[t] + 1) / denom) for t in self.vocab}
            # Weight normalisation (the "WCNB" of the paper). Without it a class whose complement is
            # large still carries systematically bigger magnitudes and the collapse comes back wearing
            # the other sign.
            norm = sum(abs(x) for x in w.values()) or 1.0
            self.loglik[cat] = {t: x / norm for t, x in w.items()}
            self.loglik[cat]["__unseen__"] = math.log(1 / denom) / norm
            self.logprior[cat] = 0.0
        return self

    def scores(self, feats):
        out = {}
        for cat in self.logprior:
            ll = self.loglik[cat]
            unseen = ll["__unseen__"]
            s = self.logprior[cat] + sum(ll.get(w, unseen) for w in feats if w in self.vocab)
            out[cat] = -s if self.complement else s      # CNB: least complement-like wins
        return out

    def predict(self, feats, margin=0.0):
        """Abstain to 'other' when the top two classes are too close to call.

        THE CONFIDENCE MUST BE SCALE-FREE, AND FOR A LONG TIME IT WAS NOT — which is why abstention
        was switched off and 40% of every category on the site was wrong.

        WCNB divides each weight by the sum of |weights| over the WHOLE vocabulary, so one term
        contributes about 1/V and a document of three in-vocab words scores ~0.0005. The old code
        returned `top - second` from those raw scores: across the entire held-out set the maximum gap
        was 0.001 and the median was 0.000, so ANY threshold above zero abstained on everything
        (margin 2.0 → 193 of 209) and the only usable setting was 0, meaning never abstain. A softmax
        does not rescue it either — the posteriors come out at 0.0667 each, exactly uniform over 15
        classes. The ranking was fine the whole time; only its magnitude was meaningless.

        So confidence is the margin as a FRACTION of the score range across the classes. That is
        scale-free, and measured against held-out labels it is a real signal:

            threshold   coverage   accuracy of what is kept
              0.00        100%        60.3%      <- what shipped
              0.30         70%        71.2%
              0.40         62%        77.5%
              0.50         50%        83.8%

        Returns (label, relative_margin) where relative_margin is 0..1.
        """
        if not feats:
            return "other", 0.0
        s = self.scores(feats)
        if not s:
            return "other", 0.0
        rank = sorted(s.items(), key=lambda kv: -kv[1])
        if len(rank) < 2:
            return rank[0][0], 1.0
        spread = rank[0][1] - rank[-1][1]
        rel = (rank[0][1] - rank[1][1]) / spread if spread > 0 else 0.0
        return (rank[0][0] if rel >= margin else "other"), rel


# The author's own declared category from .claude-plugin/marketplace.json. 1,361 plugins carry one
# across a 136-value vocabulary; mapping the common terms into our 15 more than doubles the training
# set with labels a human actually chose. Only unambiguous terms are mapped — anything vague ("core",
# "patterns", "misc") is left out rather than guessed, because bad labels poison the model.
DECLARED = {
    "development": "devtools", "developer tools": "devtools", "developer-tools": "devtools",
    "devops": "cloud", "deployment": "cloud", "cloud": "cloud", "infrastructure": "cloud",
    "testing": "devtools", "code-quality": "devtools", "git": "devtools", "ci": "devtools",
    "productivity": "productivity", "workflow": "productivity", "workflow-pack": "productivity",
    "product-management": "productivity", "project-management": "productivity", "planning": "productivity",
    "security": "security", "email-security": "security", "compliance": "security", "privacy": "security",
    "database": "database", "data": "data", "analytics": "data", "monitoring": "data",
    "observability": "data", "reporting": "data",
    "design": "design", "ui": "design", "ux": "design", "accessibility": "design", "frontend": "design",
    "documentation": "docs", "docs": "docs", "content": "docs", "writing": "docs",
    "ai": "ai", "llm": "ai", "machine-learning": "ai", "agents": "ai",
    "research": "search", "search": "search",
    "marketing": "comms", "communication": "comms", "email": "comms", "social": "comms", "sales": "comms",
    "finance": "finance", "payments": "finance", "legal": "other",
    "browser": "browser", "automation": "devtools", "files": "files", "storage": "files",
}


def declared_labels():
    """Extra training rows from plugin manifests, keyed by the same id ingest_plugins.py writes."""
    import re as _re
    path = os.path.join(ROOT, "data", "plugins_cache.json")
    if not os.path.exists(path):
        return {}
    try:
        cache = json.load(open(path))
    except Exception:
        return {}
    out = {}
    for k, v in cache.items():
        if not k.startswith("man:"):
            continue
        repo = k[4:]
        try:
            m = json.loads(v)
        except Exception:
            continue
        for pl in (m.get("plugins") or []):
            cat = DECLARED.get((pl.get("category") or "").strip().lower())
            if cat and pl.get("name"):
                cid = "plugin:" + repo.lower() + "/" + _re.sub(r"[^a-z0-9]+", "-", str(pl["name"]).lower()).strip("-")
                out[cid] = cat

    # CAP PER CLASS. These are the plugin AUTHOR'S OWN category, and authors overwhelmingly write
    # "development" or "productivity": declared labels alone sit at 69.4% top-2 concentration against
    # 23.4% for the hand-labelled set. Uncapped they became 1,400 of 2,157 training rows — 65% — so
    # the model was learning the authors' bias rather than the taxonomy, and it showed exactly where
    # you would expect: macro recall fell through its floor to 52.8% and board concentration climbed
    # to 65.4% as plugin ingestion grew.
    #
    # They are still worth having: they are free, attributable, and they cover vocabulary the hand set
    # never sees. Capped, they supplement the balanced set instead of drowning it. DECL_CAP is swept
    # against held-out macro/micro in --eval, not chosen by feel.
    cap = int(os.environ.get("DECL_CAP", "80"))
    if cap > 0:
        kept, per = {}, collections.Counter()
        # deterministic: sort by id so a re-run keeps the same subset and the eval is reproducible
        for cid in sorted(out):
            c = out[cid]
            if per[c] < cap:
                kept[cid] = c
                per[c] += 1
        out = kept
    return out


# NOTE: a regex pre-filter was tried here as a "high-precision first stage" and MEASURED WORSE —
# 54.7% vs 56.5% for the model alone. The intuition that hand-written rules are more precise than a
# trained model did not survive the held-out set, so the stage was deleted rather than kept because it
# sounded reasonable. If you are tempted to add one back, run --eval first.


def load_labels():
    gt = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "classify", "cat_*.json"))):
        for r in json.load(open(f)):
            c = (r.get("category") or "other").strip().lower()
            gt[r["id"]] = c if c in VALID else "other"
    return gt


def rows_for(con, ids=None):
    q = "SELECT id, name, title, description, npm_pkg, source_repo, gh_topics FROM capabilities"
    if ids:
        q += " WHERE id IN (%s)" % ",".join("?" * len(ids))
        return con.execute(q, list(ids)).fetchall()
    return con.execute(q).fetchall()


def evaluate(con, margin):
    gt = dict(declared_labels()); gt.update(load_labels())   # hand labels override declared ones
    rows = {r[0]: r for r in rows_for(con, list(gt))}
    data = [(features(*rows[i][1:7]), c, rows[i][1]) for i, c in gt.items() if i in rows]
    # STABLE 80/20 split. Python's hash() on str is salted per process (PYTHONHASHSEED), so an earlier
    # version of this line reshuffled the split on every run and the "accuracy deltas" it produced were
    # partly noise. md5 is stable across processes, which is the whole point of a regression suite.
    data.sort(key=lambda d: hashlib.md5(" ".join(d[0][:8]).encode()).hexdigest())
    cut = int(len(data) * 0.8)
    train, test = data[:cut], data[cut:]
    m = NB().fit([(f, c) for f, c, _ in train])
    right = collections.Counter(); total = collections.Counter(); abstain = 0
    for feats, truth, nm in test:
        pred, _ = m.predict(feats, margin)
        total[truth] += 1
        if pred == truth:
            right[truth] += 1
        if pred == "other" and truth != "other":
            abstain += 1
    acc = sum(right.values()) / max(1, len(test))
    return acc, abstain, len(test), right, total


def main():
    con = build.db()
    margin = float(os.environ.get("CLASSIFY_MARGIN", "0.20"))   # RELATIVE, 0..1 — see NB.predict

    if "--eval" in sys.argv:
        print(f"training on data/classify/cat_*.json  (margin={margin})")
        for mg in (0.0, 0.2, 0.3, 0.4, 0.5):
            acc, ab, n, right, total = evaluate(con, mg)
            print(f"  margin {mg:5.1f}   accuracy {acc*100:5.1f}%   wrongly-abstained {ab:3}/{n}")
        acc, ab, n, right, total = evaluate(con, margin)
        print(f"\nper-category recall at margin={margin} (held-out n={n}):")
        for cat in sorted(total, key=lambda c: -total[c]):
            print(f"  {cat:14} {right[cat]:3}/{total[cat]:3}  {100*right[cat]/total[cat]:5.1f}%")
        con.close(); return 0

    gt = dict(declared_labels()); gt.update(load_labels())
    train = [(features(*r[1:7]), gt[r[0]])
             for r in rows_for(con, list(gt)) if r[0] in gt]
    model = NB().fit(train)
    print(f"trained on {len(train)} labelled capabilities")

    where = "" if "--all" in sys.argv else " WHERE category IS NULL OR category=''"
    rows = con.execute("SELECT id, name, title, description, npm_pkg, source_repo, gh_topics FROM capabilities" + where).fetchall()
    tally, samples = collections.Counter(), collections.defaultdict(list)
    dry = "--dry-run" in sys.argv
    for cid, name, title, desc, pkg, repo, topics in rows:
        cat, conf = model.predict(features(name, title, desc, pkg, repo, topics), margin)
        # hand labels always win over the model, and are not subject to its threshold
        basis = "model" if cat != "other" else None
        if cid in gt:
            cat, basis, conf = gt[cid], "declared", 1.0
        tally[cat] += 1
        if len(samples[cat]) < 4:
            samples[cat].append((name or "")[:24])
        if not dry:
            # RECORDED, NOT JUST DECIDED. Without the basis a reader — and every generator — cannot
            # tell the author's own word from a coin-flip the model won by a hair.
            con.execute("UPDATE capabilities SET category=?, category_basis=?, category_conf=? "
                        "WHERE id=?", (cat, basis, round(conf, 4), cid))
    if not dry:
        con.commit()
    print(f"{'would classify' if dry else 'classified'} {len(rows)} capabilities")
    for cat, n in tally.most_common():
        print(f"  {cat:14} {n:5}  ({100*n/max(1,len(rows)):4.1f}%)   e.g. {', '.join(samples[cat])[:70]}")
    if not dry:
        build.export(con)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
