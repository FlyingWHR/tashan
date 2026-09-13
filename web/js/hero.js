// tashan — hero micro-animation: cycle the dimensions we measure. Self-hosted (strict CSP).
(function () {
  "use strict";
  var el = document.getElementById("rot");
  if (!el) return;
  // WHAT SOMEONE COULD TYPE, not what we measure. This used to cycle the measurement axes under the
  // headline — advisories, permissions, upkeep — which read as a second claim competing with the
  // one above it. It now sits inside the search control and cycles jobs, so the hint answers the
  // question the control asks. Every one of these resolves to a real task hub, so the suggestion is
  // never a phrase the search then fails on.
  var words = ["review code", "automate a browser", "analyse a spreadsheet",
               "query postgres", "scrape a website", "read my gmail"];
  var i = 0;
  var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) { el.firstChild.textContent = words[0]; return; }
  // A REEL, not a cross-fade. The old motion slid half a line and faded through, which reads as a
  // glitch at small sizes; this drives the word fully out of the clipped window (.rot is
  // overflow:hidden with a fixed height) and brings the next one up from below, so it reads as one
  // strip of text moving past a slot. No opacity: a reel does not fade, it travels, and fading is
  // what made the old one look like a rendering error rather than a mechanism.
  var OUT = "transform .34s cubic-bezier(.55,0,.6,.2)";    // leaves with acceleration
  var IN = "transform .46s cubic-bezier(.16,1,.3,1)";      // arrives and settles
  setInterval(function () {
    i = (i + 1) % words.length;
    var inner = el.firstChild;
    inner.style.transition = OUT;
    inner.style.transform = "translateY(-115%)";
    setTimeout(function () {
      inner.style.transition = "none";
      inner.textContent = words[i];
      inner.style.transform = "translateY(115%)";
      void inner.offsetWidth;                              // commit the jump before easing back
      inner.style.transition = IN;
      inner.style.transform = "translateY(0)";
    }, 340);
  }, 2600);
})();
