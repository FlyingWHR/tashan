// tashan — capability detail: the measured dossier + the richest hub for one capability.
// A neutral instrument points OUTWARD — repo health, where the capability lives on every registry,
// and where its community actually is. Rendered from the exported measured data (v2).
(function () {
  "use strict";
  var el = document.getElementById("cap");

  // boot() runs LAST (see the call at the end of this IIFE) so every helper and data constant — CAT,
  // _tabSeq, etc. — is initialized before render() is ever called. (var assignments below only run when
  // execution reaches them; calling render() from up here would see them still undefined.)
  function boot() {
  // FAST PATH: a prerendered page carries this cap's full data inline — render instantly, no network.
  // If an island is present we are ALREADY on the canonical page, so we never navigate away from here —
  // a parse/render error shows a message, it must never trigger a redirect (that would reload-loop).
  var island = document.getElementById("cap-data");
  if (island) {
    var o = null;
    try { o = JSON.parse(island.textContent); } catch (e) { console.error("cap-data parse failed", e); }
    if (o && o.c) {
      document.title = pretty(o.c.name) + " — tashan";
      try { render(o.c, { generated_at: o.at }); }
      catch (e) { console.error("render failed", e); el.innerHTML = notfound(); }
    } else {
      el.innerHTML = notfound();
    }
    return;
  }

  // LEGACY PATH: /capability.html?id=… (old links / bookmarks) — no island. Redirect to the prerendered
  // page (never to ourselves) instead of pulling the 1.2 MB export at runtime.
  var meta = document.querySelector('meta[name="cap-id"]');
  var id = new URLSearchParams(location.search).get("id") || (meta ? meta.content : "") || "";
  var target = id ? "/capability/" + slug(id) + ".html" : "";
  if (target && target !== location.pathname) { location.replace(target); return; }
  el.innerHTML = notfound();
  }

  function render(c, d) {
    var fr = fresh(c.npm_last_publish || c.gh_pushed || c.last_seen);
    var co = (c.co_used || []).map(function (x) {
      return '<a href="/capability/' + slug(x.id) + '.html">' + esc(pretty(x.id.split(":").slice(1).join(":"))) + ' <span style="opacity:.5">·' + x.n + '</span></a>';
    }).join("");

    el.innerHTML =
      '<div class="cap-hd">' +
        '<a class="back" href="/">&lsaquo; The Index</a>' +
        '<h1>' + esc(pretty(c.name)) + vitalityChip(c) + '</h1>' +
        '<div class="cid">' + esc(c.id) + ' &nbsp;·&nbsp; <span class="tag">' + esc(kindLabel(c.kind)) + '</span>' +
          (c.category && CAT[c.category] ? ' <a class="cattag cattag--link" href="/?cat=' + esc(c.category) + '">' + esc(CAT[c.category]) + '</a>' : '') +
          (officialOrg(c) ? ' <span class="official">✓ ' + esc(officialOrg(c)) + ' · official</span>' : '') +
          (c.single_maintainer ? ' <span class="riskflag" title="One primary maintainer — a bus-factor risk">◑ single-maintainer</span>' : '') +
          (c.npm_deprecated ? ' &nbsp;·&nbsp; <span class="fresh fresh--cold">deprecated</span>' : '') +
          (c.gh_archived ? ' &nbsp;·&nbsp; <span class="fresh fresh--cold">archived</span>' : '') + '</div>' +
        (c.description ? '<p class="cap-desc">' + esc(c.description) + '</p>' : '') +
      '</div>' +
      takeBlock(c) +
      worksWith(c) +
      installBlock(c) +
      '<div class="stats">' +
        stat("Trust", c.trust == null ? "—" : c.trust, "jade", "maintenance + freshness, gated by adoption") +
        stat("Expertise", c.expertise == null ? "—" : c.expertise, "jade", c.expertise_verdict ? "LLM-graded: " + c.expertise_verdict : "not yet graded") +
        stat("Adoption", adoption(c), "", c.npm_downloads != null ? "npm downloads / week" : "distinct public repos") +
        stat("Maintenance", score(c.maintenance), "", "cadence · maintainers · status") +
        stat("Freshness", fr.txt, "", "latest release / push", fr.cls) +
        stat("Bus factor", busFactor(c), "", "distinct contributors", c.single_maintainer ? "fresh--cold" : "") +
      '</div>' +
      (c.expertise_note ? '<div class="expert-read"><span class="vd vd--' + esc(c.expertise_verdict) + '">' + esc(c.expertise_verdict) + '</span>' +
        '<p>&ldquo;' + esc(c.expertise_note) + '&rdquo;</p><span class="expert-read__by mono">— tashan expertise-eval, read of the actual capability</span></div>' : '') +
      repoHealth(c) +
      alsoOn(c) +
      (co ? section("Configured alongside", '<div class="colist">' + co + '</div>', "In real public configs, these ship together.") : '') +
      community(c) +
      (c.trust != null ? embedBlock(c) : '') +
      '<div class="callout" style="margin-top:var(--sp-12)"><b>What this means.</b> Trust blends how actively the ' +
        'capability is <b>maintained</b> (release cadence, maintainer/contributor count, deprecation, registry status) and how ' +
        '<b>fresh</b> it is, gated by real <b>adoption</b> — npm weekly downloads where published, distinct public ' +
        'configs otherwise. <b>Vitality</b> reads finished-but-loved (stable) apart from abandoned. It is <b>not</b> an ' +
        'outcome eval: does-it-actually-work-well testing and retention are on the ' +
        '<a class="link" href="/methodology.html">roadmap</a>. Measured ' + fdate(d.generated_at) + '.</div>';

    wireTabs();
    wireCopy();
  }

  // ---------- tashan's read: turn the measured evidence into a one-line DECISION (the whole point) ----------
  function takeBlock(c) {
    if (c.trust == null && !c.expertise_verdict) return "";
    var quality = { deep: "Deep, real domain work", solid: "Solid — does the job well",
      thin: "Thin — shallow coverage", wrapper: "A thin wrapper over an API", slop: "Low-quality, likely AI-slop" }[c.expertise_verdict];
    var maint = { active: "actively maintained", stable: "mature and stable", abandoned: "looks abandoned" }[c.vitality];
    var adopted = (c.npm_downloads >= 5e4 || c.config_reach >= 20) ? "broadly adopted"
                : (c.npm_downloads >= 5e3) ? "moderately adopted" : null;
    var risks = [];
    if (c.single_maintainer) risks.push("one primary maintainer");
    if (c.gh_archived) risks.push("the repo is archived");
    if (c.npm_deprecated) risks.push("the package is deprecated");
    var t = c.trust || 0, verdict, cls;
    if (c.gh_archived || c.npm_deprecated) { verdict = "Proceed with care"; cls = "take--warn"; }
    else if (t >= 80 && (c.expertise_verdict === "deep" || c.expertise_verdict === "solid")) { verdict = "A safe default"; cls = "take--good"; }
    else if (t >= 62) { verdict = "Worth a look"; cls = "take--ok"; }
    else { verdict = "Weigh the evidence"; cls = "take--ok"; }
    var facts = [quality, maint, adopted].filter(Boolean).join(", ");
    facts = facts ? facts.charAt(0).toUpperCase() + facts.slice(1) + "." : "Scored on public evidence.";
    var riskStr = risks.length ? ' <span class="take__risk">Watch: ' + esc(risks.join(", ")) + '.</span>' : "";
    return '<div class="take ' + cls + '"><span class="take__v">' + esc(verdict) + '</span>' +
      '<p class="take__t">' + esc(facts) + riskStr + '</p></div>';
  }

  // ---------- vitality chip (Active / Stable / Abandoned — "finished != dead") ----------
  function vitalityChip(c) {
    if (!c.vitality) return "";
    var meta = {
      active:    ["● active", "vd--deep", "Actively maintained — recent commits or releases"],
      stable:    ["◐ stable", "vd--solid", "Mature & maintained — quiet but still adopted, low unresolved-issue pressure"],
      abandoned: ["○ abandoned", "vd--wrapper", "Stale under issue pressure, deprecated, or archived"]
    }[c.vitality];
    if (!meta) return "";
    return ' <span class="vchip ' + meta[1] + '" title="' + esc(meta[2]) + '">' + esc(meta[0]) + '</span>';
  }

  // ---------- GitHub repo health (the capability's own source repo) ----------
  function repoHealth(c) {
    if (!c.source_repo || c.gh_stars == null) return "";
    var rows = [];
    rows.push(hstat("Stars", fmt(c.gh_stars)));
    if (c.gh_forks != null) rows.push(hstat("Forks", fmt(c.gh_forks)));
    if (c.gh_contributors != null) rows.push(hstat("Contributors", fmt(c.gh_contributors) + (c.single_maintainer ? " ◑" : ""), c.single_maintainer ? "bus-factor risk" : ""));
    if (c.gh_open_issues != null) rows.push(hstat("Open issues", fmt(c.gh_open_issues), issuePressure(c)));
    if (c.gh_last_release) rows.push(hstat("Latest release", fdate(c.gh_last_release)));
    if (c.gh_pushed) rows.push(hstat("Last push", fdate(c.gh_pushed)));
    if (c.gh_license) rows.push(hstat("License", esc(c.gh_license)));
    var topics = (c.gh_topics || []).slice(0, 6).map(function (t) { return '<span class="topic">' + esc(t) + '</span>'; }).join("");
    var warn = c.gh_archived ? '<p class="repo__warn">⚠ This repository is <b>archived</b> — no further maintenance is expected.</p>' : "";
    return section("Repository health",
      '<div class="hstats">' + rows.join("") + '</div>' +
      (topics ? '<div class="topics">' + topics + '</div>' : "") + warn,
      'Signals from the capability’s own source repo — is it maintained, or just done?',
      '<a class="link" href="https://github.com/' + esc(c.source_repo) + '">' + esc(c.source_repo) + ' ↗</a>');
  }

  function issuePressure(c) {
    if (!c.gh_stars || c.gh_open_issues == null) return "";
    var r = c.gh_open_issues / Math.max(c.gh_stars, 1);
    return r > 0.15 ? "elevated" : "low pressure";
  }

  // ---------- "Also on" — registry cross-links (a neutral instrument points everywhere) ----------
  function alsoOn(c) {
    var direct = [], search = [];
    if (c.npm_pkg) direct.push(xlink("npm", "https://www.npmjs.com/package/" + encodeURIComponent(c.npm_pkg)));
    if (c.source_repo) {
      direct.push(xlink("GitHub", "https://github.com/" + enc(c.source_repo)));
      direct.push(xlink("Glama", "https://glama.ai/mcp/servers/" + enc(c.source_repo)));
    }
    var q = encodeURIComponent(pretty(c.name));
    search.push(xlink("mcp.so", "https://mcp.so/search?q=" + q));
    search.push(xlink("Smithery", "https://smithery.ai/?q=" + q));
    search.push(xlink("PulseMCP", "https://www.pulsemcp.com/servers?q=" + q));
    if (c.registry_name) search.push(xlink("MCP registry", "https://registry.modelcontextprotocol.io/?search=" + encodeURIComponent(c.registry_name)));
    return section("Also measured / listed on",
      '<div class="xlinks">' + direct.join("") +
        '<span class="xlinks__sep" title="These use custom slugs — links go to their search">search ↓</span>' +
        search.join("") + '</div>',
      'We don’t lock you in. Cross-check the same capability wherever it’s listed.');
  }

  // ---------- Community — where this capability's people actually are ----------
  // Community = where THIS capability is actually discussed — its own repo/chat/threads. Never a generic
  // forum. If we can't point to a real, specific community, we show nothing (honest > padded).
  function community(c) {
    var links = [];
    if (c.gh_homepage && !/npmjs\.(org|com)|github\.com/i.test(c.gh_homepage))             // skip npm/github (redundant)
      links.push(xlink("Homepage / docs", c.gh_homepage));                                // the project's own site
    if (c.discord_url)
      links.push(xlink("Discord", c.discord_url));                                        // the project's own chat
    if (c.gh_has_discussions && c.source_repo)
      links.push(xlink("GitHub Discussions", "https://github.com/" + enc(c.source_repo) + "/discussions"));
    if (c.source_repo)
      links.push(xlink("Issues" + (c.gh_open_issues != null ? " · " + fmt(c.gh_open_issues) + " open" : ""),
        "https://github.com/" + enc(c.source_repo) + "/issues"));
    if (!links.length) return "";                                                          // no real community -> no section
    return section("Community & support",
      '<div class="xlinks">' + links.join("") + '</div>',
      "Where " + esc(pretty(c.name)) + " is actually discussed — its own repo and threads, not a generic forum.");
  }

  // model-company official detection (visual tagging) — from npm scope / repo owner
  function officialOrg(c) {
    var s = ((c.npm_pkg || "") + " " + (c.source_repo || "")).toLowerCase();
    if (/modelcontextprotocol|anthropic/.test(s)) return "Anthropic";
    if (/(^|[\/@\s])openai/.test(s)) return "OpenAI";
    if (/google|googleapis|gemini/.test(s)) return "Google";
    if (/(^|[\/@\s])microsoft|(^|\/)azure/.test(s)) return "Microsoft";
    return null;
  }

  // ---------- Works-with: which agent clients this capability runs in (protocol-derived, honest) ----------
  function worksWith(c) {
    var clients;
    if (c.kind === "skill") clients = ["Claude Code", "Cursor", "Codex CLI"];        // skill-supporting clients
    else if (c.kind === "remote") clients = ["Claude Code", "Cursor", "Claude Desktop", "Codex CLI", "Gemini CLI", "ChatGPT"];
    else clients = ["Claude Code", "Cursor", "Claude Desktop", "Codex CLI", "Gemini CLI", "Cline", "Windsurf", "VS Code"];  // any MCP client
    return '<div class="worksrow"><span class="worksrow__l mono">Works with</span>' +
      clients.map(function (n) { return '<span class="wchip">' + esc(n) + '</span>'; }).join("") + '</div>';
  }

  // ---------- install: per-client tabs (the biggest real usage pain = cross-client config) ----------
  function installBlock(c) {
    var links = [];
    if (c.npm_pkg) links.push('<a class="link" href="https://www.npmjs.com/package/' + encodeURIComponent(c.npm_pkg) + '">npm ↗</a>');
    if (c.source_repo) links.push('<a class="link" href="https://github.com/' + enc(c.source_repo) + '">source ↗</a>');
    var linksHTML = links.length ? '<span class="install__links">' + links.join(' &nbsp;·&nbsp; ') + '</span>' : '';

    if (c.kind === "skill") {
      var folder = pretty(c.name).replace(/[^a-z0-9_-]/gi, "-");
      return '<div class="install"><div class="install__hd"><h2>Install</h2>' + linksHTML + '</div>' +
        tabs(c, [
          ["Claude Code", "Drop the skill folder into your skills directory:", "cp -r " + folder + " ~/.claude/skills/", "sh"],
          ["Project", "Or scope it to one project:", "cp -r " + folder + " .claude/skills/", "sh"]
        ]) + '</div>';
    }
    if (!c.npm_pkg) {
      return '<div class="install"><div class="install__hd"><h2>Install</h2>' + linksHTML + '</div>' +
        '<p class="install__lbl">Remote / registry server — configure it from its ' +
        (c.source_repo ? '<a class="link" href="https://github.com/' + enc(c.source_repo) + '">source</a>' : 'source') + '.</p></div>';
    }
    var name = pretty(c.name).replace(/[^a-z0-9_-]/gi, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
    var pkg = c.npm_pkg;
    var jsonSnip = '{\n  "mcpServers": {\n    "' + name + '": {\n      "command": "npx",\n      "args": ["-y", "' + pkg + '"]\n    }\n  }\n}';
    var tomlSnip = '[mcp_servers.' + name + ']\ncommand = "npx"\nargs = ["-y", "' + pkg + '"]';
    return '<div class="install">' +
      '<div class="install__hd"><h2>Install</h2>' + linksHTML + '</div>' +
      tabs(c, [
        ["Claude Code", "One command in your terminal:", "claude mcp add " + name + " -- npx -y " + pkg, "sh"],
        ["Cursor", "Add to <code>~/.cursor/mcp.json</code> (or a project <code>.cursor/mcp.json</code>):", jsonSnip, "json"],
        ["Claude Desktop", "Add to <code>claude_desktop_config.json</code>, then restart:", jsonSnip, "json"],
        ["Codex CLI", "Add to <code>~/.codex/config.toml</code>:", tomlSnip, "toml"],
        ["npx", "Run it directly:", "npx -y " + pkg, "sh"]
      ]) + '</div>';
  }

  var _tabSeq = 0;
  function tabs(c, items) {
    var gid = "tabs" + (_tabSeq++);
    var heads = items.map(function (it, i) {
      return '<button class="tab' + (i === 0 ? " is-on" : "") + '" data-tab="' + gid + '-' + i + '" type="button">' + esc(it[0]) + '</button>';
    }).join("");
    var panes = items.map(function (it, i) {
      var cid = gid + "-" + i + "-code";
      return '<div class="tabpane' + (i === 0 ? " is-on" : "") + '" id="' + gid + '-' + i + '">' +
        '<p class="install__lbl mono">' + it[1] + '</p>' +
        '<pre class="install__snip"><button class="install__copy install__copy--pre" data-copy-el="' + cid + '" type="button">copy</button>' +
        '<code id="' + cid + '" class="lang-' + it[3] + '">' + esc(it[2]) + '</code></pre></div>';
    }).join("");
    return '<div class="tabs" data-group="' + gid + '"><div class="tabs__hd">' + heads + '</div>' + panes + '</div>';
  }

  function wireTabs() {
    [].forEach.call(document.querySelectorAll(".tabs"), function (g) {
      g.addEventListener("click", function (e) {
        var b = e.target.closest(".tab"); if (!b) return;
        var target = b.getAttribute("data-tab");
        [].forEach.call(g.querySelectorAll(".tab"), function (x) { x.classList.toggle("is-on", x === b); });
        [].forEach.call(g.querySelectorAll(".tabpane"), function (p) { p.classList.toggle("is-on", p.id === target); });
      });
    });
  }

  var CAT = { browser:"Browser & Web", search:"Search", database:"Database", devtools:"Dev Tools & CI",
    cloud:"Cloud & Infra", files:"Files & Memory", data:"Data & Analytics", docs:"Docs & Knowledge",
    comms:"Communication", design:"Design", ai:"AI & Agents", finance:"Finance & Crypto",
    productivity:"Productivity", security:"Security", other:"Other" };

  function slug(id) { return String(id).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }
  function embedBlock(c) {
    var url = "https://tashan.sh/badge/" + slug(c.id) + ".svg";
    var page = "https://tashan.sh/capability/" + (c.slug || slug(c.id)) + ".html";
    var md = "[![tashan](" + url + ")](" + page + ")";
    return '<div class="embed">' +
      '<h2 class="embed__h">Show your score</h2>' +
      '<p class="embed__p">Measured this well? Put the live badge in your README — it updates as the score does.</p>' +
      '<img class="embed__badge" src="/badge/' + slug(c.id) + '.svg" alt="tashan badge for ' + esc(pretty(c.name)) + '">' +
      '<div class="embed__code"><code id="embedCode">' + esc(md) + '</code>' +
      '<button class="embed__copy" id="embedCopy" type="button">copy</button></div></div>';
  }

  function wireCopy() {
    var cp = document.getElementById("embedCopy");
    if (cp) cp.addEventListener("click", function () {
      copy(document.getElementById("embedCode").textContent, cp);
    });
    [].forEach.call(document.querySelectorAll(".install__copy"), function (b) {
      b.addEventListener("click", function () {
        var t = b.getAttribute("data-copy");
        if (!t && b.getAttribute("data-copy-el")) t = document.getElementById(b.getAttribute("data-copy-el")).textContent;
        if (t) copy(t, b);
      });
    });
  }
  function copy(text, btn) {
    var label = btn.textContent;
    (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject())
      .then(function () { btn.textContent = "copied ✓"; setTimeout(function () { btn.textContent = label; }, 1500); })
      .catch(function () { btn.textContent = "select"; });
  }

  // ---------- small helpers ----------
  function section(title, body, sub, aside) {
    return '<section class="capsec"><div class="capsec__hd"><h2>' + esc(title) + '</h2>' +
      (aside ? '<span class="capsec__aside mono">' + aside + '</span>' : "") + '</div>' +
      (sub ? '<p class="capsec__sub">' + sub + '</p>' : "") + body + '</section>';
  }
  function hstat(label, val, sub) {
    return '<div class="hstat"><span class="hstat__v mono">' + val + '</span><span class="hstat__l">' + esc(label) + '</span>' +
      (sub ? '<span class="hstat__s">' + esc(sub) + '</span>' : "") + '</div>';
  }
  function xlink(label, href) { return '<a class="xlink" href="' + href + '" rel="noopener">' + esc(label) + ' <span class="xlink__a">↗</span></a>'; }
  function kindLabel(k) { return k === "skill" ? "skill" : k; }
  function busFactor(c) { return c.gh_contributors != null ? String(c.gh_contributors) : (c.npm_maintainers != null ? String(c.npm_maintainers) : "—"); }
  function adoption(c) {
    if (c.npm_downloads != null) return compact(c.npm_downloads) + "/wk";
    if (c.config_reach) return fmt(c.config_reach);
    return "—";
  }
  function score(v) { return (v == null) ? "—" : String(v); }
  function stat(label, val, cls, sub, valcls) {
    return '<div class="stat"><p class="l">' + esc(label) + '</p>' +
      '<div class="v ' + (cls || "") + ' ' + (valcls || "") + '">' + esc(String(val)) + '</div>' +
      '<div class="s">' + esc(sub) + '</div></div>';
  }
  function fresh(iso) {
    if (!iso) return { txt: "—", cls: "fresh--warm" };
    var months = (Date.now() - new Date(iso).getTime()) / 2.63e9;
    if (months < 1.5) return { txt: "active", cls: "fresh--hot" };
    if (months < 12) return { txt: Math.round(months) + " mo ago", cls: "fresh--warm" };
    return { txt: (Math.round(months / 12 * 10) / 10) + " yr ago", cls: "fresh--cold" };
  }
  function compact(n) {
    if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + "M";
    if (n >= 1e3) return (n / 1e3).toFixed(n >= 1e4 ? 0 : 1) + "k";
    return String(n);
  }
  function pretty(name) { return String(name).replace(/^@modelcontextprotocol\/server-/, "").replace(/-mcp$/, "").replace(/^mcp-server-/, "").replace(/^mcp-/, ""); }
  function enc(repo) { return String(repo).split("/").map(encodeURIComponent).join("/"); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function fmt(n) { return (n == null) ? "—" : String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function fdate(iso) { if (!iso) return ""; return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  function notfound() { return '<div class="cap-hd"><a class="back" href="/">&lsaquo; The Index</a><h1>Not tracked yet</h1><div class="cid">This capability isn\'t in the current pass. The Index grows every run.</div></div>'; }

  boot();  // run last — all helpers + data constants (CAT, _tabSeq) are initialized by now
})();
