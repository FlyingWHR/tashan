// tashan — the Index: category catalog + a faceted, sortable, URL-stateful trust leaderboard (v2).
// Proven pattern (Algolia/Linear/NN-g): sort is ONE ordering (select); filters are many concurrent
// refinements (AND across facets, OR within). Active refinements show as removable chips + a live count.
(function () {
  "use strict";
  var rowsEl = document.getElementById("rows");
  // facets are Sets (multi-select); toggles are bool; sort is one key
  var state = { cat: new Set(), task: new Set(), kind: new Set(), vitality: new Set(), verdict: new Set(),
                official: false, clean: false, sort: "trust" };
  var data = { caps: [], cats: [], catMeta: {}, tasks: [], roles: [], taskMeta: {}, taskIds: null };
  var PAGE = 100, shownCount = PAGE;   // board pagination: show PAGE rows, "show more" reveals the rest

  var KIND_LABEL = { npm: "npm", pkg: "npm-pkg", docker: "docker", python: "python", remote: "remote", skill: "skill" };
  var VIT_LABEL = { active: "active", stable: "stable", abandoned: "abandoned" };
  var VERDICTS = ["deep", "solid", "thin", "wrapper", "slop"];
  var SORTS = [["trust", "Trust"], ["adoption", "Adoption"], ["fresh", "Freshness"],
               ["expertise", "Expertise"], ["maint", "Maintenance"], ["name", "Name A–Z"]];

  // reuse terminal.js's session-cached loader (one fetch+parse of the slim index per session, shared)
  var loadIndex = window.tashanIndex || function () { return fetch("/data/index.json").then(function (r) { if (!r.ok) throw 0; return r.json(); }); };
  Promise.all([
    loadIndex(),
    fetch("/data/categories.json").then(function (r) { return r.ok ? r.json() : { categories: [] }; }).catch(function () { return { categories: [] }; }),
    // The task taxonomy (labels, roles) and the tag->capability map. The map is 3.6 KB gz against a
    // 39.8 KB index, so it is fetched up front: a lazy path for that saves nothing measurable and costs
    // a loading state, a race on first click, and a filter that silently does nothing until it lands.
    fetch("/data/tasks.json").then(function (r) { return r.ok ? r.json() : { tasks: [], roles: [] }; }).catch(function () { return { tasks: [], roles: [] }; }),
    fetch("/data/tags.json").then(function (r) { return r.ok ? r.json() : { tasks: {} }; }).catch(function () { return { tasks: {} }; })
  ]).then(function (res) {
    var d = res[0];
    // measured ⊂ tracked — the two nest, so the pair is readable. "quality-measured" previously showed
    // enriched_npm, which counts npm metadata fetches and is not a quality measurement at all.
    set("sCaps", fmt(d.measured || d.ranked));
    set("sRepos", fmt(d.total_capabilities));
    set("sDate", "measured " + fdate(d.generated_at));
    var fm = document.getElementById("footMethod");
    if (fm) fm.textContent = "public-signal v2 · " + fmt(d.total_capabilities) + " capabilities · " + fdate(d.generated_at);
    var bn = document.getElementById("boardNote");
    if (bn) bn.textContent = d.note || "";

    data.caps = (d.capabilities || []).filter(function (c) { return c.id.indexOf("key:") !== 0; });
    (res[1].categories || []).forEach(function (c) { data.catMeta[c.id] = c; });
    data.cats = res[1].categories || [];
    data.tasks = (res[2] && res[2].tasks) || [];
    data.roles = (res[2] && res[2].roles) || [];
    data.tasks.forEach(function (t) { data.taskMeta[t.slug] = t; });
    var raw = (res[3] && res[3].tasks) || {};
    data.taskIds = {};
    Object.keys(raw).forEach(function (k) { data.taskIds[k] = new Set(raw[k]); });
    // Count what the board actually holds, not what the export knows: the slim index is capped, so a
    // rail promising 30 would open onto 12 if we counted the bulk figure.
    var onBoard = {};
    data.caps.forEach(function (c) { onBoard[c.id] = 1; });
    data.tasks.forEach(function (t) {
      var ids = raw[t.slug] || [];
      t.count = ids.filter(function (i) { return onBoard[i]; }).length;
    });
    urlToState();
    buildToolbar();
    renderTasks();
    renderCatalog();
    render();
    if (hasFilters()) { var a = document.getElementById("board-anchor"); if (a) a.scrollIntoView({ block: "start" }); }
  }).catch(function () {
    rowsEl.innerHTML = '<tr><td colspan="6"><div class="empty">Measurement data isn\'t published yet — the pipeline is still running. Check back shortly.</div></td></tr>';
  });

  addEventListener("popstate", function () { shownCount = PAGE; urlToState(); buildToolbar(); renderTasks(); renderCatalog(); render(); });

  // ---- URL state (shareable, back-button-friendly; defaults omitted) ----
  function urlToState() {
    var q = new URLSearchParams(location.search);
    state.cat = csvSet(q.get("cat"));
    state.task = csvSet(q.get("task"));
    state.kind = csvSet(q.get("kind"));
    state.vitality = csvSet(q.get("vitality"));
    state.verdict = csvSet(q.get("verdict"));
    state.official = q.get("official") === "1";
    state.clean = q.get("clean") === "1";
    state.sort = q.get("sort") || "trust";
  }
  function stateToURL(push) {
    var q = new URLSearchParams();
    if (state.cat.size) q.set("cat", [].concat.apply([], [Array.from(state.cat)]).join(","));
    if (state.task.size) q.set("task", Array.from(state.task).join(","));
    if (state.kind.size) q.set("kind", Array.from(state.kind).join(","));
    if (state.vitality.size) q.set("vitality", Array.from(state.vitality).join(","));
    if (state.verdict.size) q.set("verdict", Array.from(state.verdict).join(","));
    if (state.official) q.set("official", "1");
    if (state.clean) q.set("clean", "1");
    if (state.sort !== "trust") q.set("sort", state.sort);
    var url = location.pathname + (q.toString() ? "?" + q.toString() : "");
    history[push ? "pushState" : "replaceState"](null, "", url);
  }
  function csvSet(v) { return new Set(v ? v.split(",").filter(Boolean) : []); }
  function hasFilters() { return state.task.size || state.cat.size || state.kind.size || state.vitality.size || state.verdict.size || state.official || state.clean; }

  // ---- the toolbar: Type/Activity/Assessment pills + Official/Clean toggles + Sort select ----
  function buildToolbar() {
    var tb = document.getElementById("toolbar");
    if (!tb) return;
    var counts = facetCounts();
    var kinds = ["npm", "pkg", "docker", "python", "remote", "skill"].filter(function (k) { return counts.kind[k]; });
    tb.innerHTML =
      grp("Type", pillset("kind", kinds, function (k) { return KIND_LABEL[k] || k; }, counts.kind)) +
      grp("Activity", pillset("vitality", ["active", "stable", "abandoned"].filter(function (v) { return counts.vitality[v]; }), function (v) { return VIT_LABEL[v]; }, counts.vitality)) +
      grp("Depth", pillset("verdict", VERDICTS.filter(function (v) { return counts.verdict[v]; }), function (v) { return v; }, counts.verdict)) +
      '<div class="tgroup">' +
        toggle("official", "✓ Official", counts.official) +
        toggle("clean", "Hide deprecated/archived", null) +
      '</div>' +
      '<label class="sortsel"><span>Sort</span><select id="sortSel">' +
        SORTS.map(function (s) { return '<option value="' + s[0] + '"' + (state.sort === s[0] ? " selected" : "") + '>' + s[1] + '</option>'; }).join("") +
      '</select></label>';

    tb.onclick = function (e) {
      var p = e.target.closest("[data-facet]");
      if (!p) return;
      var f = p.getAttribute("data-facet"), v = p.getAttribute("data-val");
      if (f === "official" || f === "clean") { state[f] = !state[f]; }
      else { state[f].has(v) ? state[f].delete(v) : state[f].add(v); }
      commit();
    };
    var sel = document.getElementById("sortSel");
    if (sel) sel.onchange = function () { state.sort = sel.value; commit(); };
  }
  function grp(label, inner) { return '<div class="tgroup"><span class="tgroup__l mono">' + label + '</span>' + inner + '</div>'; }
  function pillset(facet, vals, labelFn, counts) {
    return vals.map(function (v) {
      var on = state[facet].has(v);
      return '<button class="fpill' + (on ? " is-on" : "") + '" data-facet="' + facet + '" data-val="' + esc(v) + '" aria-pressed="' + on + '" type="button">' +
        esc(labelFn(v)) + '<span class="fpill__c">' + (counts[v] || 0) + '</span></button>';
    }).join("");
  }
  function toggle(facet, label, count) {
    var on = state[facet];
    return '<button class="fpill fpill--toggle' + (on ? " is-on" : "") + '" data-facet="' + facet + '" aria-pressed="' + on + '" type="button">' +
      esc(label) + (count ? '<span class="fpill__c">' + count + '</span>' : "") + '</button>';
  }
  // counts computed against the FULL set (v1; disjunctive faceting deferred — see research). Since they're
  // over the full set they're invariant between filter clicks — compute ONCE per load, not per commit().
  function facetCounts() {
    if (data._facets) return data._facets;
    var out = { kind: {}, vitality: {}, verdict: {}, official: 0 };
    data.caps.forEach(function (c) {
      var k = normKind(c);
      out.kind[k] = (out.kind[k] || 0) + 1;
      if (c.vitality) out.vitality[c.vitality] = (out.vitality[c.vitality] || 0) + 1;
      if (c.expertise_verdict) out.verdict[c.expertise_verdict] = (out.verdict[c.expertise_verdict] || 0) + 1;
      if (officialOrg(c)) out.official++;
    });
    data._facets = out;
    return out;
  }

  // ---- category rail (the browse axis) — compact refinement list; leader shown on hover (measured touch) ----
  // ---- the task rail: the PRIMARY browse axis — what work are you doing? ----
  // The 15 domain categories describe what a capability touches; this describes what you are trying to
  // get done, which is how people actually arrive. Tasks are multi-select (a capability does several
  // jobs) where category is deliberately single-select (browse ONE domain at a time). Grouped by role
  // purely for legibility — roles are labels here, never a page or a filter of their own.
  // ONE row shape for the whole left rail. The two rails had drifted into using the same class names
  // for opposite things — `crow__n` was the COUNT in the task rail and the LABEL in the category rail —
  // so they rendered differently and read as two unrelated widgets glued together.
  function railRow(attr, id, label, count, on, tip) {
    return '<button class="crow' + (on ? " is-on" : "") + '" data-' + attr + '="' + esc(id) + '"' +
      ' type="button" aria-pressed="' + !!on + '" title="' + esc(tip || label) + '">' +
      '<span class="crow__l">' + esc(label) + "</span>" +
      '<span class="crow__c mono">' + count + "</span></button>";
  }

  function renderTasks() {
    var rail = document.getElementById("taskrail");
    if (!rail || !data.tasks.length) return;
    // Only tasks with a real shelf behind them are offered. A rail full of one-capability jobs is a
    // worse browse than no rail: it promises a catalog we do not have yet.
    var live = data.tasks.filter(function (t) { return (t.count || 0) >= 3; });
    if (!live.length) { rail.innerHTML = ""; return; }
    var byRole = {};
    live.forEach(function (t) {
      (t.roles && t.roles.length ? t.roles : ["other"]).forEach(function (r) {
        (byRole[r] = byRole[r] || []).push(t);
      });
    });
    var roleLabel = {};
    data.roles.forEach(function (r) { roleLabel[r.id] = r.label; });
    var order = Object.keys(byRole).sort(function (a, b) { return byRole[b].length - byRole[a].length; });
    var html = order.map(function (r) {
      var items = byRole[r].sort(function (a, b) { return (b.count || 0) - (a.count || 0); });
      return '<div class="trole"><p class="trole__h mono">' + esc(roleLabel[r] || r) + "</p>" +
        items.map(function (t) {
          return railRow("task", t.slug, t.label, t.count || 0, state.task.has(t.slug), t.blurb);
        }).join("") + "</div>";
    }).join("");
    rail.innerHTML = html;
    rail.onclick = function (e) {
      var b = e.target.closest("[data-task]");
      if (!b) return;
      var v = b.getAttribute("data-task");
      state.task.has(v) ? state.task.delete(v) : state.task.add(v);
      commit();
    };
  }

  function renderCatalog() {
    var rail = document.getElementById("catrail");
    if (!rail || !data.cats.length) return;
    if (!data._catAgg) {                       // per-category count + leader: invariant, compute once
      var counts = {}, top = {};
      data.caps.forEach(function (c) {
        if (!c.category) return;
        counts[c.category] = (counts[c.category] || 0) + 1;
        if (c.trust != null && (!top[c.category] || c.trust > top[c.category].trust)) top[c.category] = c;
      });
      data._catAgg = { counts: counts, top: top };
    }
    var counts = data._catAgg.counts, top = data._catAgg.top;
    function row(id, label, count, on, lead) {
      var tip = lead ? label + " — top: " + pretty(lead.name) + " (Trust " + lead.trust + ")" : label;
      return railRow("cat", id, label, count, on, tip);
    }
    var html = "";
    data.cats.forEach(function (cat) {
      var n = counts[cat.id] || 0;
      if (!n) return;
      html += row(cat.id, cat.label, n, state.cat.has(cat.id), top[cat.id]);
    });
    rail.innerHTML = html;
    rail.onclick = function (e) {
      var b = e.target.closest("button[data-cat]");
      if (!b) return;
      // Multi-select, same as tags. It used to be single-select with an "All" row, so the left rail
      // had two different interaction models sitting on top of each other — clicking a tag added to a
      // selection, clicking a category replaced one. Same place, same look, opposite behaviour.
      var cat = b.dataset.cat;
      state.cat.has(cat) ? state.cat.delete(cat) : state.cat.add(cat);
      commit();
    };
  }

  function commit() { shownCount = PAGE; stateToURL(true); buildToolbar(); renderTasks(); renderCatalog(); render(); }

  function passes(c) {
    // Task filter: OR within the group, AND against every other facet — the same shape as Type and
    // Activity. Tasks are multi-select because a capability genuinely does several jobs; category stays
    // single-select because browsing two domains at once is not a thing people mean.
    if (state.task.size) {
      var hit = false;
      state.task.forEach(function (t) { var s2 = data.taskIds[t]; if (s2 && s2.has(c.id)) hit = true; });
      if (!hit) return false;
    }
    if (state.cat.size && !state.cat.has(c.category)) return false;   // OR within group
    if (state.kind.size && !state.kind.has(normKind(c))) return false;
    if (state.vitality.size && !state.vitality.has(c.vitality)) return false;
    if (state.verdict.size && !state.verdict.has(c.expertise_verdict)) return false;
    if (state.official && !officialOrg(c)) return false;
    if (state.clean && (c.npm_deprecated || c.gh_archived || (c.registry_status && c.registry_status !== "active"))) return false;
    return true;
  }
  function normKind(c) { return (c.kind === "npm" || c.kind === "pkg") ? (c.kind) : c.kind; }

  function sortComparator(a, b) {
    // Unrated capabilities (catalogued, no per-item evidence yet) always sort BELOW rated ones, whatever
    // the chosen sort. They are real and installable, but a board is a ranking — an item we can't rank
    // must not occupy a rank. Within the unrated block the chosen sort still applies.
    var ar = a.trust != null, br = b.trust != null;
    if (ar !== br) return ar ? -1 : 1;
    switch (state.sort) {
      // Sort on the SCORE, not on raw evidence. `npm_downloads || config_reach` compared 422 weekly
      // downloads against "2 marketplaces" as if they were one magnitude, so 422 always beat a
      // 51,323-star plugin. The score is the only cross-kind-comparable number we have.
      case "adoption": return num(b.adoption) - num(a.adoption);
      case "fresh": return recency(b) - recency(a);
      case "expertise": return (num(b.expertise) - num(a.expertise)) || (num(b.trust) - num(a.trust));
      case "maint": return num(b.maintenance) - num(a.maintenance);
      case "name": return pretty(a.name).toLowerCase() < pretty(b.name).toLowerCase() ? -1 : 1;
      default: return num(b.trust) - num(a.trust);   // trust
    }
  }
  function recency(c) { var iso = c.npm_last_publish || c.gh_pushed || c.last_seen; return iso ? new Date(iso).getTime() : 0; }

  function render() {
    var bt = document.getElementById("boardTitle");
    var singleCat = state.cat.size === 1 ? Array.from(state.cat)[0] : null;
    if (bt) bt.textContent = singleCat && data.catMeta[singleCat] ? data.catMeta[singleCat].label : "The field, ranked";
    var bd = document.getElementById("boardDesc");
    if (bd) bd.innerHTML = singleCat && data.catMeta[singleCat]
      ? esc(data.catMeta[singleCat].blurb)
      : 'Trust is a transparent composite of maintenance and freshness, gated by real adoption — never one black box. Tags like <span class="vd vd--deep">deep</span> and <span class="vd vd--thin">thin</span> are our expertise-eval\'s read. Open any row for the full breakdown.';

    var list = data.caps.filter(passes).slice().sort(sortComparator);
    renderActiveBar(list.length);
    var shown = list.slice(0, shownCount);
    if (!shown.length) { rowsEl.innerHTML = '<tr><td colspan="6"><div class="empty">No capabilities match these filters. <button class="linkbtn" id="clearEmpty" type="button">Clear filters</button></div></td></tr>';
      var ce = document.getElementById("clearEmpty"); if (ce) ce.onclick = clearAll; return; }
    var html = "";
    shown.forEach(function (c, i) {
      var t = c.trust, bar = (t == null) ? 0 : t;
      var fr = vitalityCell(c);
      var dep = c.npm_deprecated ? ' <span class="fresh fresh--cold">deprecated</span>' : "";
      var vd = c.expertise_verdict ? ' <span class="vd vd--' + esc(c.expertise_verdict) + '" title="LLM expertise-eval: ' + (c.expertise || "") + '/100">' + esc(c.expertise_verdict) + '</span>' : "";
      var org = officialOrg(c);
      var off = org ? ' <span class="official" title="Official from ' + esc(org) + '">✓ ' + esc(org) + '</span>' : "";
      var catTag = (!singleCat && c.category && data.catMeta[c.category]) ? ' <span class="cattag" title="Category">' + esc(data.catMeta[c.category].label) + '</span>' : "";
      html += '<tr data-href="' + capHref(c) + '">' +
        '<td class="rank">' + (i + 1) + '</td>' +
        '<td><div class="cap__name"><a class="cap__link" href="' + capHref(c) + '">' + esc(pretty(c.name)) + '</a> <span class="tag">' + esc(KIND_LABEL[c.kind] || c.kind) + '</span>' + off + vd + dep + '</div>' +
        '<div class="cap__id">' + esc(c.id) + catTag + '</div></td>' +
        '<td class="num">' + adoption(c) + '</td>' +
        '<td class="num num--dim">' + score(c.maintenance) + '</td>' +
        '<td><span class="fresh ' + fr.cls + '"' + (fr.title ? ' title="' + esc(fr.title) + '"' : '') + '>' + fr.txt + '</span></td>' +
        '<td><div class="sig' + (t == null ? ' sig--none' : '') + '">' + (t == null
          ? '<span class="unrated" title="Catalogued, not rated: its only maintenance evidence is the repository it lives in, which every skill in that repo shares. A grade of its own SKILL.md is what makes it rankable.">not rated yet</span>'
          : '<span class="sig__val">' + Math.round(t) + '</span>') +
        '<span class="bar"><i style="width:' + bar + '%"></i></span></div></td>' +
        '</tr>';
    });
    if (list.length > shown.length) {                      // reveal the rest instead of hard-capping the board
      var more = Math.min(PAGE, list.length - shown.length);
      html += '<tr class="board__more"><td colspan="6"><button class="btn btn--ghost" id="showMore" type="button">' +
        'Show ' + more + ' more <span class="mono" style="opacity:.55">· ' + shown.length + ' of ' + fmt(list.length) + '</span></button></td></tr>';
    }
    rowsEl.innerHTML = html;
    // whole-row click navigates (the row shows cursor:pointer); real links/buttons inside act normally
    rowsEl.onclick = function (e) {
      if (e.target.closest("a, button")) return;
      var tr = e.target.closest("tr[data-href]");
      if (tr) location.href = tr.getAttribute("data-href");
    };
    var sm = document.getElementById("showMore");
    if (sm) sm.onclick = function () { shownCount += PAGE; render(); };
  }

  // ---- active-refinements bar: removable chips + "showing N of M" + clear all ----
  function renderActiveBar(matchCount) {
    var bar = document.getElementById("activebar");
    if (!bar) return;
    var chips = [];
    state.task.forEach(function (v) { chips.push(chip("task", v, data.taskMeta[v] ? data.taskMeta[v].label : v)); });
    state.cat.forEach(function (v) { chips.push(chip("cat", v, data.catMeta[v] ? data.catMeta[v].label : v)); });
    state.kind.forEach(function (v) { chips.push(chip("kind", v, KIND_LABEL[v] || v)); });
    state.vitality.forEach(function (v) { chips.push(chip("vitality", v, VIT_LABEL[v])); });
    state.verdict.forEach(function (v) { chips.push(chip("verdict", v, v)); });
    if (state.official) chips.push(chip("official", "1", "✓ Official"));
    if (state.clean) chips.push(chip("clean", "1", "no deprecated/archived"));
    if (!chips.length) { bar.hidden = true; bar.innerHTML = ""; return; }
    bar.hidden = false;
    bar.innerHTML = '<div class="activebar__chips">' + chips.join("") +
      '<button class="activebar__clear" id="clearAll" type="button">Clear all</button></div>' +
      '<span class="activebar__count mono">showing ' + fmt(matchCount) + ' of ' + fmt(data.caps.length) + '</span>';
    bar.querySelectorAll("[data-rm]").forEach(function (b) {
      b.onclick = function () {
        var f = b.getAttribute("data-rm"), v = b.getAttribute("data-val");
        if (f === "official" || f === "clean") state[f] = false; else state[f].delete(v);
        commit();
      };
    });
    var ca = document.getElementById("clearAll"); if (ca) ca.onclick = clearAll;
  }
  function chip(facet, val, label) {
    return '<button class="achip" data-rm="' + facet + '" data-val="' + esc(val) + '" type="button">' + esc(label) + ' <span class="achip__x">✕</span></button>';
  }
  function clearAll() {
    state.task.clear(); state.cat.clear(); state.kind.clear(); state.vitality.clear(); state.verdict.clear();
    state.official = false; state.clean = false;
    commit();
  }

  // vitality-aware Fresh cell (server read; "finished != dead") with date fallback
  function vitalityCell(c) {
    if (c.vitality === "active") return { txt: "active", cls: "fresh--hot" };
    if (c.vitality === "stable") return { txt: "stable", cls: "fresh--warm", title: "Mature & maintained — quiet but still adopted, low unresolved-issue pressure" };
    if (c.vitality === "abandoned") return { txt: "abandoned", cls: "fresh--cold", title: "Stale under issue pressure, deprecated, or archived" };
    return fresh(c.npm_last_publish || c.gh_pushed || c.last_seen);
  }

  // resolved at export time (build.py) — the board no longer ships source_repo just to re-derive this
  function officialOrg(c) { return c.official || null; }
  function officialOrgLegacy(c) {
    var s = ((c.npm_pkg || "") + " " + (c.source_repo || "")).toLowerCase();
    if (/modelcontextprotocol|anthropic/.test(s)) return "Anthropic";
    if (/(^|[\/@\s])openai/.test(s)) return "OpenAI";
    if (/google|googleapis|gemini/.test(s)) return "Google";
    if (/(^|[\/@\s])microsoft|(^|\/)azure/.test(s)) return "Microsoft";
    return null;
  }
  // The Adoption cell used to print RAW evidence — "422/wk" on one row, "2 repos" on the next — while
  // Maint and Trust printed 0–100 scores. So the one column you might sort or compare on was the one
  // column whose numbers meant different things per row, and 422 downloads looked bigger than the
  // 51,323 stars behind the row under it. Show the SCORE (comparable, and the number that actually
  // feeds Trust) with the raw evidence under it as provenance — publish the arithmetic, don't hide it.
  function evidence(c) {
    if (c.npm_downloads != null) return compact(c.npm_downloads) + "/wk";
    if (c.gh_stars != null) return compact(c.gh_stars) + " ★";
    // config_reach counts different evidence per kind and cannot carry one label: for an MCP server it
    // is public agent configs that USE it; for a plugin it is marketplace manifests that LIST it.
    if (c.config_reach) return fmt(c.config_reach) + (c.kind === "plugin" ? " marketplaces" : " repos");
    return "";
  }
  function adoption(c) {
    var ev = evidence(c);
    if (c.adoption == null) return ev ? '<span class="num--dim">—</span><span class="unit">' + ev + '</span>'
                                     : '<span class="num--dim">—</span>';
    return String(c.adoption) + (ev ? '<span class="unit">' + ev + '</span>' : "");
  }
  function score(v) { return (v == null) ? '<span class="num--dim">—</span>' : String(v); }
  function num(v) { return v == null ? 0 : v; }
  function fresh(iso) {
    if (!iso) return { txt: "—", cls: "fresh--warm" };
    var months = (Date.now() - new Date(iso).getTime()) / 2.63e9;
    if (months < 1.5) return { txt: "active", cls: "fresh--hot" };
    if (months < 12) return { txt: Math.round(months) + "mo", cls: "fresh--warm" };
    return { txt: Math.round(months / 12 * 10) / 10 + "y", cls: "fresh--cold" };
  }
  function pretty(name) {
    return String(name).replace(/^@modelcontextprotocol\/server-/, "").replace(/-mcp$/, "").replace(/^mcp-server-/, "").replace(/^mcp-/, "");
  }
  // prefer the prerendered, indexable pretty URL; fall back to the client route
  // slug is DERIVED, not shipped — it is exactly slugify(id) (build.py), and sending both cost ~9 KB gz
  // of a 45 KB index for a string we can recompute in 40 bytes. Must stay byte-identical to build.py's
  // slugify or every listing 404s; tests/test_site.py checks the two agree across the whole export.
  function capHref(c) { return "/capability/" + c.id.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") + ".html"; }
  function compact(n) {
    if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + "M";
    if (n >= 1e3) return (n / 1e3).toFixed(n >= 1e4 ? 0 : 1) + "k";
    return String(n);
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function fmt(n) { return (n == null) ? "—" : String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function fdate(iso) { if (!iso) return ""; var d = new Date(iso); return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  function set(id, v) { var el = document.getElementById(id); if (el) el.textContent = v; }
})();
