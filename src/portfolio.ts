import sample from "../docs/api-examples/current-portfolio.json";
import { companyQuote, exchangeRate, marketCompanies } from "./marketData";

export type Holding = {
  id: string; ticker: string; name: string; exchange: string; assetClass: string;
  currency: string; value: number; expectedReturn: number | null; eScore: number | null; color: string;
  unitPrice?: number | null; units?: number | null; greenExplanation?: string;
};
export type Portfolio = { name: string; baseCurrency: string; asOf: string; isDemo: boolean; holdings: Holding[] };
export type Candidate = Omit<Holding, "value"> & { unitPrice: number; riskLevel: number; keywords: string; greenExplanation: string };
export type ParsedImport = { holdings: Holding[]; asOf: string; sourceCurrency: string | null };
const colors = ["#5487bb", "#65a593", "#8d9dca", "#bb8f45", "#8b99a6"];
const roundMoney = (value: number) => Math.round((value + Number.EPSILON) * 100) / 100;
export function convertPrice(price: number, from: string, to: string) { return roundMoney(price * exchangeRate(from, to)); }
export function sharePrice(holding: Holding | Candidate, currency: string) {
  if (holding.unitPrice == null) return null;
  try { return convertPrice(holding.unitPrice, holding.currency, currency); }
  catch { return null; }
}
export function samplePortfolio(): Portfolio {
  const quantities: Record<string, number> = { AR:280, FC:300, HM:200, RM:200 };
  return { name:"Current portfolio",baseCurrency:"HKD",asOf:sample.asOf,isDemo:true,
    holdings:sample.data.holdings.map((h,i) => {
      const quote = companyQuote(h.stockCode, h.name);
      const units = quantities[displayTicker(h.stockCode)];
      return { id:h.id,ticker:h.stockCode,name:h.name,exchange:h.exchange,assetClass:"Equity",currency:"HKD",
        value:h.holdingValueBase,unitPrice:h.holdingValueBase/units,units,
        expectedReturn:quote?.expectedReturn??h.expectedReturn.value,eScore:quote?.eScore??h.eScore.value,greenExplanation:quote?.greenExplanation,color:colors[i%colors.length] };
    }) };
}
export const candidates: Candidate[] = marketCompanies.map(c => ({ id:c.id,ticker:c.ticker,name:c.name,exchange:c.exchange,currency:c.currency,
  assetClass:"Equity",unitPrice:c.price,riskLevel:c.riskLevel,eScore:c.eScore,expectedReturn:c.expectedReturn,color:c.color,keywords:c.keywords,greenExplanation:c.greenExplanation }));
export function recommendStocks(risk: number, green: number, maxInvestment: number, currency: string) {
  return candidates.filter(c => {
    const price=sharePrice(c,currency);
    return c.riskLevel <= risk && c.eScore! >= 5.5 + green*.5 && price!==null && price>0 && price<=maxInvestment;
  })
    .sort((a,b) => {
      const priority = (c: Candidate) => (c.eScore ?? 0)*green + (c.expectedReturn ?? 0)*100*(6-green) - Math.abs(c.riskLevel-risk)*2;
      return priority(b)-priority(a);
    });
}
export function hydratePortfolio(p: Portfolio): Portfolio {
  return { ...p, holdings:p.holdings.map(h => {
    const quote = companyQuote(h.ticker,h.name);
    const unitPrice = h.unitPrice ?? (quote ? convertPrice(quote.price,quote.currency,p.baseCurrency) : null);
    const quantity = unitPrice ? h.value/unitPrice : null;
    const units = h.units ?? (quantity !== null && Math.abs(quantity-Math.round(quantity)) < .0001 ? Math.round(quantity) : null);
    return {...h,unitPrice,units,greenExplanation:h.greenExplanation ?? (h.eScore==null||h.eScore===quote?.eScore?quote?.greenExplanation:undefined),
      expectedReturn:h.expectedReturn ?? quote?.expectedReturn ?? null,eScore:h.eScore ?? quote?.eScore ?? null};
  }) };
}
export function totalValue(p: Portfolio) { return p.holdings.reduce((sum,h) => sum+h.value,0); }
export function metrics(p: Portfolio) {
  const total = totalValue(p);
  const aggregate = (key: "expectedReturn" | "eScore") => {
    const covered=p.holdings.filter(h=>h[key]!==null);
    const coveredValue=covered.reduce((sum,h)=>sum+h.value,0);
    return {value:total>0 && Math.abs(coveredValue-total)<.005 ? covered.reduce((sum,h)=>sum+h.value*h[key]!,0)/total : null,coverage:total>0?coveredValue/total:0};
  };
  return {expectedReturn:aggregate("expectedReturn"),greenScore:aggregate("eScore")};
}
export function money(value: number,currency: string) { return new Intl.NumberFormat("en-US",{style:"currency",currency,maximumFractionDigits:2}).format(value); }
export function unitMoney(value: number,currency: string) { return new Intl.NumberFormat("en-US",{style:"currency",currency,minimumFractionDigits:2,maximumFractionDigits:6}).format(value); }
export function percent(value: number|null,digits=2) { return value===null?"Unavailable":`${(value*100).toFixed(digits)}%`; }
export function score(value: number|null) { return value===null?"Unavailable":value.toFixed(2); }
export function displayTicker(ticker: string) { return ticker.replace(/^DEMO-/i,""); }
export function greenExplanation(h: Holding | Candidate) {
  return h.greenExplanation ?? (h.eScore === null ? "Environmental assessment is unavailable for this company." : `An E-score of ${score(h.eScore)} describes this company's environmental performance. Higher scores indicate stronger performance across emissions, resource use and transition readiness.`);
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
    const companyName = name >= 0 && r[name] ? r[name] : symbol;
    const quote = companyQuote(symbol, companyName);
    const suppliedUnits = unitsColumn >= 0 && r[unitsColumn] ? Number(r[unitsColumn]) : null;
    const suppliedPrice = priceColumn >= 0 && r[priceColumn] ? Number(r[priceColumn]) : null;
    if (suppliedUnits !== null && (!Number.isSafeInteger(suppliedUnits) || suppliedUnits <= 0)) throw new Error(`Row ${i + 2}: units must be a positive whole number.`);
    if (suppliedPrice !== null && (!Number.isFinite(suppliedPrice) || suppliedPrice <= 0)) throw new Error(`Row ${i + 2}: unit price must be positive.`);
    if (suppliedUnits !== null && suppliedPrice !== null && Math.abs(suppliedUnits * suppliedPrice - amount) > .01) throw new Error(`Row ${i + 2}: unit price × units must match current holding value.`);
    const unitPrice = suppliedPrice ?? (suppliedUnits ? amount / suppliedUnits : quote ? convertPrice(quote.price, quote.currency, ccy) : null);
    const quantity = unitPrice ? amount / unitPrice : null;
    const units = suppliedUnits ?? (quantity !== null && Math.abs(quantity - Math.round(quantity)) < .0001 ? Math.round(quantity) : null);
    return { id: `import-${i}`, ticker: symbol === "-" ? "CASH" : symbol, name: companyName,
      exchange: exchange >= 0 ? r[exchange] : quote?.exchange ?? "Unresolved",
      assetClass: kind, currency: ccy, value: amount, unitPrice, units,
      expectedReturn: quote?.expectedReturn ?? null, eScore: quote?.eScore ?? null,
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
export function simulate(p: Portfolio,stock: Candidate,units: number,funding:"new_money"|"rebalance",sales:Record<string,string>,additional:number,maxInvestment=Infinity): Portfolio {
  if (!Number.isSafeInteger(units) || units<=0) throw new Error("Enter a positive whole number of shares.");
  const price=sharePrice(stock,p.baseCurrency);
  if(price===null||price<=0)throw new Error("Share pricing is unavailable in this reporting currency.");
  const amount=roundMoney(price*units);
  if (!Number.isFinite(amount) || amount<=0) throw new Error("Enter a positive investment amount.");
  if (amount>maxInvestment) throw new Error(`Investment amount exceeds your maximum of ${money(maxInvestment,p.baseCurrency)}. Reduce the number of shares or update Settings.`);
  if (!Number.isFinite(additional) || additional<0) throw new Error("Additional money must be zero or positive.");
  let released=0;
  const holdings=p.holdings.map(h=>{
    const sold=funding==="rebalance"?Number(sales[h.id]||0):0;
    if (!Number.isFinite(sold)||sold<0||sold>h.value) throw new Error(`The sale amount for ${h.name} must be between zero and its current value.`);
    const soldUnits=h.unitPrice?Math.round(sold/h.unitPrice):0;
    if (sold>0 && h.units!=null && h.unitPrice && Math.abs(soldUnits*h.unitPrice-sold)>.01) throw new Error(`Sell a whole number of shares of ${h.name}.`);
    released+=sold;
    return {...h,value:roundMoney(h.value-sold),units:h.units==null?null:h.units-soldUnits};
  }).filter(h=>h.value>0);
  if (funding==="rebalance" && Math.abs(released+additional-amount)>.01) throw new Error("Sales plus additional money must equal the investment total.");
  const existing=holdings.find(h=>displayTicker(h.ticker)===displayTicker(stock.ticker) && h.exchange===stock.exchange);
  if (existing) {
    existing.value=roundMoney(existing.value+amount);
    existing.units=existing.units==null?null:existing.units+units;
    existing.unitPrice=existing.units?existing.value/existing.units:price;
  } else {
    const original=p.holdings.find(h=>displayTicker(h.ticker)===displayTicker(stock.ticker)&&h.exchange===stock.exchange);
    holdings.push({...stock,id:original?.id??stock.id,currency:p.baseCurrency,value:amount,unitPrice:price,units});
  }
  const result={...p,name:"Recommended portfolio",holdings};
  if (!Number.isFinite(totalValue(result))) throw new Error("Simulation value exceeds the supported numeric range.");
  return result;
}
export function download(name:string,content:BlobPart,type="text/csv;charset=utf-8") {
  const url=URL.createObjectURL(new Blob([content],{type}));
  const a=document.createElement("a");a.href=url;a.download=name;a.click();
  window.setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export const importTemplate="stock_code,exchange,company_name,current_holding_value,currency,units,unit_price,as_of_date\nAR,XHKG,Aurora Renewables,28000,HKD,280,100,2026-10-03\nHM,XHKG,Harbour Mobility,20000,HKD,200,100,2026-10-03\n";
