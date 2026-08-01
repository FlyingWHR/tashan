/* /welcome — the first screen after paying.
 *
 * WHY THIS IS NOT AUTO-SIGN-IN. Polar's success_url does carry `?checkout_id={CHECKOUT_ID}`, so we
 * know WHICH checkout just completed. Turning that into a licence key requires
 * customer-portal/license-keys/list, which requires a customer session, which is created by a
 * server-side endpoint that requires the ORGANISATION access token. That token can read every
 * customer's record. Holding it in an edge function, on a path keyed only by an id that travels in
 * URLs, browser history and Referer headers, is a materially larger trust surface than this product
 * has ever asked for — wrangler.toml says plainly that the org token is deliberately absent.
 *
 * So: one paste, once, in a browser, where paste is one keystroke and a password manager often does
 * it unprompted. Every machine after this one is a click, because /activate approves device codes
 * against this session. The customer types their key at most once in their life either way; this
 * decides only whether that once happens here or on the first machine.
 *
 * If the org token is ever added, this page becomes a redirect and nothing else changes.
 *
 * Two states, never guessed. An unreachable API renders SIGNED OUT — never an optimistic "you're in".
 */
(function () {
  "use strict";

  var host = document.getElementById("welcome");
  if (!host) return;

  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };

  function signedIn(a) {
    var who = a.email || a.name || "your account";
    host.innerHTML =
      '<p class="kicker">Welcome to tashan Pro</p>' +
      "<h1>You're in.</h1>" +
      '<p class="lede">Signed in as <b>' + esc(who) + "</b>. One command puts Pro on any machine you " +
      "work on — there is no key to copy and nothing to add to your shell profile.</p>" +

      '<div class="callout mono fs-sm">npx tashan-cli login</div>' +
      "<p>It prints a short code and opens your browser. Because this browser is signed in, approving " +
      "is one click — the same flow as <code>gh auth login</code>. Repeat it on every machine.</p>" +

      "<h2>Then</h2>" +
      '<div class="callout mono fs-sm">npx tashan-cli doctor</div>' +
      "<p>Reads your Claude Code, Cursor and Desktop configs and tells you what to do about what it " +
      "finds. Nothing about your config is uploaded — the CLI reads local files and asks us only " +
      "about capability names. That was true before you paid and it is true now.</p>" +

      "<h2>What the licence changed</h2>" +
      "<p>Free <code>doctor</code> named every finding: how many advisories, whether something runs a " +
      "script at install, what it can reach. It still does, for everyone, permanently. With the " +
      "licence it also gives you <b>the part you act on</b> — which advisory and the version that " +
      "fixes it, what the install script runs, the full permission list, and the replacement to move " +
      "to.</p>" +

      '<p class="mt-12"><a class="btn btn--primary" href="/account.html">Your account &rsaquo;</a>' +
      '<a class="btn btn--ghost ml-3" href="/support.html">Get help &rsaquo;</a></p>';
  }

  // /api/checkout redirects here with ?e= when the exchange could not complete. Say which, plainly:
  // "it did not work" sends someone to support, "that link was already used" does not.
  var NOTE = {
    used:   "That sign-in link had already been used. Your key is in your purchase email — paste it once below.",
    unpaid: "That checkout has not completed. If you have just paid, give it a moment and reload.",
    stale:  "That sign-in link has expired. Paste your key once below and this browser stays signed in.",
  }[new URLSearchParams(location.search).get("e")] || "";

  function signedOut() {
    host.innerHTML =
      '<p class="kicker">Welcome to tashan Pro</p>' +
      "<h1>One paste, once.</h1>" +
      '<p class="lede">Your licence key is in the email that just arrived. Paste it here and this ' +
      "browser stays signed in — after that, every machine you ever work on is approved with a " +
      "click, and you never type it again.</p>" +
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
