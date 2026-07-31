/* /activate — the browser half of the device-authorisation grant.
 *
 * A terminal somewhere ran `npx tashan-cli login` and is polling. This page is where a human says
 * yes. It has exactly three states and it must never guess which one it is in:
 *
 *   signed in      -> show the code, one button, done
 *   signed out     -> two doors: buy Pro, or paste the key from the purchase email ONCE, ever
 *   no code        -> explain what this page is for, because people do arrive here by accident
 *
 * The rule that matters: a session is never assumed. If /api/account cannot be reached we render
 * SIGNED OUT, never an optimistic "you're Pro" — a false positive here sends someone to click an
 * approve button that will 401, which is worse than asking them to sign in.
 *
 * boot() runs last. A page in this codebase once called render() above a `const` that had not
 * initialised, which threw on load and produced a reload loop.
 */
(function () {
  "use strict";

  var host = document.getElementById("activate");
  if (!host) return;

  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };

  var norm = function (s) { return String(s || "").toUpperCase().replace(/[^A-Z0-9]/g, ""); };
  var pretty = function (c) { c = norm(c); return c.length === 8 ? c.slice(0, 4) + "-" + c.slice(4) : c; };

  var params = new URLSearchParams(location.search);
  var code = norm(params.get("code"));

  function api(path, opts) {
    return fetch(path, Object.assign({ headers: { "content-type": "application/json" } }, opts || {}))
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, status: r.status, body: j }; }); });
  }

  // ---- the parts -------------------------------------------------------------------------------

  function codeBlock() {
    return '<p class="actv__lbl mono">The code in your terminal</p>' +
      '<p class="actv__code mono">' + esc(pretty(code)) + "</p>";
  }

  function askForCode(msg) {
    host.innerHTML =
      '<h1>Authorise a device</h1>' +
      '<p class="lede">Your terminal is waiting for you to confirm a code. Run ' +
      '<code>npx tashan-cli login</code> if you have not yet — it prints one and opens this page.</p>' +
      (msg ? '<div class="callout"><b>' + esc(msg) + "</b></div>" : "") +
      '<form class="actv__form" id="codeForm">' +
      '<label class="actv__lbl mono" for="codeIn">Enter the code</label>' +
      '<input class="actv__in mono" id="codeIn" name="code" type="text" autocomplete="off" ' +
      'autocapitalize="characters" spellcheck="false" placeholder="WXYZ-1234" maxlength="9" required>' +
      '<button class="btn btn--primary" type="submit">Continue &rsaquo;</button>' +
      "</form>";
    var f = document.getElementById("codeForm");
    f.onsubmit = function (e) {
      e.preventDefault();
      var v = norm(document.getElementById("codeIn").value);
      if (v.length !== 8) return askForCode("A code is 8 characters, like WXYZ-1234.");
      code = v;
      history.replaceState(null, "", "/activate?code=" + pretty(v));
      boot();
    };
  }

  function signedOut() {
    host.innerHTML =
      '<h1>Sign in to authorise</h1>' +
      codeBlock() +
      '<p class="lede">This browser is not signed in yet, so there is nothing to hand the terminal. ' +
      "Two ways in — after either one, you never do this again on any machine.</p>" +

      '<div class="actv__doors">' +
        '<div class="actv__door">' +
          '<p class="actv__k mono">I already bought Pro</p>' +
          '<h2>Paste your licence key, once</h2>' +
          '<p>It is in your purchase email. This is the only time you will type it — every machine ' +
          "after this one is approved with a click.</p>" +
          '<form id="keyForm">' +
            '<label class="actv__lbl mono" for="keyIn">Licence key</label>' +
            '<input class="actv__in mono" id="keyIn" name="key" type="password" autocomplete="off" ' +
            'spellcheck="false" placeholder="tashan_…" required>' +
            '<button class="btn btn--primary" type="submit">Sign in &rsaquo;</button>' +
            '<p class="actv__err" id="keyErr" hidden></p>' +
          "</form>" +
        "</div>" +
        '<div class="actv__door">' +
          '<p class="actv__k mono">I do not have Pro</p>' +
          '<h2>What the licence adds</h2>' +
          '<p>The free tier names every finding and always will. Pro tells you which advisory, the ' +
          "version that fixes it, what an install script actually runs, and the replacement for " +
          "anything dead in your config.</p>" +
          '<p><a class="btn btn--ghost" href="/pricing.html">See what Pro costs &rsaquo;</a></p>' +
        "</div>" +
      "</div>";

    var kf = document.getElementById("keyForm");
    kf.onsubmit = function (e) {
      e.preventDefault();
      var err = document.getElementById("keyErr");
      var btn = kf.querySelector("button");
      var key = document.getElementById("keyIn").value.trim();
      err.hidden = true;
      btn.disabled = true;
      btn.textContent = "Checking…";
      api("/api/account", { method: "POST", body: JSON.stringify({ key: key }) }).then(function (r) {
        btn.disabled = false;
        btn.textContent = "Sign in ›";
        if (!r.ok || !r.body || !r.body.signed_in) {
          err.textContent = (r.body && r.body.error) || "That key was not accepted.";
          err.hidden = false;
          return;
        }
        boot();                      // signed in now — fall through to the approve state
      }).catch(function () {
        btn.disabled = false;
        btn.textContent = "Sign in ›";
        err.textContent = "Could not reach tashan. Check your connection and try again.";
        err.hidden = false;
      });
    };
  }

  function approve(acct) {
    var who = acct.email || acct.name || "your account";
    host.innerHTML =
      '<h1>Authorise this device?</h1>' +
      codeBlock() +
      '<p class="lede">A terminal asked to sign in as <b>' + esc(who) + "</b>. Confirm the code above " +
      "matches the one it printed, then approve.</p>" +
      (acct.active ? "" : '<div class="callout"><b>Heads up.</b> This licence is ' + esc(acct.status || "not active") +
        ". You can still approve the device; the CLI will show the free tier until the licence is live again.</div>") +
      '<p class="actv__cta">' +
        '<button class="btn btn--primary" id="yes" type="button">Approve this device &rsaquo;</button>' +
        '<button class="btn btn--ghost" id="no" type="button">Not me &mdash; deny</button>' +
      "</p>" +
      '<p class="actv__err" id="apErr" hidden></p>' +
      '<p class="note">Approving hands this machine your licence so the CLI can store it. It does not ' +
      "give it your password — there is not one — and you can release the machine any time from " +
      '<a class="link" href="/account.html">your account</a>.</p>';

    function decide(ok) {
      var err = document.getElementById("apErr");
      var y = document.getElementById("yes"), n = document.getElementById("no");
      y.disabled = n.disabled = true;
      err.hidden = true;
      api("/api/device", { method: "POST", body: JSON.stringify({ user_code: code, approve: ok }) })
        .then(function (r) {
          if (!r.ok) {
            y.disabled = n.disabled = false;
            err.textContent = (r.body && r.body.message) || (r.body && r.body.error) ||
              "Could not authorise that code.";
            err.hidden = false;
            return;
          }
          done(ok, who);
        })
        .catch(function () {
          y.disabled = n.disabled = false;
          err.textContent = "Could not reach tashan. Try again.";
          err.hidden = false;
        });
    }
    document.getElementById("yes").onclick = function () { decide(true); };
    document.getElementById("no").onclick = function () { decide(false); };
  }

  function done(ok, who) {
    host.innerHTML = ok
      ? '<h1>Approved.</h1>' +
        '<p class="lede">Your terminal has it — it will say <code>Pro is active on this machine</code> ' +
        "within a few seconds. You can close this tab.</p>" +
        '<div class="callout"><b>Next.</b> <code>npx tashan-cli doctor</code> reads your Claude Code, ' +
        "Cursor and Desktop configs and now names the fix for everything it finds, not just the " +
        "finding.</div>" +
        '<p class="mt-12"><a class="btn btn--ghost" href="/account.html">Your account &rsaquo;</a></p>'
      : '<h1>Denied.</h1>' +
        '<p class="lede">Nothing was handed over. The terminal will stop waiting and report that the ' +
        "request was denied.</p>" +
        '<p class="note">If that was not you, nothing has leaked — a code is useless without an ' +
        "approval from a signed-in browser, and this one is now dead.</p>" +
        '<p class="mt-12"><a class="btn btn--ghost" href="/">Back to the Index &rsaquo;</a></p>';
  }

  // ---- entry point -----------------------------------------------------------------------------

  function boot() {
    if (!code) return askForCode("");
    host.innerHTML = '<p class="updated mono">Checking…</p>';
    // Does the code exist at all? Failing here is far better than failing after someone clicks
    // Approve, because at this point the fix is "run the command again" and they still have the
    // terminal open.
    api("/api/device?code=" + encodeURIComponent(pretty(code))).then(function (d) {
      if (!d.ok || !d.body || !d.body.found) {
        return askForCode("That code has expired or was never issued. Run npx tashan-cli login again.");
      }
      return api("/api/account").then(function (r) {
        // No session, unreachable API, or an error — all render signed out. Never optimistic.
        if (!r.ok || !r.body || !r.body.signed_in) return signedOut();
        approve(r.body);
      });
    }).catch(function () {
      askForCode("Could not reach tashan. Check your connection and try again.");
    });
  }

  boot();
})();
