// Mastered — shared: mark the active nav link.
(function () {
  var path = location.pathname.replace(/index\.html$/, "") || "/";
  document.querySelectorAll(".nav__links a").forEach(function (a) {
    var href = a.getAttribute("href").replace(/index\.html$/, "") || "/";
    if (href === path) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
})();
