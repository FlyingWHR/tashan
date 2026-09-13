// tashan — the Index: category catalog + a faceted, sortable, URL-stateful trust leaderboard (v2).
// Proven pattern (Algolia/Linear/NN-g): sort is ONE ordering (select); filters are many concurrent
// refinements (AND across facets, OR within). Active refinements show as removable chips + a live count.
(function () {
  "use strict";
  // terminal.js owns the verdict vocabulary and loads on every page before this one. Guard the call
  // anyway: a cross-file global is a load-order dependency, and if terminal.js ever fails to arrive
  // the dossier should render a plain chip rather than throw and show nothing at all. The headless
  // render test found this by running this file alone, which is exactly the condition being guarded.
  function vchip(v) {
    if (!v) return "";
    return window.tashanVerdict ? window.tashanVerdict(v)
      : '<span class="vd vd--' + esc(v) + '">' + esc(v) + "</span>";
  }


  var rowsEl = document.getElementById("rows");
  // facets are Sets (multi-select); toggles are bool; sort is one key
  // `role` is single-valued and deliberately not a Set: the page asks "what do you do", and nobody
  // holds two jobs while answering it. A role is a NAMED UNION OF TASKS, so it filters through the
  // task index rather than adding a parallel axis to the data.
  var state = { role: "", cat: new Set(), task: new Set(), kind: new Set(), vitality: new Set(), verdict: new Set(),
                official: false, clean: false, combine: false, sort: "tashan_score" };
  var data = { caps: [], cats: [], catMeta: {}, tasks: [], roles: [], taskMeta: {}, taskIds: null, roleIds: {} };
  // The board opened with 100 rows — a 7,500px table that was 75% of the page height, scrolled past
  // rather than read. TEASER is the ranked proof you are looking at real measurement; PAGE is the
  // increment once you have chosen a job and actually want the shelf.
  var TEASER = 10, PAGE = 25, shownCount = TEASER;

  var KIND_LABEL = { npm: "npm", pkg: "npm-pkg", docker: "docker", python: "python", remote: "remote",
                     skill: "skill", plugin: "plugin" };
  var VIT_LABEL = { active: "active", stable: "stable", abandoned: "abandoned" };
  var VERDICTS = ["deep", "solid", "thin", "wrapper", "slop"];
  var SORTS = [["tashan_score", "tashan score"], ["adoption", "Adoption"], ["fresh", "Freshness"],
               ["expertise", "Instruction depth"], ["maint", "Upkeep"], ["name", "Name A–Z"]];

  // reuse terminal.js's session-cached loader (one fetch+parse of the slim index per session, shared)
  // BOARD FIRST, CATALOGUED TAIL AFTER. index.json holds ranked + catalogued rows and is the contract
  // the published CLI reads, so it stays as it is. The browser does not need the unrated tail to paint
  // a RANKING: those 800 rows were 16.4 KB gz of a 56.8 KB first paint, 29% of the payload for entries
  // the ranking cannot order. board.json is 40.4 KB; catalogued.json arrives when the page is idle, so
  // filtering to unrated rows still works — it just stops being on the critical path.
  // Falls back to index.json if board.json is missing, so an older deploy cannot blank the page.
  var loadIndex = window.tashanIndex || function () {
    return fetch("/data/board.json").then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .catch(function () { return fetch("/data/index.json").then(function (r) { if (!r.ok) throw 0; return r.json(); }); });
  };
  Promise.all([
    loadIndex(),
    fetch("/data/categories.json").then(function (r) { return r.ok ? r.json() : { categories: [] }; }).catch(function () { return { categories: [] }; }),
    // The task taxonomy (labels, roles) and the tag->capability map. The map is 3.6 KB gz against a
    // 39.8 KB index, so it is fetched up front: a lazy path for that saves nothing measurable and costs
    // a loading state, a race on first click, and a filter that silently does nothing until it lands.
    // shared with terminal.js — see window.tashanTasks. Fetching it here too cost 68 KB twice.
    (window.tashanTasks ? window.tashanTasks() : fetch("/data/tasks.json").then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }))
      .then(function (t) { return t || { tasks: [], roles: [] }; }),
    fetch("/data/tags.json").then(function (r) { return r.ok ? r.json() : { tasks: {} }; }).catch(function () { return { tasks: {} }; })
  ]).then(function (res) {
    var d = res[0];
    // measured ⊂ tracked — the two nest, so the pair is readable. "quality-measured" previously showed
    // enriched_npm, which counts npm metadata fetches and is not a quality measurement at all.
    set("sCaps", fmt(d.measured || d.ranked));
    set("sRepos", fmt(d.total_capabilities));
    set("sDate", "measured " + fdate(d.generated_at));
    var fm = document.getElementById("footMethod");
    if (fm) fm.textContent = fmt(d.total_capabilities) + " capabilities · measured " + fdate(d.generated_at);
    // Coverage: what we have actually checked, of what we rank. Hidden until the data arrives so a
    // reader never sees em-dashes where a number belongs.
    var cov = document.getElementById("coverage");
    // coverage_of, never `ranked`: the slim index reuses `ranked` for its own board slice.
    if (cov && d.coverage_of) {
      var pct = function (n) { return n ? fmt(n) + " (" + Math.round(100 * n / d.coverage_of) + "%)" : "—"; };
      set("covRanked", fmt(d.coverage_of));
      set("covRisk", pct(d.risk_scanned));
      set("covGraded", pct(d.expertise_graded));
      set("covJob", pct(d.job_mapped));
      cov.hidden = false;
    }
    var bn = document.getElementById("boardNote");
    data._note = d.note || "";        // kept, because render() restores it when no filter narrows
    if (bn) bn.textContent = data._note;

    data.caps = (d.capabilities || []).filter(function (c) { return c.id.indexOf("key:") !== 0; });
    // The tail is merged by terminal.js's shared loader (the ONE place that fetches). It fires this
    // event when the extra rows land, so facet counts and the unrated filter refresh once instead of
    // being computed twice on first paint.
    if (!window.__tashanTailWired) {
      window.__tashanTailWired = 1;
      window.addEventListener("tashan:catalogued", function () {
        window.tashanIndex().then(function (d) {
          data.caps = (d.capabilities || []).filter(function (c) { return c.id.indexOf("key:") !== 0; });
          data._facets = null;
          commit();
        });
      });
    }
    (res[1].categories || []).forEach(function (c) { data.catMeta[c.id] = c; });
    data.cats = res[1].categories || [];
    data.tasks = (res[2] && res[2].tasks) || [];
    data.roles = (res[2] && res[2].roles) || [];
    data.tasks.forEach(function (t) { data.taskMeta[t.slug] = t; });
    var raw = (res[3] && res[3].tasks) || {};
    data.taskIds = {};
    Object.keys(raw).forEach(function (k) { data.taskIds[k] = new Set(raw[k]); });
    // ONE POPULATION, COUNTED ONCE. These counts used to be filtered to the board — the reasoning
    // was sound (the slim index is capped, so a rail promising 30 should not open onto 12) and the
    // result was worse than the problem: the homepage said "Software engineer 176" and /role/
    // engineer.html said 1,030, for the same role, on the same site. A reader who clicks through
    // sees a six-fold disagreement and concludes the numbers are made up — which is the one
    // conclusion this product cannot afford.
    //
    // So the count is now the catalogue's, matching every hub page exactly, and the over-promise it
    // reintroduces is answered where it actually appears: boardNote() says how many of them the
    // board is showing and links to the page that holds the rest. A number that disagrees with
    // another page is a bug; a number that is bigger than one view of it is just a view.
    var onBoard = {};
    data.caps.forEach(function (c) { onBoard[c.id] = 1; });
    data.tasks.forEach(function (t) {
      var ids = raw[t.slug] || [];
      t.count = ids.length;                      // catalogue, as /task/<slug>.html reports it
      t.onBoard = ids.filter(function (i) { return onBoard[i]; }).length;
    });
    // role -> the set of capability ids reachable through any of its tasks. Computed once: the grid
    // prints a count per role and the filter tests membership, and both would otherwise re-walk 69
    // task lists on every render.
    data.roles.forEach(function (r) { data.roleIds[r.id] = new Set(); });
    data.tasks.forEach(function (t) {
      var ids = raw[t.slug] || [];
      (t.roles || []).forEach(function (rid) {
        var into = data.roleIds[rid];
        if (into) ids.forEach(function (i) { into.add(i); });
      });
    });
    urlToState();
    // A shared ?role= URL must render what clicking that role renders. commit() sets this on every
    // interaction, but the first paint reads state from the URL and never went through commit — so a
    // link to a job opened on the 10-row teaser while the click that produced it opened on 25.
    shownCount = hasFilters() ? PAGE : TEASER;
    buildToolbar();
    renderRoles();
    renderTasks();
    renderCatalog();
    render();
    if (hasFilters()) { var a = document.getElementById("board-anchor"); if (a) a.scrollIntoView({ block: "start" }); }
  }).catch(function () {
    rowsEl.innerHTML = '<tr><td colspan="5"><div class="empty">Measurement data isn\'t published yet — the pipeline is still running. Check back shortly.</div></td></tr>';
  });

  addEventListener("popstate", function () { urlToState(); shownCount = hasFilters() ? PAGE : TEASER;
    buildToolbar(); renderRoles(); renderTasks(); renderCatalog(); render(); });

  // ---- URL state (shareable, back-button-friendly; defaults omitted) ----
  function urlToState() {
    var q = new URLSearchParams(location.search);
    state.role = q.get("role") || "";
    state.cat = csvSet(q.get("cat"));
    state.task = csvSet(q.get("task"));
    state.kind = csvSet(q.get("kind"));
    state.vitality = csvSet(q.get("vitality"));
    state.verdict = csvSet(q.get("verdict"));
    state.combine = q.get("combine") === "1";
    state.official = q.get("official") === "1";
    state.clean = q.get("clean") === "1";
    state.sort = q.get("sort") || "tashan_score";
  }
  function stateToURL(push) {
    var q = new URLSearchParams();
    if (state.role) q.set("role", state.role);
    if (state.cat.size) q.set("cat", [].concat.apply([], [Array.from(state.cat)]).join(","));
    if (state.task.size) q.set("task", Array.from(state.task).join(","));
    if (state.kind.size) q.set("kind", Array.from(state.kind).join(","));
    if (state.vitality.size) q.set("vitality", Array.from(state.vitality).join(","));
    if (state.verdict.size) q.set("verdict", Array.from(state.verdict).join(","));
    if (state.combine) q.set("combine", "1");
    if (state.official) q.set("official", "1");
    if (state.clean) q.set("clean", "1");
    if (state.sort !== "tashan_score") q.set("sort", state.sort);
    var url = location.pathname + (q.toString() ? "?" + q.toString() : "");
    history[push ? "pushState" : "replaceState"](null, "", url);
  }
  function csvSet(v) { return new Set(v ? v.split(",").filter(Boolean) : []); }
  function hasFilters() { return state.role || state.task.size || state.cat.size || state.kind.size || state.vitality.size || state.verdict.size || state.official || state.clean; }

  // ---- the toolbar: Type/Activity/Assessment pills + Official/Clean toggles + Sort select ----
  function buildToolbar() {
    var tb = document.getElementById("toolbar");
    if (!tb) return;
    var counts = facetCounts();
    // DERIVED from the data, never a hand-kept list. The literal here was
    // ["npm","pkg","docker","python","remote","skill"] — no "plugin" — so 343 plugins sat on the board
    // with no way to filter for them and no pill acknowledging they existed. A hardcoded facet list
    // silently deletes any type someone adds later, which is exactly how that happened.
    // Ordered by population so the common types read first; unknown keys fall back to their raw name.
    var kinds = Object.keys(counts.kind).filter(function (k) { return counts.kind[k]; })
      .sort(function (a, b) { return counts.kind[b] - counts.kind[a]; });
    tb.innerHTML =
      grp("Type", pillset("kind", kinds, function (k) { return KIND_LABEL[k] || k; }, counts.kind)) +
      grp("Activity", pillset("vitality", ["active", "stable", "abandoned"].filter(function (v) { return counts.vitality[v]; }), function (v) { return VIT_LABEL[v]; }, counts.vitality)) +
      grp("Depth", pillset("verdict", VERDICTS.filter(function (v) { return counts.verdict[v]; }), function (v) { return v; }, counts.verdict)) +
      // Sort and the toggles share ONE row, last. The <select> used to sit between Activity and Depth,
      // where it broke the facet flow mid-stream: a tall native control wedged between pill groups,
      // pushing Depth onto a new line at an arbitrary indent so no two labels lined up. It is a
      // different KIND of control from a facet and now reads as one.
      grp("Sort",
        '<label class="sortsel"><select id="sortSel">' +
          SORTS.map(function (s) { return '<option value="' + s[0] + '"' + (state.sort === s[0] ? " selected" : "") + '>' + s[1] + '</option>'; }).join("") +
        '</select></label>' +
        toggle("official", "✓ Official", counts.official) +
        (counts.dirty ? toggle("clean", "Hide deprecated/archived", counts.dirty) : ""));

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
  // Pills go in their OWN wrapper so the group can be a two-column grid (label | values). Without the
  // wrapper every pill is a direct grid child and lands in its own column.
  function grp(label, inner) {
    return '<div class="tgroup"><span class="tgroup__l mono">' + label + '</span>'
         + '<div class="tgroup__v">' + inner + '</div></div>';
  }
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
    var out = { kind: {}, vitality: {}, verdict: {}, official: 0, dirty: 0 };
    data.caps.forEach(function (c) {
      var k = normKind(c);
      out.kind[k] = (out.kind[k] || 0) + 1;
      if (c.vitality) out.vitality[c.vitality] = (out.vitality[c.vitality] || 0) + 1;
      if (c.expertise_verdict) out.verdict[c.expertise_verdict] = (out.verdict[c.expertise_verdict] || 0) + 1;
      if (officialOrg(c)) out.official++;
      // What "Hide deprecated/archived" would actually remove. It was rendered unconditionally on a
      // board holding zero of them, so the control could only ever do nothing — and a filter that
      // never changes the result teaches a reader that none of the filters work.
      if (c.npm_deprecated || c.gh_archived || (c.registry_status && c.registry_status !== "active")) out.dirty++;
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
  // Picking a tag or a category REPLACES the selection unless "Combine" is on. Multi-select by default
  // made the common case worse: nearly everyone is browsing one thing at a time, and an additive rail
  // silently accumulates refinements until the board is empty for reasons the reader cannot see.
  // Combining is real but occasional, so it is a switch rather than the default.
  function pick(setName, v) {
    var set = state[setName];
    if (state.combine) { set.has(v) ? set.delete(v) : set.add(v); return; }
    if (set.has(v) && set.size === 1) { set.clear(); return; }   // clicking the active one clears it
    state[setName] = new Set([v]);
  }

  // Baymard's filter-truncation testing: ~10 values is the sweet spot, 6 the floor, and past ~15 the
  // list stops being scannable and hides the OTHER filter types from view. We were rendering 95 rows
  // across 7 groups. Truncate to SHOWN, with a "+ N more" affordance directly beneath the values.
  // A value the user has already selected is always rendered, or applying a filter from the expanded
  // list would make that filter vanish when the list collapsed again.
  // 7. Baymard's band is 6-15 with ~10 ideal, but the count has to answer to the viewport: at 10 the
  // two lists ran 135px past it and at 8 (after the type scale raised row height to 33px) still 56px,
  // each time reintroducing the nested scrollbar this exists to remove. 7 clears it with room.
  var SHOWN = 7;
  function truncate(items, keyOf, selected, expanded) {
    if (expanded || items.length <= SHOWN + 1) return { list: items, hidden: 0 };
    var head = items.slice(0, SHOWN);
    var seen = {}; head.forEach(function (i) { seen[keyOf(i)] = 1; });
    items.slice(SHOWN).forEach(function (i) {
      if (selected.has(keyOf(i)) && !seen[keyOf(i)]) { head.push(i); seen[keyOf(i)] = 1; }
    });
    return { list: head, hidden: items.length - head.length };
  }
  // Expanding 70 more rows in place just rebuilds the wall we are removing, and the full set is
  // genuinely a different job from refining — it wants room, counts and the hub links. It gets its
  // own page, which doubles as the parent index those 68 hub pages never had.
  function moreRow(kind, hidden) {
    if (!hidden) return "";
    return '<a class="crow crow--more" href="/browse.html#' + (kind === "cat" ? "categories" : "tasks") +
      '">+ ' + hidden + " more &rsaquo;</a>";
  }

  // The icon id is derived, never stored: cat-<category> / role-<role>. The sprite inlined in the
  // page supplies the geometry, so there is no second copy of the path data to drift from
  // pipeline/icons.py. A missing symbol renders nothing, which is the right failure — a label with
  // no icon still reads.
  function icon(kind, id) {
    return '<svg class="icon" aria-hidden="true" focusable="false"><use href="#i-' +
      kind + "-" + esc(String(id)) + '"/></svg>';
  }

  function railRow(attr, id, label, count, on, tip, iconKind) {
    return '<button class="crow' + (on ? " is-on" : "") + '" data-' + attr + '="' + esc(id) + '"' +
      ' type="button" aria-pressed="' + !!on + '" title="' + esc(tip || label) + '">' +
      '<span class="crow__l">' + (iconKind ? icon(iconKind, id) : "") + esc(label) + "</span>" +
      '<span class="crow__c mono">' + count + "</span></button>";
  }

  function renderCombineToggle() {
    var t = document.getElementById("combineTog");
    if (!t) return;
    t.setAttribute("aria-checked", String(state.combine));
    t.classList.toggle("is-on", state.combine);
    t.onclick = function () {
      state.combine = !state.combine;
      // Leaving combine mode collapses a stacked selection to one, or the board would keep showing a
      // multi-selection the rail can no longer express.
      if (!state.combine) {
        if (state.task.size > 1) state.task = new Set([Array.from(state.task)[0]]);
        if (state.cat.size > 1) state.cat = new Set([Array.from(state.cat)[0]]);
      }
      commit();
    };
  }

  function roleLabel(id) {
    var r = data.roles.filter(function (x) { return x.id === id; })[0];
    return r ? r.label : id;
  }

  // THE JOB PICKER. The headline promises capabilities for the work you actually do, and until now the
  // only way to express that was a 236px rail of task chips beside a 7,500px table — the promise was a
  // secondary control. Roles already existed in tasks.json (23 of them, each a set of tasks, each with
  // an icon already in the inlined sprite); they were used for grouping on /browse.html and nowhere
  // else. This makes the axis the page is sold on the first thing you can touch.
  function renderRoles() {
    var grid = document.getElementById("rolegrid");
    if (!grid || !data.roles.length) return;
    var live = data.roles.map(function (r) {
      return { id: r.id, label: r.label, n: (data.roleIds[r.id] || { size: 0 }).size };
    }).filter(function (r) { return r.n >= 5; })      // a job with 4 shelves is not a shelf
      .sort(function (a, b) { return b.n - a.n; });
    grid.innerHTML = live.map(function (r) {
      var on = state.role === r.id;
      return '<button class="rolecard' + (on ? " is-on" : "") + '" type="button" data-role="' + esc(r.id) + '"' +
        ' aria-pressed="' + on + '">' +
        '<svg class="rolecard__i" aria-hidden="true"><use href="#i-role-' + esc(r.id) + '"></use></svg>' +
        '<span class="rolecard__l">' + esc(r.label) + '</span>' +
        '<span class="rolecard__n mono">' + fmt(r.n) + '</span></button>';
    }).join("");
    grid.onclick = function (e) {
      var b = e.target.closest("[data-role]");
      if (!b) return;
      var v = b.getAttribute("data-role");
      state.role = state.role === v ? "" : v;          // clicking the active job clears it
      commit();
      if (state.role) {
        var a = document.getElementById("board-anchor");
        if (a) a.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    };
  }

  function renderTasks() {
    renderCombineToggle();
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
    // Collapsed to the ten biggest shelves, the shape Hugging Face uses for its task facet over a
    // comparably large catalogue. The role headings live on /browse.html, where there is room for them.
    var flat = live.slice().sort(function (a, b) { return (b.count || 0) - (a.count || 0); });
    var cut = truncate(flat, function (t) { return t.slug; }, state.task, false);
    var html = cut.list.map(function (t) {
      return railRow("task", t.slug, t.label, t.count || 0, state.task.has(t.slug), t.blurb);
    }).join("") + moreRow("task", cut.hidden);
    rail.innerHTML = html;
    rail.onclick = function (e) {
      var b = e.target.closest("[data-task]");
      if (!b) return;
      pick("task", b.getAttribute("data-task"));
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
        if (c.tashan_score != null && (!top[c.category] || c.tashan_score > top[c.category].trust)) top[c.category] = c;
      });
      data._catAgg = { counts: counts, top: top };
    }
    var counts = data._catAgg.counts, top = data._catAgg.top;
    function row(id, label, count, on, lead) {
      var tip = lead ? label + " — top: " + disp(lead) + " (" + lead.trust + ")" : label;
      return railRow("cat", id, label, count, on, tip, "cat");
    }
    var live = data.cats.filter(function (cat) { return counts[cat.id]; })
      .sort(function (a, b) { return counts[b.id] - counts[a.id]; });
    var cut = truncate(live, function (c) { return c.id; }, state.cat, false);
    var html = cut.list.map(function (cat) {
      return row(cat.id, cat.label, counts[cat.id], state.cat.has(cat.id), top[cat.id]);
    }).join("") + moreRow("cat", cut.hidden);
    rail.innerHTML = html;
    rail.onclick = function (e) {
      var b = e.target.closest("button[data-cat]");
      if (!b) return;
      // Same rule as tags — see pick(). The two rails used to disagree (one additive, one replacing),
      // which is what made the left column feel unpredictable.
      pick("cat", b.dataset.cat);
      commit();
    };
  }

  function commit() {
    shownCount = hasFilters() ? PAGE : TEASER;   // no filter means the teaser, not a wall of rows
    stateToURL(true); buildToolbar(); renderRoles(); renderTasks(); renderCatalog(); render();
  }

  function passes(c) {
    // Task filter: OR within the group, AND against every other facet — the same shape as Type and
    // Activity. Tasks are multi-select because a capability genuinely does several jobs; category stays
    // single-select because browsing two domains at once is not a thing people mean.
    if (state.task.size) {
      var hit = false;
      state.task.forEach(function (t) { var s2 = data.taskIds[t]; if (s2 && s2.has(c.id)) hit = true; });
      if (!hit) return false;
    }
    // A role is the union of its tasks, so it is one membership test, not a second traversal.
    if (state.role) { var rs = data.roleIds[state.role]; if (!rs || !rs.has(c.id)) return false; }
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
    var ar = a.tashan_score != null, br = b.tashan_score != null;
    if (ar !== br) return ar ? -1 : 1;
    switch (state.sort) {
      // Sort on the SCORE, not on raw evidence. `npm_downloads || config_reach` compared 422 weekly
      // downloads against "2 marketplaces" as if they were one magnitude, so 422 always beat a
      // 51,323-star plugin. The score is the only cross-kind-comparable number we have.
      case "adoption": return num(b.adoption) - num(a.adoption);
      case "fresh": return recency(b) - recency(a);
      case "expertise": return (num(b.expertise) - num(a.expertise)) || (num(b.tashan_score) - num(a.tashan_score));
      // `maintenance` was renamed to `upkeep` in the schema (build.py RENAMES) and this was never
      // updated, so num(undefined) - num(undefined) === 0 for every pair and choosing "Upkeep"
      // silently left the board in whatever order it was already in.
      case "maint": return num(b.upkeep) - num(a.upkeep);
      case "name": return disp(a).toLowerCase() < disp(b).toLowerCase() ? -1 : 1;
      default: return num(b.tashan_score) - num(a.tashan_score);   // trust
    }
  }
  function recency(c) { var iso = c.npm_last_publish || c.gh_pushed || c.last_seen; return iso ? new Date(iso).getTime() : 0; }

  function render() {
    var bt = document.getElementById("boardTitle");
    var singleCat = state.cat.size === 1 ? Array.from(state.cat)[0] : null;
    var roleMeta = state.role && data.roles.filter(function (r) { return r.id === state.role; })[0];
    if (bt) bt.textContent = roleMeta ? roleMeta.label
      : (singleCat && data.catMeta[singleCat] ? data.catMeta[singleCat].label : "Ranked by the tashan score");
    // Only the category blurb, which says something the page cannot: what is IN this category. The
    // default text was a paragraph restating the column headers, which already carry the same
    // explanation in their tooltips — and it still called the score "Trust", a name retired two
    // renames ago, so the one line most visitors read was also the one that was wrong.
    var bd = document.getElementById("boardDesc");
    if (bd) {
      var blurb = singleCat && data.catMeta[singleCat] ? data.catMeta[singleCat].blurb : "";
      bd.textContent = blurb;
      bd.hidden = !blurb;
    }

    var list = data.caps.filter(passes).slice().sort(sortComparator);
    // WHAT THIS BOARD IS SHOWING, when it is showing less than the count that got you here. The
    // rail and the role grid now report the catalogue, so they agree with /task/ and /role/ — which
    // means the board, capped for first paint, can hold fewer rows than the tile you clicked
    // promised. Saying so is the whole fix: an unexplained gap reads as a broken number, and a
    // stated one reads as a view. Links to the page that actually holds the rest.
    var bn2 = document.getElementById("boardNote");
    if (bn2) {
      var full = 0, hub = "";
      if (state.role) {
        full = (data.roleIds[state.role] || { size: 0 }).size;
        hub = "/role/" + state.role + ".html";
      } else if (state.task && state.task.size === 1) {
        var ts = Array.from(state.task)[0];
        var tm = data.tasks.filter(function (t) { return t.slug === ts; })[0];
        if (tm) { full = tm.count || 0; hub = "/task/" + ts + ".html"; }
      }
      if (full > list.length) {
        bn2.innerHTML = "Showing the " + list.length.toLocaleString() + " highest-ranked of "
          + full.toLocaleString() + ' measured for this work. <a class="link" href="' + hub
          + '">See all &rsaquo;</a>';
      } else {
        bn2.textContent = data._note || "";
      }
    }
    renderActiveBar(list.length);
    var shown = list.slice(0, shownCount);
    if (!shown.length) { rowsEl.innerHTML = '<tr><td colspan="5"><div class="empty">No capabilities match these filters. <button class="linkbtn" id="clearEmpty" type="button">Clear filters</button></div></td></tr>';
      var ce = document.getElementById("clearEmpty"); if (ce) ce.onclick = clearAll; return; }
    var html = "";
    shown.forEach(function (c, i) {
      var t = c.tashan_score, bar = (t == null) ? 0 : t;
      var fr = vitalityCell(c);
      var dep = c.npm_deprecated ? ' <span class="fresh fresh--cold">deprecated</span>' : "";
      // Security is the headline of the product, so a finding belongs where people scan, not only on
      // the dossier. A chip rather than a column: it costs no width and appears only when there is
      // something to say, so a clean board stays quiet instead of printing "0 advisories" 5,788 times.
      var sec = "";
      if (c.sec_advisory_count) {
        var sv = (c.sec_max_severity || "").toLowerCase();
        sec += ' <span class="sev sev--' + (sv === "malicious" ? "mal" : sv === "critical" ? "crit"
          : sv === "high" ? "high" : sv === "low" ? "low" : "mod") + '" title="' + c.sec_advisory_count +
          ' known advisor' + (c.sec_advisory_count === 1 ? "y" : "ies") +
          ' against the current release">' + c.sec_advisory_count + ' advisor' +
          (c.sec_advisory_count === 1 ? "y" : "ies") + '</span>';
      }
      if (c.sec_install_script) sec += ' <span class="sev sev--mod" title="Executes a script when installed">install script</span>';
      var vd = c.expertise_verdict ? " " + vchip(c.expertise_verdict) : "";
      var org = officialOrg(c);
      var off = org ? ' <span class="official" title="Official from ' + esc(org) + '">✓ ' + esc(org) + '</span>' : "";
      var catTag = (!singleCat && c.category && data.catMeta[c.category]) ? ' <span class="cattag" title="Category">' + esc(data.catMeta[c.category].label) + '</span>' : "";
      html += '<tr data-href="' + capHref(c) + '">' +
        '<td class="rank">' + (i + 1) + '</td>' +
        '<td><div class="cap__name"><a class="cap__link" href="' + capHref(c) + '">' + esc(disp(c)) + '</a> <span class="tag">' + esc(KIND_LABEL[c.kind] || c.kind) + '</span>' + off + vd + dep + sec + '</div>' +
        // was: the full id, "pkg:@supabase/mcp-server-supabase" under a row already headed
        // "@supabase/mcp-server-supabase". The category is the only thing here a reader did not have.
        '<div class="cap__id">' + catTag + '</div></td>' +
        // ONE headline, then the evidence it came from, then one health flag. The board used to print
        // Adoption, Maint, Fresh AND Trust — four numbers competing for the same glance, none of which
        // is the answer to "should I install this". Components moved to the dossier, which has room to
        // explain them; the evidence column stays because it is the part no competitor can show.
        '<td><div class="sig' + (t == null ? ' sig--none' : '') + '">' + (t == null
          ? '<span class="unrated" title="Catalogued, not scored: its only upkeep evidence is the repository it lives in, which every skill in that repo shares. A grade of its own SKILL.md is what makes it scorable.">not scored yet</span>'
          : '<span class="sig__val">' + Math.round(t) + '</span>') +
        '<span class="bar" data-w="' + bar + '"><i></i></span></div></td>' +
        '<td class="num">' + evidenceCell(c) + '</td>' +
        '<td><span class="fresh ' + fr.cls + '"' + (fr.title ? ' title="' + esc(fr.title) + '"' : '') + '>' + fr.txt + '</span></td>' +
        '</tr>';
    });
    if (list.length > shown.length) {                      // reveal the rest instead of hard-capping the board
      var more = Math.min(PAGE, list.length - shown.length);
      html += '<tr class="board__more"><td colspan="5"><button class="btn btn--ghost" id="showMore" type="button">' +
        'Show ' + more + ' more <span class="mono o-55">· ' + shown.length + ' of ' + fmt(list.length) + '</span></button></td></tr>';
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
    if (state.role) chips.push(chip("role", state.role, roleLabel(state.role)));
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
        if (f === "official" || f === "clean") state[f] = false;
        else if (f === "role") state.role = "";
        else state[f].delete(v);
        commit();
      };
    });
    var ca = document.getElementById("clearAll"); if (ca) ca.onclick = clearAll;
  }
  function chip(facet, val, label) {
    return '<button class="achip" data-rm="' + facet + '" data-val="' + esc(val) + '" type="button">' + esc(label) + ' <span class="achip__x">✕</span></button>';
  }
  function clearAll() {
    state.role = "";
    state.task.clear(); state.cat.clear(); state.kind.clear(); state.vitality.clear(); state.verdict.clear();
    state.official = false; state.clean = false;   // `combine` is a mode, not a refinement — it survives Clear all
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
  function evidenceCell(c) {
    var ev = evidence(c);
    return ev ? '<span class="ev">' + ev + "</span>" : '<span class="num--dim">—</span>';
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
  // The human label, derived ONCE in build.py's apply_labels over the whole corpus — it has to see
  // every other row to know that 364 skills share the title "claude-community" and that two products
  // are both called "Notion". pretty() stays for the places that build an IDENTIFIER (an install
  // command, a folder name), where spaces and "·" would be wrong.
  function disp(c) { return c.label || pretty(c.name); }
  // prefer the prerendered, indexable pretty URL; fall back to the client route
  // slug is DERIVED, not shipped — it is exactly slugify(id) (build.py), and sending both cost ~9 KB gz
  // of a 45 KB index for a string we can recompute in 40 bytes. Must stay byte-identical to build.py's
  // slugify or every listing 404s; tests/test_site.py checks the two agree across the whole export.
  // `c.slug` is present ONLY when the derivation is wrong for that row — i.e. it lost a slug
  // collision (`@stripe/mcp` and `stripe-mcp` both derive to pkg-stripe-mcp, so one page served two
  // capabilities). Deriving unconditionally sent the official Stripe row to the unofficial one's
  // dossier. Prefer the shipped value; derive for the other 6,323.
  function capHref(c) { return "/capability/" + (c.slug || c.id.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")) + ".html"; }
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
