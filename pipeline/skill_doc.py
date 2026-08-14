#!/usr/bin/env python3
"""What a skill's own SKILL.md contains — stated as facts, never as a grade.

WHY THIS IS NOT A GRADE. 14,309 skills carry their own SKILL.md in capability_text.doc_body, and
none of them is graded: the expertise rubric is built for MCP servers and its first criterion is
per-tool documentation, which a skill structurally cannot satisfy — it is a folder of instructions
for a model, not a server exposing an interface. Applying it anyway lands skills at 2.7% `deep`
against servers' 16-20%, measuring the mismatch rather than the writing. See docs/GRADING-RUBRIC.md.

So this publishes the EVIDENCE instead of a verdict. Four checkable statements about a document:

    when   does it say WHEN the skill should be used
    stop   does it say when it should NOT be used
    ex     does it show at least two worked examples
    setup  does it cover setup or prerequisites
    limit  does it state a limitation

Facts need no shared vocabulary, so they cannot be misread as comparable to a server's grade — which
is exactly the trap a fifth verdict word would set. Measured on 250 sampled skills, the four
positive criteria run 70% / 58.8% / 65.2% / 42.8%, so this discriminates rather than marking
everything the same.

It also gives a skill dossier something measured to say. 2,775 skill pages are noindexed as thin
because a description was the only signal they carried.

    python3 pipeline/skill_doc.py            # measure every skill with a staged SKILL.md
    python3 pipeline/skill_doc.py --selftest # no DB, no network
"""
import json, os, re, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# WHEN: an explicit activation contract. Deliberately anchored — a bare "when" anywhere in 40 KB of
# prose is not a contract, and criterion (d) in the server rubric was ruined once by exactly that
# kind of unanchored match ("something always says 'doesn't'").
WHEN = re.compile(r"(?:^|\n)\s*#{1,4}\s*when to use|when to use this|use this (?:skill )?when|"
                  r"\buse when\b|triggers?\s*:|activat\w+\s+when", re.I)
STOP = re.compile(r"when not to use|do not use (?:this )?when|don'?t use (?:this )?when|"
                  r"\bnot for\b|out of scope|\bavoid (?:using )?(?:this )?when", re.I)
SETUP = re.compile(r"\b(install|prerequisite|requires?|setup|configure|env(?:ironment)? var|"
                   r"api[ _-]?key|npx|npm i|pip install|uvx)\b", re.I)
LIMIT = re.compile(r"(?:^|\n)\s*#{1,4}\s*(?:limitations?|caveats?|known issues)\b|"
                   r"\bdoes not (?:support|handle|work)\b|\bcannot\b|\bwill not\b|\bonly works\b", re.I)
FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
# An install line is not a worked example of USING the thing — the same distinction
# grade_evidence.worked_examples() already draws for servers.
INSTALL_ONLY = re.compile(r"^\s*(npm|npx|pip|uvx|brew|yarn|pnpm|docker)\b", re.I)


def measure(md):
    md = md or ""
    blocks = [b for b in FENCE.findall(md)
              if b.strip() and not INSTALL_ONLY.match(b.strip().split("\n")[0])]
    return {
        "when": bool(WHEN.search(md)),
        "stop": bool(STOP.search(md)),
        "ex": len(blocks) >= 2,
        "setup": bool(SETUP.search(md)),
        "limit": bool(LIMIT.search(md)),
    }


def sentence(m):
    """One line a reader can check against the document itself."""
    yes = []
    if m["when"]:  yes.append("says when to use it")
    if m["stop"]:  yes.append("says when not to")
    if m["ex"]:    yes.append("shows worked examples")
    if m["setup"]: yes.append("covers setup")
    if m["limit"]: yes.append("states a limitation")
    if not yes:
        return "Its SKILL.md does not say when to use it, show a worked example, cover setup, or " \
               "state a limitation."
    return "Its SKILL.md " + ", ".join(yes[:-1]) + (" and " if len(yes) > 1 else "") + yes[-1] + "."


def main():
    import build
    con = build.db()
    rows = con.execute(
        "SELECT t.cap_id, t.doc_body FROM capability_text t JOIN capabilities c ON c.id = t.cap_id "
        "WHERE t.cap_id LIKE 'skill:%' AND t.doc_source = 'skill_md' "
        "AND LENGTH(COALESCE(t.doc_body,'')) > 400").fetchall()
    n = 0
    tally = {k: 0 for k in ("when", "stop", "ex", "setup", "limit")}
    for cap_id, body in rows:
        m = measure(body)
        for k in tally:
            tally[k] += m[k]
        con.execute("UPDATE capabilities SET skill_doc=? WHERE id=?", (json.dumps(m), cap_id))
        n += 1
    con.commit()
    print(f"skill docs: measured {n:,} SKILL.md files")
    for k in ("when", "stop", "ex", "setup", "limit"):
        print(f"  {k:6} {tally[k]:6,}  {100 * tally[k] / max(1, n):5.1f}%")
    build.export(con)
    con.close()
    return 0


def _selftest():
    rich = """---\ndescription: x\n---\n# Thing\n## When to use\nUse when reviewing a PR.\n
## When not to use\nNot for greenfield work.\nInstall with `npx thing`.\n
```bash\nthing review --pr 12\n```\n```bash\nthing summarise\n```\n## Limitations\nDoes not support monorepos.\n"""
    m = measure(rich)
    assert all(m.values()), m
    assert "says when to use it" in sentence(m) and "states a limitation" in sentence(m)

    bare = "# Thing\nA skill that does things.\n"
    b = measure(bare)
    assert not any(b.values()), b
    assert "does not say when to use it" in sentence(b)

    # An install snippet alone is not a worked example — the same rule servers are held to.
    only_install = "# T\n```bash\nnpm install thing\n```\n```bash\nnpx thing\n```\n"
    assert measure(only_install)["ex"] is False, "install lines must not count as worked examples"

    # An unanchored "cannot" in prose should not manufacture a limitation... but a real one should.
    assert measure("# T\nIt cannot be used with Python 2.")["limit"] is True
    assert measure("# T\nThis is a skill.")["limit"] is False
    print("skill_doc selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
