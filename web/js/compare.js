// tashan — pick any two capabilities and put them side by side.
//
// 398 head-to-head pages are pre-generated, and a reader could only ever reach the pairs we chose:
// top 8 per category, both above 1,000 weekly downloads. Every other comparison — the one someone
// actually has, between the thing they run today and the thing someone just recommended — did not
// exist as a surface. This is that surface.
//
// It renders from the SLIM board index, which carries score, adoption, upkeep, vitality, advisory
// count, maintainer concentration and status. It deliberately does NOT invent the rows it cannot
// read (expertise grade, install script, provenance, licence): those live on the dossiers and are
// linked, never approximated. A comparison that guesses is worth less than one that says what it
// doesn't know.
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var inA = $("cmpA"), inB = $("cmpB"), out = $("cmpOut"), list = $("cmpList"), note = $("cmpNote");
  if (!inA || !inB || !out) return;

  var CAPS = [], BY_ID = {}, BY_LABEL = {}, PAIRS = {};

  var load = window.tashanIndex || function () {
    return fetch("/data/board.json").then(function (r) { return r.json(); });
  };

  Promise.all([
    load(),
    // The manifest of pre-generated pages, so a pair that HAS a full page is sent there rather than
    // rendered thinner here. Optional: a missing file just means no upgrade link.
    fetch("/data/compare.json").then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; })
  ]).then(function (res) {
    CAPS = (res[0] && res[0].capabilities) || [];
    CAPS.forEach(function (c) {
      BY_ID[c.id] = c;
      var lbl = disp(c);
      // Two capabilities can share a display label; the id disambiguates and the datalist shows both.
      if (!BY_LABEL[lbl]) BY_LABEL[lbl] = c;
      BY_LABEL[lbl + " — " + c.id] = c;
    });
    var man = res[1] && res[1].by_category;
    if (man) {
      Object.keys(man).forEach(function (cat) {
        man[cat].forEach(function (p) { PAIRS[p.slug] = true; });
      });
    }
    fillList();
    fromQuery();
  }).catch(function () {
    out.innerHTML = '<p class="empty">Could not load the Index. <a class="linkbtn" href="/">Back to the board</a></p>';
  });

  function disp(c) { return c.label || c.name || c.id; }

  function fillList() {
    if (!list) return;
    // Ranked, so the top of the datalist is the top of the board rather than alphabetical noise.
    var rows = CAPS.slice().sort(function (a, b) {
      return (b.tashan_score || 0) - (a.tashan_score || 0);
    });
    var seen = {}, html = "";
    for (var i = 0; i < rows.length; i++) {
      var lbl = disp(rows[i]);
      var key = seen[lbl] ? lbl + " — " + rows[i].id : lbl;
      seen[lbl] = 1;
      html += '<option value="' + esc(key) + '"></option>';
    }
    list.innerHTML = html;
  }

  function resolve(v) {
    v = (v || "").trim();
    if (!v) return null;
    return BY_LABEL[v] || BY_ID[v] || BY_ID["pkg:" + v] || null;
  }

  function fromQuery() {
    var q = new URLSearchParams(location.search);
    var a = BY_ID[q.get("a") || ""], b = BY_ID[q.get("b") || ""];
    if (a) inA.value = disp(a);
    if (b) inB.value = disp(b);
    if (a && b) render(a, b);
  }

  function onChange() {
    var a = resolve(inA.value), b = resolve(inB.value);
    if (!a || !b) {
      out.innerHTML = "";
      if (note) note.textContent = "";
      return;
    }
    if (a.id === b.id) {
      out.innerHTML = '<p class="empty">Those are the same capability.</p>';
      return;
    }
    // Deep-linkable without a reload, so a comparison can be sent to someone.
    var u = "?a=" + encodeURIComponent(a.id) + "&b=" + encodeURIComponent(b.id);
    history.replaceState(null, "", u);
    render(a, b);
  }
  inA.addEventListener("change", onChange);
  inB.addEventListener("change", onChange);
  inA.addEventListener("input", onChange);
  inB.addEventListener("input", onChange);

  // ---- cells, matching the wording the board already uses so two surfaces cannot disagree -------
  function num(v) { return v == null ? '<span class="num--dim">—</span>' : String(Math.round(v)); }

  function compact(n) {
    if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1).replace(/\.0$/, "") + "M";
    if (n >= 1e3) return Math.round(n / 1e3) + "k";
    return String(n);
  }

  function evidence(c) {
    if (c.npm_downloads != null) return compact(c.npm_downloads) + "/wk";
    if (c.gh_stars != null) return compact(c.gh_stars) + " ★";
    if (c.config_reach) return c.config_reach + (c.kind === "plugin" ? " marketplaces" : " repos");
    return "—";
  }

  function vitality(c) {
    if (c.vitality === "active") return "active";
    if (c.vitality === "stable") return "stable";
    if (c.vitality === "abandoned") return "abandoned";
    return "—";
  }

  function status(c) {
    var bits = [];
    if (c.gh_archived) bits.push("repository archived");
    if (c.registry_status && c.registry_status !== "active") bits.push("registry: " + c.registry_status);
    if (!c.rated) bits.push("catalogued, not rated");
    return bits.length ? bits.join(", ") : "nothing flagged";
  }

  function advisories(c) {
    var n = c.sec_advisory_count;
    if (n == null) return "not yet scanned";
    return n ? n + " known advisor" + (n === 1 ? "y" : "ies") : "no known advisories";
  }

  // From terminal.js, which is loaded on every page — NOT re-derived here. The first version of this
  // file rolled its own and dropped the export's `slug` override. That does not 404, which is what
  // makes it dangerous: slugify("pkg:@stripe/mcp") is "pkg-stripe-mcp", and that page EXISTS — it is
  // the third-party `stripe-mcp`, score 45, displayed under the same name "Stripe" as the official
  // @stripe/mcp at 69. So the header of a comparison would link to a different capability than the
  // row it sits above, silently. The fallback below is only for a page loading compare.js alone.
  function href(c) {
    return window.tashanCapHref ? window.tashanCapHref(c)
      : "/capability/" + (c.slug || c.id.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")) + ".html";
  }
  function slug(c) { return href(c).slice("/capability/".length, -".html".length); }

  function row(label, a, b, why) {
    return '<tr><th scope="row">' + esc(label) + "</th><td>" + a + "</td><td>" + b +
      '</td><td class="cmp__n">' + esc(why || "") + "</td></tr>";
  }

  function render(a, b) {
    var sa = a.tashan_score, sb = b.tashan_score;
    var gap = Math.abs((sa || 0) - (sb || 0));
    var hi = (sa || 0) >= (sb || 0) ? a : b;
    var lead;
    if (sa == null || sb == null) {
      lead = "One of these is not rated, so the score cannot decide it — the evidence rows below are all there is.";
    } else if (gap >= 10) {
      lead = "<b>" + esc(disp(hi)) + "</b> scores " + Math.round(gap) +
        " points higher on the same evidence, which is a real separation rather than noise.";
    } else if (gap >= 3) {
      lead = "<b>" + esc(disp(hi)) + "</b> scores " + Math.round(gap) +
        " points higher — a narrow lead. Read the evidence rows before treating it as decisive.";
    } else {
      lead = "These two are level on the tashan score, so the score does not decide it. " +
        "The evidence rows below are where they differ.";
    }

    var slugs = [slug(a), slug(b)].sort();
    var full = PAIRS[slugs[0] + "-vs-" + slugs[1]] ? "/compare/" + slugs[0] + "-vs-" + slugs[1] + ".html" : null;

    var head = '<thead><tr><th scope="col"></th>' +
      '<th scope="col"><a class="link" href="' + esc(href(a)) + '">' + esc(disp(a)) + "</a></th>" +
      '<th scope="col"><a class="link" href="' + esc(href(b)) + '">' + esc(disp(b)) + "</a></th>" +
      '<th class="cmp__n" scope="col">what it means</th></tr></thead>';

    var body = row("tashan score", num(sa), num(sb), "upkeep + freshness, gated by adoption") +
      row("Adoption evidence", esc(evidence(a)), esc(evidence(b)), "the raw public signal the score came from") +
      row("Adoption", num(a.adoption), num(b.adoption), "that evidence, on a 0–100 scale") +
      row("Upkeep", num(a.upkeep), num(b.upkeep), "cadence, maintainers, status") +
      row("Activity", esc(vitality(a)), esc(vitality(b)), "still moving, finished, or stopped") +
      row("Security", esc(advisories(a)), esc(advisories(b)), "OSV, at the version you would install today") +
      row("Maintainers", a.single_maintainer ? "one primary" : "more than one",
          b.single_maintainer ? "one primary" : "more than one", "bus-factor risk") +
      row("Flags", esc(status(a)), esc(status(b)), "anything the Index knows against it");

    out.innerHTML =
      '<p class="lede">' + lead + " Both are measured the same way, on the same day, from public " +
      'evidence only. <a class="link" href="/methodology.html">How we measure &rsaquo;</a></p>' +
      '<div class="cmp"><table class="cmp__t">' + head + "<tbody>" + body + "</tbody></table></div>" +
      // Says plainly what this view cannot show, rather than quietly omitting it. The dossiers are
      // free and carry the rest; pretending the table is complete would be the same defect the
      // methodology page exists to avoid.
      '<p class="note">This view reads the board index, so it does not carry the expertise grade, ' +
      "the install-time script, the build provenance or the licence. Those are on each dossier, free: " +
      '<a class="link" href="' + esc(href(a)) + '">' + esc(disp(a)) + "</a> · " +
      '<a class="link" href="' + esc(href(b)) + '">' + esc(disp(b)) + "</a>." +
      (full ? ' There is a full side-by-side for this pair: <a class="link" href="' + full + '">' +
        esc(disp(a)) + " vs " + esc(disp(b)) + " &rsaquo;</a>" : "") + "</p>";

    if (note) {
      note.textContent = "Neither score is a security verdict — “well maintained” and " +
        "“nothing known is wrong” are different claims, which is why the audit is its own row.";
    }
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
})();
