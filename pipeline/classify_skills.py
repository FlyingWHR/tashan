#!/usr/bin/env python3
"""tashan — assign categories to skills so they live in the same taxonomy as everything else.

A user browsing "Docs & Knowledge" wants every capability that does that job — an MCP server that reads
Confluence AND a skill that writes docx. Leaving skills uncategorised kept them out of every category
hub, which is the silo problem wearing a different hat.

WHY A HEURISTIC AND NOT AN LLM: skill names and descriptions in SKILL.md are unusually literal
("pdf", "frontend-design", "security-audit", "postgres-expert"), so keyword routing over name +
description is accurate enough to be useful and — unlike a model call — is deterministic, free, and
reviewable line by line. It is explicitly the weaker method: `merge_categories.py` (LLM-graded) wins on
any capability it covers, and this only fills what that hasn't reached. Rules are ordered most-specific
first; anything that matches nothing lands in `other` rather than being guessed at.

    python3 pipeline/classify_skills.py [--dry-run]
"""
import os, re, sys
import build

# Matched against the NAME only. The first attempt matched name+description and was badly wrong —
# `pdf` landed in security, `docx` in design, `xlsx` in database, and 379 skills fell into "search" —
# because loose patterns hit incidental words in prose (`auth[on]` matches "co-authoring", which is
# exactly how doc-coauthoring became a security skill). SKILL.md names are literal, so the name is the
# high-precision signal and the description is noise for this purpose.
#
# Anything that doesn't match confidently stays `other` — an honest "unsorted" beats a confident wrong
# shelf, and `other` is the queue for LLM classification (merge_categories.py), which supersedes this.
RULES = [
    ("files",        r"^(pdf|docx?|xlsx?|csv|pptx?|file|folder|zip|archive|backup|dropbox|gdrive|s3)\b|"
                     r"\b(file-|folder-|filesystem|storage|compress|rename-|organi[sz]e-files)"),
    ("security",     r"\b(security|vulnerab|owasp|pentest|cve|threat-model|secrets?-|credential|encrypt|"
                     r"compliance|gdpr|soc2|sast|malware|sandbox|permission|redact)"),
    ("database",     r"\b(sql|postgres|mysql|sqlite|mongo|redis|supabase|prisma|drizzle|database|db-|"
                     r"schema|migration)"),
    ("browser",      r"\b(browser|playwright|puppeteer|selenium|scrap|crawl|headless|webapp-test|e2e)"),
    ("search",       r"\b(search|retrieval|rag|embedding|vector|semantic)-|^(search|rag)\b"),
    ("cloud",        r"\b(aws|gcp|azure|kubernetes|k8s|docker|terraform|deploy|infra|serverless|"
                     r"cloudflare|vercel|netlify|helm|devops|sre)\b"),
    ("comms",        r"\b(slack|email|gmail|discord|telegram|whatsapp|chat|notification|crm|salesforce|"
                     r"hubspot|outreach|newsletter|comms)\b"),
    ("finance",      r"\b(financ|invoice|accounting|tax|payment|stripe|billing|crypto|trading|stock|"
                     r"budget|payroll|revenue|pricing|cfo|investment)"),
    ("design",       r"\b(design|figma|ui|ux|css|tailwind|animation|brand|logo|icon|color|typograph|"
                     r"layout|image|video|3d|render|sprite|canvas|slide|presentation|art)\b"),
    ("docs",         r"\b(docs?|documentation|readme|writing|write|markdown|knowledge|wiki|notes?|"
                     r"summar|citation|changelog|tutorial|blog)\b"),
    ("data",         r"\b(data|analytic|dashboard|etl|excel|spreadsheet|chart|visuali[sz]|metric|"
                     r"statistic|pandas|dataset|scraping|report)\b"),
    ("ai",           r"\b(llm|prompt|agent|subagent|model|eval|openai|anthropic|claude|gpt|inference|"
                     r"context|memory|mcp|skill)\b"),
    ("productivity", r"\b(task|todo|calendar|schedul|project|jira|linear|notion|workflow|planning|plan|"
                     r"meeting|okr|standup|habit|productivity)\b"),
    ("devtools",     r"\b(git|github|gitlab|ci|cd|lint|test|debug|refactor|review|compil|build|"
                     r"typescript|javascript|python|rust|golang|java|ruby|php|swift|kotlin|api|sdk|"
                     r"framework|codebase|repo|commit|architect|engineer|developer|expert|pro)\b"),
]


def classify(name, desc):
    """Name-anchored. `desc` is accepted for signature stability but deliberately unused — including it
    is what produced the wrong shelves above."""
    hay = re.sub(r"[_/]", "-", (name or "").lower())
    for cat, pat in RULES:
        if re.search(pat, hay):
            return cat
    return "other"


def main():
    dry = "--dry-run" in sys.argv
    con = build.db()
    rows = con.execute("SELECT id, name, title, description FROM capabilities "
                       "WHERE kind='skill' AND (category IS NULL OR category='')").fetchall()
    tally, samples = {}, {}
    for cid, name, title, desc in rows:
        cat = classify((name or "") + " " + (title or ""), desc)
        tally[cat] = tally.get(cat, 0) + 1
        samples.setdefault(cat, []).append(name)
        if not dry:
            con.execute("UPDATE capabilities SET category=? WHERE id=?", (cat, cid))
    if not dry:
        con.commit()
    print(f"{'would classify' if dry else 'classified'} {len(rows)} skills")
    for cat, n in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"  {cat:14} {n:4}   e.g. {', '.join(samples[cat][:4])[:78]}")
    if not dry:
        build.export(con)
    con.close()


if __name__ == "__main__":
    main()
