import type { FxRate } from "./dataset";
// Only actual dated rates from the selected dataset may restate imported values.
export function exchangeRate(from: string, to: string, rates: FxRate[] = []) {
  if (from === to) return 1;
  if (to !== "HKD") throw new Error("Portfolio reporting and optimization require HKD.");
  const rate = rates.find(item => item.pair === `${from}HKD` && Number.isFinite(item.rate) && item.rate > 0 && item.date);
  if (!rate) throw new Error(`No dated ${from}/HKD exchange rate is available in this dataset. Supply holdings already valued in HKD, or upload a snapshot containing that FX pair. Conversion is blocked.`);
  return rate.rate;
}
