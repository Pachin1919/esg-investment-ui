import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { ArrowRight, ArrowsLeftRight, CheckCircle, Compass, DownloadSimple, FileArrowUp, Gauge, Info, Leaf, MagnifyingGlass, SlidersHorizontal, Sparkle, SquaresFour, X } from "@phosphor-icons/react";
import { candidates, download, importTemplate, metrics, money, normalizeImport, parsePortfolioImport, percent, samplePortfolio, score, simulate, totalValue } from "./portfolio";
import type { Candidate, Holding, ParsedImport, Portfolio } from "./portfolio";

type View = "overview" | "recommendations" | "simulate" | "method";
type State = {
  portfolio: Portfolio | null;
  risk: number; green: number; preferencesSet: boolean;
  selectedId: string; amount: string; inputMode: "amount" | "units";
  funding: "new_money" | "rebalance"; additional: string; sales: Record<string, string>;
  result: Portfolio | null;
};
const initialState: State = { portfolio: null, risk: 3, green: 4, preferencesSet: false, selectedId: candidates[0].id, amount: "10000", inputMode: "amount", funding: "new_money", additional: "0", sales: {}, result: null };
const storageKey = "verdant-analysis-v2";
const riskColors = ["#287b53", "#326bbb", "#a97808", "#be621e", "#b13c46"];
const nav = [["overview", SquaresFour, "Portfolio"], ["recommendations", Sparkle, "Recommendations"], ["simulate", ArrowsLeftRight, "Simulator"], ["method", Compass, "Methodology"]] as const;

function Button({ children, onClick, disabled, kind = "primary" }: { children: ReactNode; onClick?: () => void; disabled?: boolean; kind?: "primary" | "secondary" | "ghost" }) {
  return <button type="button" className={`button ${kind}`} onClick={onClick} disabled={disabled}>{children}</button>;
}
function Brand({ onHome }: { onHome: () => void }) {
  return <button className="brand" onClick={onHome} aria-label="Verdant home"><span className="brand-symbol"><Leaf size={22} weight="fill" /></span>verdant<span className="brand-period">.</span></button>;
}
function Dialog({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    const dialog = ref.current!; dialog.showModal();
    const overflow = document.body.style.overflow; document.body.style.overflow = "hidden";
    return () => { dialog.close(); document.body.style.overflow = overflow; opener?.focus(); };
  }, []);
  return <dialog ref={ref} className="flow-dialog" onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) onClose(); }} aria-labelledby="flow-title"><div className="setup-modal"><div className="setup-top"><h2 id="flow-title">{title}</h2><button className="close-button" onClick={onClose} aria-label="Close dialog"><X /></button></div>{children}</div></dialog>;
}
function RiskBadge({ value }: { value: number }) {
  return <span className="risk-badge" style={{ "--risk-color": riskColors[value - 1] } as React.CSSProperties}><i />Risk level {value}</span>;
}
function Preferences({ risk: savedRisk, green: savedGreen, onSave }: { risk: number; green: number; onSave: (risk: number, green: number) => void }) {
  const [risk, setRisk] = useState(savedRisk), [green, setGreen] = useState(savedGreen);
  return <div className="setup-body preferences-body"><span className="setup-icon"><SlidersHorizontal /></span><h3>What matters to you?</h3><p>Set the inputs for recommendations. Live ranking will use the backend model.</p>
    <fieldset><legend>Risk tolerance</legend><p>Level 1 is lower tolerance; level 5 is higher tolerance. These are preferences, not a stock risk rating.</p><div className="five-options risk-options" role="group" aria-label="Risk tolerance">{[1, 2, 3, 4, 5].map(v => <button key={v} aria-pressed={risk === v} className={risk === v ? "selected" : ""} style={{ "--risk-color": riskColors[v - 1] } as React.CSSProperties} onClick={() => setRisk(v)}><span>{v}</span>Level {v}{risk === v && <CheckCircle size={16} />}</button>)}</div><div className="scale-endpoints"><span>Lower tolerance</span><span>Higher tolerance</span></div></fieldset>
    <fieldset><legend>Green preference</legend><p>The latest Q&amp;A allows five levels: 1 puts less emphasis on green firms; 5 puts more emphasis on them.</p><div className="five-options green-options" role="group" aria-label="Green preference">{[1, 2, 3, 4, 5].map(v => <button key={v} aria-pressed={green === v} className={green === v ? "selected" : ""} onClick={() => setGreen(v)}><span><Leaf size={18} weight={green === v ? "fill" : "regular"} /></span>Level {v}</button>)}</div><div className="scale-endpoints"><span>Less emphasis</span><span>More emphasis</span></div></fieldset>
    <Button onClick={() => onSave(risk, green)}>Save preferences &amp; review portfolio <ArrowRight /></Button>
  </div>;
}

function ImportFlow({ onImport, onDemo }: { onImport: (p: Portfolio) => void; onDemo: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [parsed, setParsed] = useState<ParsedImport | null>(null), [fileName, setFileName] = useState("");
  const [base, setBase] = useState("HKD"), [rates, setRates] = useState<Record<string, string>>({});
  const [error, setError] = useState(""), [reading, setReading] = useState(false);
  const currencies = [...new Set(parsed?.holdings.map(h => h.currency) ?? [])];
  const foreign = currencies.filter(c => c !== base);
  async function read(file?: File) {
    if (!file) return;
    setParsed(null); setError(""); setReading(true); setRates({});
    try {
      if (!file.name.toLowerCase().endsWith(".csv")) throw new Error("Choose a CSV file.");
      if (file.size > 10 * 1024 * 1024) throw new Error("The file must be smaller than 10 MB.");
      const data = parsePortfolioImport(await file.text()); setParsed(data); setFileName(file.name);
      if (data.sourceCurrency) setBase(data.sourceCurrency);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not read this file."); }
    finally { setReading(false); if (input.current) input.current.value = ""; }
  }
  return <div className="setup-body import-body"><span className="setup-icon"><FileArrowUp /></span><h3>Import your current holdings.</h3><p>Use current market value, not original purchase cost. Broker exports with “Total Market Value (SEK)” are supported, including equities, funds and cash.</p>
    <input ref={input} type="file" accept=".csv,text/csv" aria-label="Portfolio CSV" className="sr-only" onChange={e => { void read(e.target.files?.[0]); }} />
    <Button kind="secondary" onClick={() => input.current?.click()} disabled={reading}><FileArrowUp />{reading ? "Reading CSV…" : parsed ? "Choose another CSV" : "Choose a CSV file"}</Button>
    <div className="import-format"><span>Required: ticker, current holding value, currency</span><button onClick={() => download("verdant-portfolio-template.csv", importTemplate)}><DownloadSimple size={16} />Download template</button></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {parsed && <div className="import-review"><strong>{fileName} · {parsed.holdings.length} holdings</strong><p>Valuation date: {parsed.asOf}. {parsed.sourceCurrency ? `Market values are already expressed in ${parsed.sourceCurrency}; the stock-currency field is not applied again.` : "Values use the currency declared on each row."}</p><label>Reporting currency<select value={base} onChange={e => { setBase(e.target.value); setRates({}); }}>{[...new Set(["HKD", "USD", "CNY", "TWD", "SEK", ...currencies])].map(c => <option key={c}>{c}</option>)}</select></label>
      {foreign.length > 0 && <p>No live FX service is connected. Supply conversion rates matching the valuation date.</p>}
      {foreign.map(c => <label key={c}>1 {c} = <input type="number" min="0" step="any" aria-label={`${c} to ${base} rate`} value={rates[c] ?? ""} onChange={e => setRates(r => ({ ...r, [c]: e.target.value }))} />{base}</label>)}
      <div className="import-preview table-scroll"><table><thead><tr><th>Asset</th><th>Class</th><th>Current value</th></tr></thead><tbody>{parsed.holdings.map(h => <tr key={h.id}><td>{h.name}<small>{h.ticker}</small></td><td>{h.assetClass}</td><td>{money(h.value, h.currency)}</td></tr>)}</tbody></table></div>
      <Button onClick={() => { try { onImport(normalizeImport(parsed, base, rates, fileName)); } catch (e) { setError((e as Error).message); } }} disabled={foreign.some(c => !rates[c])}>Confirm import &amp; set preferences <ArrowRight /></Button>
    </div>}
    <div className="setup-divider"><span>or</span></div><Button kind="ghost" onClick={onDemo}>Use fictional sample holdings</Button><p className="privacy-note">Your CSV is parsed locally. This prototype stores holdings and drafts in this browser; nothing is sent to a trading platform.</p>
  </div>;
}

function MetricCards({ portfolio }: { portfolio: Portfolio }) {
  const m = metrics(portfolio);
  return <div className="workspace-metrics"><article className="workspace-metric"><div><span>Expected return</span><SquaresFour /></div><strong>{percent(m.expectedReturn.value)}</strong><p>{portfolio.isDemo ? "Annual · fictional fixture" : "Awaiting backend estimate"}</p></article><article className="workspace-metric"><div><span>Portfolio green score</span><Leaf /></div><strong>{score(m.greenScore.value)}</strong><p>{portfolio.isDemo ? "Demo scale 0–10 · final range pending" : "Score range & model pending"}</p></article><article className="workspace-metric"><div><span>Portfolio volatility</span><Gauge /></div><strong className="unavailable">Unavailable</strong><p>First-version availability unconfirmed</p></article></div>;
}
function HoldingsTable({ portfolio, onDetail }: { portfolio: Portfolio; onDetail: (h: Holding) => void }) {
  return <section className="workspace-panel"><div className="panel-heading"><div><h2>Current holdings</h2><p>Current market value · {portfolio.baseCurrency} · {portfolio.asOf}</p></div><strong>{money(totalValue(portfolio), portfolio.baseCurrency)}</strong></div><div className="table-scroll"><table className="analysis-table"><thead><tr><th>Company / asset</th><th>Current value</th><th>Portfolio weight</th><th>Expected return</th><th>E-score</th></tr></thead><tbody>{portfolio.holdings.map(h => <tr key={h.id}><td><button className="holding-detail" onClick={() => onDetail(h)}><i style={{ background: h.color }}>{h.ticker.slice(0, 2)}</i><span>{h.name}<small>{h.ticker} · {h.assetClass}</small></span></button></td><td>{money(h.value, portfolio.baseCurrency)}</td><td>{percent(h.value / totalValue(portfolio), 1)}</td><td>{percent(h.expectedReturn)}</td><td>{score(h.eScore)}</td></tr>)}</tbody></table></div></section>;
}
function CompanyDetails({ company, isDemo, onSimulate }: { company: Holding | Candidate; isDemo: boolean; onSimulate?: () => void }) {
  return <div className="setup-body company-details"><span className="illustrative-pill">{isDemo ? "Fictional company · demo metrics" : "Imported asset · analysis pending"}</span><h3>{company.name}</h3><p>{company.ticker} · {company.exchange}</p><div className="company-key-metrics"><article><span>Expected return</span><strong>{percent(company.expectedReturn)}</strong><small>{isDemo ? "Annual demo estimate" : "Backend not connected"}</small></article><article><span>E-score</span><strong>{score(company.eScore)}</strong><small>{isDemo ? "Demo scale 0–10" : "Final range pending"}</small></article></div><p>Higher E-score means more environmentally friendly. It does not imply higher return or a better investment.</p><details><summary>Data basis &amp; limitations</summary><p>{isDemo ? "These are fictional fixtures. No verified company documents or financial model are attached." : "Your file provides holding values, not forecast or environmental analysis. No scores are inferred from company names."} Expected-return assumptions, final scoring range and sources require the backend. No company trends or industry comparison are available.</p></details>{onSimulate && <Button onClick={onSimulate}>Simulate investment <ArrowRight /></Button>}</div>;
}
function Methodology() {
  const items = [
    ["E-score", "The current product focuses on environment only. Higher means more environmentally friendly; it is not a return forecast. The final range is unconfirmed; 0–10 is used only for labeled fictional fixtures."],
    ["Expected return", "Annual expected return is the proposed display. The backend still needs to confirm horizon, currency, dividends, costs and model assumptions. Demo values are fixed fixtures, not validated forecasts."],
    ["Preferences", "Risk tolerance and green preference both use levels 1–5 in the latest Q&A. Level 5 means higher risk tolerance or stronger green preference. Colors identify preference levels, not credit ratings or investment quality."],
    ["Portfolio assessment", "Portfolio results are metric cards. The demo aggregates fixed company figures by current-value weights. The real aggregation model and volatility availability remain unconfirmed. Missing values stay unavailable."],
    ["Simulation", "Add new money, or select holdings to reduce and optionally add money. Local arithmetic previews holding values and weights. Imported portfolios require the backend for simulated return and score results."],
    ["Data & privacy", "CSV values mean current market value, not acquisition cost. Currency normalization uses supplied values or explicit user-provided rates. Holdings and drafts persist in this browser. Use Clear portfolio to remove them."],
  ];
  return <div className="workspace-page"><div className="workspace-heading"><div><span className="workspace-eyebrow">METHODOLOGY</span><h1>Understand the numbers.</h1><p>Environmental performance, expected return and risk have distinct meanings.</p></div></div><div className="methodology-grid">{items.map(([title, text]) => <article className="workspace-panel" key={title}><span><Compass /></span><h2>{title}</h2><p>{text}</p></article>)}</div></div>;
}

export default function Workbench({ entry, onHome }: { entry: "import" | "demo" | "resume"; onHome: () => void }) {
  const [state, setState] = useState<State>(() => {
    if (entry === "demo") return { ...initialState, portfolio: samplePortfolio(), preferencesSet: true };
    try { const saved = JSON.parse(localStorage.getItem(storageKey) ?? "null"); if (saved?.portfolio?.holdings?.length && saved.risk >= 1 && saved.risk <= 5 && saved.green >= 1 && saved.green <= 5) return { ...initialState, ...saved }; } catch { /* Start fresh when storage is unavailable. */ }
    return initialState;
  });
  const [view, setView] = useState<View>("overview");
  const [setup, setSetup] = useState<"import" | "preferences" | null>(entry === "import" || !state.portfolio ? "import" : !state.preferencesSet ? "preferences" : null);
  const [detail, setDetail] = useState<Holding | Candidate | null>(null), [error, setError] = useState(""), [query, setQuery] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => { try { localStorage.setItem(storageKey, JSON.stringify(state)); } catch { /* The workflow also works without persistence. */ } }, [state]);
  useEffect(() => { if (!notice) return; const id = window.setTimeout(() => setNotice(""), 4000); return () => window.clearTimeout(id); }, [notice]);
  const p = state.portfolio;
  const selected = candidates.find(c => c.id === state.selectedId) ?? candidates[0];
  const amount = state.inputMode === "units" ? Number(state.amount) * selected.demoPrice : Number(state.amount);
  const updateDraft = (fields: Partial<State>) => { setState(s => ({ ...s, ...fields, result: null })); setError(""); };
  const go = (next: View) => {
    if ((next === "recommendations" || next === "simulate") && !state.preferencesSet) { setSetup("preferences"); return; }
    setView(next); setError(""); window.scrollTo(0, 0);
  };
  const select = (c: Candidate) => { updateDraft({ selectedId: c.id }); setDetail(null); go("simulate"); };
  const load = (portfolio: Portfolio) => { setState(s => ({ ...initialState, risk: s.risk, green: s.green, portfolio })); setSetup("preferences"); };
  const m = p ? metrics(p) : null;
  const step = !p ? 0 : !state.preferencesSet ? 1 : view === "recommendations" ? 2 : view === "simulate" ? state.result ? 4 : 3 : 2;
  return <div className="workbench"><aside className="app-sidebar"><Brand onHome={onHome} /><span className="nav-label">ANALYSIS WORKSPACE</span><nav aria-label="Workspace navigation">{nav.map(([id, Icon, label]) => <button key={id} aria-label={label} aria-current={view === id ? "page" : undefined} className={view === id ? "active" : ""} onClick={() => go(id)} disabled={!p && id !== "method"}><Icon size={20} />{label}</button>)}</nav><div className="preference-card"><small>YOUR PREFERENCES</small><RiskBadge value={state.risk} /><p>Green preference · Level {state.green}</p><button onClick={() => setSetup("preferences")} disabled={!p}>Update preferences</button></div><button className="back-landing" onClick={onHome}><Leaf />Back to website</button></aside>
    <div className="app-main"><header className="app-topbar"><span className="breadcrumb">Workspace / {nav.find(n => n[0] === view)?.[2]}</span><div className="topbar-actions"><span className="portfolio-status">{p?.isDemo ? "Fictional sample" : p ? "Imported · API pending" : "No portfolio"}</span><button className="import-button" onClick={() => setSetup("import")}><FileArrowUp />Import</button></div></header><main>
      <ol className="workflow-steps" aria-label="Investment analysis workflow">{["Import holdings", "Set preferences", "Recommendations", "Simulate investment", "Compare portfolios"].map((label, i) => <li key={label} className={i === step ? "active" : i < step ? "complete" : ""}><span>{i < step ? <CheckCircle size={17} /> : i + 1}</span>{label}</li>)}</ol>
      {p && <div className="workspace-demo-note"><Info /><span>{p.isDemo ? "Demo mode: fictional company metrics; local illustrative calculations, not backend forecasts." : "Import complete: values and weights are available. Expected returns, E-scores and live recommendations await the backend."}</span></div>}
      {!p && <section className="workspace-panel empty-workspace"><FileArrowUp size={40} /><h1>Start with your holdings.</h1><p>Import current market values, then choose risk and green preferences.</p><Button onClick={() => setSetup("import")}>Import portfolio</Button><Button kind="secondary" onClick={() => load(samplePortfolio())}>Try sample holdings</Button></section>}
      {p && view === "overview" && <div className="workspace-page"><div className="workspace-heading"><div><span className="workspace-eyebrow">PORTFOLIO ASSESSMENT</span><h1>Your portfolio, with environmental context.</h1><p>Understand expected return and green performance before considering a change.</p></div><Button onClick={() => go("recommendations")}>View stock recommendations <ArrowRight /></Button></div><MetricCards portfolio={p} /><div className="analysis-meta"><span>{p.holdings.length} assets · {money(totalValue(p), p.baseCurrency)}</span><span>E-score coverage {percent(m!.greenScore.coverage, 0)}</span><RiskBadge value={state.risk} /><span>Green preference · Level {state.green}</span></div><HoldingsTable portfolio={p} onDetail={setDetail} /><div className="workspace-actions"><Button kind="secondary" onClick={() => setSetup("preferences")}><SlidersHorizontal />Edit preferences</Button><Button kind="ghost" onClick={() => download("verdant-portfolio.json", JSON.stringify(p, null, 2), "application/json")}>Export portfolio</Button><Button kind="ghost" onClick={() => { setState(initialState); setSetup("import"); setNotice("Portfolio and simulation removed from this browser."); }}>Clear portfolio</Button></div></div>}
      {p && view === "recommendations" && <div className="workspace-page"><div className="workspace-heading"><div><span className="workspace-eyebrow">STOCK RECOMMENDATIONS</span><h1>Explore a potential investment.</h1><p>Recommendation inputs: current holdings, risk tolerance and green preference.</p></div><label className="workspace-search"><MagnifyingGlass size={18} /><input aria-label="Search recommendations" placeholder="Search company or ticker" value={query} onChange={e => setQuery(e.target.value)} /></label></div><div className="recommendation-summary"><RiskBadge value={state.risk} /><span>Green preference · Level {state.green}<strong>{p.isDemo ? "Illustrative candidates · not a validated ranking" : "Backend recommendations pending · examples shown for workflow preview"}</strong></span><button onClick={() => setSetup("preferences")}>Edit preferences</button></div><div className="recommendation-grid">{candidates.filter(c => `${c.name} ${c.ticker}`.toLowerCase().includes(query.toLowerCase())).map(c => <article className="recommendation-card" key={c.id}><span className="illustrative-pill">Fictional example</span><div className="rec-company"><i style={{ background: c.color }}>{c.ticker.slice(-2)}</i><div><h2>{c.name}</h2><p>{c.ticker} · {c.exchange}</p></div></div><p className="rec-reason">{c.reason}</p><div className="rec-metrics"><span>Expected return<strong>{percent(c.expectedReturn)}</strong><small>Annual demo estimate</small></span><span>E-score<strong>{score(c.eScore)}</strong><small>Demo scale 0–10</small></span></div><Button onClick={() => select(c)}>Simulate {c.ticker} <ArrowRight /></Button><Button kind="ghost" onClick={() => setDetail(c)}>Company details</Button></article>)}</div>{!candidates.some(c => `${c.name} ${c.ticker}`.toLowerCase().includes(query.toLowerCase())) && <p role="status">No matching examples. Try another name or clear the search.</p>}</div>}
      {p && view === "simulate" && <div className="workspace-page"><div className="workspace-heading"><div><span className="workspace-eyebrow">SIMULATE INVESTMENT</span><h1>Test an amount. Compare the change.</h1><p>The original portfolio stays unchanged. Drafts persist when you leave this page.</p></div><Button kind="secondary" onClick={() => go("recommendations")}>Choose another stock</Button></div><div className="simulator-grid"><section className="workspace-panel simulation-input"><label className="selection-label">Selected stock<select aria-label="Selected stock" value={selected.id} onChange={e => updateDraft({ selectedId: e.target.value })}>{candidates.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label><div className="rec-company"><i style={{ background: selected.color }}>{selected.ticker.slice(-2)}</i><div><h2>{selected.name}</h2><p>{selected.ticker} · fictional candidate</p></div></div>
          <fieldset className="funding-options"><legend>Funding source</legend><label><input type="radio" name="funding" checked={state.funding === "new_money"} onChange={() => updateDraft({ funding: "new_money" })} />Add new money</label><label><input type="radio" name="funding" checked={state.funding === "rebalance"} onChange={() => updateDraft({ funding: "rebalance" })} />Rebalance existing holdings</label></fieldset>
          <div className="input-mode"><button aria-pressed={state.inputMode === "amount"} onClick={() => updateDraft({ inputMode: "amount", amount: "10000" })}>Amount</button><button aria-pressed={state.inputMode === "units"} disabled={!p.isDemo} onClick={() => updateDraft({ inputMode: "units", amount: "10" })}>Units · demo only</button></div><label className="investment-amount">{state.inputMode === "amount" ? `Investment amount (${p.baseCurrency})` : "Number of units"}<input aria-label="Investment amount" type="number" min={state.inputMode === "units" ? "1" : "0.01"} step={state.inputMode === "units" ? "1" : "0.01"} value={state.amount} onChange={e => updateDraft({ amount: e.target.value })} /></label>{state.inputMode === "units" && <p className="simulation-help">Fictional price: {money(selected.demoPrice, p.baseCurrency)} per unit · total {money(amount || 0, p.baseCurrency)}. No live quote or lot-size rules.</p>}
          {state.funding === "rebalance" && <div className="sale-inputs"><h3>Choose amounts to release</h3>{p.holdings.map(h => <label key={h.id}><span>{h.name}<small>Available {money(h.value, p.baseCurrency)}</small></span><input aria-label={`Sell ${h.name}`} type="number" min="0" max={h.value} step="0.01" value={state.sales[h.id] ?? ""} placeholder="0" onChange={e => updateDraft({ sales: { ...state.sales, [h.id]: e.target.value } })} /></label>)}<label><span>Additional money ({p.baseCurrency})</span><input aria-label="Additional money" type="number" min="0" step="0.01" value={state.additional} onChange={e => updateDraft({ additional: e.target.value })} /></label><p className="simulation-help">Sales plus additional money must equal your investment amount. Original holdings will not be changed.</p></div>}
          <p className="simulation-help">{p.isDemo ? "Demo arithmetic uses fixed sample returns and E-scores. It does not run the proposed investment model." : "The request preview updates holding values only. Analytical results require the backend."}</p>{error && <p className="form-error" role="alert">{error}</p>}<Button onClick={() => { try { if (state.inputMode === "units" && (!Number.isInteger(Number(state.amount)) || Number(state.amount) <= 0)) throw new Error("Enter a positive whole number of units."); const result = simulate(p, selected, amount, state.funding, state.sales, state.funding === "rebalance" ? Number(state.additional || 0) : 0); setState(s => ({ ...s, result })); setError(""); setNotice(p.isDemo ? "Illustrative simulation updated." : "Request preview saved. Backend analysis pending."); } catch (e) { setError((e as Error).message); } }}>{p.isDemo ? "Run demo simulation" : "Prepare simulation request"}<ArrowRight /></Button>
        </section><section className="workspace-panel comparison-panel"><div className="panel-heading"><div><h2>Current vs. simulated</h2><p>{state.result ? "Same valuation basis · unchanged baseline" : "Run a simulation to compare portfolios"}</p></div></div>{state.result ? <><Comparison baseline={p} result={state.result} /><details className="request-preview"><summary>View simulation request</summary><pre>{JSON.stringify({ backendConnected: false, isDemo: p.isDemo, reportingCurrency: p.baseCurrency, preferences: { riskLevel: state.risk, greenPreference: state.green }, holdings: p.holdings.map(({ ticker, exchange, value }) => ({ ticker, exchange, currentValue: value })), purchase: { stockId: selected.id, investmentAmount: amount, currency: p.baseCurrency }, fundingMode: state.funding, sales: state.funding === "rebalance" ? state.sales : {}, additionalMoney: state.funding === "rebalance" ? Number(state.additional || 0) : amount }, null, 2)}</pre></details><Button kind="ghost" onClick={() => updateDraft({ result: null })}>Reset comparison</Button></> : <div className="comparison-empty"><ArrowsLeftRight size={35} /><h3>Choose a stock and investment amount.</h3><p>Compare expected return, green score, portfolio value and holding weights. Volatility remains unavailable.</p></div>}</section></div></div>}
      {view === "method" && <Methodology />}
    </main></div>
    {setup && <Dialog title={setup === "import" ? "Import holdings · step 1" : "Set preferences · step 2"} onClose={() => setSetup(null)}>{setup === "import" ? <ImportFlow onImport={load} onDemo={() => load(samplePortfolio())} /> : <Preferences risk={state.risk} green={state.green} onSave={(risk, green) => { setState(s => ({ ...s, risk, green, preferencesSet: true, result: null })); setSetup(null); go("overview"); }} />}</Dialog>}
    {detail && <Dialog title="Company analysis" onClose={() => setDetail(null)}><CompanyDetails company={detail} isDemo={"demoPrice" in detail || !!p?.isDemo} onSimulate={"demoPrice" in detail ? () => select(detail) : undefined} /></Dialog>}
    {notice && <div className="toast" role="status"><CheckCircle size={18} />{notice}</div>}
  </div>;
}

function Comparison({ baseline, result }: { baseline: Portfolio; result: Portfolio }) {
  const before = metrics(baseline), after = metrics(result);
  const change = (a: number | null, b: number | null, percentUnit: boolean) => a === null || b === null ? "Pending" : `${b - a >= 0 ? "+" : ""}${((b - a) * (percentUnit ? 100 : 1)).toFixed(percentUnit ? 3 : 2)} ${percentUnit ? "pp" : "points"}`;
  const rows = [
    ["Portfolio value", money(totalValue(baseline), baseline.baseCurrency), money(totalValue(result), result.baseCurrency), money(totalValue(result) - totalValue(baseline), result.baseCurrency)],
    ["Expected return · annual", percent(before.expectedReturn.value, 3), percent(after.expectedReturn.value, 3), change(before.expectedReturn.value, after.expectedReturn.value, true)],
    ["Portfolio green score", score(before.greenScore.value), score(after.greenScore.value), change(before.greenScore.value, after.greenScore.value, false)],
    ["Portfolio volatility", "Unavailable", "Unavailable", "Pending"],
    ["E-score coverage", percent(before.greenScore.coverage, 1), percent(after.greenScore.coverage, 1), change(before.greenScore.coverage, after.greenScore.coverage, true)],
  ];
  return <><div className="table-scroll"><table className="comparison-table"><thead><tr><th>Metric</th><th>Current</th><th>Simulated</th><th>Change</th></tr></thead><tbody>{rows.map(row => <tr key={row[0]}>{row.map((v, i) => i === 0 ? <th key={i} scope="row">{v}</th> : <td key={i}>{v}</td>)}</tr>)}</tbody></table></div><p className="model-note">{baseline.isDemo ? "Higher green score does not imply higher expected return. Demo score scale and aggregation are provisional." : "Analytical metrics are unavailable until the backend returns results."}</p><div className="table-scroll"><table className="comparison-table"><caption>Holding weights after the proposed investment</caption><thead><tr><th>Asset</th><th>Current</th><th>Simulated</th></tr></thead><tbody>{[...new Set([...baseline.holdings, ...result.holdings].map(h => h.id))].map(id => { const a = baseline.holdings.find(h => h.id === id), b = result.holdings.find(h => h.id === id); return <tr key={id}><th scope="row">{b?.name ?? a?.name}</th><td>{percent((a?.value ?? 0) / totalValue(baseline), 1)}</td><td>{percent((b?.value ?? 0) / totalValue(result), 1)}</td></tr>; })}</tbody></table></div></>;
}
