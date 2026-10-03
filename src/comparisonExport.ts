// CSV exports of the two comparison tables. Raw numbers (weights and returns as fractions),
// not the formatted strings on screen, so the files can be worked with in a spreadsheet.
import type { Recommendation } from "./api";
import { comparisonPositions, performanceRows } from "./Comparison";
import { tradeAction } from "./live";
import type { Universe } from "./live";
import type { Portfolio } from "./portfolio";

type Cell = string | number | null | undefined;
const quote = (v: Cell) => (v == null ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
// The BOM makes Excel read the file as UTF-8 (labels contain "·" and "–").
const csv = (header: string[], rows: Cell[][]) => "﻿" + [header, ...rows].map(r => r.map(quote).join(",")).join("\r\n") + "\r\n";
// Drops floating-point noise (28000.000000000004) without changing any figure that is shown.
const round = (x: number | null | undefined, digits = 6) => (x == null ? null : Number(x.toFixed(digits)));
const diff = (a: number | null, b: number | null) => (a === null || b === null ? null : round(b - a));

export function performanceCsv(baseline: Portfolio, result: Portfolio, rec: Recommendation) {
  let section = "";
  return csv(["section", "metric", "old_portfolio", "new_portfolio", "change"],
    performanceRows(baseline, result, rec.before, rec.after, rec.target_capital).map(r => {
      section = r.section ?? section;
      return [section, r.label, round(r.before), round(r.after), diff(r.before, r.after)];
    }));
}

export function positionsCsv(rec: Recommendation, universe: Universe, currency: string) {
  return csv(["ticker", "company", "sector", `unit_price_${currency}`, "old_units", "new_units", "units_change",
    `old_total_${currency}`, `new_total_${currency}`, "e_score", "old_weight", "new_weight", "action"],
    comparisonPositions(rec).map(t => {
      const c = universe.get(t.firm_id);
      return [t.firm_id, c?.name ?? t.firm_id, c?.sector, round(t.price, 3), t.shares_current, t.shares_target, t.shares_delta,
        round(t.capital_current, 2), round(t.capital_target, 2), c?.score, round(t.capital_current / rec.total_capital), round(t.w_target),
        tradeAction(t.side, t.w_current, t.w_target).label];
    }));
}

/** The "Recommended positions" panel: what to hold after the trades, largest first. */
export function recommendedPositionsCsv(rec: Recommendation, universe: Universe, currency: string) {
  return csv(["ticker", "company", "sector", `unit_price_${currency}`, "action", "shares", "shares_change", `total_${currency}`, "weight", "e_score"],
    [...comparisonPositions(rec)].sort((a, b) => b.w_target - a.w_target).map(t => {
      const c = universe.get(t.firm_id);
      return [t.firm_id, c?.name ?? t.firm_id, c?.sector, round(t.price, 3), tradeAction(t.side, t.w_current, t.w_target).label,
        t.shares_target, t.shares_delta, round(t.capital_target, 2), round(t.w_target), c?.score];
    }));
}
