// tashan — shared, on every page: active-nav marking + first-party analytics.
(function () {
  "use strict";

  // ---- active nav link ----
  var path = location.pathname.replace(/index\.html$/, "") || "/";
  document.querySelectorAll(".nav__links a").forEach(function (a) {
    var href = a.getAttribute("href").replace(/index\.html$/, "") || "/";
    if (href === path) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });


  // ---- session state in the nav, on every page ---------------------------------------------------
  // The site never showed whether you were signed in. A customer who had paid saw exactly the page a
  // stranger saw, on all ~5,900 of them, which is why Pro never felt like anything.
  //
  // THREE RULES, and the third is the one that matters:
  //   1. Start neutral. The shell ships signed-out; this only ever ADDS marks, so there is no flash
  //      of a wrong state on a static page.
  //   2. Cache per tab, briefly. Every page is a full document load, and one /api/account round trip
  //      per navigation would put a Polar call in the critical path of browsing the Index.
  //   3. NEVER be optimistic. An unreachable API, a 503, a malformed body — all render signed out. A
  //      false Pro mark tells someone their licence is fine when it may have lapsed, and it is the
  //      one lie a status indicator must never tell.
  var SKEY = "tashan_acct";
  var TTL = 60 * 1000;

  function paint(a) {
    var link = document.getElementById("navAcct");
    if (!link) return;
    var pro = document.getElementById("navPro");
    if (!a || !a.signed_in) {
      link.title = "Sign in";
      link.setAttribute("aria-label", "Sign in");
      return;                                   // signed out is the shipped state; nothing to add
    }
    link.classList.add("is-in");
    var who = a.email || a.name;
    // An expired or revoked licence is its own state, not a quieter version of "signed in". Saying
    // "Your account" over a lapsed subscription is how someone discovers it lapsed by having a
    // command fail instead of by reading their own header.
    var what = a.active ? "tashan Pro"
      : (a.status && a.status !== "granted" ? "tashan — licence " + a.status : "Your account");
    link.title = what + (who ? " — " + who : "");
    link.setAttribute("aria-label", link.title);
    if (a.active && pro) {
      link.classList.add("is-pro");
      pro.hidden = false;
    }
    if (a.active) proPaid();
  }

  // Never sell a trial to someone already paying. capability.js swaps the dossier panel because it
  // has the row's own series to put there; every OTHER surface carrying a .pro panel had no swap at
  // all, so an active subscriber read "Start a 7-day trial" on the homepage. This is the floor, not
  // a second implementation of the dossier panel: the offer becomes a way back to their account.
  function proPaid() {
    var panels = document.querySelectorAll('.pro[data-state="free"]');
    for (var i = 0; i < panels.length; i++) {
      var cta = panels[i].querySelector(".pro__cta");
      if (!cta) continue;
      panels[i].setAttribute("data-state", "pro");
      cta.innerHTML = '<a class="btn btn--primary" href="/account.html" data-e="cta" ' +
        'data-k="pro-account">Your account &rsaquo;</a>' +
        '<span class="pro__free mono"> Pro is active on this browser.</span>';
    }
  }

  function session() {
    var cached = null;
    try {
      var raw = sessionStorage.getItem(SKEY);
      if (raw) {
        var c = JSON.parse(raw);
        if (c && Date.now() - c.at < TTL) cached = c.a;
      }
    } catch (e) { /* private mode, or a value we no longer understand — just refetch */ }
    if (cached) return paint(cached);
    fetch("/api/account", { headers: { accept: "application/json" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (a) {
        if (!a) return;                          // 503 / error: stay signed out, never guess
        try { sessionStorage.setItem(SKEY, JSON.stringify({ at: Date.now(), a: a })); } catch (e) {}
        paint(a);
      })
      .catch(function () { /* offline: the shipped signed-out shell is already correct */ });
  }

  // Exposed so sign-out can drop the cache immediately rather than leaving a Pro mark on screen for
  // up to a minute after the session ended.
  window.tashanSession = { clear: function () { try { sessionStorage.removeItem(SKEY); } catch (e) {} } };
  session();

  // ---- analytics: first-party, cookieless, CSP-clean (same-origin beacon to /api/e) ----
  // No cookies, no localStorage, no fingerprint, no third-party script. Honors Do-Not-Track /
  // Global-Privacy-Control. Session id is a random in-memory value (this tab only) purely to stitch a
  // funnel within one visit; it is never persisted, so nobody is tracked across sessions. Silent-fail:
  // if the collector isn't deployed (local dev), beacons no-op and never touch the page.
  var DNT = navigator.doNotTrack === "1" || window.doNotTrack === "1" || navigator.globalPrivacyControl === true;
  var sid = Math.random().toString(36).slice(2, 10);
  var host = location.hostname;

  function send(ev, props) {
    if (DNT) return;
    var body = {
      e: ev,
      p: path,                                   // page path (no query, no hash — no PII)
      r: document.referrer ? hostOf(document.referrer) : "",   // referrer HOST only
      s: sid,
      w: window.innerWidth < 700 ? "sm" : window.innerWidth < 1100 ? "md" : "lg"  // coarse viewport bucket
    };
    if (props) for (var k in props) if (props[k] != null) body[k] = props[k];
    try {
      var payload = JSON.stringify(body);
      if (navigator.sendBeacon) { navigator.sendBeacon("/api/e", payload); return; }
      fetch("/api/e", { method: "POST", body: payload, keepalive: true, headers: { "Content-Type": "application/json" } }).catch(function () {});
    } catch (e) { /* analytics must never break the page */ }
  }
  function hostOf(u) { try { return new URL(u).hostname; } catch (e) { return ""; } }

  // ONE BEACON, ONE DNT CHECK. A page script that needs to record something calls this rather than
  // POSTing /api/e itself — a second copy of the beacon is a second copy of the Do-Not-Track
  // decision, and the one that gets forgotten is the one that leaks. /audit uses it to record that
  // an audit actually RAN, which is the funnel step between arriving and being offered anything.
  window.tashanEvent = function (name, props) {
    if (!name) return;
    send(String(name).slice(0, 32), props || null);
  };

  // public hook so other scripts (⌘K search, etc.) can record events
  window.t = { track: send };

  // page view
  send("pageview");

  // one delegated listener captures the PLG-relevant interactions without per-page wiring
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a[href]");
    var btn = e.target.closest && e.target.closest("[data-copy], .install__copy, .embed__copy");
    if (btn) {
      var what = btn.className.indexOf("embed") >= 0 ? "badge"
               : btn.className.indexOf("install") >= 0 ? "install"
               : (btn.getAttribute("data-copy-label") || "copy");
      send("copy", { k: what });
      return;
    }
    if (!a) return;
    var href = a.getAttribute("href") || "";
    // DECLARED EVENTS FIRST. Every commercial CTA on the site carries data-e/data-k — the panel on
    // 9,638 dossiers, the block on 173 hubs, the one on 413 comparisons — and nothing read them.
    // A click on /pricing.html is internal, is not a capability link and is not a mailto, so it
    // fell through all three branches below and recorded NOTHING. The entire commercial surface was
    // unmeasurable: no way to tell which page, or which of the three CTA shapes, sends anyone to
    // the pricing page at all.
    //
    // The comment below still said "every paid-intent CTA is a mailto, because there is no checkout
    // yet". There is a checkout. The Polar link is https and does get caught as `outbound`, so the
    // LAST step of the funnel was measured while the step that feeds it was not.
    var decl = a.closest("[data-e]");
    if (decl) {
      send(decl.getAttribute("data-e") || "cta", {
        k: decl.getAttribute("data-k") || "",
        v: location.pathname
      });
    }
    if (/^https?:\/\//.test(href)) {
      var h = hostOf(href);
      if (h && h !== host) send("outbound", { k: h, v: a.getAttribute("data-src") || "" });   // registry / repo / community
    } else if (href.indexOf("mailto:") === 0) {
      // Contact intent — the teams enquiry and "embedding tashan in your product". It stopped being
      // the only conversion event when Polar went live; the CTA branch above now records the step
      // before the checkout, and the checkout itself lands in `outbound`.
      // Every paid-intent CTA used to be a mailto — the Pro waitlist
      // and the "embedding tashan in your product" contact — because there is no checkout yet. The
      // outbound branch above only matches ^https?://, so all of it recorded nothing, and the pricing
      // page's entire job (find out which part people would pay for) was unmeasurable. The subject
      // line distinguishes waitlist from teams from product enquiry, so key on that, not the address.
      var subj = (href.split("subject=")[1] || "").split("&")[0];
      send("intent", { k: decodeURIComponent(subj) || "email", v: location.pathname });
    } else if (href.indexOf("/capability/") === 0) {
      send("conav", { k: href.slice(12).replace(/\.html$/, "") });                              // graph traversal (co-use / board)
    }
  }, true);
})();

// ---- pricing: the monthly/annual toggle -------------------------------------------------------
// Present only when pipeline/prerender.py::bake_pricing() found a real annual price in
// data/entitlements.json. THE ANNUAL BUTTON ONCE CHARGED MONTHLY — two cadences pointed at one
// Polar checkout, so the buyer was billed $6/month and the funnel logged an annual conversion. This
// reads both URLs off the CTA rather than holding its own copy, so there is no second place for a
// link to be wrong, and it refuses to switch if the two URLs are identical.
(function () {
  "use strict";
  var wrap = document.querySelector(".ptoggle");
  var cta = document.getElementById("proCta");
  if (!wrap || !cta) return;
  var url = { month: cta.getAttribute("data-monthly-url"), year: cta.getAttribute("data-annual-url") };
  var label = { month: cta.getAttribute("data-monthly-label"), year: cta.getAttribute("data-annual-label") };
  if (!url.month || !url.year || url.month === url.year) return;   // never offer a cadence that bills another

  wrap.addEventListener("click", function (e) {
    var b = e.target.closest(".ptoggle__b");
    if (!b) return;
    var cad = b.getAttribute("data-cad");
    if (!url[cad]) return;
    wrap.querySelectorAll(".ptoggle__b").forEach(function (x) {
      var on = x === b;
      x.classList.toggle("is-on", on);
      x.setAttribute("aria-pressed", on ? "true" : "false");
    });
    cta.setAttribute("href", url[cad]);
    cta.textContent = label[cad] + " ›";
    // The headline price moves with the button. Leaving it behind showed "$6 /mo" above a "$50
    // annually" CTA — two prices for one plan, on the page whose whole job is that the number you
    // see is the number you are charged.
    var pr = document.getElementById("proPrice");
    var amt = cta.getAttribute("data-" + (cad === "year" ? "annual" : "monthly") + "-price");
    var per = cta.getAttribute("data-" + (cad === "year" ? "annual" : "monthly") + "-cad");
    if (pr && amt && per) { pr.textContent = amt; pr.insertAdjacentHTML("beforeend", "<small>" + per + "</small>"); }
    // The trial line carries a price too ("7 days free, then $6/mo"), so it moves as well or it
    // contradicts the button directly above it.
    var tm = document.getElementById("proTerms");
    var tt = cta.getAttribute("data-" + (cad === "year" ? "annual" : "monthly") + "-terms");
    if (tm && tt) tm.innerHTML = tt;
    // the analytics tag has to move with the cadence, or every annual sale is recorded as monthly —
    // which is exactly how the charging bug stayed invisible
    cta.setAttribute("data-src", "pricing-pro-" + (cad === "year" ? "annual" : "monthly"));
  });
})();
