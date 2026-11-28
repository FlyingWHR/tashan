// One paired case per completed workflow. Include every charged request, even
// retries, in the attempt that incurred it. Costs are imported USD amounts.
export function compareCosts(input) {
  const { period, fee_usd, cases } = input || {};
  const money = n => Number.isFinite(n) && n >= 0;
  if (typeof period !== "string" || !period.trim() || !money(fee_usd) || !Array.isArray(cases) || !cases.length)
    throw new Error("Supply a period, fee_usd for that period, and paired cases.");
  const casesSeen = new Set(), receipts = new Set(), regressions = [];
  const totals = { baseline: { accepted: 0, usd: 0 }, tashan: { accepted: 0, usd: 0 } };
  const tokens = { baseline: 0, tashan: 0 };
  for (const entry of cases) {
    if (!entry || typeof entry.id !== "string" || !entry.id.trim() || casesSeen.has(entry.id))
      throw new Error("Each case needs a unique ID.");
    casesSeen.add(entry.id);
    for (const variant of Object.keys(totals)) {
      const run = entry[variant];
      if (typeof run?.accepted !== "boolean" || !Array.isArray(run.charges) || !run.charges.length)
        throw new Error(`Include the outcome and all billed requests for ${entry.id} (${variant}).`);
      for (const charge of run.charges) {
        if (!charge || typeof charge.id !== "string" || !charge.id.trim() || receipts.has(charge.id) || !money(charge.usd))
          throw new Error("Each charge needs a unique request ID and a nonnegative USD amount.");
        receipts.add(charge.id);
        totals[variant].usd += charge.usd;
        if (charge.total_tokens === undefined) {
          tokens[variant] = null;
        } else {
          if (!Number.isSafeInteger(charge.total_tokens) || charge.total_tokens < 0)
            throw new Error("Use a nonnegative integer for total_tokens.");
          if (tokens[variant] !== null) {
            tokens[variant] += charge.total_tokens;
            if (!Number.isSafeInteger(tokens[variant])) throw new Error("Token count exceeds the supported range.");
          }
        }
      }
      totals[variant].accepted += Number(run.accepted);
    }
    if (entry.baseline.accepted && !entry.tashan.accepted) regressions.push(entry.id);
  }
  const round = n => Number(n.toFixed(8));
  for (const [variant, row] of Object.entries(totals)) {
    row.total_tokens = tokens[variant];
    row.tokens_per_accepted = row.accepted && tokens[variant] !== null ? round(tokens[variant] / row.accepted) : null;
    row.usd_per_accepted = row.accepted ? round(row.usd / row.accepted) : null;
    row.usd = round(row.usd);
  }
  const difference = round(totals.baseline.usd - totals.tashan.usd - fee_usd);
  return { period, cases: cases.length, ...totals, fee_usd, regressions,
    tokens_saved: regressions.length || !totals.baseline.accepted || tokens.baseline === null || tokens.tashan === null
      ? null : tokens.baseline - tokens.tashan,
    spend_difference_after_fee_usd: difference,
    net_savings_usd: regressions.length || !totals.baseline.accepted ? null : difference };
}
