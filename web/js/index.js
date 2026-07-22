// Mastered — render the Index (leaderboard) from measured public-signal data.
(function () {
  "use strict";
  var DATA = "/data/capabilities.json";
  var rowsEl = document.getElementById("rows");
  var state = { caps: [], filter: "all", max: 1 };

  fetch(DATA).then(function (r) {
    if (!r.ok) throw new Error("no data");
    return r.json();
  }).then(function (d) {
    // hero stats
    set("sCaps", fmt(d.capabilities_found));
    set("sRepos", fmt(d.unique_repos));
    set("sConfigs", fmt(d.sample_configs));
    set("sDate", "measured " + fdate(d.generated_at));
    var fm = document.getElementById("footMethod");
    if (fm) fm.textContent = "public-signal v1 · " + fmt(d.sample_configs) + " configs · " + fdate(d.generated_at);
    var bn = document.getElementById("boardNote");
    if (bn) bn.textContent = d.note || "";

    // keep identity-reliable capabilities front; drop pure server-key fallbacks from default view
    state.caps = (d.capabilities || []).filter(function (c) { return !c.id.startsWith("key:"); });
    state.max = state.caps.reduce(function (m, c) { return Math.max(m, c.owners); }, 1);
    render();
  }).catch(function () {
    rowsEl.innerHTML = '<tr><td colspan="7"><div class="empty">Measurement data isn\'t published yet — the scraper is still running. Check back shortly.</div></td></tr>';
  });

  // row navigation (delegated — no inline handlers, strict CSP)
  rowsEl.addEventListener("click", function (e) {
    var tr = e.target.closest("tr[data-href]");
    if (tr) location.href = tr.getAttribute("data-href");
  });

  // filters
  var chips = document.getElementById("chips");
  if (chips) chips.addEventListener("click", function (e) {
    var b = e.target.closest("button[data-f]");
    if (!b) return;
    state.filter = b.dataset.f;
    [].forEach.call(chips.querySelectorAll("button"), function (x) {
      x.setAttribute("aria-pressed", String(x === b));
    });
    render();
  });

  function passes(c) {
    if (state.filter === "all") return true;
    if (state.filter === "npm") return c.kind === "npm" || c.kind === "pkg";
    return c.kind === state.filter;
  }

  function render() {
    var list = state.caps.filter(passes).slice(0, 60);
    if (!list.length) { rowsEl.innerHTML = '<tr><td colspan="7"><div class="empty">No capabilities of this type in the sample yet.</div></td></tr>'; return; }
    var html = "";
    list.forEach(function (c, i) {
      var sig = signal(c.owners, state.max);
      var fr = fresh(c.last_seen);
      html += '<tr data-href="/capability.html?id=' + encodeURIComponent(c.id) + '">' +
        '<td class="rank">' + (i + 1) + '</td>' +
        '<td><div class="cap__name">' + esc(pretty(c.name)) + ' <span class="tag">' + esc(c.kind) + '</span></div>' +
        '<div class="cap__id">' + esc(c.id) + '</div></td>' +
        '<td class="num">' + fmt(c.owners) + '</td>' +
        '<td class="num num--dim">' + fmt(c.repos) + '</td>' +
        '<td class="num num--dim">' + fmt(c.stars_median) + '</td>' +
        '<td><span class="fresh ' + fr.cls + '">' + fr.txt + '</span></td>' +
        '<td><div class="sig"><span class="sig__val">' + sig + '</span>' +
        '<span class="bar"><i style="width:' + sig + '%"></i></span></div></td>' +
        '</tr>';
    });
    rowsEl.innerHTML = html;
  }

  // --- the Mastered Signal: owner-reach, log-normalized to the top capability (documented in Methodology) ---
  function signal(owners, max) {
    return Math.max(1, Math.round(100 * Math.log(1 + owners) / Math.log(1 + max)));
  }
  function fresh(iso) {
    if (!iso) return { txt: "—", cls: "fresh--warm" };
    var months = (Date.now() - new Date(iso).getTime()) / 2.63e9;
    if (months < 1.5) return { txt: "active", cls: "fresh--hot" };
    if (months < 12) return { txt: Math.round(months) + "mo", cls: "fresh--warm" };
    return { txt: Math.round(months / 12 * 10) / 10 + "y", cls: "fresh--cold" };
  }
  function pretty(name) {
    return name.replace(/^@modelcontextprotocol\/server-/, "").replace(/-mcp$/, "").replace(/^mcp-server-/, "").replace(/^mcp-/, "");
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function fmt(n) { return (n == null) ? "—" : String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function fdate(iso) { if (!iso) return ""; var d = new Date(iso); return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  function set(id, v) { var el = document.getElementById(id); if (el) el.textContent = v; }
})();
