// /audit — paste an MCP config, see what is actually in it.
//
// WHY THIS PAGE EXISTS. Until now there was no surface on this site where a human could DO anything.
// Every page described measurements; the only thing anyone could act on was a $6/month subscription
// to an API and a CLI. Someone deciding right now whether to install four MCP servers had no way to
// ask us about their four, and no way to pay us for one answer. That is a likelier explanation of
// 2,642 views and zero offer clicks than "nobody has heard of us".
//
// YOUR KEYS NEVER LEAVE THE BROWSER, and this is not a courtesy — an MCP config is one of the most
// secret-dense files a developer owns. GITHUB_TOKEN, database URLs, cloud credentials and API keys
// all live in the `env` block right next to the package name. So the parse happens HERE, entirely
// client-side, and the only thing posted to /v0.1/audit is a list of bare package names. Nothing
// else is read, kept, or transmitted. The page says so where a reader will see it before pasting,
// not in a privacy policy, because a promise made after the paste is worthless.
//
// identify() IS DUPLICATED FROM cli/doctor.mjs ON PURPOSE. The site is zero-build with a strict CSP
// and classic scripts, so there is no import path from a Node module into this file. Two copies of
// one definition is exactly how prerender.py and capability.js drifted three times in a night, so
// tests/test_audit_parity.mjs runs BOTH implementations over the same fixtures and fails if they
// ever disagree. Change one, change the other, or the suite stops you.

(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };

  // --- the parser, pinned to cli/doctor.mjs by tests/test_audit_parity.mjs -------------------------

  /** Drop a trailing @version/@tag without eating a scoped package's leading @.
   *  "@playwright/mcp@latest" -> "@playwright/mcp", "@upstash/context7-mcp" -> unchanged. */
  function stripVersion(spec) {
    var at = spec.lastIndexOf("@");
    return at > 0 ? spec.slice(0, at) : spec;
  }

  /** One config entry -> what it actually runs. Mirrors doctor.mjs identify(). */
  function identify(entry) {
    if (!entry || typeof entry !== "object") return null;
    if (entry.url) {
      try { return { kind: "remote", id: new URL(entry.url).host }; }
      catch (e) { return { kind: "remote", id: entry.url }; }
    }
    var args = Array.isArray(entry.args) ? entry.args : [];
    var cmd = String(entry.command || "");
    var pick = function () {
      for (var i = 0; i < args.length; i++) {
        if (typeof args[i] === "string" && args[i].charAt(0) !== "-") return args[i];
      }
      return null;
    };
    if (/npx$/.test(cmd)) {
      var pkg = pick();
      if (pkg) return { kind: "npm", id: stripVersion(String(pkg)) };
    }
    if (/^(uvx|uv)$/.test(cmd)) { var py = pick(); if (py) return { kind: "python", id: py }; }
    if (/docker$/.test(cmd)) {
      for (var j = 0; j < args.length; j++) {
        if (typeof args[j] === "string" && args[j].charAt(0) !== "-" && args[j] !== "run") {
          return { kind: "docker", id: args[j] };
        }
      }
    }
    return cmd ? { kind: "local", id: cmd } : null;
  }

  /** Everything runnable in a pasted blob. Accepts every config shape we know plus a bare list,
   *  because people paste what they have, not what a parser wants. Never throws. */
  function serversFrom(text) {
    var out = [], seen = {};
    var add = function (label, ident) {
      if (!ident || !ident.id) return;
      var k = ident.kind + ":" + ident.id;
      if (seen[k]) return;
      seen[k] = 1;
      out.push({ label: label, kind: ident.kind, id: ident.id });
    };
    var doc = null;
    try { doc = JSON.parse(text); } catch (e) { doc = null; }

    if (doc && typeof doc === "object") {
      // `mcpServers` (Claude Code/Desktop, Cursor, Windsurf) and `servers` (VS Code). Accept a
      // whole settings file too — people paste the entire ~/.claude.json, which nests the block.
      var blocks = [];
      var walk = function (node, depth) {
        if (!node || typeof node !== "object" || depth > 4) return;
        if (node.mcpServers && typeof node.mcpServers === "object") blocks.push(node.mcpServers);
        if (node.servers && typeof node.servers === "object") blocks.push(node.servers);
        for (var k in node) {
          if (Object.prototype.hasOwnProperty.call(node, k) && node[k] && typeof node[k] === "object") {
            walk(node[k], depth + 1);
          }
        }
      };
      walk(doc, 0);
      if (!blocks.length && !Array.isArray(doc)) blocks.push(doc);   // the block pasted on its own
      for (var b = 0; b < blocks.length; b++) {
        for (var name in blocks[b]) {
          if (Object.prototype.hasOwnProperty.call(blocks[b], name)) {
            add(name, identify(blocks[b][name]));
          }
        }
      }
      if (Array.isArray(doc)) {
        for (var i = 0; i < doc.length; i++) {
          if (typeof doc[i] === "string") add(doc[i], { kind: "npm", id: stripVersion(doc[i]) });
        }
      }
    }
    if (!out.length) {
      // Not JSON: treat it as a list of names, one per line or comma-separated. A half-remembered
      // list is still a question worth answering.
      var parts = text.split(/[\n,]+/);
      for (var p = 0; p < parts.length; p++) {
        var t = parts[p].trim().replace(/^["'`]|["'`,]$/g, "");
        if (t && !/[{}[\]]/.test(t) && t.length < 120) {
          add(t, { kind: "npm", id: stripVersion(t) });
        }
      }
    }
    return out;
  }

  // --- rendering ----------------------------------------------------------------------------------

  var VERDICT = {
    replace: { cls: "bad", word: "Replace" },
    review: { cls: "warn", word: "Look at this" },
    keep: { cls: "ok", word: "Fine" },
  };

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function row(r) {
    var v = VERDICT[r.verdict] || { cls: "", word: r.verdict || "unrated" };
    var li = el("li", "aud__r aud__r--" + v.cls);
    var top = el("div", "aud__top");
    var a = el("a", "aud__n");
    a.href = r.url || "#";
    a.textContent = r.name || r.id;
    top.appendChild(a);
    top.appendChild(el("span", "aud__v mono", v.word));
    if (r.tashan_score != null) top.appendChild(el("span", "aud__s mono", String(r.tashan_score)));
    li.appendChild(top);

    var flags = (r.flags || []).slice();
    if (flags.length) {
      var ul = el("ul", "aud__f");
      for (var i = 0; i < flags.length; i++) {
        ul.appendChild(el("li", null, String(flags[i])));
      }
      li.appendChild(ul);
    } else if (r.rated === false) {
      li.appendChild(el("p", "aud__f mono", "not rated — no per-item evidence, which is not the same as safe"));
    }
    return li;
  }

  function render(data, asked) {
    var out = $("audOut");
    out.textContent = "";
    var rows = data.audited || [];
    var s = data.summary || {};

    var head = el("div", "aud__sum");
    head.appendChild(el("p", "aud__sum__h",
      "Measured " + (s.measured || rows.length) + " of " + asked.length + "."));
    var line = [];
    if (s.replace) line.push(s.replace + " to replace");
    if (s.review) line.push(s.review + " worth a look");
    if (s.keep) line.push(s.keep + " fine");
    head.appendChild(el("p", "aud__sum__l mono", line.join(" · ") || "nothing flagged"));
    out.appendChild(head);

    // Order by what needs attention: a list sorted alphabetically buries the one row that matters.
    var order = { replace: 0, review: 1, keep: 2 };
    rows.sort(function (a, b) {
      return (order[a.verdict] == null ? 3 : order[a.verdict])
           - (order[b.verdict] == null ? 3 : order[b.verdict]);
    });
    var ul = el("ul", "aud__l");
    for (var i = 0; i < rows.length; i++) ul.appendChild(row(rows[i]));
    out.appendChild(ul);

    var un = data.unmeasured || [];
    if (un.length) {
      // ABSENCE IS NOT SAFETY. This line is the whole reason the tool can be trusted.
      var names = un.map(function (u) { return typeof u === "string" ? u : (u.name || u.id); });
      out.appendChild(el("p", "aud__un",
        "We hold no measurement for " + names.length + ": " + names.join(", ")
        + ". That means we have not looked, never that they are safe."));
    }
    $("audNote").textContent = data.note || "";
    offer(rows, s);
  }

  // THE OFFER IS EARNED, NEVER A STANDING NAG. This project's rule is that the Pro panel appears
  // because a finding put it there, so it stays hidden until someone has actually checked a setup —
  // and it is a WATCH pitch, not a "see more" one. Everything on this page is already free and stays
  // free; what a subscription adds is the axis a single look cannot give you, which is time. Selling
  // "unlock the findings" here would be selling what we just gave away.
  function offer(rows, sum) {
    var panel = document.querySelector('.pro[data-pro="audit"]');
    if (!panel || !rows.length) return;
    var watchable = rows.filter(function (r) { return r.id; }).length;
    if (!watchable) return;
    var lede = panel.querySelector(".pro__lede");
    if (lede) {
      var attention = (sum.replace || 0) + (sum.review || 0);
      lede.textContent = attention
        ? ("Right now " + attention + " of these " + watchable + " want a look. What one check cannot "
           + "show you is the change — a maintainer adding an install script in a patch release, an "
           + "advisory landing against the version you already run. That is what watching them adds.")
        : ("These " + watchable + " look fine today. What one check cannot show you is the change — a "
           + "maintainer adding an install script in a patch release, an advisory landing against the "
           + "version you already run. That is what watching them adds.");
    }
    panel.hidden = false;
  }

  function run() {
    var text = $("audIn").value || "";
    var found = serversFrom(text);
    var btn = $("audGo");
    var out = $("audOut");
    if (!found.length) {
      out.textContent = "";
      out.appendChild(el("p", "aud__err",
        "Nothing runnable found. Paste an mcpServers block, or just the package names."));
      return;
    }
    // Only names go over the wire. `found` still carries kind/label for display; they stay here.
    var names = found.filter(function (f) { return f.kind === "npm" || f.kind === "python"; })
                     .map(function (f) { return f.id; });
    var localOnly = found.length - names.length;
    if (!names.length) {
      out.textContent = "";
      out.appendChild(el("p", "aud__err",
        "Found " + found.length + " entr" + (found.length === 1 ? "y" : "ies") + ", but all are local "
        + "commands or remote URLs. We measure published packages, so there is nothing to look up."));
      return;
    }

    btn.disabled = true;
    btn.textContent = "Checking…";
    out.textContent = "";
    fetch("/v0.1/audit", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ servers: names }),
    }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (d) {
      render(d, names);
      if (localOnly) {
        $("audNote").textContent = (($("audNote").textContent || "") + " " + localOnly
          + " local or remote entr" + (localOnly === 1 ? "y was" : "ies were")
          + " skipped — we can only measure published packages.").trim();
      }
    }).catch(function (e) {
      out.appendChild(el("p", "aud__err", "Could not reach the audit (" + e.message + "). "
        + "Nothing was sent anywhere else; try again."));
    }).then(function () {
      btn.disabled = false;
      btn.textContent = "Check my setup";
    });
  }

  function boot() {
    var btn = $("audGo");
    if (!btn) return;
    btn.addEventListener("click", run);
    $("audIn").addEventListener("keydown", function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") run();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  // Exposed for tests/test_audit_parity.mjs, which runs this file and cli/doctor.mjs over the same
  // fixtures. Two copies of one definition only stay honest if something checks.
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { identify: identify, stripVersion: stripVersion, serversFrom: serversFrom };
  }
})();
