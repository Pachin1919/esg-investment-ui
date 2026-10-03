import { useRef, useState } from "react";
import { ArrowRight, DownloadSimple, FileArrowUp } from "@phosphor-icons/react";
import { displayTicker, download, importTemplate, money, normalizeImport, parsePortfolioImport, unitMoney } from "./portfolio";
import type { Lookup, ParsedImport, Portfolio } from "./portfolio";
import { exchangeRate } from "./marketData";
import { Button } from "./ui";

export default function ImportFlow({ lookup, onImport }: { lookup: Lookup; onImport: (p: Portfolio) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [parsed, setParsed] = useState<ParsedImport | null>(null), [fileName, setFileName] = useState("");
  const [base, setBase] = useState("HKD");
  const [error, setError] = useState(""), [reading, setReading] = useState(false);
  const currencies = [...new Set(parsed?.holdings.map(h => h.currency) ?? [])];
  const foreign = currencies.filter(c => c !== base);
  let preview: Portfolio | null = null, conversionError = "";
  if (parsed) { try { preview = normalizeImport(parsed, base, fileName); } catch (e) { conversionError = (e as Error).message; } }
  async function read(file?: File) {
    if (!file) return;
    setParsed(null); setError(""); setReading(true);
    try {
      if (!file.name.toLowerCase().endsWith(".csv")) throw new Error("Choose a CSV file.");
      if (file.size > 10 * 1024 * 1024) throw new Error("The file must be smaller than 10 MB.");
      const data = parsePortfolioImport(await file.text(), lookup); setParsed(data); setFileName(file.name);
      if (data.sourceCurrency) setBase(data.sourceCurrency);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not read this file."); }
    finally { setReading(false); if (input.current) input.current.value = ""; }
  }
  return <div className="setup-body import-body"><span className="setup-icon"><FileArrowUp /></span><h3>Import your current holdings.</h3><p>Use current market value, not original purchase cost. Broker exports with “Total Market Value (SEK)” are supported, including equities, funds and cash.</p>
    <input ref={input} type="file" accept=".csv,text/csv" aria-label="Portfolio CSV" className="sr-only" onChange={e => { void read(e.target.files?.[0]); }} />
    <Button kind="secondary" onClick={() => input.current?.click()} disabled={reading}><FileArrowUp />{reading ? "Reading CSV…" : parsed ? "Choose another CSV" : "Choose a CSV file"}</Button>
    <div className="import-format"><span>Required: ticker (e.g. 0700.HK), current value, currency · Optional: units, unit_price</span><button onClick={() => download("green-street-portfolio-template.csv", importTemplate)}><DownloadSimple size={16} />Download template</button></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {parsed && <div className="import-review"><strong>{fileName} · {parsed.holdings.length} holdings</strong><p>Valuation date: {parsed.asOf}. {parsed.sourceCurrency ? `Market values are already expressed in ${parsed.sourceCurrency}; the stock-currency field is not applied again.` : "Values use the currency declared on each row."}</p><label>Reporting currency<select value={base} onChange={e => { setBase(e.target.value); setError(""); }}>{[...new Set(["HKD", "USD", "CNY", "TWD", "SEK", ...currencies])].map(c => <option key={c}>{c}</option>)}</select></label>
      {foreign.length > 0 && <div className="automatic-fx"><strong>Automatic currency conversion</strong><p>All holdings are converted to {base} for your portfolio.</p>{foreign.map(c => { let rate: number | null = null; try { rate=exchangeRate(c,base); } catch { /* The conversion error is shown below. */ } return <div key={c}><span>1 {c}</span><b>{rate===null?"Unavailable":rate.toFixed(6)} {base}</b></div>; })}</div>}
      {conversionError && <p className="form-error" role="alert">{conversionError}</p>}
      <div className="import-preview table-scroll"><table><thead><tr><th>Asset</th><th>Unit price ({base})</th><th>Units</th><th>Total value ({base})</th></tr></thead><tbody>{(preview?.holdings ?? parsed.holdings).map(h => <tr key={h.id}><td>{h.name}<small>{displayTicker(h.ticker)}</small></td><td>{h.unitPrice==null?"Unavailable":unitMoney(h.unitPrice,h.currency)}</td><td>{h.units??"Unavailable"}</td><td>{money(h.value,h.currency)}</td></tr>)}</tbody></table></div>
      <Button onClick={() => { if(preview) onImport(preview); }} disabled={!preview}>Confirm upload <ArrowRight /></Button>
    </div>}
    <p className="privacy-note">Your holdings and settings are saved in this browser.</p>
  </div>;
}
