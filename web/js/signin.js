/* The sign-in form, defined once.
 *
 * WHY THIS EXISTS. Three pages need the same thing — /activate (approve a device), /welcome (the
 * screen after paying) and /account (someone who closed the tab and came back). Each had, or was
 * about to have, its own copy of one input, one POST and one set of error strings. This codebase has
 * been bitten twice this week by exactly that shape: a security offer rendered server-side and not
 * client-side so it was invisible, and a nav+footer that drifted into six variants across 18 copies.
 * A credential form is the last place to let three copies disagree about what "that key was not
 * accepted" means, or about whether a failed request clears the field.
 *
 * The whole surface is: build the markup, wire the submit, call back on success.
 *
 *   tashanSignin.html({ id: "wKey", label: "Licence key", cta: "Sign in ›" })
 *   tashanSignin.wire("wKey", function (account) { ... })
 */
(function () {
  "use strict";

  function html(o) {
    var id = o.id;
    return '<form class="actv__form" id="' + id + 'Form">' +
      '<label class="actv__lbl mono" for="' + id + 'In">' + (o.label || "Licence key") + "</label>" +
      '<input class="actv__in mono" id="' + id + 'In" name="key" type="password" autocomplete="off" ' +
      'spellcheck="false" placeholder="tashan_…" required' + (o.autofocus ? " autofocus" : "") + ">" +
      '<button class="btn btn--primary" type="submit">' + (o.cta || "Sign in &rsaquo;") + "</button>" +
      '<p class="actv__err" id="' + id + 'Err" hidden></p>' +
      "</form>";
  }

  function wire(id, onDone) {
    var f = document.getElementById(id + "Form");
    if (!f) return;
    var input = document.getElementById(id + "In");
    var err = document.getElementById(id + "Err");
    var btn = f.querySelector("button");
    var label = btn.innerHTML;

    function fail(msg) {
      btn.disabled = false;
      btn.innerHTML = label;
      err.textContent = msg;
      err.hidden = false;
      // Leave the value alone. Clearing it on failure means retyping a 40-character key because of
      // one stray space, which is the moment someone gives up and emails support instead.
      input.focus();
      input.select();
    }

    f.onsubmit = function (e) {
      e.preventDefault();
      err.hidden = true;
      btn.disabled = true;
      btn.textContent = "Checking…";
      fetch("/api/account", {
        method: "POST",
        headers: { "content-type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ key: input.value.trim() }),
      })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
        .then(function (r) {
          if (!r.ok || !r.body || !r.body.signed_in) {
            return fail((r.body && r.body.error) || "That key was not accepted.");
          }
          // The nav caches the session per tab; a stale signed-out cache would leave the header
          // saying "Sign in" on the very page that just signed you in.
          if (window.tashanSession) window.tashanSession.clear();
          if (window.t && window.t.track) window.t.track("signin", { from: id });
          btn.disabled = false;
          btn.innerHTML = label;
          onDone(r.body);
        })
        .catch(function () { fail("Could not reach tashan. Check your connection and try again."); });
    };
  }

  window.tashanSignin = { html: html, wire: wire };
})();
