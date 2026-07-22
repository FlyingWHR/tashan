// Methodology — stamp the "updated" line from the live dataset.
fetch("/data/capabilities.json").then(function (r) { return r.json(); }).then(function (d) {
  var u = document.getElementById("updated");
  if (u) u.textContent = "public-signal · v1 · " + (d.sample_configs || "—") + " configs · " +
    new Date(d.generated_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}).catch(function () {});
