// Rebuild with: npx --yes esbuild@0.17.19 tools/token-preview-worker.mjs --bundle --minify --supported:template-literal=false --outfile=web/assets/token-preview-worker.js
// The tokenizer's licence is distributed in /assets/gpt-tokenizer-LICENSE.txt.
import { compareJson } from "../cli/tokens.mjs";

self.onmessage = ({ data }) => {
  try {
    const { report } = compareJson(data.input, data.table);
    self.postMessage(report);
  } catch {
    self.postMessage({ error: "Enter a valid JSON tool result." });
  }
};
