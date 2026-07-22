// Mastered — capability detail, rendered from measured data.
(function () {
  "use strict";
  var id = new URLSearchParams(location.search).get("id") || "";
  var el = document.getElementById("cap");

  fetch("/data/capabilities.json").then(function (r) { return r.json(); }).then(function (d) {
    var caps = d.capabilities || [];
    var maxOwners = caps.reduce(function (m, c) { return Math.max(m, c.owners); }, 1);
    var c = caps.find(function (x) { return x.id === id; });
    if (!c) { el.innerHTML = notfound(); return; }
    document.title = pretty(c.name) + " — Mastered";
    render(c, maxOwners, d);
  }).catch(function () { el.innerHTML = notfound(); });

  function render(c, max, d) {
    var sig = Math.max(1, Math.round(100 * Math.log(1 + c.owners) / Math.log(1 + max)));
    var fr = fresh(c.last_seen);
    var co = (c.co_used || []).map(function (x) {
      return '<a href="/capability.html?id=' + encodeURIComponent(x.id) + '">' + esc(pretty(x.id.split(":").slice(1).join(":"))) + ' <span style="opacity:.5">·' + x.n + '</span></a>';
    }).join("");
    el.innerHTML =
      '<div class="cap-hd">' +
        '<a class="back" href="/">&lsaquo; The Index</a>' +
        '<h1>' + esc(pretty(c.name)) + '</h1>' +
        '<div class="cid">' + esc(c.id) + ' &nbsp;·&nbsp; <span class="tag">' + esc(c.kind) + '</span></div>' +
      '</div>' +
      '<div class="stats">' +
        stat("Mastered Signal", sig, "amber", "owner-reach, normalized") +
        stat("Reach", fmt(c.owners), "", "distinct owners") +
        stat("Repos", fmt(c.repos), "", "public repos in sample") +
        stat("★ median", fmt(c.stars_median), "", "of host repos") +
        stat("★ max", fmt(c.stars_max), "", "biggest host repo") +
        stat("Freshness", fr.txt, fr.amber ? "" : "", "last host-repo push", fr.cls) +
      '</div>' +
      (co ? '<h2 style="font-size:1.1rem;font-weight:600;color:#fff;margin:0 0 var(--sp-3)">Configured alongside</h2><div class="colist">' + co + '</div>' : '') +
      '<div class="callout" style="margin-top:var(--sp-12)"><b>What this means.</b> These numbers are measured from ' +
        fmt(d.sample_configs) + ' public GitHub configs (' + fdate(d.generated_at) + '). <b>Reach</b> counts distinct ' +
        'owners who wired this into a real config — the hardest signal to fake. It is <b>not</b> an endorsement of quality; ' +
        'retention and outcome layers are on the <a class="link" href="/methodology.html">roadmap</a>.</div>';
  }

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
  function pretty(name) { return String(name).replace(/^@modelcontextprotocol\/server-/, "").replace(/-mcp$/, "").replace(/^mcp-server-/, "").replace(/^mcp-/, ""); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function fmt(n) { return (n == null) ? "—" : String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function fdate(iso) { if (!iso) return ""; return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  function notfound() { return '<div class="cap-hd"><a class="back" href="/">&lsaquo; The Index</a><h1>Not measured yet</h1><div class="cid">This capability isn\'t in the current sample. The Index grows every scan.</div></div>'; }
})();
