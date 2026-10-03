import sample from "../docs/api-examples/current-portfolio.json";
import ideas from "../docs/api-examples/stock-recommendations.json";

export type Holding = {
  id: string;
  ticker: string;
  name: string;
  exchange: string;
  assetClass: string;
  currency: string;
  value: number;
  expectedReturn: number | null;
  eScore: number | null;
  color: string;
};
export type Portfolio = {
  name: string;
  baseCurrency: string;
  asOf: string;
  isDemo: boolean;
  holdings: Holding[];
};
export type Candidate = Omit<Holding, "value"> & { demoPrice: number; reason: string };
export type ParsedImport = { holdings: Holding[]; asOf: string; sourceCurrency: string | null };
const colors = ["#5487bb", "#65a593", "#8d9dca", "#bb8f45", "#8b99a6"];

export function samplePortfolio(): Portfolio {
  return {
    name: "Sample portfolio",
    baseCurrency: "HKD",
    asOf: sample.asOf,
    isDemo: true,
    holdings: sample.data.holdings.map((h, i) => ({
      id: h.id, ticker: h.stockCode, name: h.name, exchange: h.exchange,
      assetClass: "Equity", currency: "HKD", value: h.holdingValueBase,
      expectedReturn: h.expectedReturn.value, eScore: h.eScore.value, color: colors[i % colors.length],
    })),
  };
}

export const candidates: Candidate[] = ideas.data.recommendations.map((h, i) => ({
  id: h.id, ticker: h.stockCode, name: h.name, exchange: h.exchange,
  assetClass: "Equity", currency: "HKD", expectedReturn: h.expectedReturn.value,
  eScore: h.eScore.value, color: colors[i], demoPrice: i === 0 ? 120 : 100,
  reason: "Its illustrative E-score is above the sample portfolio average. Final ranking and risk matching require the backend.",
}));

export function totalValue(p: Portfolio) {
  return p.holdings.reduce((sum, h) => sum + h.value, 0);
}

export function metrics(p: Portfolio) {
  const total = totalValue(p);
  const aggregate = (key: "expectedReturn" | "eScore") => {
    const covered = p.holdings.filter(h => h[key] !== null);
    const coveredValue = covered.reduce((sum, h) => sum + h.value, 0);
    return {
      value: total > 0 && coveredValue === total
        ? covered.reduce((sum, h) => sum + h.value * h[key]!, 0) / total : null,
      coverage: total > 0 ? coveredValue / total : 0,
    };
  };
  return { expectedReturn: aggregate("expectedReturn"), greenScore: aggregate("eScore") };
}

export function money(value: number, currency: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(value);
}
export function percent(value: number | null, digits = 2) {
  return value === null ? "Unavailable" : `${(value * 100).toFixed(digits)}%`;
}
export function score(value: number | null) {
  return value === null ? "Unavailable" : value.toFixed(2);
}

// Parse quoted broker exports, including commas/newlines inside a quoted cell.
export function parseCSV(text: string): string[][] {
  const cleaned = text.replace(/^\uFEFF/, "");
  const delimiter = cleaned.split(/\r?\n/, 1)[0].includes(";") ? ";" : ",";
  const rows: string[][] = [];
  let row: string[] = [], cell = "", quoted = false;
  for (let i = 0; i < cleaned.length; i++) {
    const c = cleaned[i];
    if (c === '"') {
      if (quoted && cleaned[i + 1] === '"') { cell += '"'; i++; }
      else if (quoted || cell.trim() === "") quoted = !quoted;
      else throw new Error("Unexpected quote in CSV. Quote fields containing commas.");
    } else if (c === delimiter && !quoted) { row.push(cell.trim()); cell = ""; }
    else if ((c === "\n" || c === "\r") && !quoted) {
      if (c === "\r" && cleaned[i + 1] === "\n") i++;
      row.push(cell.trim()); if (row.some(Boolean)) rows.push(row); row = []; cell = "";
    } else cell += c;
  }
  if (quoted) throw new Error("Unclosed quoted field in CSV.");
  row.push(cell.trim()); if (row.some(Boolean)) rows.push(row);
  return rows;
}

export function parsePortfolioImport(text: string): ParsedImport {
  const rows = parseCSV(text);
  if (rows.length < 2) throw new Error("The CSV needs a header and at least one holding.");
  const headers = rows[0].map(h => h.toLowerCase().replace(/[\s_-]/g, ""));
  const find = (...names: string[]) => headers.findIndex(h => names.includes(h));
  const ticker = find("ticker", "stockcode", "symbol");
  const name = find("name", "companyname");
  const assetClass = find("assetclass", "assettype");
  const exchange = find("exchange", "market");
  const currency = find("currency");
  const date = find("asofdate", "valuationdate");
  const value = headers.findIndex(h => /^(totalmarketvalue|currentholdingvalue|marketholdingvalue|marketvalue|currentvalue)(\([a-z]{3}\))?$/.test(h));
  if (ticker < 0 || value < 0) throw new Error("Required columns: ticker (or stock_code), current_holding_value (or Total Market Value), and currency.");
  const sourceCurrency = rows[0][value].match(/\(([A-Za-z]{3})\)/)?.[1].toUpperCase() ?? null;
  if (!sourceCurrency && currency < 0) throw new Error("Add a currency column, or a currency in the market-value header, such as Total Market Value (SEK).");
  const dates = new Set<string>();
  const holdings = rows.slice(1).map((r, i): Holding => {
    if (r.length !== rows[0].length) throw new Error(`Row ${i + 2}: column count does not match the header. Quote names containing commas.`);
    const amount = Number(r[value].replace(/,/g, ""));
    const kind = assetClass >= 0 ? r[assetClass] : "Equity";
    const symbol = r[ticker];
    if ((!symbol || symbol === "-") && kind.toLowerCase() !== "cash") throw new Error(`Row ${i + 2}: missing stock code.`);
    if (!r[value] || !Number.isFinite(amount) || amount <= 0) throw new Error(`Row ${i + 2}: current holding value must be positive. Cost basis and allocation percentages are not market values.`);
    const ccy = sourceCurrency ?? r[currency].toUpperCase();
    if (!/^[A-Z]{3}$/.test(ccy)) throw new Error(`Row ${i + 2}: use a three-letter currency code.`);
    try { new Intl.NumberFormat("en", { style: "currency", currency: ccy }); } catch { throw new Error(`Row ${i + 2}: invalid currency.`); }
    if (date >= 0 && r[date]) {
      const d = r[date];
      if (!/^\d{4}-\d{2}-\d{2}$/.test(d) || !Number.isFinite(Date.parse(d)) || new Date(d).toISOString().slice(0, 10) !== d) throw new Error(`Row ${i + 2}: invalid valuation date.`);
      dates.add(d);
    }
    return { id: `import-${i}`, ticker: symbol === "-" ? "CASH" : symbol,
      name: name >= 0 && r[name] ? r[name] : symbol, exchange: exchange >= 0 ? r[exchange] : "Unresolved",
      assetClass: kind, currency: ccy, value: amount, expectedReturn: null, eScore: null, color: colors[i % colors.length] };
  });
  if (dates.size > 1) throw new Error("Use a common valuation date for all holdings.");
  return { holdings, asOf: [...dates][0] ?? "Not supplied", sourceCurrency };
}

export function normalizeImport(parsed: ParsedImport, baseCurrency: string, rates: Record<string, string>, fileName: string): Portfolio {
  const holdings = parsed.holdings.map(h => {
    const rate = h.currency === baseCurrency ? 1 : Number(rates[h.currency]);
    if (!Number.isFinite(rate) || rate <= 0) throw new Error(`Enter a positive ${h.currency} → ${baseCurrency} conversion rate.`);
    const converted = Math.round(h.value * rate * 100) / 100;
    if (!Number.isFinite(converted) || converted <= 0) throw new Error("Converted holding values must be positive and finite.");
    return { ...h, currency: baseCurrency, value: converted };
  });
  const p = { name: fileName, baseCurrency, asOf: parsed.asOf, isDemo: false, holdings };
  if (!Number.isFinite(totalValue(p))) throw new Error("Portfolio value exceeds the supported numeric range.");
  return p;
}

export function simulate(p: Portfolio, stock: Candidate, amount: number, funding: "new_money" | "rebalance", sales: Record<string, string>, additional: number): Portfolio {
  if (!Number.isFinite(amount) || amount <= 0) throw new Error("Enter a positive investment amount.");
  if (!Number.isFinite(additional) || additional < 0) throw new Error("Additional money must be zero or positive.");
  let released = 0;
  const holdings = p.holdings.map(h => {
    const sold = funding === "rebalance" ? Number(sales[h.id] || 0) : 0;
    if (!Number.isFinite(sold) || sold < 0 || sold > h.value) throw new Error(`The sale amount for ${h.name} must be between zero and its current value.`);
    released += sold;
    return { ...h, value: Math.round((h.value - sold) * 100) / 100 };
  }).filter(h => h.value > 0);
  if (funding === "rebalance" && Math.abs(released + additional - amount) > .005) throw new Error("Sales plus additional money must equal the investment amount. This demo does not automatically choose holdings to sell.");
  const existing = holdings.find(h => h.id === stock.id);
  if (existing) existing.value += amount;
  else holdings.push({ ...stock, currency: p.baseCurrency, value: amount, expectedReturn: p.isDemo ? stock.expectedReturn : null, eScore: p.isDemo ? stock.eScore : null });
  const result = { ...p, name: "Simulation draft", holdings };
  if (!Number.isFinite(totalValue(result))) throw new Error("Simulation value exceeds the supported numeric range.");
  return result;
}

export function download(name: string, text: string, type = "text/csv;charset=utf-8") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a"); a.href = url; a.download = name; a.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const importTemplate = "stock_code,exchange,company_name,current_holding_value,currency,as_of_date\nDEMO-AR,XHKG,Aurora Renewables,28000,HKD,2026-10-03\nDEMO-HM,XHKG,Harbour Mobility,20000,HKD,2026-10-03\n";
