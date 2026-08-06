// tashan — the demand board. Public demand for a capability to be tracked and graded, registered as
// GitHub issues so the demand itself is public evidence. No money moves: backing is a +1. If paid
// grade-bounties are ever built, settlement must trigger on PUBLICATION and never on the result, or
// the number becomes purchasable and worthless.
(function () {
  "use strict";
  var rows = document.getElementById("reqrows");

  fetch("/data/requests.json").then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (d) {
    var reqs = (d.requests || []).slice().sort(function (a, b) { return (b.backers || 0) - (a.backers || 0); });
    if (!reqs.length) { return showQueue(); }
    rows.innerHTML = reqs.map(row).join("");
  }).catch(showQueue);

  // NOBODY HAS ASKED YET, AND AN EMPTY BOARD READS AS NOBODY CARING. The honest filler is not a
  // fabricated wishlist — it is what the pipeline measures next, in the order it will actually do
  // it. Same demand ranking the scan and grading queues walk (pipeline/coverage.py), so the page
  // cannot advertise a queue the pipeline does not run.
  function showQueue() {
    fetch("/data/coverage.json").then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (c) {
      var q = c.queue || [];
      if (!q.length) { rows.innerHTML = empty(); return; }
      var head = document.getElementById("reqhead");
      if (head) head.textContent = "Next to be measured";
      // "ranked by how many people asked" is true of the request board and false of the queue. Every
      // label that describes the table has to switch with it, or the page states a sort it isn't using.
      var aside = document.getElementById("reqaside");
      if (aside) aside.textContent = "ranked by adoption, most-used first";
      // The column holds backer counts when there ARE requests and download counts when it is the
      // queue. Renaming it in the HTML would have mislabelled the real board the day one arrived.
      var col = document.getElementById("reqcol3");
      if (col) col.textContent = "Adoption";
      var sub = document.getElementById("reqsub");
      if (sub) {
        sub.textContent = "No one has requested a grade yet, so this is the measurement queue instead" +
          " — ranked by the adoption evidence we hold, most-used first. Requesting something moves it here.";
      }
      rows.innerHTML = q.map(qrow).join("");
    }).catch(function () { rows.innerHTML = empty(); });
  }

  var AXIS = { score: "tashan score", scan: "security scan", grade: "expertise grade", task: "task mapping" };

  function qrow(r, i) {
    var href = "/capability.html?id=" + encodeURIComponent(r.id);
    var missing = (r.missing || []).map(function (m) {
      return '<span class="tag">' + esc(AXIS[m] || m) + '</span>';
    }).join(" ");
    var dl = r.downloads ? fmt(r.downloads) + "/wk" : "—";
    return '<tr>' +
      '<td class="rank">' + (i + 1) + '</td>' +
      '<td><div class="cap__name"><a href="' + href + '">' + esc(r.name || r.id) + '</a></div>' +
        '<div class="cap__id">awaiting ' + missing + '</div></td>' +
      '<td class="num num--dim">' + dl + '</td>' +
      '<td><span class="vchip" title="In the measurement queue">○ queued</span></td>' +
      '<td class="ta-r"></td>' +
      '</tr>';
  }

  function fmt(n) {
    if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1).replace(/\.0$/, "") + "M";
    if (n >= 1e3) return Math.round(n / 1e3) + "k";
    return String(n);
  }

  function row(r, i) {
    var href = r.slug ? "/capability/" + r.slug + ".html" : (r.cap_id ? "/capability.html?id=" + encodeURIComponent(r.cap_id) : null);
    var name = esc(r.name) + (r.kind ? ' <span class="tag">' + esc(r.kind === "npm" || r.kind === "pkg" ? "npm" : r.kind) + '</span>' : "");
    var nameCell = href ? '<a href="' + href + '">' + name + '</a>' : name;
    var st = statusChip(r.status);
    // "Back" registers PUBLIC demand via a GitHub issue. Backing is a public +1, never a charge.
    // This comment used to say we do not show a dollar amount, while the line directly below rendered
    // one from a hand-written fixture — the comment was right and the code was wrong. No money has
    // moved, so no money is displayed.
    var back = '<a class="fpill" href="https://github.com/tashan-sh/tashan/issues/new?labels=grade-bounty&title=' +
      encodeURIComponent("Back grade: " + (r.name || r.cap_id || "")) +
      '" rel="noopener" title="Register public demand for this grade — it settles when the grade is published, whatever it says">＋ Back ↗</a>';
    return '<tr>' +
      '<td class="rank">' + (i + 1) + '</td>' +
      '<td><div class="cap__name">' + nameCell + '</div>' +
        '<div class="cap__id">' + esc(r.why || "") + '</div></td>' +
      '<td class="num num--dim">' + (r.backers || 0) + '</td>' +
      '<td>' + st + '</td>' +
      '<td class="ta-r">' + back + '</td>' +
      '</tr>';
  }

  function statusChip(s) {
    if (s === "funded") return '<span class="vchip vd--solid" title="Bounty met — queued for grading">◐ funded</span>';
    if (s === "graded") return '<span class="vchip vd--deep" title="Grade published — bounty settled">● graded</span>';
    return '<span class="vchip" title="Open — awaiting backing">○ open</span>';
  }

  function empty() {
    return '<tr><td colspan="5"><div class="empty">No open requests yet — <a class="linkbtn" href="https://github.com/tashan-sh/tashan/issues/new?labels=grade-request">open the first one ↗</a></div></td></tr>';
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
})();
