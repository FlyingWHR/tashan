// tashan — capability detail: the measured dossier + the richest hub for one capability.
// A neutral instrument points OUTWARD — repo health, where the capability lives on every registry,
// and where its community actually is. Rendered from the exported measured data (v2).
(function () {
  "use strict";
  // THE MOUNT IS PART OF THE PRERENDER CONTRACT. This read getElementById("cap"), but prerender.py
  // emits <main class="wrap" id="main"> and never an id="cap" — so on all 5,788 generated dossiers el
  // was null, render() threw at el.innerHTML, the catch threw again, and the reader only ever saw the
  // static server HTML. Everything client-only (the per-client install tabs, Upkeep, Freshness) simply
  // did not exist. The <main> element is the one thing both halves agree on, so key on it and let the
  // id go. See [[prerender-and-capability-js-are-one-concept]].
  var el = document.querySelector("main");

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
      document.title = disp(o.c) + " — tashan";
      try { render(o.c, { generated_at: o.at, scorer: o.sv }); }
      catch (e) { console.error("render failed", e); el.innerHTML = notfound(); }
      // AFTER render, and in its own try. The Pro panel is server-rendered and lives outside the
      // element render() replaces, so it has to be upgraded separately — and a failure here must
      // never take the dossier with it. The shipped free state is a correct thing to leave on
      // screen; a blank page is not.
      try { proPanel(o.c); } catch (e) { console.error("pro panel failed", e); }
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

  // Checkout carries the capability that triggered it, so we learn which pages actually convert
  // rather than guessing. Set per render because several rows read it.
  var PRICING = "/pricing.html";
  var CAP_ID = "";

  function render(c, d) {
    CAP_ID = c.id || "";
    var fr = fresh(c.npm_last_publish || c.gh_pushed || c.last_seen);
    var co = (c.co_used || []).map(function (x) {
      return '<a href="/capability/' + slug(x.id) + '.html">' + esc(pretty(x.id.split(":").slice(1).join(":"))) + ' <span class="o-50">·' + x.n + '</span></a>';
    }).join("");

    el.innerHTML =
      '<div class="cap-hd">' +
        '<a class="back" href="/">&lsaquo; The Index</a>' +
        '<h1>' + esc(disp(c)) + vitalityChip(c) + '</h1>' +
        // The id led this line and was a longer restatement of the <h1> directly above it, with the
        // same string a third time in the install command. Machine key -> links row; see prerender.py.
        '<div class="cid"><span class="tag">' + esc(kindLabel(c.kind)) + '</span>' +
          // Gated on category_basis, not on category: an abstained row carries 'other' and would
          // otherwise link to a shelf nobody put it on. Mirrors prerender.py — the client replaces
          // the server render and the two have drifted three times.
          (c.category && c.category_basis && CAT[c.category] ? ' <a class="cattag cattag--link" href="/?cat=' + esc(c.category) + '">' + esc(CAT[c.category]) + '</a>' : '') +
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
        stat("tashan score", c.tashan_score == null ? "—" : c.tashan_score, "jade", "upkeep + freshness, gated by adoption") +
        stat("Instruction depth", c.expertise == null ? "—" : c.expertise, "jade",
             c.expertise_verdict ? "graded against the published rubric" : "not yet graded") +
        stat("Adoption", adoption(c), "", c.npm_downloads != null ? "npm downloads / week" : "distinct public repos") +
        stat("Upkeep", score(c.upkeep), "", "cadence · maintainers · status") +
        stat("Freshness", fr.txt, "", "latest release / push", fr.cls) +
        stat("Bus factor", busFactor(c), "", "distinct contributors", c.single_maintainer ? "fresh--cold" : "") +
        // Evidence coverage: the multiplier that discounts a score by up to 30% when inputs are
        // missing. Mirrors prerender.py::summary — this function replaces the server render, so a
        // component shown only there would be visible to crawlers and hidden from people, which is
        // the same drift as before with the halves swapped.
        stat("Evidence", c.coverage == null ? "—" : Math.round(c.coverage * 100) + "%",
             "", "how many of the score's inputs we actually have") +
      '</div>' +
      securityBlock(c) +
      (c.expertise_note ? '<div class="expert-read">' + vchip(c.expertise_verdict) +
        '<p>&ldquo;' + esc(c.expertise_note) + '&rdquo;</p><span class="expert-read__by mono">— tashan expertise-eval, read of the actual capability</span></div>' :
       // WHY A GRADE IS ABSENT, and it must survive hydration. prerender.py renders this and this
       // file did not, so on 528 pages — including @modelcontextprotocol/server-filesystem, third on
       // the board — the server said "Not graded: shares its documentation with 3 other
       // capabilities" and the client wiped it the instant it painted. The client REPLACES the
       // server render; the two are one concept and drift silently, which is the third time that
       // has happened here. Silence reads as "nobody looked" when the truth is that we looked and
       // refused to grade a document about something else, and that distinction is the product.
       c.doc_status ? '<div class="expert-read"><p class="mono fs-sm">Not graded: ' +
        esc(c.doc_status) + '.' + (/documentation with|never names it/.test(c.doc_status) ?
          ' A grade read off another project\u2019s document would borrow its credit, or its blame.'
          : '') + '</p></div>' : '') +
      changedBlock(c) +
      doctorCta() +
      proPanelFree(c) +
      closingPitch(c) +
      repoHealth(c) +
      alsoOn(c) +
      (co ? section("Configured alongside", '<div class="colist">' + co + '</div>', "In real public configs, these ship together.") : '') +
      community(c) +
      (c.tashan_score != null ? embedBlock(c) : '') +
      '<div class="callout mt-12"><b>What this means.</b> The tashan score blends how actively the ' +
        'capability is <b>maintained</b> (release cadence, maintainer/contributor count, deprecation, registry status) and how ' +
        '<b>fresh</b> it is, gated by real <b>adoption</b> — npm weekly downloads where published, distinct public ' +
        'configs otherwise. <b>Health</b> reads finished-but-loved (stable) apart from abandoned. It is <b>not</b> an ' +
        'outcome eval: does-it-actually-work-well testing and retention are on the ' +
        '<a class="link" href="/methodology.html">roadmap</a>. Measured ' + fdate(d.generated_at) +
        (d.scorer ? ", scorer " + esc(d.scorer) : "") + '. ' +
        // MIRRORS prerender.py::summary. The server render carries this line and this function
        // REPLACES the server render, so a link that exists only in prerender.py is a link no
        // reader with JS ever sees. See [[prerender-and-capability-js-are-one-concept]].
        '<a class="link" href="/support.html?ref=' + encodeURIComponent(CAP_ID) + '#corrections' +
        '">Something wrong here?</a></div>';

    wireTabs();
    wireCopy();
  }

  // ---------- tashan's read: turn the measured evidence into a one-line DECISION (the whole point) ----------
  function takeBlock(c) {
    if (c.tashan_score == null && !c.expertise_verdict) return "";
    var quality = { deep: "Deep, real domain work", solid: "Solid — does the job well",
      thin: "Thin — shallow coverage", wrapper: "A thin wrapper over an API", slop: "Low-quality, likely AI-slop" }[c.expertise_verdict];
    var maint = { active: "actively maintained", stable: "mature and stable", abandoned: "looks abandoned" }[c.vitality];
    var adopted = (c.npm_downloads >= 5e4 || c.config_reach >= 20) ? "broadly adopted"
                : (c.npm_downloads >= 5e3) ? "moderately adopted" : null;
    var risks = [];
    if (c.single_maintainer) risks.push("one primary maintainer");
    if (c.gh_archived) risks.push("the repo is archived");
    if (c.npm_deprecated) risks.push("the package is deprecated");
    // SECURITY FINDINGS BELONG IN THE HEADLINE READ. They are deliberately not inputs to the SCORE —
    // "well maintained" and "nothing known is wrong" are different claims, and azure is
    // Microsoft-official, scores 86 and runs an install script — but this line is not the score. It
    // is the one-sentence decision, and it already carries non-score risks (single maintainer,
    // archived, deprecated). Leaving security out of it produced pages that read "Worth a look —
    // deep, real domain work, actively maintained" directly above "Handles credentials or secrets".
    // That is the summary contradicting the evidence under it. The score is untouched.
    if (c.sec_advisory_count) {
      risks.push(c.sec_advisory_count + " known advisor" + (c.sec_advisory_count === 1 ? "y" : "ies"));
    }
    if (c.sec_install_script) risks.push("it runs a script at install time");
    var permList = [];
    try { permList = c.sec_permissions ? JSON.parse(c.sec_permissions) : []; } catch (e) { permList = []; }
    // Name the reach that would make someone stop and think, not every declared permission.
    if (permList.indexOf("credentials") >= 0) risks.push("it handles credentials");
    else if (permList.indexOf("shell") >= 0) risks.push("it can run shell commands");
    var t = c.tashan_score || 0, verdict, cls;
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
  // WHAT CHANGED RECENTLY — mirrors prerender.py::changed_block. The client REPLACES the server
// render, so anything the static page shows and this does not is wiped the instant JS runs; that
// has happened three times in this file. Free in full: the existence of a risk is never paywalled,
// and this is the clearest demonstration of the product there is.
var SEV_RANK = { high: 0, medium: 1, low: 2 };
// Mirrors prerender.py's closing line, and is suppressed for the same reason: changedBlock has
// already made the case on those pages, and saying it twice is how a measured page starts reading
// like a landing page. The client REPLACES the server render — omit this and 8,648 pages lose it
// the instant JS runs, which is the drift that has bitten this file three times.
// MIRRORS prerender.py::pro_panel — the FREE state, and it has to be here because render()
// replaces <main> wholesale. Without it the server-rendered panel is destroyed the instant JS runs
// and proPanel() finds no #pro to upgrade: the offer would exist for crawlers and vanish for every
// human. That is the drift this file has shipped three times, in the same place, for the same
// reason.
// Mirrors prerender.py::doctor_cta. The free action comes BEFORE the paid one, because the only
// organic arrivals we can see are package-name searches landing here, and the strongest thing we
// have to give them costs nothing. render() replaces <main>, so this must exist here too.
function doctorCta() {
  return '<section class="dcta">' +
    '<p class="dcta__lbl mono">You searched for one. Check the rest of your stack:</p>' +
    '<pre class="install__snip"><button class="install__copy install__copy--pre" type="button" ' +
    'data-copy="npx tashan-cli doctor">copy</button><code>npx tashan-cli doctor</code></pre>' +
    '<p class="dcta__sub">Reads the config already on your machine and names what is dead, ' +
    'deprecated or running code at install time. No account, nothing uploaded.</p></section>';
}

function proPanelFree(c) {
  var name = esc(c.label || c.name || 'this capability');
  var n = (c.changes || []).length;
  var line;
  if (n) {
    line = 'We recorded <b>' + n + (n === 1 ? ' change' : ' changes') + '</b> to ' + name +
      ' in the last 45 days. Pro tells you on the day — for the servers in your own config, ' +
      'not the ones you thought to look up.';
  } else if (c.tashan_score != null) {
    line = name + ' scores <b>' + Math.round(c.tashan_score) + '</b> today. Pro keeps the series, ' +
      'so you can see whether that is a project getting better or one on its way down.';
  } else {
    line = 'Pro adds the history to tashan doctor, so a run over your own config says which of ' +
      'yours gained an advisory or started running an install script — and what to move to.';
  }
  return '<section class="pro" id="pro" data-state="free">' +
    '<div class="pro__hd"><span class="pro__tag mono">tashan Pro</span>' +
    '<span class="pro__price mono">$6<span class="pro__per">/mo</span></span></div>' +
    '<p class="pro__lede">' + line + '</p>' +
    '<ul class="pro__list">' +
    '<li>Every score since we started measuring, for any capability</li>' +
    '<li>The named replacement when something you run is dying — not just that it is</li>' +
    '<li><code>tashan doctor</code> over the config you already have, on your machine</li>' +
    '</ul>' +
    '<p class="pro__cta"><a class="btn btn--primary" href="' + PRICING + '" ' +
    'data-e="cta" data-k="pro-dossier">Start a 7-day trial &rsaquo;</a>' +
    '<span class="pro__free mono"> Everything measured on this page stays free.</span></p>' +
    '</section>';
}

// ── the Pro half of the panel ────────────────────────────────────────────────────────────────
// prerender.py ships [data-state="free"] so a crawler reads the offer. This upgrades it in place
// once /api/account confirms an active licence, reusing the session cache site.js already keeps so
// browsing does not put a Polar round trip on every page.
//
// UPGRADE-ONLY, like the nav mark: it starts as the honest offer and only ever replaces it with
// more. A failed fetch, an expired licence or an unreachable API leaves the free state on screen,
// which is correct — never an optimistic Pro.
//
// A paying customer is not shown a price again. They have bought; repeating the offer is the
// fastest way to make a subscription feel like a nag.
function proPanel(c) {
  var el = document.getElementById('pro');
  if (!el) return;
  var acct = null;
  try {
    var raw = sessionStorage.getItem('tashan_acct');
    if (raw) { var p = JSON.parse(raw); if (p && p.a) acct = p.a; }
  } catch (e) { /* private mode — fall through to the fetch */ }
  if (acct) return acct.active ? paintPro(el, c) : undefined;
  fetch('/api/account', { headers: { accept: 'application/json' } })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (a) { if (a && a.active) paintPro(el, c); })
    .catch(function () { /* offline: the shipped offer is already the right thing to show */ });
}

function paintPro(el, c) {
  el.setAttribute('data-state', 'pro');
  var ch = c.changes || [];
  var rows = '';
  function row(k, v) {
    return '<div class="pro__row"><span class="pro__k mono">' + esc(k) + '</span>' +
           '<span class="pro__v">' + v + '</span></div>';
  }
  rows += row('Capability', esc(c.label || c.name || c.id));
  rows += row('Changes', ch.length ? esc(String(ch.length)) + ' in the last 45 days' :
                                     'none in the last 45 days');
  if (ch.length) {
    rows += row('Latest', '<b>' + esc(ch[0].what || '') + '</b>' +
      (ch[0].action ? '<br><span class="pro__k">' + esc(ch[0].action) + '</span>' : ''));
  }
  rows += row('History', '<a class="link" href="/methodology.html#history">' +
    'every score since we started measuring</a> &mdash; <code>tashan doctor --trend</code>');
  el.querySelector('.pro__lede').innerHTML =
    'You have Pro. Here is the record behind ' + esc(c.label || c.name || 'this capability') + '.';
  var list = el.querySelector('.pro__list');
  if (list) list.outerHTML = '<div class="pro__rows">' + rows + '</div>';
}

function closingPitch(c) {
  if ((c.changes || []).length) return '';
  return '<p class="chg__pro mono fs-sm">Everything on this page is public evidence and free. ' +
    'What it cannot know is whether <em>you</em> run this — <code>npx tashan-cli doctor</code> ' +
    'reads your own config and names what is wrong in it, also free. ' +
    '<a class="link" href="/pricing.html">tashan Pro</a> tells you the day any of it changes.</p>';
}

function changedBlock(c) {
  var ch = (c.changes || []).slice().sort(function (a, b) {
    return (SEV_RANK[a.sev] == null ? 3 : SEV_RANK[a.sev]) - (SEV_RANK[b.sev] == null ? 3 : SEV_RANK[b.sev]);
  }).slice(0, 3);
  if (!ch.length) return '';
  var items = ch.map(function (x) {
    return '<li class="chg chg--' + esc(x.sev || 'low') + '">' +
      '<span class="chg__at mono">' + esc(x.at || '') + '</span> <b>' + esc(x.what || '') + '</b>' +
      (x.why ? '<span class="chg__why"> ' + esc(x.why) + '</span>' : '') + '</li>';
  }).join('');
  return '<section class="changed"><h2 class="sec-h">What changed recently</h2>' +
    '<ul class="chg-list">' + items + '</ul>' +
    '<p class="chg__pro mono fs-sm">You are reading this because you came looking. ' +
    '<a class="link" href="/pricing.html">tashan Pro</a> tells you the day it happens, for the ' +
    'servers in your own config — <code>tashan doctor</code>.</p></section>';
}

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
    var q = encodeURIComponent(disp(c));
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
      "Where " + esc(disp(c)) + " is actually discussed — its own repo and threads, not a generic forum.");
  }

  // model-company official detection (visual tagging) — from npm scope / repo owner
  // An endorsement claim has ONE definition: build.py::official_of, resolved at export time. This
  // held a stale copy of the old substring rule and badged @atomicmail/mcp-modelcontextprotocol as
  // Anthropic — contradicting the board, on the same capability. Read the answer, never re-derive it.
  function officialOrg(c) { return c.official || null; }

  // ---------- Works-with: which agent clients this capability runs in (protocol-derived, honest) ----------
  // COMPATIBILITY IS A CLAIM, AND IT WAS BEING MADE WITHOUT EVIDENCE. This printed a flat list of
  // eight client names for every npm-backed capability in the corpus, derived from `kind` alone —
  // so a Claude Code plugin and a generic stdio server made the identical claim, and "Works with
  // VS Code" appeared on thousands of pages nobody had checked. Optimistic coverage is the opposite
  // of the precision this product sells.
  //
  // What we can honestly support is a LEVEL, and the level's basis:
  //   native      the artifact type IS this client's own format (a plugin is a Claude Code plugin)
  //   installable the client documents how to load this artifact type (every MCP client documents
  //               stdio server config; that is the CLIENT's promise, not this publisher's)
  //   manual      it can be copied or configured by hand, with no documented installer
  // Anything we cannot place is simply absent — an omission is honest, a guess is not. Mirrors
  // prerender.py::works_with; the two render the same row and must agree.
  var MCP_CLIENTS = ["Claude Code", "Cursor", "Claude Desktop", "Codex CLI", "Gemini CLI", "Cline",
                     "Windsurf", "VS Code"];
  var REMOTE_CLIENTS = ["Claude Code", "Cursor", "Claude Desktop", "Codex CLI", "Gemini CLI", "ChatGPT"];

  function compatibility(c) {
    if (c.kind === "plugin") return [["native", ["Claude Code"]]];
    if (c.kind === "skill")  return [["native", ["Claude Code"]], ["manual", ["Cursor", "Codex CLI"]]];
    if (c.kind === "remote") return [["installable", REMOTE_CLIENTS]];
    return [["installable", MCP_CLIENTS]];
  }

  function worksWith(c) {
    var groups = compatibility(c);
    var basis = c.kind === "plugin" || c.kind === "skill"
      ? "from the artifact type — a " + esc(c.kind) + " is a Claude Code format"
      : "from the artifact type and each client's own documented MCP support — not verified against this capability";
    return '<div class="worksrow"><span class="worksrow__l mono">Works with</span>' +
      groups.map(function (g) {
        return g[1].map(function (n) {
          return '<span class="wchip wchip--' + g[0] + '" title="' + esc(g[0]) + ' — ' + basis + '">' +
            esc(n) + ' <i class="wchip__lvl">' + g[0] + '</i></span>';
        }).join("");
      }).join("") + '</div>';
  }

  // ---------- install: per-client tabs (the biggest real usage pain = cross-client config) ----------
  // terminal.js owns the verdict vocabulary and loads on every page before this one. Guard the call
  // anyway: a cross-file global is a load-order dependency, and if terminal.js ever fails to arrive
  // the dossier should render a plain chip rather than throw and show nothing at all. The headless
  // render test found this by running this file alone, which is exactly the condition being guarded.
  function vchip(v) {
    if (!v) return "";
    return window.tashanVerdict ? window.tashanVerdict(v)
      : '<span class="vd vd--' + esc(v) + '">' + esc(v) + "</span>";
  }

  function installBlock(c) {
    // DISCONTINUED: no install path, at all. This function REPLACES the server render, so a stop
    // notice that exists only in prerender.py is a stop notice no reader with JS ever sees — and the
    // failure mode is the worst one available here, a page quietly offering to install something we
    // have been told is switched off. Mirrors prerender.py::summary.
    if (c.discontinued) {
      var notice = c.self_unmaintained || c.description || "";
      return '<div class="callout callout--stop"><b>Discontinued — do not install.</b> ' +
        (notice ? "The author's own notice: &ldquo;" + esc(String(notice).slice(0, 200)) + "&rdquo; " : "") +
        "It stays listed so anyone already running it can find this page, and so " +
        "<code>npx tashan-cli doctor</code> can warn about it. It is not scored and does not " +
        "appear in any ranking.</div>";
    }
    var links = [];
    if (c.npm_pkg) links.push('<a class="link" href="https://www.npmjs.com/package/' + encodeURIComponent(c.npm_pkg) + '">npm ↗</a>');
    if (c.source_repo) links.push('<a class="link" href="https://github.com/' + enc(c.source_repo) + '">source ↗</a>');
    links.push('<span class="capid" title="the id the CLI and API use">' + esc(c.id) + '</span>');
    var linksHTML = links.length ? '<span class="install__links">' + links.join(' &nbsp;·&nbsp; ') + '</span>' : '';

    if (c.kind === "skill") {
      // collapse + strip: a leading "-" would make `cp -r -foo …` parse as a flag, not a folder
      var folder = pretty(c.name).replace(/[^a-z0-9_-]/gi, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
      return '<div class="install"><div class="install__hd"><h2>Install</h2>' + linksHTML + '</div>' +
        tabs(c, [
          ["Claude Code", "Drop the skill folder into your skills directory:", "cp -r " + folder + " ~/.claude/skills/", "sh"],
          ["Project", "Or scope it to one project:", "cp -r " + folder + " .claude/skills/", "sh"]
        ]) + '</div>';
    }
    // A PLUGIN IS NOT A REMOTE SERVER. With no branch of its own, every Claude Code plugin fell into
    // the npm-less catch-all below and 3,624 pages told the reader to "configure it from its source"
    // as though it were a hosted endpoint. Two steps, because a marketplace must be registered before
    // anything in it can be installed — and the marketplace NAME is not its repo (anthropics/
    // claude-plugins-community publishes as "claude-community"), so both halves are carried.
    // Mirrors prerender.py::summary — the client REPLACES that render, so the two must agree.
    if (c.kind === "plugin" && c.plugin_market_repo && c.title) {
      return '<div class="install"><div class="install__hd"><h2>Install</h2>' + linksHTML + '</div>' +
        tabs(c, [
          ["Claude Code", "Register the marketplace, then install from it:",
           "/plugin marketplace add " + c.plugin_market_repo + "\n/plugin install " + c.name + "@" + c.title,
           "sh"]
        ]) + '<p class="install__lbl">Run <code>/reload-plugins</code> to activate it in the current session.</p></div>';
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
      '<img class="embed__badge" src="/badge/' + slug(c.id) + '.svg" alt="tashan badge for ' + esc(disp(c)) + '">' +
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
  // ---------- security audit: entirely free ---------------------------------------------------
  // Every finding AND its actionable detail — which advisory, the version that fixes it, the exact
  // install command — is shown to everyone. The detail used to be the paid half; charging for the
  // remediation of a vulnerability we just reported is the one move an independent rater does not
  // get to make. Pro sells time (history, change alerts), never the current state.
  var PERM_LABEL = {
    filesystem: "Reads and writes files", shell: "Runs shell commands",
    network: "Makes network requests", browser: "Drives a browser",
    database: "Connects to databases", credentials: "Handles credentials or secrets",
    cloud: "Talks to cloud provider APIs"
  };
  var SEV_CLS = { MALICIOUS: "sev--mal", CRITICAL: "sev--crit", HIGH: "sev--high",
                  MODERATE: "sev--mod", MEDIUM: "sev--mod", LOW: "sev--low" };

  // Mirror of prerender.py::advisory_detail — both render the same row and must agree.
  function advisoryDetail(c) {
    var adv = c.sec_advisories || [];
    if (typeof adv === "string") { try { adv = JSON.parse(adv); } catch (e) { adv = []; } }
    if (!adv.length) return '<span class="secrow__ok">see the advisory database for detail</span>';
    return '<span class="secrow__ok">' + adv.slice(0, 6).map(function (a) {
      return "<code>" + esc(a.id || "?") + "</code> " +
        (a.fixed ? "fixed in " + esc(a.fixed) : "no fix published");
    }).join(" · ") + "</span>";
  }

  // The /api/security round trip that used to live here is GONE. It fetched the advisory list and
  // the install command for licence holders and swapped them into the free rows; both now ship in
  // the inline island for every reader, so there is nothing left to reveal. See build.py::redact_paid.

  function secRow(label, value, detail, cls) {
    return '<div class="secrow' + (cls ? " " + cls : "") + '">' +
      '<span class="secrow__l">' + label + '</span>' +
      '<span class="secrow__v mono">' + (value || "") + '</span>' +
      '<span class="secrow__d">' + (detail || "") + '</span></div>';
  }

  function securityBlock(c) {
    if (!c.sec_scanned_at) {
      // Never imply an audit happened. An unscanned capability says so, and says why.
      return section("Security audit",
        '<p class="hubnote">Not scanned yet. We audit npm-published capabilities for known ' +
        'advisories, install-time scripts and permission surface; this one has no npm package we ' +
        'can resolve, or has not reached the queue.</p>', "");
    }
    var rows = [], perms = [];
    try { perms = c.sec_permissions ? JSON.parse(c.sec_permissions) : []; } catch (e) { perms = []; }

    var n = c.sec_advisory_count || 0;
    if (n) {
      var sev = c.sec_max_severity || "UNKNOWN";
      rows.push(secRow(
        '<b>' + n + ' known advisor' + (n === 1 ? "y" : "ies") + '</b>',
        '<span class="sev ' + (SEV_CLS[sev] || "") + '">' + esc(sev.toLowerCase()) + '</span>',
        advisoryDetail(c),
        "secrow--alert"));
    } else {
      rows.push(secRow("No known advisories",
        '<span class="sev sev--none">clear</span>',
        '<span class="secrow__ok">checked against OSV for ' + esc(c.npm_latest_version || "the current release") + '</span>'));
    }

    if (c.sec_install_script) {
      rows.push(secRow("<b>Runs a script at install time</b>", '<span class="sev sev--high">code</span>',
        typeof c.sec_install_script === "string"
          ? '<code class="secrow__cmd">' + esc(c.sec_install_script) + "</code>"
          : '<span class="secrow__ok">a script runs on install</span>', "secrow--alert"));
    }

    if (perms.length) {
      // The export ships only the FIRST permission plus sec_perm_n, because the full list is what a
      // licence buys — it used to ship whole, in a file anyone can curl. perms.length would now
      // always be 1, so the count comes from the field.
      // Every permission, named, for free. "What it can reach on your machine" is the free tier's
      // own promise on the pricing page — gating it sold the same fact twice and left the headline
      // read unable to warn about credentials.
      rows.push(secRow(
        esc(perms.map(function (p) { return PERM_LABEL[p] || p; }).join(" · ")), "",
        '<span class="secrow__ok">from declared dependencies</span>'));
    } else {
      // Mirrors prerender.py: an empty result is "nothing declared", never "nothing possible".
      rows.push(secRow("No access inferred from declared dependencies", "",
        '<span class="secrow__ok">nothing it depends on reaches files, shell or network. This reads ' +
        "declarations only — built-in APIs are invisible to it, so absence of a declaration is not " +
        "absence of access</span>"));
    }

    if (c.sec_remote_content) {
      rows.push(secRow("Can carry remote content into your agent", "",
        '<span class="secrow__ok">it can pull third-party text into the model\'s context — treat ' +
        "what it returns as untrusted input</span>"));
    }
    rows.push(secRow(c.sec_provenance ? "Signed build provenance" : "No build provenance",
      "", '<span class="secrow__ok">' + (c.sec_provenance
        ? "published from public CI with an attestation"
        : "no attestation — the published artifact cannot be traced to its source") + "</span>",
      c.sec_provenance ? "" : "secrow--warn"));

    // No offer, no "unlock": nothing in this section is gated. Mirrors prerender.py::security_block,
    // and it has to — this function REPLACES the prerendered dossier via el.innerHTML, so the two
    // must render the same audit or one of them is a lie about the other.
    return section("Security audit", '<div class="sec">' + rows.join("") + '</div>',
      "Every finding is shown in full — which advisory, the version that fixes it, and the exact " +
      "command run at install time. Nothing in this audit is behind a licence.",
      "scanned " + fdate(c.sec_scanned_at));
  }

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
  // see index.js disp(): the label is derived once in build.py over the whole corpus.
  function disp(c) { return c.label || pretty(c.name); }
  function pretty(name) { return String(name).replace(/^@modelcontextprotocol\/server-/, "").replace(/-mcp$/, "").replace(/^mcp-server-/, "").replace(/^mcp-/, ""); }
  function enc(repo) { return String(repo).split("/").map(encodeURIComponent).join("/"); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function fmt(n) { return (n == null) ? "—" : String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function fdate(iso) { if (!iso) return ""; return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  function notfound() { return '<div class="cap-hd"><a class="back" href="/">&lsaquo; The Index</a><h1>Not tracked yet</h1><div class="cid">This capability isn\'t in the current pass. The Index grows every run.</div></div>'; }

  boot();  // run last — all helpers + data constants (CAT, _tabSeq) are initialized by now
})();
