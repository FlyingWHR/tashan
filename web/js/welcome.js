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
    // Not the buyer's fault and not their problem to solve — say so, and do not imply they did
    // something wrong. Their key is real and the paste form below works.
    unconfigured: "Automatic sign-in is not switched on for this site yet — that is on us, not you. " +
                  "Your key is in your purchase email; paste it once below and this browser stays signed in.",
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
