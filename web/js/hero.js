// tashan — hero micro-animation: cycle the dimensions we measure. Self-hosted (strict CSP).
(function () {
  "use strict";
  var el = document.getElementById("rot");
  if (!el) return;
  var words = ["adoption", "maintenance", "freshness", "expertise", "retention"];
  var i = 0;
  var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) { el.firstChild.textContent = "everything that matters"; return; }
  setInterval(function () {
    i = (i + 1) % words.length;
    var inner = el.firstChild;
    inner.style.transform = "translateY(-0.5em)";
    inner.style.opacity = "0";
    setTimeout(function () {
      inner.textContent = words[i];
      inner.style.transform = "translateY(0.5em)";
      // reflow, then settle
      void inner.offsetWidth;
      inner.style.transition = "transform .32s cubic-bezier(.2,.7,.2,1), opacity .32s ease";
      inner.style.transform = "translateY(0)";
      inner.style.opacity = "1";
    }, 260);
  }, 2100);
})();
