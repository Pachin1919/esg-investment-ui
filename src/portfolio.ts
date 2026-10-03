import { exchangeRate } from "./marketData";

export type Holding = {
  id: string; ticker: string; name: string; exchange: string; assetClass: string;
  currency: string; value: number; expectedReturn: number | null; eScore: number | null; color: string;
  unitPrice?: number | null; units?: number | null; greenExplanation?: string; sector?: string;
};
export type Portfolio = { name: string; baseCurrency: string; asOf: string; isDemo: boolean; holdings: Holding[] };
export type ParsedImport = { holdings: Holding[]; asOf: string; sourceCurrency: string | null };
// Looks up a ticker in the live universe: fills name, score and colour for imported rows.
export type Lookup = (ticker: string) => Partial<Holding> | undefined;
const colors = ["#5487bb", "#65a593", "#8d9dca", "#bb8f45", "#8b99a6"];
const roundMoney = (value: number) => Math.round((value + Number.EPSILON) * 100) / 100;
export function totalValue(p: Portfolio) { return p.holdings.reduce((sum,h) => sum+h.value,0); }
export function metrics(p: Portfolio) {
  const total = totalValue(p);
  const aggregate = (key: "expectedReturn" | "eScore") => {
    const covered=p.holdings.filter(h=>h[key]!==null);
    const coveredValue=covered.reduce((sum,h)=>sum+h.value,0);
    // value-weighted over the holdings that have the figure; `coverage` says how much of the portfolio that is
    return {value:coveredValue>0 ? covered.reduce((sum,h)=>sum+h.value*h[key]!,0)/coveredValue : null,coverage:total>0?coveredValue/total:0};
  };
  return {expectedReturn:aggregate("expectedReturn"),greenScore:aggregate("eScore")};
}
export function money(value: number,currency: string) { return new Intl.NumberFormat("en-US",{style:"currency",currency,maximumFractionDigits:2}).format(value); }
export function unitMoney(value: number,currency: string) { return new Intl.NumberFormat("en-US",{style:"currency",currency,minimumFractionDigits:2,maximumFractionDigits:3}).format(value); }
export function initials(name: string) { const w=name.replace(/[^A-Za-z0-9 ]+/g," ").trim().split(/\s+/); return ((w[0]?.[0]??"")+(w[1]?.[0]??w[0]?.[1]??"")).toUpperCase(); }
export function percent(value: number|null,digits=2) { return value===null?"Unavailable":`${(value*100).toFixed(digits)}%`; }
export function score(value: number|null) { return value===null?"Unavailable":value.toFixed(2); }
export function displayTicker(ticker: string) { return ticker.replace(/^DEMO-/i,""); }
// "2" -> "0002.HK", "700.hk" -> "0700.HK"; other symbols are upper-cased (same rule as the server).
export function normalizeTicker(raw: string) {
  const t = raw.trim().toUpperCase();
  const m = t.match(/^(\d{1,5})(\.HK)?$/);
  return m ? `${m[1].padStart(4, "0")}.HK` : t;
}
export function greenExplanation(h: Holding) {
  return h.greenExplanation ?? (h.eScore === null ? "Environmental assessment is unavailable for this company." : `An E-score of ${score(h.eScore)} describes this company's environmental performance. It is the company's emission-intensity rank within its sector (0–10); higher is greener.`);
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

export function parsePortfolioImport(text: string, lookup: Lookup = () => undefined): ParsedImport {
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
  const unitsColumn = find("units", "quantity", "shares");
  const priceColumn = find("unitprice", "shareprice", "price");
  const value = headers.findIndex(h => /^(totalmarketvalue|currentholdingvalue|marketholdingvalue|marketvalue|currentvalue)(\([a-z]{3}\))?$/.test(h));
  if (ticker < 0 || value < 0) throw new Error("Required columns: ticker (or stock_code), current_holding_value (or Total Market Value), and currency.");
  const sourceCurrency = rows[0][value].match(/\(([A-Za-z]{3})\)/)?.[1].toUpperCase() ?? null;
  if (!sourceCurrency && currency < 0) throw new Error("Add a currency column, or a currency in the market-value header, such as Total Market Value (SEK).");
  const dates = new Set<string>();
  const holdings = rows.slice(1).map((r, i): Holding => {
    if (r.length !== rows[0].length) throw new Error(`Row ${i + 2}: column count does not match the header. Quote names containing commas.`);
    if (!/^(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$/.test(r[value])) throw new Error(`Row ${i + 2}: use a positive market value with a decimal point, for example 23878.25. Commas may only separate thousands.`);
    const amount = Number(r[value].replace(/,/g, ""));
    const kind = assetClass >= 0 ? r[assetClass] : "Equity";
    const symbol = r[ticker] === "-" ? "-" : normalizeTicker(r[ticker]);
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
    const quote = lookup(symbol);
    const companyName = quote?.name ?? (name >= 0 && r[name] ? r[name] : symbol);
    const suppliedUnits = unitsColumn >= 0 && r[unitsColumn] ? Number(r[unitsColumn]) : null;
    const suppliedPrice = priceColumn >= 0 && r[priceColumn] ? Number(r[priceColumn]) : null;
    if (suppliedUnits !== null && (!Number.isSafeInteger(suppliedUnits) || suppliedUnits <= 0)) throw new Error(`Row ${i + 2}: units must be a positive whole number.`);
    if (suppliedPrice !== null && (!Number.isFinite(suppliedPrice) || suppliedPrice <= 0)) throw new Error(`Row ${i + 2}: unit price must be positive.`);
    if (suppliedUnits !== null && suppliedPrice !== null && Math.abs(suppliedUnits * suppliedPrice - amount) > .01) throw new Error(`Row ${i + 2}: unit price × units must match current holding value.`);
    const unitPrice = suppliedPrice ?? (suppliedUnits ? amount / suppliedUnits : null);
    const quantity = unitPrice ? amount / unitPrice : null;
    const units = suppliedUnits ?? (quantity !== null && Math.abs(quantity - Math.round(quantity)) < .0001 ? Math.round(quantity) : null);
    return { id: symbol === "-" ? `cash-${i}` : symbol, ticker: symbol === "-" ? "CASH" : symbol, name: companyName,
      exchange: exchange >= 0 ? r[exchange] : quote?.exchange ?? "Unresolved",
      assetClass: kind, currency: ccy, value: amount, unitPrice, units,
      expectedReturn: null, eScore: quote?.eScore ?? null, sector: quote?.sector,
      greenExplanation: quote?.greenExplanation, color: quote?.color ?? colors[i % colors.length] };
  });
  if (dates.size > 1) throw new Error("Use a common valuation date for all holdings.");
  return { holdings, asOf: [...dates][0] ?? "Not supplied", sourceCurrency };
}


export function normalizeImport(parsed: ParsedImport, baseCurrency: string, fileName: string): Portfolio {
  exchangeRate("USD",baseCurrency);
  const holdings=parsed.holdings.map(h => {
    const rate=exchangeRate(h.currency,baseCurrency);
    const value=roundMoney(h.value*rate);
    if (!Number.isFinite(value) || value<=0) throw new Error("Converted holding values must be positive and finite.");
    return {...h,currency:baseCurrency,value,unitPrice:h.unitPrice==null?null:(h.units?value/h.units:h.unitPrice*rate)};
  });
  const p={name:fileName,baseCurrency,asOf:parsed.asOf,isDemo:false,holdings};
  if (!Number.isFinite(totalValue(p))) throw new Error("Portfolio value exceeds the supported numeric range.");
  return p;
}
export function download(name:string,content:BlobPart,type="text/csv;charset=utf-8") {
  const url=URL.createObjectURL(new Blob([content],{type}));
  const a=document.createElement("a");a.href=url;a.download=name;a.click();
  window.setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export const importTemplate="stock_code,exchange,company_name,current_holding_value,currency,units,unit_price,as_of_date\n0002.HK,XHKG,CLP Holdings,28000,HKD,,,2026-10-03\n0700.HK,XHKG,Tencent Holdings,24000,HKD,,,2026-10-03\n";
