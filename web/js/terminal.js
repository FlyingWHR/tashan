// tashan — the terminal frame: top ticker, bottom status line, and a ⌘K command palette.
// Injected on every page (self-hosted, strict-CSP-safe). Data from the slim /data/index.json.
(function () {
  "use strict";
  var caps = [], ticker, statusline, pal, input, listEl, sel = 0, view = [];

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
  function verdictHTML(v) { return v ? '<span class="tk-v tk-v--' + v + '">' + v + '</span>' : ""; }

  function fillTicker(track) {
    var top = caps.slice(0, 26);
    var seg = top.map(function (c) {
      return '<span class="tk"><span class="tk-n">' + esc(pretty(c.name)) + '</span> '
        + '<span class="tk-t">' + (c.trust == null ? "—" : c.trust) + '</span> ' + verdictHTML(c.expertise_verdict) + '</span>';
    }).join('<span class="tk-sep">·</span>');
    var content = '<span class="tk-lead">LIVE ▸ ranked by trust</span>' + seg + '<span class="tk-sep">·</span>';
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
  }

  // ---------- command palette ----------
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
    input = el("input", "pal__input"); input.type = "text"; input.setAttribute("placeholder", "search capabilities…  (try: deep, kubernetes, notion)");
    input.setAttribute("aria-label", "Search capabilities");
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
  function open() { if (!pal) return; pal.hidden = false; document.body.classList.add("pal-open"); input.value = ""; query(""); input.focus(); }
  function close() { if (!pal) return; pal.hidden = true; document.body.classList.remove("pal-open"); }
  function query(q) {
    q = q.trim().toLowerCase();
    var pool;
    if (!q) {
      pool = PAGES.concat(caps.slice(0, 8));
    } else if (["deep", "solid", "thin", "wrapper", "slop"].indexOf(q) >= 0) {
      pool = caps.filter(function (c) { return c.expertise_verdict === q; });
    } else {
      pool = PAGES.filter(function (p) { return p.name.toLowerCase().indexOf(q) >= 0; })
        .concat(caps.filter(function (c) { return c._s.indexOf(q) >= 0; }));   // _s: lowercased once at load
    }
    view = pool.slice(0, 40); sel = 0; renderList();
  }
  function renderList() {
    if (!view.length) { listEl.innerHTML = '<div class="pal__empty">no match — try a name, or a verdict like <b>deep</b></div>'; return; }
    listEl.innerHTML = view.map(function (o, i) {
      if (o.kind === "page")
        return '<div class="pal__row' + (i === sel ? " is-sel" : "") + '" data-href="' + o.href + '"><span class="pal__go">go</span><span class="pal__nm">' + esc(o.name) + '</span></div>';
      return '<div class="pal__row' + (i === sel ? " is-sel" : "") + '" data-href="' + capHref(o) + '">'
        + '<span class="pal__badge">' + (o.trust == null ? "—" : o.trust) + '</span>'
        + '<span class="pal__nm">' + esc(pretty(o.name)) + '</span>' + verdictHTML(o.expertise_verdict)
        + '<span class="pal__id">' + esc(o.id) + '</span></div>';
    }).join("");
    var s = listEl.querySelector(".is-sel"); if (s) s.scrollIntoView({ block: "nearest" });
    [].forEach.call(listEl.querySelectorAll(".pal__row"), function (r) {
      r.addEventListener("click", function () { location.href = r.getAttribute("data-href"); });
    });
  }
  function go() { var o = view[sel]; if (!o) return; location.href = o.kind === "page" ? o.href : capHref(o); }
  // slug is derived, not shipped — see index.js capHref. Must match build.py slugify() byte for byte.
  function capHref(o) { return "/capability/" + o.id.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") + ".html"; }

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
  window.tashanIndex = function () {
    if (window.__tashanIndexP) return window.__tashanIndexP;
    var p;
    try {
      var box = JSON.parse(sessionStorage.getItem("tashan_index"));
      if (box && box.d && box.t && (Date.now() - box.t) < INDEX_TTL_MS) p = Promise.resolve(box.d);
    } catch (e) {}
    if (!p) p = fetch("/data/index.json").then(function (r) { return r.json(); }).then(function (d) {
      try { sessionStorage.setItem("tashan_index", JSON.stringify({ t: Date.now(), d: d })); } catch (e) {}
      return d;
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
  }).catch(function () { if (statusline) statusline.innerHTML = '<span class="sl-a"><span class="sl-logo"></span>tashan.sh</span><span class="sl-k">press <kbd>⌘K</kbd> to search</span>'; });
})();
