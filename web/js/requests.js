// tashan — the demand board. A neutrality-safe grade-bounty queue (pump.fun GO model): you fund the
// grade, never the score; settlement is outcome-independent. V1 is static (reads requests.json; submit
// via a GitHub issue, back via a payment link). V2 adds a write path (Cloudflare Function + D1).
(function () {
  "use strict";
  var rows = document.getElementById("reqrows");

  fetch("/data/requests.json").then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (d) {
    var reqs = (d.requests || []).slice().sort(function (a, b) { return (b.usd || 0) - (a.usd || 0) || (b.backers || 0) - (a.backers || 0); });
    if (!reqs.length) { rows.innerHTML = empty(); return; }
    rows.innerHTML = reqs.map(row).join("");
  }).catch(function () { rows.innerHTML = empty(); });

  function row(r, i) {
    var href = r.slug ? "/capability/" + r.slug + ".html" : (r.cap_id ? "/capability.html?id=" + encodeURIComponent(r.cap_id) : null);
    var name = esc(r.name) + (r.kind ? ' <span class="tag">' + esc(r.kind === "npm" || r.kind === "pkg" ? "npm" : r.kind) + '</span>' : "");
    var nameCell = href ? '<a href="' + href + '">' + name + '</a>' : name;
    var st = statusChip(r.status);
    // "Back" registers PUBLIC demand via a GitHub issue (the neutrality-safe queue). USDC co-funding that
    // settles-on-publish arrives with the write path; until then backing is a public +1, never a charge —
    // so we don't show a dollar amount or link a payment endpoint that doesn't exist yet.
    var back = '<a class="fpill" href="https://github.com/tashan-sh/tashan/issues/new?labels=grade-bounty&title=' +
      encodeURIComponent("Back grade: " + (r.name || r.cap_id || "")) +
      '" rel="noopener" title="Register public demand for this grade — it settles when the grade is published, whatever it says">＋ Back ↗</a>';
    return '<tr>' +
      '<td class="rank">' + (i + 1) + '</td>' +
      '<td><div class="cap__name">' + nameCell + '</div>' +
        '<div class="cap__id">' + esc(r.why || "") + '</div></td>' +
      '<td class="num"><b>$' + (r.usd != null ? r.usd.toFixed(2) : "0.00") + '</b></td>' +
      '<td class="num num--dim">' + (r.backers || 0) + '</td>' +
      '<td>' + st + '</td>' +
      '<td style="text-align:right">' + back + '</td>' +
      '</tr>';
  }

  function statusChip(s) {
    if (s === "funded") return '<span class="vchip vd--solid" title="Bounty met — queued for grading">◐ funded</span>';
    if (s === "graded") return '<span class="vchip vd--deep" title="Grade published — bounty settled">● graded</span>';
    return '<span class="vchip" title="Open — awaiting backing">○ open</span>';
  }

  function empty() {
    return '<tr><td colspan="6"><div class="empty">No open requests yet — <a class="linkbtn" href="https://github.com/tashan-sh/tashan/issues/new?labels=grade-request">open the first one ↗</a></div></td></tr>';
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
})();
