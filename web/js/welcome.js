/* /welcome — the first screen after paying.
 *
 * AUTO SIGN-IN, WHEN POLAR SENDS US THE ID. This comment used to say the organisation token was
 * "deliberately absent" and that pasting a key was therefore the design. Both halves are now stale:
 * functions/api/checkout.js exists, POLAR_ORG_TOKEN is set on the Pages project, and the exchange
 * works. What was never done is the one-line change in Polar — the checkout links' success_url is
 * still a bare `https://tashan.sh/welcome.html`, with no id on it, so /api/checkout is never
 * reached and every customer is asked to paste a key. Two half-finished states coexisting, and the
 * finished one unreachable.
 *
 * Polar substitutes {CHECKOUT_ID} ONLY into a parameter you write yourself; it appends nothing on
 * its own. So this page now handles the id if it ever arrives here, and /api/checkout handles it if
 * Polar is pointed straight there. Either success_url works:
 *
 *     https://tashan.sh/api/checkout?id={CHECKOUT_ID}        <- preferred, no page renders first
 *     https://tashan.sh/welcome.html?checkout_id={CHECKOUT_ID}
 *
 * The paste form stays as the fallback, because a customer whose exchange fails — Polar down, id
 * already burned, JS off — must never be stranded on the screen they just paid to see.
 *
 * Two states, never guessed. An unreachable API renders SIGNED OUT — never an optimistic "you're in".
 */
(function () {
  "use strict";

  var host = document.getElementById("welcome");
  if (!host) return;

  // If Polar sent the checkout id here, hand it to the endpoint that can exchange it. Done before
  // anything renders, so the customer sees the signed-in page rather than a form they do not need.
  // ONE ATTEMPT, and never a loop: /api/checkout burns the id, so a retry can only ever fail, and a
  // page that keeps redirecting is worse than one that asks for a paste.
  try {
    var q = new URLSearchParams(location.search);
    var cid = q.get("checkout_id") || q.get("id");
    if (cid && !q.get("e")) {
      location.replace("/api/checkout?id=" + encodeURIComponent(cid));
      return;
    }
  } catch (e) { /* no URLSearchParams, or an opaque URL: fall through to the paste form */ }

  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };

  function signedIn(a) {
    var who = a.email || a.name || "your account";
    if (!a.active) {
      host.innerHTML = "<h1>Check your subscription</h1><p>Open your account to check your plan and licence.</p>" +
        '<a class="btn btn--primary" href="/account.html">Open account</a>';
      return;
    }
    host.innerHTML =
      '<p class="kicker">tashan Pro</p><h1>Connect your terminal</h1>' +
      '<p class="lede">Signed in as <b>' + esc(who) + '</b>. Run this command and approve the code in your browser.</p>' +
      '<div class="callout mono fs-sm">npx tashan-cli login</div>' +
      '<h2>Use fewer input tokens</h2><p>Put tashan wrap -- before one local MCP server’s command and reconnect. Pro now compacts JSON results from that tool.</p>' +
      '<div class="callout mono fs-sm">tashan daily</div>' +
      '<p><a class="link" href="/account.html">Manage subscription</a> &nbsp;·&nbsp; <a class="link" href="/support.html">Get help</a></p>';
  }

  // /api/checkout redirects here with ?e= when the exchange could not complete. Say which, plainly:
  // "it did not work" sends someone to support, "that link was already used" does not.
  var NOTE = {
    used: "This sign-in link was already used. Use the key from your purchase email.",
    unpaid: "Checkout is still open. Finish the payment in Polar, then return here.",
    pending: "Your licence is being prepared. Use the key when your purchase email arrives.",
    stale: "This sign-in link expired. Use the key from your purchase email.",
    unavailable: "Automatic sign-in is temporarily unavailable. Use the key from your purchase email.",
    unconfigured: "Automatic sign-in is unavailable. Use the key from your purchase email.",
  }[new URLSearchParams(location.search).get("e")] || "";

  function signedOut() {
    host.innerHTML =
      '<p class="kicker">Welcome to tashan Pro</p>' +
      "<h1>Sign in with your licence key</h1>" +
      '<p class="lede">Find the key in your purchase email and paste it below.</p>' +
      (NOTE ? '<div class="callout"><b>' + NOTE + "</b></div>" : "") +
      window.tashanSignin.html({ id: "wKey", autofocus: true }) +
      '<p class="note">In CI, where there is no browser to open, <code>npx tashan-cli activate &lt;key&gt;</code> ' +
      "does the same thing non-interactively.</p>";
    window.tashanSignin.wire("wKey", signedIn);
  }

  fetch("/api/account")
    .then(function (r) { return r.json(); })
    .then(function (a) { (a && a.signed_in) ? signedIn(a) : signedOut(); })
    .catch(function () { signedOut(); });
})();
