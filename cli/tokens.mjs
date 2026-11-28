// Count only the JSON payload that the caller intends to put in model context.
import { countTokens } from "gpt-tokenizer/encoding/o200k_base";

const plainText = { disallowedSpecial: new Set(), allowedSpecial: new Set() };

function asTable(value, compact) {
  if (!Array.isArray(value) || value.length < 2) return null;
  if (!value.every(row => row !== null && typeof row === "object" && !Array.isArray(row))) return null;
  const columns = Object.keys(value[0]);
  const layout = JSON.stringify(columns);
  if (!value.every(row => JSON.stringify(Object.keys(row)) === layout)) return null;
  // Round-tripping must preserve every original lexeme, including long integers,
  // duplicate keys, escapes and negative zero. Whitespace was removed lexically.
  if (JSON.stringify(value) !== compact) return null;
  return JSON.stringify({ columns, rows: value.map(row => columns.map(key => row[key])) });
}

export function compareJson(input, table = false) {
  const value = JSON.parse(input);
  const compact = input.replace(/"(?:\\[\s\S]|[^"\\])*"|[ \t\r\n]+/g,
    match => match.startsWith('"') ? match : "");
  const before = countTokens(input, plainText);
  let after = before, output = input, format = "original";
  function compare(candidate, name) {
    if (candidate === null || candidate === output) return;
    const tokens = countTokens(candidate, plainText);
    if (tokens < after) {
      after = tokens;
      output = candidate;
      format = name;
    }
  }
  compare(compact, "compact-json");
  if (table) compare(asTable(value, compact), "columns-and-rows");
  return { output, report: { encoding: "o200k_base", format, before, after, saved: before - after } };
}

// Hide only runs of positive test records. Keep unknown lines, failure detail and
// nearby test names verbatim. The file path and fold markers count toward the total.
export function compareCiLog(input, path) {
  const lines = input.match(/[^\n]*\n|[^\n]+$/g) || [];
  const passing = line => {
    const text = line.replace(/\x1b\[[0-9;]*m/g, "")
      .replace(/^(?:[^\t\n]+\t[^\t\n]+\t)?\d{4}-\d\d-\d\dT[\d:.]+Z /, "").trimStart();
    return /^(?:ok(?:\s{2,}|\s+\d+\s+-\s)|PASS\s+\S|test\s+.+\s+\.\.\. ok\s*$)/.test(text)
      && !/\b(?:TODO|SKIP|WARN(?:ING)?|ERROR|FAIL(?:ED|URE)?)\b|##\[error\]/.test(text);
  };
  const parts = [];
  let hidden = 0;
  for (let i = 0; i < lines.length;) {
    const start = i;
    while (i < lines.length && passing(lines[i])) i++;
    if (i - start >= 5) {
      const count = i - start - 2;
      hidden += count;
      parts.push(lines[start], `[lines ${start + 2}–${i - 1}: ${count} passing tests folded]\n`, lines[i - 1]);
    } else {
      for (let j = start; j < i; j++) parts.push(lines[j]);
    }
    if (i < lines.length) parts.push(lines[i++]);
  }
  const before = countTokens(input, plainText);
  const candidate = hidden ? `[Full log: ${JSON.stringify(path)}]\n` + parts.join("") : input;
  const after = hidden ? countTokens(candidate, plainText) : before;
  const useFold = after < before;
  return {
    output: useFold ? candidate : input,
    report: { encoding: "o200k_base", format: useFold ? "ci-log" : "original", before,
      after: useFold ? after : before, saved: useFold ? before - after : 0,
      folded_lines: useFold ? hidden : 0 },
  };
}
