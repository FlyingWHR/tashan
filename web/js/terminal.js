// tashan — the terminal frame: top ticker, bottom status line, and a ⌘K command palette.
// Injected on every page (self-hosted, strict-CSP-safe). Data from the slim /data/index.json.
(function () {
  "use strict";
  var caps = [], jobs = [], ticker, statusline, pal, input, listEl, sel = 0, view = [];

  // ---------- build chrome ----------
  function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }

  function buildTicker() {
    ticker = el("div", "ticker"); ticker.setAttribute("aria-hidden", "true");
    var track = el("div", "ticker__track"); ticker.appendChild(track);
    document.body.insertBefore(ticker, document.body.firstChild);
    return track;
  }
  function buildStatus() {
    statusline = el("div", "statusline"); statusline.setAttribute("aria-hidden", "true");
    document.body.appendChild(statusline);
  }
  // MIRROR OF pipeline/chrome.py::VERDICT_LABEL / VERDICT_BLURB. Exposed on window because index.js
  // and capability.js each had their own copy of the chip and neither said what the word meant —
  // three renderers, one vocabulary, and the same drift this codebase keeps paying for.
  var VERDICT = {
    deep:    ["deep",        "documents every tool, with worked examples, setup and a stated limitation"],
    solid:   ["solid",       "documents the job properly, with examples you could follow"],
    thin:    ["thin",        "shallow — says what it does, not how to actually use it"]
    // No `wrapper`, no `slop`: both were withdrawn from the scale as claims we could not support.
    // Mirrors chrome.VERDICT_LABEL, which is the one definition on the Python side.
  };
  window.tashanVerdict = function (v, cls) {
    if (!v) return "";
    var d = VERDICT[v] || [v, ""];
    cls = cls || "vd";
    return '<span class="' + cls + " " + cls + "--" + v + '" title="Instruction depth: ' +
      esc(d[1]) + '">' + esc(d[0]) + "</span>";
  };
  function verdictHTML(v) { return window.tashanVerdict(v, "tk-v"); }

  function fillTicker(track) {
    var top = caps.slice(0, 26);
    var seg = top.map(function (c) {
      return '<span class="tk"><span class="tk-n">' + esc(disp(c)) + '</span> '
        + '<span class="tk-t">' + (c.tashan_score == null ? "—" : c.tashan_score) + '</span> ' + verdictHTML(c.expertise_verdict) + '</span>';
    }).join('<span class="tk-sep">·</span>');
    var content = '<span class="tk-lead">LIVE ▸ ranked by tashan score</span>' + seg + '<span class="tk-sep">·</span>';
    track.innerHTML = content + content; // identical halves → seamless -50% loop
  }
  function fillStatus(d) {
    statusline.innerHTML =
      '<span class="sl-a"><span class="sl-logo"></span>tashan.sh</span>'
      + '<span class="sl-i"><b>' + fmt(d.measured || d.ranked) + '</b> measured</span>'
      + '<span class="sl-i">of <b>' + fmt(d.total_capabilities) + '</b> tracked</span>'
      + '<span class="sl-sp"></span>'
      + '<span class="sl-k">press <kbd>⌘K</kbd> / <kbd>/</kbd> to search</span>'
      + '<span class="sl-i sl-dim">measured ' + fdate(d.generated_at) + '</span>';
    // chrome.py emits <p id="footMethod"> into the footer of all 6,113 pages, but only index.js ever
    // filled it — so every page except the homepage shipped a permanently empty paragraph where the
    // measurement date was supposed to be. This function already loads everywhere and already holds
    // the numbers, so fill it here and let index.js keep its own copy for the homepage.
    var fm = document.getElementById("footMethod");
    if (fm) fm.textContent = fmt(d.total_capabilities) + " capabilities · measured " + fdate(d.generated_at);
  }

  // ---------- command palette ----------
  // THE SEARCH ANSWERS "what do you need to get done", not only "name the package".
  // 69 task pages and 23 role pages existed and the search could not reach any of them — it matched
  // capability names and four static links, so the entire job-oriented tier was reachable only from
  // a footer link and the sitemap. Tasks carry author-written synonyms ("review a contract", "hooks",
  // "permissions"), which is exactly the vocabulary someone types when they do not know the name of
  // the tool they need.
  // Words that carry no intent — dropping them is what lets a typed sentence match a task label.
  var STOP = ["the", "for", "with", "and", "how", "help", "need", "want", "find", "best", "using",
              "from", "into", "that", "this", "your", "our", "get", "can", "any"];
  var PAGES = [
    { name: "The Index", id: "@index", href: "/", kind: "page" },
    { name: "Methodology", id: "@methodology", href: "/methodology.html", kind: "page" },
    { name: "Pricing", id: "@pricing", href: "/pricing.html", kind: "page" },
    { name: "About", id: "@about", href: "/about.html", kind: "page" }
  ];
  function buildPalette() {
    pal = el("div", "pal"); pal.setAttribute("role", "dialog"); pal.hidden = true;
    var box = el("div", "pal__box");
    var head = el("div", "pal__head");
    head.innerHTML = '<span class="pal__prompt">tashan&nbsp;❯</span>';
    input = el("input", "pal__input"); input.type = "text"; input.setAttribute("placeholder", "What do you need to get done?  (try: review a contract, kubernetes, deep)");
    input.setAttribute("aria-label", "Search capabilities");
    // id/name so it is a real named field, not an anonymous box: assistive tech and password
    // managers both key off them, and Chrome files an issue on a form field that has neither.
    input.id = "palSearch"; input.name = "q"; input.setAttribute("autocomplete", "off");
    // role=dialog without a name announces as "dialog"; point it at the only thing in the box.
    pal.setAttribute("aria-label", "Search capabilities");
    head.appendChild(input);
    listEl = el("div", "pal__list");
    var foot = el("div", "pal__foot"); foot.innerHTML = '<span><kbd>↑</kbd><kbd>↓</kbd> move</span><span><kbd>↵</kbd> open</span><span><kbd>esc</kbd> close</span><span class="pal__by">measured, not claimed</span>';
    box.appendChild(head); box.appendChild(listEl); box.appendChild(foot);
    pal.appendChild(box);
    document.body.appendChild(pal);
    var qTimer;                                            // debounce: don't rescan the whole index every keystroke
    input.addEventListener("input", function () { clearTimeout(qTimer); qTimer = setTimeout(function () { query(input.value); }, 90); });
    pal.addEventListener("click", function (e) { if (e.target === pal) close(); });
  }
  window.tashanSearch = function () { open(); };
  // Any visible control can open the palette — delegated, so a page only has to add the element.
  document.addEventListener("click", function (e) {
    if (e.target.closest && e.target.closest("#heroSearch, [data-search]")) open();
  });
  function open() { if (!pal) return; pal.hidden = false; document.body.classList.add("pal-open"); input.value = ""; query(""); input.focus(); }
  function close() { if (!pal) return; pal.hidden = true; document.body.classList.remove("pal-open"); }
  function query(q) {
    q = q.trim().toLowerCase();
    var pool;
    if (!q) {
      pool = PAGES.concat(jobs.slice(0, 6)).concat(caps.slice(0, 6));
    } else if (["deep", "solid", "thin", "wrapper", "slop"].indexOf(q) >= 0) {
      pool = caps.filter(function (c) { return c.expertise_verdict === q; });
    } else {
      // TOKEN MATCH, because people type sentences. A plain substring test could not answer "review
      // a contract" even though the contract-review task literally carries "contract review" as a
      // synonym — the words were in the wrong order with a stopword between them. Score each job by
      // how many meaningful query words it contains and rank on that.
      var toks = q.split(/[^a-z0-9]+/).filter(function (t) {
        return t.length > 2 && STOP.indexOf(t) < 0;
      });
      var scored = [];
      if (toks.length) {
        jobs.forEach(function (j) {
          var n = 0;
          for (var i = 0; i < toks.length; i++) {
            // Stem longer words to 5 chars so spelling and inflection stop mattering: "analyse"
            // (and "analysing", "analyzed") all reach "analysis" through "analy". Without this the
            // British spelling of a word in our own example copy returned nothing.
            var t = toks[i];
            if (j._s.indexOf(t) >= 0 || (t.length >= 6 && j._s.indexOf(t.slice(0, 5)) >= 0)) n++;
          }
          if (n) scored.push({ n: n, j: j });
        });
        scored.sort(function (x, y) { return y.n - x.n; });
      }
      pool = PAGES.filter(function (p) { return p.name.toLowerCase().indexOf(q) >= 0; })
        .concat(scored.map(function (x) { return x.j; }))
        .concat(caps.filter(function (c) { return c._s.indexOf(q) >= 0; }));   // _s: lowercased once at load
    }
    view = pool.slice(0, 40); sel = 0; renderList();
  }
  function renderList() {
    if (!view.length) { listEl.innerHTML = '<div class="pal__empty">no match — try a name, or a verdict like <b>deep</b></div>'; return; }
    listEl.innerHTML = view.map(function (o, i) {
      if (o.kind === "page" || o.kind === "job")
        return '<div class="pal__row' + (i === sel ? " is-sel" : "") + '" data-href="' + o.href + '">'
          + '<span class="pal__go">' + (o.kind === "job" ? o.what : "go") + '</span>'
          + '<span class="pal__nm">' + esc(o.name) + '</span></div>';
      return '<div class="pal__row' + (i === sel ? " is-sel" : "") + '" data-href="' + capHref(o) + '">'
        + '<span class="pal__badge">' + (o.tashan_score == null ? "—" : o.tashan_score) + '</span>'
        + '<span class="pal__nm">' + esc(disp(o)) + '</span>' + verdictHTML(o.expertise_verdict)
        + '<span class="pal__id">' + esc(o.id) + '</span></div>';
    }).join("");
    var s = listEl.querySelector(".is-sel"); if (s) s.scrollIntoView({ block: "nearest" });
    [].forEach.call(listEl.querySelectorAll(".pal__row"), function (r) {
      r.addEventListener("click", function () { location.href = r.getAttribute("data-href"); });
    });
  }
  function go() { var o = view[sel]; if (!o) return; location.href = o.href || capHref(o); }
  // slug is derived EXCEPT where the export ships an override — see index.js capHref. The derivation
  // must match build.py slugify() byte for byte, and `o.slug` wins when a collision made it wrong.
  function capHref(o) { return "/capability/" + (o.slug || o.id.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")) + ".html"; }
  // EXPORTED so a new page cannot invent a 16th slugify. compare.js wrote its own, dropped the
  // `o.slug` override, and sent the official pkg:@stripe/mcp (score 69) to /capability/
  // pkg-stripe-mcp.html — a page that exists and belongs to a DIFFERENT package, third-party
  // stripe-mcp at 45, shown under the same name. It never 404s, so nothing would have caught it.
  // One wrong row in 1,080 is the shape this bug always takes: invisible in every spot-check.
  window.tashanCapHref = capHref;

  // ---------- keys ----------
  document.addEventListener("keydown", function (e) {
    var typing = /^(input|textarea|select)$/i.test((e.target.tagName || ""));
    if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) { e.preventDefault(); pal.hidden ? open() : close(); return; }
    if (e.key === "/" && !typing && pal.hidden) { e.preventDefault(); open(); return; }
    if (pal.hidden) return;
    if (e.key === "Escape") { close(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(sel + 1, view.length - 1); renderList(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(sel - 1, 0); renderList(); }
    else if (e.key === "Enter") { e.preventDefault(); go(); }
  });

  // ---------- helpers ----------
  function disp(c) { return c.label || pretty(c.name); }
  function pretty(n) { return String(n).replace(/^@modelcontextprotocol\/server-/, "").replace(/-mcp$/, "").replace(/^mcp-server-/, "").replace(/^mcp-/, ""); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function fmt(n) { return (n == null) ? "—" : String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function fdate(iso) { if (!iso) return ""; return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }

  // Shared, session-cached index loader — reused by index.js too, so the slim index is fetched+parsed ONCE
  // per session instead of on every page navigation (it's `no-cache`, so each nav would otherwise re-round-trip).
  // At ~10k+ caps this becomes the SCALE.md D1 endpoint; sessionStorage is the correct interim.
  // A SESSION CACHE MUST BE ABLE TO GO STALE, or it outlives the data it copied. This one had no
  // expiry at all: sessionStorage survives reload AND hard-refresh (⌘⇧R does not clear it) and only
  // dies when the tab closes, so a tab left open across a pipeline run replayed its snapshot forever.
  // Observed: a tab kept reporting "757 capabilities measured · Jul 25" for three days while
  // /data/index.json served 4,852 — and because `_headers` no-cache only governs HTTP, revalidation
  // never got a chance to fix it. On a product whose whole claim is that the numbers are measured
  // today, silently serving a three-day-old export is the worst failure it has.
  // The TTL keeps the reason the cache exists (one fetch+parse per browsing session, not per nav)
  // while bounding how wrong it can be. Entries written by the old format lack `t`, so they fail this
  // check and re-fetch — existing sessions heal themselves with no migration.
  var INDEX_TTL_MS = 5 * 60 * 1000;
  // THE ONE LOADER. Both the palette here and the board in index.js call this — index.js does
  // `window.tashanIndex || fetch(...)`, so whatever this returns is what the page renders. Changing
  // the fetch in index.js alone is dead code; that was tried and never fired once.
  //
  // BOARD FIRST, CATALOGUED TAIL ON IDLE. board.json is the RANKED slice (1,080 rows, 40 KB gz);
  // catalogued.json is the 800 unrated rows (17 KB gz) that a ranking cannot order anyway. Splitting
  // them ended a first-paint budget that had been raised three times in three days chasing corpus
  // growth. index.json still carries both and is untouched, because the published CLI reads it and
  // trimming it would degrade copies already installed on people's machines.
  //
  // The cache KEY carries the shape. An old session holding the previous single-payload value under
  // the same key would keep serving it for the whole TTL, so a shape change needs a new key or it
  // heals only after the tab is closed.
  var CACHE_KEY = "tashan_index_v2";
  function mergeTail(d) {
    if (!d || !d.catalogued_at) return d;
    var pull = function () {
      fetch(d.catalogued_at).then(function (r) { return r.ok ? r.json() : null; }).then(function (t) {
        if (!t || !t.capabilities || !t.capabilities.length) return;
        var seen = {};
        (d.capabilities || []).forEach(function (c) { seen[c.id] = 1; });
        var add = t.capabilities.filter(function (c) { return !seen[c.id]; });
        if (!add.length) return;
        d.capabilities = (d.capabilities || []).concat(add);
        try { sessionStorage.setItem(CACHE_KEY, JSON.stringify({ t: Date.now(), d: d })); } catch (e) {}
        window.dispatchEvent(new CustomEvent("tashan:catalogued"));
      }).catch(function () {});
    };
    if (window.requestIdleCallback) requestIdleCallback(pull, { timeout: 4000 }); else setTimeout(pull, 1200);
    return d;
  }
  // tasks.json is 68 KB and BOTH terminal.js and index.js were fetching it on every homepage load —
  // 136 KB for one file, because each had its own copy of the call. Same shape of bug as the index
  // loader, one file over. Shared promise: whoever asks first pays, everyone else waits on it.
  window.tashanTasks = function () {
    if (!window.__tashanTasksP) {
      window.__tashanTasksP = fetch("/data/tasks.json")
        .then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
    }
    return window.__tashanTasksP;
  };
  window.tashanIndex = function () {
    if (window.__tashanIndexP) return window.__tashanIndexP;
    var p;
    try {
      var box = JSON.parse(sessionStorage.getItem(CACHE_KEY));
      if (box && box.d && box.t && (Date.now() - box.t) < INDEX_TTL_MS) p = Promise.resolve(box.d);
    } catch (e) {}
    // Falls back to index.json so a browser that reaches a deploy without board.json still renders.
    if (!p) p = fetch("/data/board.json")
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .catch(function () { return fetch("/data/index.json").then(function (r) { return r.json(); }); })
      .then(function (d) {
        try { sessionStorage.setItem(CACHE_KEY, JSON.stringify({ t: Date.now(), d: d })); } catch (e) {}
        return mergeTail(d);
      });
    window.__tashanIndexP = p;
    return p;
  };

  // ---------- boot ----------
  var track = buildTicker(); buildStatus(); buildPalette();
  window.tashanIndex().then(function (d) {
    caps = (d.capabilities || []).filter(function (c) { return c.id.indexOf("key:") !== 0; });
    caps.forEach(function (c) { c._s = (c.name + " " + c.id).toLowerCase(); });   // precompute search field once
    fillTicker(track); fillStatus(d);
  }).then(function () {
    return window.tashanTasks().then(function (t) {
      if (!t) return;
      (t.tasks || []).forEach(function (x) {
        jobs.push({ kind: "job", what: "task", name: x.label, href: "/task/" + x.slug + ".html",
                    _s: (x.label + " " + (x.synonyms || []).join(" ") + " " + (x.term || "")).toLowerCase() });
      });
      (t.roles || []).forEach(function (r) {
        jobs.push({ kind: "job", what: "job", name: r.label, href: "/role/" + r.id + ".html",
                    _s: r.label.toLowerCase() });
      });
    }).catch(function () {});
  }).catch(function () { if (statusline) statusline.innerHTML = '<span class="sl-a"><span class="sl-logo"></span>tashan.sh</span><span class="sl-k">press <kbd>⌘K</kbd> to search</span>'; });
})();
