/* /account.html — the account centre.
 *
 * This page renders STATE, not instructions. Four earlier versions were prose: a heading, a
 * paragraph apologising that there is no members' area, an outbound button, and at one point a box
 * asking the reader to paste a licence key. Every one of them told you about an account instead of
 * showing you yours, which is the whole of what "makeshift" meant.
 *
 * Everything below comes from /api/account, which reads Polar's public customer-portal record.
 * Nothing here is invented, and nothing is faked while loading — an unknown field renders as an
 * em dash rather than a plausible zero, the same rule the score obeys.
 *
 * boot() runs LAST in this file, deliberately. A previous page in this codebase called its render
 * before a `const` further down had initialised, which threw on every load, blanked the whole
 * dossier and produced a reload loop. Declarations first, entry point at the bottom.
 */
(function () {
  "use strict";

  var el = document.getElementById("acct");
  if (!el) return;

  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };

  var date = function (iso) {
    if (!iso) return null;
    var d = new Date(iso);
    if (isNaN(d)) return null;
    return d.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
  };

  // A definition row. The value carries the emphasis because the value is what the reader came for.
  var row = function (label, value, extra) {
    return '<div class="acct__row"><dt class="acct__k">' + esc(label) + "</dt>" +
      '<dd class="acct__v">' + (value == null ? '<span class="muted">—</span>' : value) +
      (extra ? ' <span class="acct__x">' + extra + "</span>" : "") + "</dd></div>";
  };

  var machines = function (a) {
    if (a.machines_used == null) return null;
    if (a.machines_limit == null) return esc(a.machines_used) + " activated <span class=\"acct__x\">no limit</span>";
    return esc(a.machines_used) + " of " + esc(a.machines_limit);
  };

  // ---- signed in -------------------------------------------------------------------------------
  function renderIn(a) {
    var who = a.email || a.name || "Your account";
    var state = a.active
      ? '<span class="acct__badge acct__badge--on">Pro · active</span>'
      : '<span class="acct__badge">' + esc(a.status === "expired" ? "Expired" : a.status) + "</span>";

    var when = date(a.expires_at);
    var renews = a.active
      ? row("Renews", when || '<span class="muted">with your subscription</span>')
      : row("Ended", when);

    return '<section class="acct__card">' +
      '<header class="acct__id">' +
        '<span class="acct__av" aria-hidden="true"></span>' +
        '<div class="acct__idt"><p class="acct__em">' + esc(who) + "</p>" +
        '<p class="acct__st">' + state + "</p></div>" +
        '<button class="btn btn--ghost acct__out" id="acctOut" type="button">Sign out</button>' +
      "</header>" +
      '<dl class="acct__dl">' +
        row("Plan", a.active ? "tashan Pro" : "tashan Free") +
        renews +
        row("Machines", machines(a)) +
        row("Licence key", a.display_key
          ? '<span class="mono">' + esc(a.display_key) + "</span>"
          : null, "last four") +
      "</dl>" +
      '<div class="acct__acts">' +
        '<a class="btn btn--primary" href="' + esc(a.portal) + '" rel="noopener" target="_blank">Billing &amp; invoices ↗</a>' +
        // Cancelling must be findable and must not be dressed as a call to action. A quiet link,
        // not a second button competing with the one above it.
        '<a class="acct__quiet" href="/refunds.html">Cancel</a>' +
      "</div>" +
    "</section>" +
    (a.active ? '<p class="acct__note">Signed in on this browser, so capability pages show the full ' +
      "security detail. On another machine, <code>npx tashan-cli activate</code> with the same key.</p>"
      : "");
  }

  // ---- signed out ------------------------------------------------------------------------------
  function renderOut(a, err) {
    var notice = "";
    if (err === "expired") notice = '<p class="acct__err">That sign-in link had already been used or ran out. Run the command again.</p>';
    else if (err === "unavailable") notice = '<p class="acct__err">Sign-in is temporarily unavailable. Try again in a moment.</p>';
    else if (a && a.was === "invalid") notice = '<p class="acct__err">Your licence is no longer active, so we signed you out.</p>';

    return '<section class="acct__card acct__card--in">' +
      '<span class="acct__av acct__av--lg" aria-hidden="true"></span>' +
      "<h1>Sign in</h1>" +
      '<p class="acct__lede">Your plan, the machines you have activated, your licence key and your invoices.</p>' +
      notice +
      '<div class="acct__way">' +
        '<p class="acct__wayh">From your terminal</p>' +
        '<div class="install__cmd"><code>npx tashan-cli account</code>' +
          '<button class="install__copy" type="button" data-copy="npx tashan-cli account">Copy</button></div>' +
        '<p class="acct__wayd">Opens this page already signed in, using the licence this machine ' +
          "already holds. Nothing to type, nothing to paste.</p>" +
      "</div>" +
      '<p class="acct__or"><span>or</span></p>' +
      '<a class="btn btn--ghost acct__wide" href="' + esc((a && a.portal) || "https://polar.sh/tashan/portal") +
        '" rel="noopener" target="_blank">Sign in with your email ↗</a>' +
      '<p class="acct__wayd">Goes to the billing portal, where your invoices and licence key live.</p>' +
      '<p class="acct__foot">No subscription yet? <a class="link" href="/pricing.html">See what Pro adds ›</a>' +
        " The index, every score and every finding stay free.</p>" +
    "</section>";
  }

  function paint(html) {
    el.innerHTML = html;
    el.setAttribute("aria-busy", "false");
    var out = document.getElementById("acctOut");
    if (out) out.addEventListener("click", signOut);
  }

  function signOut() {
    fetch("/api/account", { method: "DELETE", credentials: "same-origin" })
      .catch(function () { /* the cookie may already be gone; the reload settles it either way */ })
      .then(function () { location.replace("/account.html"); });
  }

  function boot() {
    var err = new URLSearchParams(location.search).get("e");
    // Strip the redeem marker so a refresh does not re-show a stale notice, and so the address bar
    // is clean the moment the page settles.
    if (err) history.replaceState(null, "", "/account.html");

    fetch("/api/account", { credentials: "same-origin", headers: { accept: "application/json" } })
      .then(function (r) { return r.json(); })
      .then(function (a) {
        if (a && a.unavailable) {
          paint('<section class="acct__card acct__card--in"><h1>Account unavailable</h1>' +
            '<p class="acct__lede">We could not reach the billing service just now. Your subscription ' +
            "is unaffected — this page will work again shortly.</p></section>");
          return;
        }
        paint(a && a.signed_in ? renderIn(a) : renderOut(a, err));
      })
      .catch(function () {
        // Offline, or the site is running as static files with no /api. Show the way in rather than
        // an error: the sign-in card is useful with no backend at all.
        paint(renderOut(null, err));
      });
  }

  boot();
})();
