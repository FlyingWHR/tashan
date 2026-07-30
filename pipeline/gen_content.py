#!/usr/bin/env python3
"""tashan — content engine (framework + exemplars).

Renders SEO/AEO articles to web/learn/<slug>.html with the answer-engine shape that gets cited:
a "Quick Answer" block (40–60 words, the exact command/path first), question-format H2s, and
Article + FAQPage + HowTo JSON-LD. Out-authorities directory sites by backing "best X" lists with
tashan's live tashan score ranking (data-backed = more citable than curated opinion).

This ships the FRAMEWORK + a few exemplar articles (EN + 中文). The full query-cluster sweep
(where-stored / how-to-install / best-X / is-X-safe × every client × EN/CN) is LLM-in-loop and runs
as a separate pass — this file is the deterministic renderer + template those articles slot into.
Stdlib only.
"""
import json, os, re, html, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assets
AV = str(assets.V)   # single source of truth for cache-busting
DATA = os.path.join(ROOT, "web", "data", "capabilities.json")
OUT = os.path.join(ROOT, "web", "learn")
BASE = "https://tashan.sh"
os.makedirs(OUT, exist_ok=True)

def esc(s): return html.escape(str(s), quote=True)
def pretty(name):
    return re.sub(r"^mcp-", "", re.sub(r"^mcp-server-", "", re.sub(r"-mcp$", "",
        re.sub(r"^@modelcontextprotocol/server-", "", str(name)))))

NAV = ('<nav class="nav"><div class="wrap nav__in">'
       '<a class="brand" href="/"><span class="brand__mark"></span>tashan<small>v2 · public-signal</small></a>'
       '<div class="nav__links"><a href="/">Index</a><a href="/start.html">Use it</a>'
       '<a href="/methodology.html">Methodology</a><a href="/learn/">Learn</a>'
       '<a href="/about.html">About</a></div></div></nav>')
FOOT = ('<footer class="footer"><div class="wrap footer__in">'
        '<div class="footer__brand"><span class="brand"><span class="brand__mark"></span>tashan</span>'
        '<p class="footer__tag">The measurement layer for AI capabilities — MCP servers and agent skills, '
        'measured on public evidence.</p>'
        '<p class="footer__meta" id="footMethod">public-signal v2</p></div>'
        '<nav class="footer__col"><p class="footer__h">Explore</p><a href="/">The Index</a>'
        '<a href="/start.html">Use it</a><a href="/learn/">Learn</a>'
        '<a href="/for-hosts.html">For hosts</a></nav>'
        '<nav class="footer__col"><p class="footer__h">tashan score</p><a href="/methodology.html">Methodology</a>'
        '<a href="/about.html">About</a><a href="/pricing.html">Pricing</a><a href="/requests.html">Requests</a></nav>'
        '<nav class="footer__col"><p class="footer__h">Sources</p>'
        '<a href="https://registry.modelcontextprotocol.io/" rel="noopener">MCP registry ↗</a>'
        '<a href="https://www.npmjs.com/" rel="noopener">npm ↗</a>'
        '<a href="https://github.com/" rel="noopener">GitHub ↗</a></nav>'
        # Selling on this site means every page needs the legal surfaces, not just the hand-written
        # eleven — these three generators produce ~5,800 of them.
        '<nav class="footer__col"><p class="footer__h">Legal</p><a href="/terms.html">Terms</a>'
        '<a href="/privacy.html">Privacy</a><a href="/refunds.html">Refunds</a>'
        '<a href="/support.html">Support</a></nav></div>'
        '<div class="wrap footer__bar"><span>© 2026 SeroLabs, Inc.</span>'
        '<span>Every score re-derivable from public evidence.</span></div></footer>')

def head(a):
    url = BASE + "/learn/" + a["slug"] + ".html"
    lds = [
        {"@context":"https://schema.org","@type":"Article","headline": a["title"],
         "description": a["desc"], "inLanguage": a.get("lang","en"), "author":{"@type":"Organization","name":"tashan"},
         "publisher":{"@type":"Organization","name":"tashan"}, "mainEntityOfPage": url},
        {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
            {"@type":"ListItem","position":1,"name":"Learn","item": BASE + "/learn/"},
            {"@type":"ListItem","position":2,"name": a["title"], "item": url}]},
    ]
    if a.get("faq"):
        lds.append({"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
            {"@type":"Question","name": q, "acceptedAnswer":{"@type":"Answer","text": ans}} for q, ans in a["faq"]]})
    if a.get("howto"):
        lds.append({"@context":"https://schema.org","@type":"HowTo","name": a["title"],
            "step":[{"@type":"HowToStep","position": i+1, "text": s} for i, s in enumerate(a["howto"])]})
    if a.get("itemlist"):   # numbers-in-schema — the data-backed ranking as an ItemList of rated apps (Agensi omits this)
        lds.append({"@context":"https://schema.org","@type":"ItemList","itemListOrder":"https://schema.org/ItemListOrderDescending",
            "numberOfItems": len(a["itemlist"]), "itemListElement":[
            {"@type":"ListItem","position": i+1, "item":{"@type":"SoftwareApplication","name": it["name"], "url": it["url"],
             "applicationCategory":"DeveloperApplication",
             "aggregateRating":{"@type":"AggregateRating","ratingValue": it["tashan_score"], "bestRating": 100, "worstRating": 0, "ratingCount": 1}}}
            for i, it in enumerate(a["itemlist"])]})
    ld = "\n".join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False) + "</script>" for x in lds)
    return ("<!doctype html>\n<html lang=\"" + a.get("lang","en") + "\">\n<head>\n"
        '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>" + esc(a["title"]) + " · tashan</title>\n"
        '<meta name="description" content="' + esc(a["desc"]) + '">\n'
        '<meta name="theme-color" content="#0b0b0a">\n<link rel="canonical" href="' + url + '">\n'
        '<meta property="og:type" content="article">\n<meta property="og:title" content="' + esc(a["title"]) + '">\n'
        '<meta property="og:description" content="' + esc(a["desc"]) + '">\n<meta property="og:url" content="' + url + '">\n'
        '<meta property="og:image" content="https://tashan.sh/assets/og.png">\n'
        '<meta property="og:image:width" content="1200">\n'
        '<meta property="og:image:height" content="630">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        '<meta name="twitter:image" content="https://tashan.sh/assets/og.png">\n'
        '<link rel="icon" href="/assets/favicon.svg">\n'
        '<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">\n'
        '<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/Geist-Variable.woff2" crossorigin>\n'
        '<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/GeistMono-Variable.woff2" crossorigin>\n'
        '<link rel="stylesheet" href="/css/site.css?v=' + AV + '">\n' + ld + "\n</head>\n<body>\n" + NAV)

def article_html(a):
    secs = ""
    for s in a["sections"]:
        secs += "<h2>" + esc(s["q"]) + "</h2>\n" + s["body"] + "\n"
    faq = ""
    if a.get("faq"):
        faq = '<h2>FAQ</h2>\n' + "".join("<h3>" + esc(q) + "</h3><p>" + esc(ans) + "</p>\n" for q, ans in a["faq"])
    return (head(a) + '<main class="wrap"><article class="prose">\n'
        '<p class="kicker"><a class="link" href="/learn/">Learn</a></p>\n'
        "<h1>" + esc(a["title"]) + "</h1>\n"
        '<div class="callout"><b>Quick answer.</b> ' + a["quick"] + '</div>\n'
        + secs + faq +
        '<p style="margin-top:var(--sp-12)"><a class="btn btn--ghost" href="/">See the ranked Index &rsaquo;</a></p>\n'
        "</article></main>\n" + FOOT +
        '<script src="/js/terminal.js?v=' + AV + '" defer></script>\n<script src="/js/site.js?v=' + AV + '" defer></script>\n</body>\n</html>\n')

def top_table(caps, kind_filter=None, n=10):
    rows = [c for c in caps if c.get("tashan_score") is not None and (kind_filter is None or kind_filter(c))][:n]
    body = ['<div class="board"><div class="board__scroll"><table class="board__t"><thead><tr>'
            '<th class="rank">#</th><th>Capability</th><th class="num">tashan score</th><th>Verdict</th><th class="num">Adoption</th></tr></thead><tbody>']
    for i, c in enumerate(rows):
        href = "/capability/" + c["slug"] + ".html" if c.get("slug") else "#"
        vd = ('<span class="vd vd--' + c["expertise_verdict"] + '">' + c["expertise_verdict"] + '</span>') if c.get("expertise_verdict") else "—"
        dl = c.get("npm_downloads")
        adopt = ((("%.1fM" % (dl/1e6)) if dl >= 1e6 else ("%.0fk" % (dl/1e3)) if dl >= 1e3 else str(dl)) + "/wk") if dl else "—"
        body.append('<tr data-href="' + href + '"><td class="rank">' + str(i+1) + '</td>'
                    '<td><a href="' + href + '">' + esc(pretty(c["name"])) + '</a></td>'
                    '<td class="num">' + str(c.get("tashan_score")) + '</td><td>' + vd + '</td>'
                    '<td class="num">' + adopt + '</td></tr>')
    body.append("</tbody></table></div></div>")
    return "".join(body)

def build_articles(caps):
    A = []
    # 1. config-location cluster (EN) — HowTo + FAQ, exact path first
    A.append({
        "slug": "where-are-claude-skills-stored", "lang": "en",
        "title": "Where are Claude skills stored?",
        "desc": "Claude Code loads skills from ~/.claude/skills (user) and .claude/skills (project). Exact paths for macOS, Linux, and Windows, plus how to verify a skill is found.",
        "quick": "Claude Code reads agent <b>skills</b> from <code>~/.claude/skills/</code> (user scope) and <code>.claude/skills/</code> in the project root (project scope). Each skill is a folder containing a <code>SKILL.md</code>. Drop the folder in, restart the session, and the skill is auto-discovered.",
        "sections": [
            {"q": "Where does Claude Code store skills on macOS and Linux?",
             "body": "<p>User-scoped skills live in <code>~/.claude/skills/&lt;skill-name&gt;/SKILL.md</code>. Project-scoped skills live in <code>.claude/skills/</code> at the repository root — those are shared with anyone who clones the repo.</p>"},
            {"q": "Where are Claude skills stored on Windows?",
             "body": "<p>Use <code>%USERPROFILE%\\.claude\\skills\\</code> for user scope, or <code>.claude\\skills\\</code> in the project.</p>"},
            {"q": "How do I check a skill is being loaded?",
             "body": "<p>Start a session in the project and confirm the skill's <code>name</code> (from its <code>SKILL.md</code> frontmatter) appears in the available skills. If not, check the folder contains a <code>SKILL.md</code> with valid frontmatter and restart.</p>"},
        ],
        "howto": ["Create ~/.claude/skills/ if it does not exist.",
                  "Put the skill folder (containing SKILL.md) inside it.",
                  "Restart the Claude Code session.",
                  "Confirm the skill's name appears as available."],
        "faq": [("Can I share a skill with my team?", "Yes — put it in .claude/skills/ inside the repo; it's committed and shared with everyone who clones it."),
                ("What format is a skill?", "A folder with a SKILL.md whose YAML frontmatter has a name and description. See tashan's tracked skills for real examples.")],
    })
    # 2. best-X cluster (EN) — DATA-BACKED ranked table (the differentiator)
    A.append({
        "slug": "best-mcp-servers-for-claude-code", "lang": "en",
        "title": "Best MCP servers for Claude Code (2026)",
        "desc": "The top MCP servers for Claude Code, ranked by tashan's measured score — real adoption and maintenance, not stars or opinion. Auto-updated from public evidence.",
        "quick": "The most trustworthy MCP servers for Claude Code right now, by measured tashan score (upkeep + freshness, gated by real adoption): <b>context7</b>, <b>chrome-devtools</b>, and <b>filesystem</b> lead. The full ranked list below updates from public evidence — not stars, not sponsorships.",
        "sections": [
            {"q": "Which MCP servers are most trusted for Claude Code?",
             "body": "<p>Ranked by tashan's tashan score — every number is re-derivable from npm downloads, release cadence, and repository health. Open any row for the full dossier.</p>" + top_table(caps, lambda c: c.get("kind") in ("npm","pkg"), 12)},
            {"q": "Why rank by tashan score instead of GitHub stars?",
             "body": "<p>Stars measure visibility, not fitness. A server can be starred and abandoned. tashan's tashan score blends how actively a server is <b>maintained</b> and how <b>fresh</b> it is, gated by real <b>adoption</b> — and flags single-maintainer and archived risks. See the <a class='link' href='/methodology.html'>methodology</a>.</p>"},
        ],
        "faq": [("How do I install one of these?", "Open its page and copy the per-client snippet — Claude Code, Cursor, Claude Desktop, or Codex. Most are `claude mcp add <name> -- npx -y <pkg>`."),
                ("Is this list sponsored?", "No. tashan sells nothing on the board, so the ranking is evidence, not spend.")],
        "itemlist": [{"name": pretty(c["name"]), "url": BASE + "/capability/" + c["slug"] + ".html", "tashan_score": c["tashan_score"]}
                     for c in [x for x in caps if x.get("tashan_score") is not None and x.get("kind") in ("npm", "pkg")][:12]],
    })
    # 3. 中文 cluster — tutorial-that-curates shell (CN long-tail)
    A.append({
        "slug": "mcp-fuwuqi-tuijian", "lang": "zh",
        "title": "MCP 服务器怎么选？用 tashan score 评分挑最靠谱的",
        "desc": "面对上千个 MCP 服务器，怎么选到真正靠谱的？tashan 用公开证据打分（tashan score = 维护 + 更新，按真实采用度加权），附带专家评级和安装方法。",
        "quick": "选 MCP 服务器别只看 star。tashan 用<b>公开证据</b>打 tashan score 分（维护活跃度 + 更新新鲜度，按真实下载量加权），并对每个能力做 <b>deep / solid / thin</b> 专家评级。下面是按 tashan score 排名的榜单，点开任意一行看完整安装方法和仓库健康度。",
        "sections": [
            {"q": "怎么判断一个 MCP 服务器靠不靠谱？",
             "body": "<p>看三件事：是否<b>仍在维护</b>（最近提交/发版）、有多少<b>真实采用</b>（npm 周下载）、以及是否有<b>单一维护者/已归档</b>风险。tashan 把这些合成一个可复现的 tashan score 分。</p>" + top_table(caps, lambda c: c.get("kind") in ("npm","pkg"), 12)},
            {"q": "MCP 服务器和 Agent Skill 有什么区别？",
             "body": "<p>MCP 服务器通过 Model Context Protocol 给 AI 暴露工具；Agent Skill 是一个带 SKILL.md 的文件夹，按需加载。tashan 用同一套模型同时追踪并打分。</p>"},
        ],
        "faq": [("这个榜单收钱排名吗？", "不收。tashan 不出售榜单上的任何东西，所以排名是证据，不是广告位。"),
                ("怎么安装？", "点开任意能力页，复制对应客户端（Claude Code / Cursor / Claude Desktop / Codex）的安装片段即可。")],
    })
    # 4. how-to-install cluster (EN) — Cursor, HowTo schema, exact path first
    A.append({
        "slug": "how-to-install-mcp-server-in-cursor", "lang": "en",
        "title": "How to install an MCP server in Cursor",
        "desc": "Add an MCP server to Cursor by editing ~/.cursor/mcp.json (global) or .cursor/mcp.json (project), then enabling it in Settings → MCP. Exact steps and the common failure points.",
        "quick": "In Cursor, add the server to <code>~/.cursor/mcp.json</code> (global) or <code>.cursor/mcp.json</code> (project root), using an <code>mcpServers</code> block with the server's <code>command</code> and <code>args</code>. Open <b>Settings → MCP</b>, toggle it on, and confirm its tools load. Use absolute paths — Cursor does not inherit your shell's working directory.",
        "sections": [
            {"q": "Where does Cursor read MCP config from?",
             "body": "<p>Global: <code>~/.cursor/mcp.json</code>. Per-project: <code>.cursor/mcp.json</code> at the repo root (committed and shared). Both use the same <code>{\"mcpServers\": { \"name\": { \"command\": …, \"args\": [ … ] } }}</code> shape.</p>"},
            {"q": "Why isn't my MCP server showing up in Cursor?",
             "body": "<p>The three usual causes: (1) the <b>Enable MCP Servers</b> toggle in Settings → MCP is off; (2) a <b>relative path</b> in <code>args</code> — Cursor doesn't inherit your shell cwd, so use absolute paths; (3) a Node/<code>npx</code>/<code>uvx</code> prerequisite is missing. Restart Cursor after editing the file.</p>"},
        ],
        "howto": ["Open or create ~/.cursor/mcp.json (or .cursor/mcp.json in your project).",
                  "Add an mcpServers entry with the server's command and args (absolute paths).",
                  "Open Settings → MCP and toggle the server on.",
                  "Confirm the server's tools appear; restart Cursor if they don't."],
        "faq": [("Can I scope an MCP server to one project in Cursor?", "Yes — put it in .cursor/mcp.json at the project root; it's committed and shared with the repo."),
                ("Which MCP servers are worth installing in Cursor?", "See tashan's tashan score-ranked Index — every server is scored on measured adoption and maintenance, not stars.")],
    })
    # 5. is-X-safe cluster (EN) — the trust wedge
    A.append({
        "slug": "how-to-tell-if-an-mcp-server-is-safe", "lang": "en",
        "title": "How to tell if an MCP server is safe",
        "desc": "MCP servers run with your agent's permissions. Judge safety by maintainer count, maintenance recency, permission surface (file/shell/network), and whether it's official — not by GitHub stars.",
        "quick": "An MCP server runs tools your agent invokes, so treat it like installing a CLI. Check five things: a <b>named, active maintainer</b> (not a single anonymous one), <b>recent maintenance</b>, a clear <b>permission surface</b> (does it read/write files, run shells, or reach the network?), <b>no unpatched advisories</b>, and whether it's <b>official</b> from a model company. tashan surfaces these per server so you don't have to dig.",
        "sections": [
            {"q": "What are the real security risks of an MCP server?",
             "body": "<p>The named ones: <b>tool-poisoning / prompt-injection</b> via tool descriptions the model sees but you don't; <b>rug-pulls</b> (a server silently changing tool behavior after you approve it); <b>single-maintainer / supply-chain</b> risk; and <b>typosquats</b> (near-identical names). None of these show up in a star count.</p>"},
            {"q": "How does tashan help judge MCP safety?",
             "body": "<p>Every capability page shows the <b>bus factor</b> (real contributor count), an <b>archived/deprecated</b> flag, the <b>maintainer</b> and license, and a plain-language read. It's a maintenance/adoption read, not a full audit — but it's the fast first filter a store's install counter can't give you. Read the <a class='link' href='/methodology.html'>methodology</a>.</p>"},
        ],
        "faq": [("Are MCP servers safe to run?", "They're as safe as any tool you install — judge the maintainer, recency, and permission surface. Prefer official or well-maintained servers; be cautious with single-maintainer, archived, or typosquat-looking ones."),
                ("Can an MCP server steal my data?", "A malicious one with file/network access could, which is why the permission surface and maintainer trust matter. tashan flags single-maintainer and archived servers as elevated risk.")],
    })
    # 6. comparison cluster (EN)
    A.append({
        "slug": "mcp-vs-agent-skills-vs-cli", "lang": "en",
        "title": "MCP vs agent skills vs CLI: which should you use?",
        "desc": "MCP servers expose live tools over a protocol; agent skills are on-demand instruction folders (SKILL.md); CLIs are scripts the agent shells out to. When to reach for each, and the trade-offs.",
        "quick": "Use an <b>MCP server</b> when the agent needs live, structured tools (a database, a browser, an API). Use an <b>agent skill</b> when you're adding know-how/instructions the agent loads on demand (a SKILL.md folder) — lighter on the context window. Use a <b>CLI</b> when a plain command does the job and you want zero protocol overhead. tashan tracks and scores MCP servers and skills in one place.",
        "sections": [
            {"q": "What's the difference between an MCP server and an agent skill?",
             "body": "<p>An <b>MCP server</b> runs a process that exposes tools to the agent over the Model Context Protocol — good for live, stateful capabilities. An <b>agent skill</b> is a folder with a <code>SKILL.md</code> the agent reads when relevant — good for expertise/instructions, and it doesn't hold a tool connection open in the context window.</p>"},
            {"q": "Is MCP dead now that skills and CLIs exist?",
             "body": "<p>No — they're complementary units of capability. MCP wins for live tools; skills win for on-demand knowledge; CLIs win for simple deterministic commands. The real question per capability is fitness, not format — which is what tashan measures across all of them.</p>"},
        ],
        "faq": [("Should I build an MCP server or a skill?", "A skill if you're packaging instructions/know-how; an MCP server if you need to expose live tools or state. tashan scores both so you can see which comparable capabilities are trusted."),
                ("Do skills use less context than MCP?", "Generally yes — skills load on demand and don't hold an open tool connection, which is why some teams prefer them for knowledge-heavy tasks.")],
    })
    return A

def index_page(A):
    cards = ""
    for a in A:
        lang = " · 中文" if a.get("lang") == "zh" else ""
        cards += ('<a class="card" href="/learn/' + a["slug"] + '.html" style="display:block;text-decoration:none">'
                  '<h3 style="margin:0 0 .4rem">' + esc(a["title"]) + '</h3>'
                  '<p style="margin:0;color:var(--text-dim);font-size:.9rem">' + esc(a["desc"][:120]) + '…<span class="mono" style="color:var(--text-faint)">' + lang + '</span></p></a>')
    body = ('<main class="wrap"><article class="prose"><h1>Learn</h1>'
            '<p class="lede">Practical, evidence-backed guides to MCP servers and agent skills — where they live, '
            'how to install them in every client, and which ones are actually worth it.</p>'
            '<div class="tashan_score" style="margin-top:var(--sp-8)">' + cards + '</div></article></main>')
    a0 = {"slug": "index", "lang": "en", "title": "Learn — MCP & agent-skill guides",
          "desc": "Evidence-backed guides to MCP servers and agent skills — where they're stored, how to install them, and which are worth it."}
    return head(a0) + body + FOOT + '<script src="/js/terminal.js?v=' + AV + '" defer></script>\n<script src="/js/site.js?v=' + AV + '" defer></script>\n</body>\n</html>\n'

def main():
    caps = json.load(open(DATA))["capabilities"]
    for c in caps: c.setdefault("slug", re.sub(r"[^a-z0-9]+", "-", c["id"].lower()).strip("-"))
    A = build_articles(caps)
    for a in A:
        open(os.path.join(OUT, a["slug"] + ".html"), "w").write(article_html(a))
    open(os.path.join(OUT, "index.html"), "w").write(index_page(A))
    print("generated %d articles + index -> %s" % (len(A), OUT))
    for a in A: print("  /learn/%s.html  (%s)" % (a["slug"], a.get("lang")))

if __name__ == "__main__":
    main()
