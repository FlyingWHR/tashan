// The account panel. Shows STATE, not prose about billing.
//
// There is no login, so the key is the credential. Paste it once and the browser remembers it, the
// same way the CLI remembers it in ~/.config/tashan/key — so a return visit opens on your status
// rather than on a form. "Forget" clears it, which matters on a shared machine.
(function () {
  var LS = "tashan.key";
  var panel = document.getElementById("acct");
  if (!panel) return;

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function fdate(iso) {
    if (!iso) return "";
    return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function signedOut(msg) {
    panel.className = "acct";
    panel.innerHTML =
      '<p class="acct__lead">Paste your licence key to see its status. It stays in this browser ' +
      'and is never sent anywhere except to check it is valid.</p>' +
      (msg ? '<p class="acct__err">' + esc(msg) + "</p>" : "") +
      '<form class="acct__form" id="acctForm">' +
      '<input class="acct__in mono" id="acctKey" type="text" autocomplete="off" spellcheck="false" ' +
      'placeholder="tashan_… or polar_…" aria-label="Licence key">' +
      '<button class="btn btn--primary" type="submit">Check</button></form>' +
      '<p class="acct__hint">Do not have it to hand? It is in the email from your purchase, or ' +
      '<a class="link" href="https://polar.sh/tashan/portal" rel="noopener">sign in to billing</a>.</p>';
    document.getElementById("acctForm").onsubmit = function (e) {
      e.preventDefault();
      var k = document.getElementById("acctKey").value.trim();
      if (k) check(k, true);
    };
  }

  function busy() {
    panel.className = "acct";
    panel.innerHTML = '<p class="acct__lead">Checking…</p>';
  }

  function signedIn(d) {
    panel.className = "acct acct--on";
    panel.innerHTML =
      '<div class="acct__row"><span class="acct__badge">Pro · active</span>' +
      '<span class="acct__k mono">key ••••' + esc(d.tail) + "</span></div>" +
      (d.expires_at ? '<p class="acct__meta">Renews ' + esc(fdate(d.expires_at)) + "</p>"
                    : '<p class="acct__meta">Active subscription</p>') +
      '<div class="acct__cta">' +
      '<a class="btn btn--primary" href="https://polar.sh/tashan/portal" rel="noopener">Billing &amp; invoices &rsaquo;</a>' +
      '<button class="linkbtn" id="acctOut" type="button">Forget this key</button></div>' +
      '<p class="acct__hint">On this machine: <code>npx tashan-cli activate &lt;your key&gt;</code> ' +
      "— then every <code>doctor</code> run prints Pro · licence active.</p>";
    document.getElementById("acctOut").onclick = function () {
      try { localStorage.removeItem(LS); } catch (e) { /* private mode */ }
      signedOut("");
    };
  }

  function unknown() {
    // Could not reach the check. This is NOT "your licence is dead" and must never read as it.
    panel.className = "acct";
    panel.innerHTML = '<p class="acct__lead">Could not check your licence just now — that is us, ' +
      'not you. Your subscription is unaffected.</p>' +
      '<div class="acct__cta"><a class="btn btn--ghost" href="https://polar.sh/tashan/portal" ' +
      'rel="noopener">Open billing &rsaquo;</a></div>';
  }

  function check(key, remember) {
    busy();
    fetch("/api/status?key=" + encodeURIComponent(key))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.state === "active") {
          if (remember) { try { localStorage.setItem(LS, key); } catch (e) { /* private mode */ } }
          signedIn(d);
        } else if (d.state === "unknown") {
          unknown();
        } else {
          try { localStorage.removeItem(LS); } catch (e) { /* ignore */ }
          signedOut("That key was not accepted. Copy it again from your purchase email or billing.");
        }
      })
      .catch(unknown);
  }

  var saved = null;
  try { saved = localStorage.getItem(LS); } catch (e) { /* private mode */ }
  if (saved) check(saved, false); else signedOut("");
})();
