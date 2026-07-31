// Methodology — stamp the "updated" line from the live dataset.
fetch("/data/index.json").then(function (r) { return r.json(); }).then(function (d) {
  var u = document.getElementById("updated");
  if (u) u.textContent = (d.total_capabilities || "—") + " capabilities · measured " +
    new Date(d.generated_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}).catch(function () {});
