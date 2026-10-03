import { displayTicker, metrics, totalValue } from "./portfolio";
import type { Portfolio } from "./portfolio";

export type ExportFormat = "csv" | "json";
export type ExportKind = "recommended" | "comparison";
export type InvestmentPreferences = { riskLevel: number; greenPreference: number; maxInvestment: number };

function portfolioSnapshot(portfolio: Portfolio) {
  const total = totalValue(portfolio);
  const analysis = metrics(portfolio);
  return {
    reportingCurrency: portfolio.baseCurrency,
    valuationDate: portfolio.asOf,
    totalValue: total,
    expectedReturn: analysis.expectedReturn.value,
    greenScore: analysis.greenScore.value,
    holdings: portfolio.holdings.map(h => ({
      ticker: displayTicker(h.ticker), company: h.name, exchange: h.exchange,
      assetClass: h.assetClass, currency: h.currency, currentValue: h.value,
      weight: total > 0 ? h.value / total : 0, expectedReturn: h.expectedReturn, eScore: h.eScore,
    })),
  };
}

function csvCell(value: string | number | null) {
  if (value === null) return "";
  let text = String(value);
  if (typeof value === "string" && /^[=+\-@\t\r]/.test(text)) text = "'" + text;
  return /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
}

function csv(rows: (string | number | null)[][]) {
  return "\uFEFF" + rows.map(row => row.map(csvCell).join(",")).join("\r\n");
}

export function createPortfolioExport(kind: ExportKind, format: ExportFormat, baseline: Portfolio, recommended: Portfolio, preferences: InvestmentPreferences) {
  const oldPortfolio = portfolioSnapshot(baseline), newPortfolio = portfolioSnapshot(recommended);
  const holdings = [...new Set([...baseline.holdings, ...recommended.holdings].map(h => h.id))].map(id => {
    const old = baseline.holdings.find(h => h.id === id), next = recommended.holdings.find(h => h.id === id);
    const holding = next ?? old!;
    return {
      ticker: displayTicker(holding.ticker), company: holding.name, exchange: holding.exchange,
      oldValue: old?.value ?? 0, newValue: next?.value ?? 0,
      valueChange: (next?.value ?? 0) - (old?.value ?? 0),
      oldWeight: old ? old.value / oldPortfolio.totalValue : 0,
      newWeight: next ? next.value / newPortfolio.totalValue : 0,
    };
  });
  const metricRows: (string | number | null)[][] = [
    ["Portfolio value", oldPortfolio.totalValue, newPortfolio.totalValue, newPortfolio.totalValue - oldPortfolio.totalValue],
    ["Expected return (fraction, annual)", oldPortfolio.expectedReturn, newPortfolio.expectedReturn, oldPortfolio.expectedReturn === null || newPortfolio.expectedReturn === null ? null : newPortfolio.expectedReturn - oldPortfolio.expectedReturn],
    ["Portfolio green score", oldPortfolio.greenScore, newPortfolio.greenScore, oldPortfolio.greenScore === null || newPortfolio.greenScore === null ? null : newPortfolio.greenScore - oldPortfolio.greenScore],
    ["E-score coverage (fraction)", metrics(baseline).greenScore.coverage, metrics(recommended).greenScore.coverage, metrics(recommended).greenScore.coverage - metrics(baseline).greenScore.coverage],
  ];
  const comparison = { metrics: metricRows.map(([metric, oldValue, newValue, change]) => ({ metric, oldValue, newValue, change })), holdings };
  const rows: (string | number | null)[][] = [
    ["Green Street", kind === "recommended" ? "Recommended portfolio" : "Portfolio comparison"],
    ["Reporting currency", baseline.baseCurrency],
    ["Valuation date", baseline.asOf],
    ["Risk level", preferences.riskLevel],
    ["Green preference", preferences.greenPreference],
    ["Maximum investment", preferences.maxInvestment],
    [],
  ];
  if (kind === "recommended") {
    rows.push(
      ["Total portfolio value", newPortfolio.totalValue],
      ["Annual expected return (fraction)", newPortfolio.expectedReturn],
      ["Portfolio green score", newPortfolio.greenScore],
      [],
      ["Ticker", "Company", "Exchange", "Asset class", "Currency", "Current value", "Weight (fraction)", "Annual expected return (fraction)", "E-score"],
      ...newPortfolio.holdings.map(h => [h.ticker, h.company, h.exchange, h.assetClass, h.currency, h.currentValue, h.weight, h.expectedReturn, h.eScore]),
    );
  } else {
    rows.push(
      ["Metric", "Old portfolio", "New portfolio", "Change"], ...metricRows, [],
      ["Ticker", "Company", "Exchange", "Old value", "New value", "Value change", "Old weight (fraction)", "New weight (fraction)"],
      ...holdings.map(h => [h.ticker, h.company, h.exchange, h.oldValue, h.newValue, h.valueChange, h.oldWeight, h.newWeight]),
    );
  }
  const payload = kind === "recommended"
    ? { preferences, recommendedPortfolio: newPortfolio }
    : { preferences, oldPortfolio, newPortfolio, comparison };
  return {
    name: `green-street-${kind === "recommended" ? "recommended-portfolio" : "portfolio-comparison"}.${format}`,
    content: format === "json" ? JSON.stringify(payload, null, 2) : csv(rows),
    mimeType: format === "json" ? "application/json" : "text/csv;charset=utf-8",
  };
}
