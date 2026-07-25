// Methodology — stamp the "updated" line from the live dataset.
fetch("/data/index.json").then(function (r) { return r.json(); }).then(function (d) {
  var u = document.getElementById("updated");
  if (u) u.textContent = "public-signal · v2 · " + (d.total_capabilities || "—") + " capabilities · " +
    new Date(d.generated_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}).catch(function () {});
