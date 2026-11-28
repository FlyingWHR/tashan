(() => {
  const form = document.getElementById("tokenPreview");
  if (!form) return;
  const input = form.querySelector("#tokenPayload");
  const table = form.querySelector("#tokenTable");
  const output = form.querySelector("output");
  const submit = form.querySelector('[type="submit"]');
  submit.disabled = false;
  let worker;
  let revision = 0;

  function clear() {
    revision++;
    if (worker) worker.terminate();
    worker = null;
    submit.disabled = false;
    output.textContent = "";
  }
  form.addEventListener("input", clear);
  form.addEventListener("submit", event => {
    event.preventDefault();
    clear();
    if (!input.value.trim()) {
      output.textContent = "Paste JSON or load the example first.";
      input.focus();
      return;
    }
    if (input.value.length > 250000) {
      output.textContent = "Use the CLI for results larger than 250,000 characters.";
      return;
    }
    submit.disabled = true;
    output.textContent = "Counting tokens on this device…";
    const current = revision;
    try {
      worker = new Worker("/assets/token-preview-worker.js");
      worker.onmessage = ({ data }) => {
        if (current !== revision) return;
        worker.terminate();
        worker = null;
        submit.disabled = false;
        output.textContent = data.error || (data.before.toLocaleString() + " → " + data.after.toLocaleString()
          + " input tokens · " + data.saved.toLocaleString() + " fewer");
      };
      worker.onerror = () => {
        if (current !== revision) return;
        clear();
        output.textContent = "Could not load the tokenizer. Try again or use the CLI below.";
      };
      worker.postMessage({ input: input.value, table: table.checked });
    } catch {
      clear();
      output.textContent = "Could not start the tokenizer. Use the CLI below.";
    }
  });
  form.querySelector('[type="button"]').addEventListener("click", async () => {
    clear();
    const current = revision;
    try {
      const response = await fetch("/assets/tool-results.json");
      if (!response.ok) throw new Error();
      const sample = await response.text();
      if (current !== revision) return;
      input.value = sample;
      table.checked = true;
      form.requestSubmit();
    } catch {
      if (current === revision) output.textContent = "Could not load the example. Paste your own JSON to try it.";
    }
  });
})();
