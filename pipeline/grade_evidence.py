#!/usr/bin/env python3
"""Extract the rubric's four criteria from a README, so a grade is read off evidence not vibes.

    python3 pipeline/grade_evidence.py            # every staged, ungradeable-free capability
    python3 pipeline/grade_evidence.py <id> …     # just these
    python3 pipeline/grade_evidence.py --selftest
    python3 pipeline/grade_evidence.py --follow --emit data/readmes/scores_x.json <id> …

WHY THIS EXISTS. docs/GRADING-RUBRIC.md opens with the measurement that justifies it: six graders
applied the same bands to the same 836 READMEs and returned `deep` anywhere from 1.5% to 22.9%. The
fix already adopted was conjunctive criteria — state what a band REQUIRES so the question becomes
"does this have X, Y and Z" rather than "does this feel deep". This is the other half: extract X, Y
and Z the same way every time, so the remaining judgement is over a fixed set of facts.

It does NOT assign a grade. It reports what it found and what it could not find, and the grader
decides — including deciding that the extraction missed something, which is why every signal comes
back with the line that produced it. A tool that returned a verdict would just be a sixth grader
with the same variance and less accountability.

The four criteria, from the rubric:
  (a) per-tool or per-feature documentation
  (b) at least two worked examples with real arguments or output
  (c) setup and auth covered
  (d) at least one stated limitation, caveat or "does not do X"
`deep` requires ALL FOUR. Missing any one is `solid` at most.
"""
import hashlib, json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "data", "readmes", "manifest.json")
LINKED = os.path.join(ROOT, "data", "readmes", "linked_cache.json")

# A fenced block that is only an install line or a client-config stanza is not a worked example —
# rule 2, "a wall of badges and client-config blocks where tool docs should be" is thin.
CONFIG_ONLY = re.compile(
    r'^\s*(\{|\[|npm |npx |pnpm |yarn |bun |pip |uvx |docker |claude mcp add|export |curl -|git clone)',
    re.I)
AUTH = re.compile(r"\b(api[_ -]?key|access[_ -]?token|auth(entication|orization)?|oauth|bearer|"
                  r"credential|\.env|environment variable|personal access token|pat\b)", re.I)
# (d) A STATED LIMITATION, NOT AN INCIDENTAL NEGATION.
#
# This pattern has now been wrong in both directions, and the second failure was the instructive one.
# It first missed @notionhq/notion-mcp-server, whose README opens with "We may sunset this local MCP
# server repository… Issues and pull requests here are not actively monitored" — about as material a
# caveat as a maintainer can write — because it was hunting for the literal word "limitation".
#
# Widening it to catch bare "doesn't" / "can't" / "beta" then broke it far worse, and the breakage
# was invisible until the READMEs were read at full length instead of truncated to 14,000 chars. In
# 60 KB of prose SOMETHING always says "doesn't". toon-memory matched on a status enum ("`unverified`
# when it doesn't"), figma-console-mcp on troubleshooting copy ("Can't find the file?"), @growthbook/
# mcp on the word "beta" inside an explanation of npm dist-tags. (d) is the criterion that separates
# `deep` from `solid`, so a pattern that always fires does not grade documents — it hands out the top
# band for length. That is what took `deep` to 23 of 57.
#
# So: a limitation must be ASSERTED. Either it sits under a section that announces one, or it is
# phrased as a constraint on the capability ("does not support X", "cannot Y", "known issue") rather
# than a stray negative verb. Version words are gone entirely — "beta" is a release stage, not a
# caveat, and a project saying "beta" has told the reader nothing about what the tool won't do.
LIMIT_HEAD = re.compile(r"^#{1,6}\s*.{0,30}\b(limitation|caveat|known issue|not supported|"
                        r"restriction|constraint|gotcha|disclaimer|deprecat|breaking change|"
                        # NO TRAILING \b: the heading says "Limitations", and a word boundary after
                        # "limitation" demands a non-word character where the plural "s" actually is.
                        # Same trap for the "deprecat" prefix. It silently matched nothing.
                        r"what .{0,20}(?:doesn't|does not|can't|cannot)|out of scope)",
                        re.I | re.M)
LIMIT = re.compile(r"("
                   r"do(?:es)? not support|doesn't support|not supported|unsupported|"
                   r"no support for|does not (?:currently )?(?:work|handle|implement|provide)|"
                   # "cannot be shared", not "can't find the file?" — the bare verb form is how
                   # troubleshooting sections talk to the reader, not how a document states a limit
                   r"cannot (?:be|currently|yet)\b|can't (?:be|currently|yet)\b|"
                   r"not (?:yet )?implemented|not (?:currently )?available|only works (?:with|on|in)|"
                   r"limitation|caveat|known issue|known limitation|out of scope|"
                   r"at your own (?:risk|discretion)|no guarantee|use with caution|"
                   # "this server is deprecated" is a limitation; "`limit`: Deprecated alias" is a
                   # changelog note about one parameter. Bare "deprecat" matched six capabilities on
                   # table cells and enum labels — a deprecated argument says nothing about what the
                   # capability cannot do, which is what (d) is asking.
                   r"(?:is|are|has been|have been|now|been) deprecated|"
                   r"deprecated (?:and|in favou?r of|since|as of)|"
                   r"sunset|no longer (?:maintained|supported|actively)|"
                   r"not actively (?:monitored|maintained|supported|developed)|unmaintained|"
                   r"we (?:may|will) (?:sunset|retire|archive|stop)|"
                   r"is not (?:a |an |intended|designed|meant|suitable)"
                   r")", re.I)


def limits(md):
    """(d) — asserted constraints, plus anything under a heading that announces them.

    Returns the SENTENCE the constraint sits in, not a character window around it. The window
    version cut mid-word and mid-clause, and these strings are published verbatim in the grade note
    on the dossier — "states a limit — 'eep the default install lean'" reads as though nobody looked
    at the output, which is the one impression a measurement product cannot afford.
    """
    out = []
    for m in LIMIT.finditer(md):
        lo = max((md.rfind(c, 0, m.start()) for c in (". ", "! ", "? ", "\n", "|")), default=-1)
        hi = min((h for h in (md.find(c, m.end()) for c in (". ", "\n", " |")) if h > 0),
                 default=m.end() + 90)
        out.append(re.sub(r"\s+", " ", md[lo + 1:min(hi + 1, lo + 200)]).strip(" .|*`>#-"))
    out = [o for o in out if len(o) > 12]        # a fragment shorter than this is not a sentence
    # A HEADING PLUS WHAT IS UNDER IT. Quoting the regex match alone published `states a limit —
    # "Limitation"` for mcp-atlassian, which tells the reader nothing and looks like a truncation
    # bug. The heading proves the section exists; the first line under it says what the limit IS.
    for m in LIMIT_HEAD.finditer(md):
        body = re.sub(r"\s+", " ", md[m.end():m.end() + 160]).strip(" s:*`>#-|\n")
        head = md[m.start():md.find("\n", m.start()) if "\n" in md[m.start():] else len(md)]
        out.append((head.strip("# ") + " — " + body[:110]).strip(" —") if body else head.strip("# "))
    return out[:3]


# DOCUMENTATION THAT LIVES ONE CLICK AWAY IS STILL ITS DOCUMENTATION. chrome-devtools-mcp scored
# zero on criterion (a) because its tools are in a linked `docs/tool-reference.md` rather than
# inline — which is better practice, not worse. Grading it as undocumented would penalise the split
# AND judge a document we never read, which is the exact error this whole review exists to correct.
# We cannot see the linked file, so we do not get to say the criterion is unmet: it is UNKNOWN, and
# the grader is told to go and look.
DOCLINK = re.compile(r"\[!?\[?[^\]]{0,60}(tool|api|reference|usage|command|feature|doc)[^\]]{0,80}\]"
                     r"(?:\([^)]*\))?\]?"
                     r"\(([^)]{1,120}\.md|[^)]*?/docs?/[^)]*|https?://[^)]*(?:docs|wiki|\.io)[^)]*)\)", re.I)
MARKETING = re.compile(r"(blazing|blazingly|revolutionary|game[- ]chang|effortless|seamless|"
                       r"cutting[- ]edge|state[- ]of[- ]the[- ]art|🚀|✨|🔥)", re.I)


def follow(rec, cache):
    """Fetch the in-repo .md files this README points at for tool docs, and return them appended.

    chrome-devtools-mcp is the case that forced this. Its README documents no tools because they
    live in `docs/tool-reference.md`; read that file and the same capability goes from an unknown
    to a clean `deep` with forty tools documented. Splitting a large reference out of the README is
    good practice, and a grader that only ever reads README.md silently penalises it.

    Only in-repo `.md` paths are followed. An external docs site may well hold the tool reference
    too, but we cannot read the web at grading time, and inventing a grade for a page we did not
    open is the whole failure this file exists to prevent — those stay unverified and capped.
    """
    md, repo = rec.get("readme") or "", (rec.get("repo") or "").strip()
    m = re.search(r"(?:github\.com/)?([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", repo)
    if not m:
        return md, []
    got = []
    # THE STAGED README IS A 14,000-CHARACTER PREFIX, and 36 of the 57 capabilities in the first
    # grading queue hit that cap exactly. A prefix is not the document: tool references and
    # limitations live at the BOTTOM of a long README, so truncation reads as "documents nothing"
    # for precisely the thorough documents the top band is meant to find. Re-read the whole file.
    if len(md) >= 14000:
        for name in ("README.md", "readme.md"):
            full = _raw(m.group(1), m.group(2), name, cache)
            if full and len(full) > len(md):
                md, _ = full, got.append("README.md (full, %d chars)" % len(full))
                break
    paths = [t for t in dict.fromkeys(re.findall(r"\]\((\.{0,2}/?[\w./-]+\.md)\)", md))
             if re.search(r"tool|api|reference|usage|command|feature", t, re.I)][:3]
    for path in paths:
        txt = _raw(m.group(1), m.group(2), path, cache)
        if txt:
            got.append(path)
            md += "\n\n" + txt
    return md[:200000], got


def _raw(owner, name, path, cache):
    """One file from a GitHub repo, cached on disk so a re-grade costs no network."""
    key = f"{owner}/{name}:{path}"
    if key not in cache:
        cache[key] = ""
        for br in ("main", "master"):
            url = f"https://raw.githubusercontent.com/{owner}/{name}/{br}/{path.lstrip('./')}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "tashan"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    cache[key] = r.read().decode("utf-8", "replace"); break
            except Exception:
                pass
    return cache[key]


def blocks(md):
    """Fenced code blocks, with the language tag."""
    return re.findall(r"```([a-zA-Z0-9_+-]*)\n([\s\S]*?)```", md)


# A FILENAME IN A HEADING IS NOT A TOOL. Loosening (a) to accept prose-y headings made it accept
# anything lowercase, and the generated notes — which publish on the dossier — came out reading
# "42 tools documented (ci.yml, publish.yml, security.yml…)" for mcp-atlassian, whose repo documents
# its GitHub workflows under `###` headings, and "generate_image, balanced, quality" for mcp-image,
# where two of the three are option VALUES. A published grade whose own evidence is visibly wrong is
# worse than no grade: it tells the reader we did not look.
#
# MCP tool names are identifiers — snake_case, kebab-case or dotted. A bare English word in a heading
# ("Usage", "limit", "quality") is a section, and a token ending in a source-file extension is a file.
EXT = (".yml", ".yaml", ".json", ".md", ".ts", ".js", ".tsx", ".mjs", ".sh", ".toml", ".lock",
       ".txt", ".env", ".py", ".go", ".rs", ".html", ".css", ".xml", ".cfg", ".ini")
NOT_A_TOOL = {"mcp-server", "server-mcp", "mcp-servers", "package-json", "read-me", "node-js",
              "claude-desktop", "claude-code", "docker-compose", "quick-start", "getting-started",
              "table-of-contents", "self-hosted", "open-source", "step-by-step",
              # AN ERROR CODE IS NOT A TOOL. Servers that document their failure modes in the same
              # `code — meaning` table shape as their tools were credited for both:
              # @professional-wiki/mediawiki-mcp-server showed "6 tools documented (list-wikis,
              # not_found, permission_denied…)" — three of those six are what it returns when the
              # call FAILS. They are snake_case, so the hyphen-corroboration rule waves them
              # through, and only a name list makes them visible.
              "not_found", "permission_denied", "invalid_input", "rate_limited", "unauthorized",
              "internal_error", "bad_request", "invalid_request", "not_implemented", "forbidden",
              "timeout", "invalid_params", "server_error", "unavailable", "conflict",
              "invalid_argument", "already_exists", "failed_precondition", "out_of_range"}


# A HOSTNAME IS NOT A TOOL. `tool_shaped` accepts a dot as an identifier separator, which is right
# for `namespace.tool` and wrong for `euparliamentmonitor.com`: european-parliament-mcp-server was
# credited with 70 tools, two of which were the websites in its own header. Restricted to real TLDs
# so a genuinely dotted tool name is untouched.
# ...and enumerating error codes one at a time is the wrong shape: the set above caught
# `not_found` and `permission_denied`, and the very next run surfaced `upstream_failure`. Error
# identifiers share a small vocabulary of heads and tails, so match the SHAPE instead.
ERRORY = re.compile(r"(^|_)(error|failure|failed|denied|invalid|unknown|missing|timeout|unavailable"
                    r"|unsupported|forbidden|unauthorized|rejected|conflict)(_|$)")

HOSTNAME = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)*\.(com|org|net|io|dev|sh|ai|co|app|eu|gov|edu|me|xyz|cloud|tools)$")


def tool_shaped(tok):
    """Does this token look like a tool identifier rather than a filename, a host or an English word?"""
    t = tok.lower()
    return (not t.endswith(EXT) and t not in NOT_A_TOOL and not HOSTNAME.match(t)
            and not ERRORY.search(t)
            and bool(re.search(r"[_.]|-", t))          # identifiers carry a separator
            and not re.fullmatch(r"[a-z][a-z-]*-\d+", t)  # `brilliant-directories-60031` is an id
            and len(t) >= 5)


def corroborated_tool(name, line):
    """A HYPHENATED token is only tool-evidence when the document treats it as a tool.

    Criterion (a) is per-tool documentation, and the extractor was reading three other things as
    tools because they share the shape `token` — description:

      mcp-remote   - `sse-first`: Tries SSE transport first, falls back to HTTP…   <- a --transport VALUE
      metaharness  | `npx @metaharness/pi-dev my-bot` | …                          <- an npx COMMAND
      loki-mode    - `eng-frontend` — …                                            <- a mode name

    All three were graded `deep`, the top band, on documentation of tools they do not have.
    mcp-remote is a PROXY: it forwards someone else's tools and exposes none of its own.

    Every genuine hit in the same batch was snake_case — get_space, list_clusters, ctx_execute,
    memory_search, accounts_list, panel_load_workflow — because that is how MCP tools are named in
    practice. Hyphens are legal in a tool name though, so this does not ban them: it asks for one
    piece of corroboration, the word "tool" in the line that documents it, or a command/flag marker
    that rules it out. Underscored and dotted identifiers are unchanged.

    Errs toward NOT counting, which for a conjunctive rubric means a capability lands in a lower
    band rather than claiming a top one it did not earn.
    """
    if "_" in name or "." in name:
        return True
    l = line.lower()
    if "--" in l or "npx " in l or "npm " in l or l.lstrip().startswith("$"):
        return False
    return "tool" in l


def tool_docs(md):
    """Named tools with something said about each — the (a) criterion.

    Counts headings and list items that look like a tool name followed by a description, and
    parameter tables under them. Deliberately generous on shape and strict on there being prose:
    a bare list of tool names is a manifest, not documentation.
    """
    hits = []
    # ### tool_name  /  ### 1. Scrape Tool (`firecrawl_scrape`)  /  - `tool` — desc  /  | `tool` | … |
    #
    # The second shape is why this was loosened. The first pass demanded a heading be NOTHING but a
    # tool name, so firecrawl-mcp — which documents every tool under "### 1. Scrape Tool
    # (`firecrawl_scrape`)" with a parameter table under each — reported zero tool docs, and twenty
    # other rows failed the same way. A heading that names a tool documents that tool whether or not
    # it also carries a number and three English words.
    for m in re.finditer(r"^#{2,4}\s+(.{2,80})$", md, re.M):
        head = m.group(1)
        tok = re.search(r"`([a-z][a-z0-9_.-]{3,40})`", head) or \
              re.match(r"^([a-z][a-z0-9_.]{3,40})\s*$", head.strip())
        if not tok or not tool_shaped(tok.group(1)):
            continue
        tail = md[m.end():m.end() + 400]
        if len(tail.strip()) > 60 and corroborated_tool(tok.group(1), head + " " + tail[:200]):
            hits.append(("heading", tok.group(1), tail.strip().split("\n")[0][:70]))
    for m in re.finditer(r"^\s*[-*|]\s*`([a-z][a-z0-9_.-]{2,40})`\s*[-—:|]\s*(.{20,})$", md, re.M):
        if tool_shaped(m.group(1)) and corroborated_tool(m.group(1), m.group(0)):
            hits.append(("list", m.group(1), m.group(2)[:70]))
    # de-dupe by tool name, keeping the richer form
    seen, out = set(), []
    for kind, name, desc in hits:
        if name in seen:
            continue
        seen.add(name)
        out.append((kind, name, desc))
    return out


def worked_examples(md):
    """(b) — fenced blocks that are neither install lines nor client config, plus prompt examples."""
    out = []
    for lang, body in blocks(md):
        first = body.strip().split("\n")[0] if body.strip() else ""
        if not first or CONFIG_ONLY.match(first):
            continue
        if lang.lower() in ("json", "jsonc", "yaml", "yml", "toml") and re.search(
                r'"(mcpServers|command|args)"|^\s*mcpServers', body):
            continue          # a client-config stanza
        out.append((lang or "—", first[:74], len(body)))
    # "Ask your agent: …" style prompt examples count as worked examples of use
    for m in re.finditer(r"^\s*[>*-]?\s*[\"“](.{25,140})[\"”]\s*$", md, re.M):
        out.append(("prompt", m.group(1)[:74], len(m.group(1))))
    return out


def contradictions(md):
    """Rule 4 — differing tool counts in one document. A FLAG FOR THE GRADER, NOT A CAP.

    It capped at `thin` until it was run on the queue, where both of its two hits were false and
    both were on the best-documented READMEs in the set. hostinger-api-mcp lists each sub-server's
    inventory ("8 tools for dns", "62 tools for vps"); figma-console-mcp tabulates 9 / 101 / 114
    across remote, cloud and local modes. Neither contradicts itself — both are being precise, and
    an automatic cap punished them for it. A rule with a 100% false-positive rate does not get to
    decide a grade; it gets to raise its hand.
    """
    counts = [int(m.group(1)) for m in re.finditer(r"\b(\d{1,3})\s+tools?\b", md, re.I)]
    return sorted(set(counts)) if len(set(counts)) > 1 else []


def subject(md, rec):
    """Is this document ABOUT this capability, or does it merely mention it?

    THE THIRD VARIANT OF THE BORROWED-GRADE CLASS. build.py's gate withholds a grade when a README
    is byte-shared with another capability or never names its own subject. `@azure/mcp` passes both
    — it names itself, and its bytes are unique — and its README is still titled "Microsoft MCP
    Servers", a catalogue of twenty sibling servers in which azure is one bullet. Grading that
    document rates Microsoft's index page and prints the number on azure's dossier.

    So: report the H1 and how often the thing is named. A long document that does not name its
    subject in the title and mentions it a handful of times is about something else.
    """
    h1 = (re.search(r"^#\s+(.{2,80})$", md, re.M) or [None, ""])[1].strip()
    names = [n for n in (rec.get("npm_pkg"), rec.get("name"),
                         (rec.get("id") or "").split(":", 1)[-1]) if n]
    leaf = max((str(n).split("/")[-1] for n in names), key=len, default="")
    return {"h1": h1[:70], "in_title": bool(leaf) and leaf.lower() in h1.lower(),
            "mentions": md.lower().count(leaf.lower()) if leaf else 0, "leaf": leaf}


def evidence(rec):
    md = rec.get("readme") or ""
    td, ex = tool_docs(md), worked_examples(md)
    auth = [m.group(0) for m in AUTH.finditer(md)][:3]
    lim = limits(md)
    doclinks = [m.group(0)[:70] for m in DOCLINK.finditer(md)][:3]
    local = [t for t in re.findall(r"\]\((\.{0,2}/?[\w./-]+\.md)\)", md)
             if re.search(r"tool|api|reference|usage|command|feature", t, re.I)]
    return {
        "id": rec["id"], "chars": len(md), "doclinks": doclinks, "doclinks_local": local[:3], "subject": subject(md, rec),
        "a_tool_docs": td, "b_examples": ex,
        "c_auth": auth, "c_install": bool(re.search(r"\b(install|npx|npm i|uvx|docker run)\b", md, re.I)),
        "d_limits": lim,
        "contradiction": contradictions(md),
        "marketing": len(MARKETING.findall(md)),
        "names_self": bool(rec.get("npm_pkg") and rec["npm_pkg"].lower() in md.lower())
                      or (rec.get("name", "").lower() in md.lower() if rec.get("name") else False),
    }


def summarise(e):
    # NOT EVERY STAGED FILE IS A DOCUMENT. `xmcp` staged 23 bytes reading "packages/xmcp/README.md"
    # — the fetcher captured a POINTER to the readme, not the readme. Graded mechanically that is
    # four unmet criteria and a confident `thin`, which is a measurement of our own fetch bug
    # printed on someone else's product page. Too short to be a document means UNGRADED.
    if e["chars"] < 400:
        return "", "UNGRADEABLE — no document staged (%d bytes)" % e["chars"]
    # (a) is UNKNOWN, not failed, when the README hands tool docs off to a linked file we have not
    # fetched. An unknown must never be scored as an absence — that is the rule the whole corpus
    # runs on, and it applies to our own evidence too.
    if len(e["a_tool_docs"]) < 2 and e["doclinks_local"]:
        return "?" + "".join(k for k, v in (
            ("b", len(e["b_examples"]) >= 2), ("c", bool(e["c_auth"]) and e["c_install"]),
            ("d", bool(e["d_limits"]))) if v), "UNKNOWN — run --follow to read the linked docs"
    a = len(e["a_tool_docs"]) >= 2
    b = len(e["b_examples"]) >= 2
    c = bool(e["c_auth"]) and e["c_install"]
    d = bool(e["d_limits"])
    met = "".join(k for k, v in (("a", a), ("b", b), ("c", c), ("d", d)) if v)
    ceiling = "deep" if met == "abcd" else ("solid" if (b or a) else "thin")
    # Tools may be documented on the vendor's own docs site, which we cannot open here — so (a) is
    # unverified rather than unmet. An unread page is not evidence for a grade OR against one, and
    # this note must therefore only ever CAP a band, never raise one. Written as a raise, it
    # promoted four capabilities with no tool docs AND no examples straight from thin to solid on
    # the strength of a documentation badge.
    if not a and e["doclinks"] and ceiling == "deep":
        ceiling = "solid — (a) unverified, tool docs are off-README"
    # Nothing in its own document and a hand-off to a page we did not read is not a measurement.
    if not a and len(e["b_examples"]) < 2 and e["doclinks"]:
        ceiling = "WITHHELD — defers to docs we cannot read, and shows nothing itself"
    return met, ceiling


def _selftest():
    rich = ("# T\n## get_thing\nReturns the thing for an id, with retries.\n"
            "```js\nawait client.call('get_thing', { id: 42 })\n```\n"
            "```js\nawait client.call('put_thing', { id: 43, body: 'x' })\n```\n"
            "## put_thing\nWrites a thing. Requires an API_KEY environment variable.\n"
            "Install with npx t.\nThis does not support batch writes.\n"
            + "Prose so the fixture clears the 400-byte stub guard. " * 6)
    e = evidence({"id": "x", "readme": rich, "name": "t"})
    met, ceil = summarise(e)
    assert met == "abcd", (met, e)
    assert ceil == "deep", ceil
    # a wall of config blocks is not a worked example
    cfg = ("# T\n```json\n{ \"mcpServers\": { \"t\": { \"command\": \"npx\" } } }\n```\nnpx t\n"
           + "Filler prose so this clears the stub guard too. " * 8)
    e2 = evidence({"id": "y", "readme": cfg, "name": "t"})
    assert len(e2["b_examples"]) == 0, e2["b_examples"]
    assert summarise(e2)[1] == "thin"
    # rule 4 flags but no longer caps — every hit it produced on the real queue was false
    e3 = evidence({"id": "z", "readme": rich + "\nProvides 14 tools.\nAll 22 tools are listed.\n",
                   "name": "t"})
    assert e3["contradiction"] == [14, 22] and summarise(e3)[1] == "deep", summarise(e3)
    # a pointer to a readme is not a readme
    assert summarise(evidence({"id": "p", "readme": "packages/x/README.md", "name": "x"}))[1] \
        .startswith("UNGRADEABLE")
    # a document titled after twenty siblings is not this capability's document
    assert not evidence({"id": "pkg:@azure/mcp", "readme": "# Microsoft MCP Servers\n" + "x" * 500,
                         "name": "azure"})["subject"]["in_title"]
    # a maintainer saying they have stopped watching the repo IS a stated limitation
    # a bare version word is not a limitation, and neither is a stray negative verb
    for noise in ("This is a beta release.", "Can't find the file? Check the path.",
                  "Returns `unverified` when it doesn't exist."):
        assert not limits("# X\n" + noise + "\n" + "Filler prose. " * 40), noise
    lh = limits("# X\n## Limitations\nIt is slow and single-threaded.\n")
    assert lh and "single-threaded" in lh[0], lh   # the heading AND what sits under it
    assert limits("# X\nThis does not support batch writes.\n"), "an asserted constraint must register"
    # the excerpt is a whole sentence, never a mid-word slice
    q = limits("We keep the default install lean. This package is not a runtime. More prose here.")[0]
    assert q.startswith("This package is not a runtime"), q
    assert not limits("# X\n| `limit` | Deprecated alias for `max`. |\n" + "Filler. " * 40)
    assert limits("# X\nThis package is deprecated and will be removed.\n")
    e4 = evidence({"id": "n", "readme": "# N\nIssues here are not actively monitored.\n"
                                        + "Filler to clear the stub guard. " * 14, "name": "n"})
    assert e4["d_limits"], "a 'not actively monitored' notice must register"
    # tool docs behind a link are unknown, never absent
    # an external docs badge forecloses `deep` but never drops the grade
    e6 = evidence({"id": "f", "readme": "# F\n[Docs](https://f.dev/docs)\nnpx f, needs an API key.\n"
                                        "```py\nf.scrape('a')\n```\n```py\nf.crawl('b')\n```\n"
                                        "Does not support PDFs.\n" + "Filler prose here. " * 25,
                   "name": "f"})
    assert summarise(e6)[1].startswith("solid"), summarise(e6)
    # …but a docs badge must never RAISE a document that shows nothing of its own
    e7 = evidence({"id": "g", "readme": "# G\n[Docs](https://g.dev/docs)\nIt does things.\n"
                                        + "Filler prose. " * 40, "name": "g"})
    assert summarise(e7)[1].startswith("WITHHELD"), summarise(e7)
    # a numbered, prose-y heading still documents the tool it names
    e8 = evidence({"id": "h", "readme": "# H\n### 1. Scrape Tool (`h_scrape`)\n"
                                        + "Fetches one page and returns markdown, with retries.\n"
                                        + "### 2. Crawl Tool (`h_crawl`)\n"
                                        + "Walks a site to a depth limit and returns each page.\n"
                                        + "Filler prose. " * 30, "name": "h"})
    assert [n for _, n, _ in e8["a_tool_docs"]] == ["h_scrape", "h_crawl"], e8["a_tool_docs"]
    # workflow files and option words are not tools
    for junk in ("ci.yml", "publish.yml", "quality", "limit", "hello", "page", "mcp-server",
                 "brilliant-directories-60031"):
        assert not tool_shaped(junk), junk
    for real in ("web_search_exa", "figma_get_status", "resolve-library-id", "code_health_score"):
        assert tool_shaped(real), real
    # the published note fits the field, closes its quote, and carries no markdown
    e9 = evidence({"id": "k", "readme": "# K\n## a_tool\nDoes a thing, at length, with detail.\n"
                                        "## b_tool\nDoes another thing, at length, with detail.\n"
                                        "```js\nk.a(1)\n```\n```js\nk.b(2)\n```\nnpx k, API_KEY.\n"
                                        "**Note:** this does not support " + "very long caveat " * 30,
                   "name": "k"})
    n = note_for("deep", e9, 1)
    assert len(n) <= 200, len(n)
    assert n.count("“") == n.count("”") == 1, n
    assert "**" not in n and "`" not in n, n
    # a long tool list must never squeeze the quotation down to a stub
    e10 = evidence({"id": "l", "readme": "# L\n"
        + "".join(f"## get_confluence_thing_number_{i}\nDoes a documented thing, at some length.\n"
                  for i in range(6))
        + "```js\nl.a(1)\n```\n```js\nl.b(2)\n```\nnpx l, API_KEY.\n"
          "This does not support deleting pages that are already archived by another user.\n",
        "name": "l"})
    n10 = note_for("deep", e10, 1)
    assert len(n10) <= 200 and n10.split("“")[1].count(" ") >= 5, n10
    e5 = evidence({"id": "c", "readme": "# C\nSee [Tool reference](./docs/tool-reference.md).\n"
                                        "npx c\nNeeds an API key.\n"
                                        + "Filler to clear the stub guard. " * 14, "name": "c"})
    assert summarise(e5)[1].startswith("UNKNOWN"), summarise(e5)
    # A DOCUMENT THAT DESCRIBES SEVERAL CAPABILITIES CREDITS NONE OF THEM.
    # 904 of the 2,090 staged READMEs over 400 chars are byte-identical to another capability's —
    # 43.3%, including one cluster of 241 skills from a single repository. Graded from that text,
    # all 241 receive the same verdict, and it is a verdict about the repository.
    _man = {
        "a": {"id": "a", "readme": "x" * 500},
        "b": {"id": "b", "readme": "x" * 500},          # byte-identical to a
        "c": {"id": "c", "readme": "y" * 500},          # its own
        "d": {"id": "d", "readme": "z" * 100},          # too short to stage; not a "share"
        "e": {"id": "e", "readme": "z" * 100},
    }
    _sh = shared_documents(_man)
    assert _sh.get("a") == 2 and _sh.get("b") == 2, _sh
    assert "c" not in _sh, "a capability with its own README must not be withheld"
    assert "d" not in _sh and "e" not in _sh, (
        "two stub READMEs under the stage threshold are not a shared document")
    assert _plain("SHARED — its README is byte-identical to 4 others").startswith("its README is the same file"), \
        "the shared-document refusal must say what it means, not fall through to the generic text"
    print("grade_evidence selftest ok")


def clean(t):
    """Prose fit to publish: no markdown, no control whitespace, no half-word at the end.

    These strings go verbatim into `expertise_note`, which renders on the dossier, so `Notes:**` and
    `**WCAG 1.4.12 Text Spacing**` leaking out of a README are our bug, not the author's.
    """
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"(\*\*|__|`|^\s*[>#|]+\s*)", "", t).strip(" .,;:—-*|")
    return re.sub(r"^\S*\s+", "", t, count=1) if t[:1].islower() and " " in t[:14] else t


def note_for(band, e, followed, budget=200):
    """One sentence of evidence per grade, inside the 200-char field, never cut mid-quote.

    The first cut appended the limitation and then truncated the whole string to 200, which left ten
    of forty-eight notes ending mid-word with an unclosed quotation mark. The quote is the part that
    has to flex, so the fixed text is measured first and the quote gets whatever room is left.
    """
    a, b = len(e["a_tool_docs"]), len(e["b_examples"])
    tail = f"; read with {followed} linked doc(s)" if followed else ""
    if band == "thin":
        return f"says what it does, not how to use it — {a} tool docs, {b} worked examples{tail}"
    if band == "solid":
        gaps = [n for n, ok in (("per-tool docs", a >= 2), ("a stated limitation", bool(e["d_limits"])),
                                ("setup/auth", bool(e["c_auth"]) and e["c_install"])) if not ok]
        return (f"{b} worked examples" + (f", {a} tools documented" if a else "")
                + "; short of deep on " + " and ".join(gaps) + tail)[:budget]
    q = clean(max(e["d_limits"], key=len))
    # THE QUOTE IS THE EVIDENCE; the tool sample is illustration. Naming three tools first left
    # mcp-atlassian — whose tool names run to 30 characters each — quoting its limitation as "Lim…",
    # which is not a quotation, it is a truncation artifact with quote marks around it. Drop tool
    # names until the quote has room to say something, and only then trim the quote itself.
    for n_tools in (3, 2, 1, 0):
        tools = ", ".join(n for _, n, _ in e["a_tool_docs"][:n_tools])
        head = (f"{a} tools documented" + (f" ({tools}…)" if tools else "")
                + f"; {b} worked examples; setup and auth covered; states a limit — ")
        room = budget - len(head) - len(tail) - 3        # two quote marks and an ellipsis
        if room >= 44 or n_tools == 0:
            break
    if len(q) > room:
        q = q[:max(room, 1)].rsplit(" ", 1)[0] + "…"
    return f"{head}“{q}”{tail}"


# The reader-facing sentence for each machine verdict. summarise() returns operator strings
# ("UNKNOWN — run --follow to read the linked docs"); a dossier needs the fact, not the instruction.
WITHHELD_TEXT = {
    "UNGRADEABLE": "no documentation was published with it",
    "WITHHELD": "its documentation points at a page we cannot read, and shows nothing itself",
    "UNKNOWN": "its tool documentation lives in files we could not fetch",
    # Not "we could not read it" — we read it fine, it just is not about this capability. Saying so
    # is more useful to a reader than a generic refusal, and it is a fact about the repository's
    # documentation rather than a criticism of this row.
    "SHARED": "its README is the same file its sibling capabilities ship, so it describes the "
              "repository rather than this capability",
}


def _plain(why):
    return WITHHELD_TEXT.get(why.split(" —")[0].strip(), "we could not read its documentation fairly")


def emit_scores(path, graded):
    """Write a scores_*.json for merge_expertise.py, with the band's own evidence as the note."""
    out = []
    for cid, band, e, followed in graded:
        a, b = len(e["a_tool_docs"]), len(e["b_examples"])
        score = (min(100, 82 + round(min(a, 40) / 40 * 10) + round(min(b, 30) / 30 * 8))
                 if band == "deep" else
                 min(79, 62 + round(min(a, 12) / 12 * 9) + round(min(b, 20) / 20 * 8))
                 if band == "solid" else 38 + min(b, 2) * 4 + (4 if e["c_auth"] else 0))
        out.append({"id": cid, "expertise": score, "verdict": band,
                    "note": note_for(band, e, followed)})
    out.sort(key=lambda r: -r["expertise"])
    json.dump(out, open(path, "w", encoding="utf-8"), indent=1)
    return out


def shared_documents(man):
    """ids whose staged README is BYTE-IDENTICAL to another capability's.

    A grade must not borrow credit from a document describing something else. 904 of the 2,090
    staged documents over 400 chars — 43.3% — are shared: one cluster is 241 skills from a single
    repository pointing at one README, another is 109 npm packages from one monorepo. Graded from
    that text, all 241 would receive the same verdict, and it would be a verdict about the
    repository rather than about any of them.

    The rule already exists for the LLM path (pipeline/doc_signals.py caps these at `thin`); it was
    simply never applied here, so the deterministic extractor — the one that scales — was the one
    without the guard.

    WITHHELD RATHER THAN CAPPED, on this path. `thin` is a published judgement that reads as "badly
    documented", and a skill in a well-documented monorepo has not earned that; what is true is
    that we cannot grade it from the document we have. That is exactly what the withheld list is
    for, and it is what this file already does for a README it cannot read.
    """
    seen, out = {}, {}
    for m in man.values():
        body = m.get("readme") or ""
        if len(body) <= 400:
            continue
        h = hashlib.sha256(body.encode("utf-8")).hexdigest()
        seen.setdefault(h, []).append(m["id"])
    for ids in seen.values():
        if len(ids) > 1:
            for i in ids:
                out[i] = len(ids)
    return out


def main(argv):
    man = {m["id"]: m for m in json.load(open(MANIFEST, encoding="utf-8"))}
    shared = shared_documents(man)
    want = [a for a in argv if not a.startswith("-")] or list(man)
    follows = "--follow" in argv
    emit = (argv[argv.index("--emit") + 1] if "--emit" in argv else None)
    want = [w for w in want if w != emit]
    graded, held = [], []
    cache = json.load(open(LINKED, encoding="utf-8")) if os.path.exists(LINKED) else {}
    for cid in want:
        rec = man.get(cid)
        if not rec:
            print(f"{cid}: not staged"); continue
        extra = []
        if follows:
            merged, extra = follow(rec, cache)
            rec = {**rec, "readme": merged}
        e = evidence(rec)
        met, ceiling = summarise(e)
        # A DOCUMENT THAT DESCRIBES SEVERAL CAPABILITIES CREDITS NONE OF THEM. Checked before the
        # bands are applied, so a shared README cannot reach the emitted file by any route.
        if cid in shared:
            ceiling = (f"SHARED — its README is byte-identical to {shared[cid] - 1} other "
                       f"capabilit{'y' if shared[cid] == 2 else 'ies'}, so it describes the "
                       f"repository rather than this one")
        (graded.append((cid, ceiling, e, len(extra))) if ceiling in ("deep", "solid", "thin")
         else held.append((cid, ceiling)))
        print("=" * 96)
        print(f"{cid}   {e['chars']:,} chars   criteria met: {met or 'none':4}   ceiling: {ceiling}")
        print(f"  (a) tool docs   {len(e['a_tool_docs'])}: "
              + "; ".join(f"{n} — {d[:38]}" for _, n, d in e["a_tool_docs"][:4]))
        print(f"  (b) examples    {len(e['b_examples'])}: "
              + "; ".join(f"[{l}] {f[:44]}" for l, f, _ in e["b_examples"][:4]))
        print(f"  (c) setup/auth  install={e['c_install']} auth={e['c_auth']}")
        print(f"  (d) limitation  " + (e["d_limits"][0][:88] if e["d_limits"] else "NONE FOUND"))
        sub = e["subject"]
        if not sub["in_title"]:
            print(f"  ~  title is \"{sub['h1']}\" — names \"{sub['leaf']}\" {sub['mentions']}x")
        if e["doclinks"]:
            print(f"  ?  tool docs linked out, not inline: {e['doclinks'][0]}")
        if e["contradiction"]:
            print(f"  !! contradiction — claims {e['contradiction']} tools in one document")
        if extra:
            print(f"  +  read {len(extra)} linked doc(s): {', '.join(extra)}")
        if e["marketing"] > 4:
            print(f"  ~  {e['marketing']} marketing markers")
    if follows:
        json.dump(cache, open(LINKED, "w", encoding="utf-8"))
    if emit:
        # WITHHELD ROWS ARE WRITTEN DOWN, not just printed. Nine of the first top-100 queue were
        # withheld and rendered identically to the 8,800 nobody has reached: blank. The refusal is
        # the more useful fact, and it is only useful if it reaches the page.
        wpath = os.path.join(os.path.dirname(emit), "withheld.json")
        json.dump([{"id": cid, "reason": _plain(why)} for cid, why in held],
                  open(wpath, "w", encoding="utf-8"), indent=1)
        print(f"{len(held)} withheld -> {wpath}")
        rows = emit_scores(emit, graded)
        print(f"\n{len(rows)} graded -> {emit}   "
              + "  ".join(f"{v}:{sum(1 for r in rows if r['verdict'] == v)}"
                          for v in ("deep", "solid", "thin")))
        # WITHHELD IS A RESULT, NOT A GAP. Printed, never written: a capability we could not read is
        # left with no grade rather than a low one, and the reason is on the record either way.
        for cid, why in held:
            print(f"  withheld  {cid:42} {why}")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() or 0 if "--selftest" in sys.argv else main(sys.argv[1:]))
