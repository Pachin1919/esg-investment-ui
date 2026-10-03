import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { ArrowLeft, ArrowRight, ArrowsLeftRight, CheckCircle, Compass, DownloadSimple, FileArrowUp, Gauge, GearSix, Leaf, MagnifyingGlass, Sparkle, SquaresFour, X } from "@phosphor-icons/react";
import { candidates, displayTicker, download, importTemplate, metrics, money, normalizeImport, parsePortfolioImport, percent, samplePortfolio, score, simulate, totalValue } from "./portfolio";
import type { Candidate, Holding, ParsedImport, Portfolio } from "./portfolio";
import Brand from "./Brand";
import { createPortfolioExport } from "./portfolioExport";
import type { ExportFormat, ExportKind } from "./portfolioExport";

type View = "overview" | "recommendations" | "method" | "settings";
type State = {
  portfolio: Portfolio | null;
  risk: number; green: number; maxInvestment: number;
  selectedId: string; amount: string; inputMode: "amount" | "units";
  funding: "new_money" | "rebalance"; additional: string; sales: Record<string, string>;
  result: Portfolio | null;
};
const initialState: State = { portfolio: null, risk: 3, green: 4, maxInvestment: 100000, selectedId: candidates[0].id, amount: "10000", inputMode: "amount", funding: "new_money", additional: "0", sales: {}, result: null };
const storageKey = "verdant-analysis-v2";
const riskColors = ["#287b53", "#326bbb", "#a97808", "#be621e", "#b13c46"];
const nav = [["overview", SquaresFour, "Current portfolio"], ["recommendations", Sparkle, "Recommendations"], ["method", Compass, "Methodology"]] as const;

function Button({ children, onClick, disabled, kind = "primary" }: { children: ReactNode; onClick?: () => void; disabled?: boolean; kind?: "primary" | "secondary" | "ghost" }) {
  return <button type="button" className={`button ${kind}`} onClick={onClick} disabled={disabled}>{children}</button>;
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
function Settings({ risk: savedRisk, green: savedGreen, maxInvestment: savedMax, currency, onSave }: { risk: number; green: number; maxInvestment: number; currency: string; onSave: (risk: number, green: number, maxInvestment: number) => void }) {
  const [risk, setRisk] = useState(savedRisk), [green, setGreen] = useState(savedGreen);
  const [maximum, setMaximum] = useState(String(savedMax)), [error, setError] = useState("");
  return <div className="workspace-page settings-page">
    <div className="workspace-heading"><div><span className="workspace-eyebrow">SETTINGS</span><h1>Your investment preferences.</h1><p>Choose your risk tolerance, environmental priority and investment budget.</p></div></div>
    <form className="settings-form" onSubmit={e => {
      e.preventDefault();
      const value = Number(maximum);
      if (!Number.isFinite(value) || value <= 0) { setError("Enter a positive maximum investment amount."); return; }
      onSave(risk, green, value); setError("");
    }}>
      <fieldset className="workspace-panel preference-setting"><legend>Risk tolerance</legend><p>Level 1 is lower tolerance; level 5 is higher tolerance.</p><div className="five-options risk-options" role="group" aria-label="Risk tolerance">{[1, 2, 3, 4, 5].map(v => <button type="button" key={v} aria-pressed={risk === v} className={risk === v ? "selected" : ""} style={{ "--risk-color": riskColors[v - 1] } as React.CSSProperties} onClick={() => setRisk(v)}><span>{v}</span>Level {v}{risk === v && <CheckCircle size={16} />}</button>)}</div><div className="scale-endpoints"><span>Lower tolerance</span><span>Higher tolerance</span></div></fieldset>
      <fieldset className="workspace-panel preference-setting"><legend>Green preference</legend><p>Choose how much emphasis to put on environmental performance.</p><div className="five-options green-options" role="group" aria-label="Green preference">{[1, 2, 3, 4, 5].map(v => <button type="button" key={v} aria-pressed={green === v} className={green === v ? "selected" : ""} onClick={() => setGreen(v)}><span><Leaf size={18} weight={green === v ? "fill" : "regular"} /></span>Level {v}</button>)}</div><div className="scale-endpoints"><span>Less emphasis</span><span>More emphasis</span></div></fieldset>
      <fieldset className="workspace-panel budget-setting"><legend>Investment budget</legend><div className="budget-setting-content"><div><p>Set the maximum amount you are comfortable investing in a single simulation.</p><p className="budget-help">Applies to both new money and rebalanced investments.</p></div><label className="budget-label" htmlFor="max-investment">Maximum investment amount ({currency})<div className="budget-input"><span>{currency}</span><input id="max-investment" aria-label="Maximum investment amount" type="number" min="0.01" step="0.01" required value={maximum} onChange={e => { setMaximum(e.target.value); setError(""); }} /></div></label></div></fieldset>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="settings-actions"><button type="submit" className="button primary">Save settings <CheckCircle size={18} /></button></div>
    </form>
  </div>;
}

function ImportFlow({ onImport }: { onImport: (p: Portfolio) => void }) {
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
    <div className="import-format"><span>Required: ticker, current holding value, currency</span><button onClick={() => download("green-street-portfolio-template.csv", importTemplate)}><DownloadSimple size={16} />Download template</button></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {parsed && <div className="import-review"><strong>{fileName} · {parsed.holdings.length} holdings</strong><p>Valuation date: {parsed.asOf}. {parsed.sourceCurrency ? `Market values are already expressed in ${parsed.sourceCurrency}; the stock-currency field is not applied again.` : "Values use the currency declared on each row."}</p><label>Reporting currency<select value={base} onChange={e => { setBase(e.target.value); setRates({}); }}>{[...new Set(["HKD", "USD", "CNY", "TWD", "SEK", ...currencies])].map(c => <option key={c}>{c}</option>)}</select></label>
      {foreign.length > 0 && <p>Supply conversion rates matching the valuation date.</p>}
      {foreign.map(c => <label key={c}>1 {c} = <input type="number" min="0" step="any" aria-label={`${c} to ${base} rate`} value={rates[c] ?? ""} onChange={e => setRates(r => ({ ...r, [c]: e.target.value }))} />{base}</label>)}
      <div className="import-preview table-scroll"><table><thead><tr><th>Asset</th><th>Class</th><th>Current value</th></tr></thead><tbody>{parsed.holdings.map(h => <tr key={h.id}><td>{h.name}<small>{h.ticker}</small></td><td>{h.assetClass}</td><td>{money(h.value, h.currency)}</td></tr>)}</tbody></table></div>
      <Button onClick={() => { try { onImport(normalizeImport(parsed, base, rates, fileName)); } catch (e) { setError((e as Error).message); } }} disabled={foreign.some(c => !rates[c])}>Confirm upload <ArrowRight /></Button>
    </div>}
    <p className="privacy-note">Your holdings and settings are saved in this browser.</p>
  </div>;
}


function MetricCards({ portfolio }: { portfolio: Portfolio }) {
  const m = metrics(portfolio);
  return <div className="workspace-metrics"><article className="workspace-metric"><div><span>Expected return</span><SquaresFour /></div><strong>{percent(m.expectedReturn.value)}</strong><p>Annual expected return</p></article><article className="workspace-metric"><div><span>Portfolio green score</span><Leaf /></div><strong>{score(m.greenScore.value)}</strong><p>Environmental performance</p></article><article className="workspace-metric"><div><span>Portfolio volatility</span><Gauge /></div><strong className="unavailable">Unavailable</strong><p>Portfolio risk</p></article></div>;
}
function HoldingsTable({ portfolio, onDetail }: { portfolio: Portfolio; onDetail: (h: Holding) => void }) {
  return <section className="workspace-panel"><div className="panel-heading"><div><h2>Current holdings</h2><p>Current market value · {portfolio.baseCurrency} · {portfolio.asOf}</p></div><strong>{money(totalValue(portfolio), portfolio.baseCurrency)}</strong></div><p className="table-scroll-hint">Swipe the table to see all metrics →</p><div className="table-scroll"><table className="analysis-table"><thead><tr><th>Company / asset</th><th>Current value</th><th>Portfolio weight</th><th>Expected return</th><th>E-score</th></tr></thead><tbody>{portfolio.holdings.map(h => <tr key={h.id}><td><button className="holding-detail" onClick={() => onDetail(h)}><i style={{ background: h.color }}>{displayTicker(h.ticker).slice(0, 2)}</i><span>{h.name}<small>{displayTicker(h.ticker)} · {h.assetClass}</small></span></button></td><td>{money(h.value, portfolio.baseCurrency)}</td><td>{percent(h.value / totalValue(portfolio), 1)}</td><td>{percent(h.expectedReturn)}</td><td>{score(h.eScore)}</td></tr>)}</tbody></table></div></section>;
}
function CompanyDetails({ company, onSimulate }: { company: Holding | Candidate; onSimulate?: () => void }) {
  return <div className="setup-body company-details"><h3>{company.name}</h3><p>{displayTicker(company.ticker)} · {company.exchange}</p><div className="company-key-metrics"><article><span>Expected return</span><strong>{percent(company.expectedReturn)}</strong><small>Annual expected return</small></article><article><span>E-score</span><strong>{score(company.eScore)}</strong><small>Environmental performance</small></article></div><p>Review environmental performance alongside expected return.</p>{onSimulate && <Button onClick={onSimulate}>Simulate investment <ArrowRight /></Button>}</div>;
}
function Methodology() {
  const items = [
    ["E-score", "E-score describes a company's environmental performance. A higher score indicates stronger environmental performance."],
    ["Expected return", "Expected return is expressed as an annual percentage. Evaluate it alongside environmental performance and portfolio risk."],
    ["Preferences", "Risk tolerance and green preference use levels 1–5. Level 5 means higher risk tolerance or a stronger green preference. Set your maximum investment amount in Settings."],
    ["Portfolio assessment", "Holding weights are based on current market value. Portfolio return and green score combine the available company metrics using these weights. Missing metrics are shown as unavailable."],
    ["Simulation", "Add new money, or reduce selected holdings and optionally add money. Compare the old and new portfolios before considering a change."],
    ["Data & privacy", "Upload current market values in a CSV file. Holdings, settings and simulation drafts are saved in this browser. Use Clear portfolio to remove your holdings."],
  ];
  return <div className="workspace-page"><div className="workspace-heading"><div><span className="workspace-eyebrow">METHODOLOGY</span><h1>Understand the numbers.</h1><p>Environmental performance, expected return and risk have distinct meanings.</p></div></div><div className="methodology-grid">{items.map(([title, text]) => <article className="workspace-panel" key={title}><span><Compass /></span><h2>{title}</h2><p>{text}</p></article>)}</div></div>;
}

export default function Workbench({ entry, onHome }: { entry: "demo" | "resume"; onHome: () => void }) {
  const [state, setState] = useState<State>(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) ?? "null");
      if (saved && saved.risk >= 1 && saved.risk <= 5 && saved.green >= 1 && saved.green <= 5) {
        return { ...initialState, ...saved, maxInvestment: Number.isFinite(saved.maxInvestment) && saved.maxInvestment > 0 ? saved.maxInvestment : initialState.maxInvestment };
      }
    } catch { /* Start fresh when storage is unavailable. */ }
    return entry === "demo" ? { ...initialState, portfolio: samplePortfolio() } : initialState;
  });
  const [view, setView] = useState<View>("overview");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState<ExportFormat>("csv");
  const [simulationOpen, setSimulationOpen] = useState(false);
  const [detail, setDetail] = useState<Holding | Candidate | null>(null), [error, setError] = useState(""), [query, setQuery] = useState("");
  const [notice, setNotice] = useState("");
  const comparisonRef = useRef<HTMLElement>(null);
  const simulationHeadingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => { try { localStorage.setItem(storageKey, JSON.stringify(state)); } catch { /* The workflow also works without persistence. */ } }, [state]);
  useEffect(() => { if (!notice) return; const id = window.setTimeout(() => setNotice(""), 4000); return () => window.clearTimeout(id); }, [notice]);
  useEffect(() => { if (view === "recommendations" && simulationOpen) simulationHeadingRef.current?.focus(); }, [view, simulationOpen]);
  const p = state.portfolio;
  const currency = p?.baseCurrency ?? "HKD";
  const selected = candidates.find(c => c.id === state.selectedId) ?? candidates[0];
  const amount = state.inputMode === "units" ? Number(state.amount) * selected.demoPrice : Number(state.amount);
  const updateDraft = (fields: Partial<State>) => { setState(s => ({ ...s, ...fields, result: null })); setError(""); };
  const go = (next: View) => { setView(next); setError(""); window.scrollTo(0, 0); };
  const select = (c: Candidate) => { updateDraft({ selectedId: c.id }); setDetail(null); setSimulationOpen(true); go("recommendations"); };
  const load = (portfolio: Portfolio) => {
    setState(s => ({ ...initialState, risk: s.risk, green: s.green, maxInvestment: s.maxInvestment, portfolio }));
    setUploadOpen(false); setSimulationOpen(false); go("overview"); setNotice("Current portfolio updated.");
  };
  const runSimulation = () => {
    if (!p) return;
    try {
      if (state.inputMode === "units" && (!Number.isInteger(Number(state.amount)) || Number(state.amount) <= 0)) throw new Error("Enter a positive whole number of units.");
      const result = simulate(p, selected, amount, state.funding, state.sales, state.funding === "rebalance" ? Number(state.additional || 0) : 0, state.maxInvestment);
      setState(s => ({ ...s, result })); setError(""); setNotice("Portfolio comparison updated.");
      window.requestAnimationFrame(() => {
        comparisonRef.current?.focus({ preventScroll: true });
        if (window.matchMedia("(max-width: 1180px)").matches) comparisonRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch (e) { setError((e as Error).message); }
  };
  const filteredCandidates = candidates.filter(c => `${c.name} ${displayTicker(c.ticker)}`.toLowerCase().includes(query.toLowerCase()));
  const exportPortfolio = (kind: ExportKind) => {
    if (!p || !state.result) return;
    const file = createPortfolioExport(kind, exportFormat, p, state.result, { riskLevel: state.risk, greenPreference: state.green, maxInvestment: state.maxInvestment });
    download(file.name, file.content, file.mimeType);
    setNotice(kind === "recommended" ? "Recommended portfolio exported." : "Portfolio comparison exported.");
  };
  return <div className="workbench">
    <aside className="app-sidebar">
      <Brand onHome={onHome} /><span className="nav-label">ANALYSIS WORKSPACE</span>
      <nav aria-label="Workspace navigation">{nav.map(([id, Icon, label]) => <button key={id} aria-label={label} aria-current={view === id ? "page" : undefined} className={view === id ? "active" : ""} onClick={() => go(id)} disabled={!p && id === "recommendations"}><Icon size={20} />{label}</button>)}</nav>
      <button className={`sidebar-settings ${view === "settings" ? "active" : ""}`} aria-label="Settings" aria-current={view === "settings" ? "page" : undefined} onClick={() => go("settings")}><span className="settings-link-title"><GearSix size={21} />Settings<ArrowRight size={16} /></span><span className="settings-link-summary">Risk {state.risk} · Green {state.green}</span><span className="settings-link-budget">Max. {money(state.maxInvestment, currency)}</span></button>
      <button className="back-landing" onClick={onHome}><Leaf />Back to website</button>
    </aside>
    <div className="app-main">
      <header className="app-topbar"><span className="breadcrumb">Workspace / {view === "settings" ? "Settings" : nav.find(n => n[0] === view)?.[2]}</span><span className="workspace-title">Green Street</span></header>
      <main>
        {view === "overview" && <div className="workspace-page">
          <div className="workspace-heading portfolio-heading"><div><span className="workspace-eyebrow">PORTFOLIO ASSESSMENT</span><h1>Current portfolio</h1><p>Manage your holdings and review their financial and environmental performance.</p></div><Button onClick={() => setUploadOpen(true)}><FileArrowUp size={20} />Upload portfolio</Button></div>
          {p ? <><MetricCards portfolio={p} /><div className="analysis-meta"><span>{p.holdings.length} assets · {money(totalValue(p), currency)}</span><span>E-score coverage {percent(metrics(p).greenScore.coverage, 0)}</span><RiskBadge value={state.risk} /><span>Green preference · Level {state.green}</span></div><HoldingsTable portfolio={p} onDetail={setDetail} /><div className="workspace-actions"><Button onClick={() => { setSimulationOpen(false); go("recommendations"); }}>View recommendations <ArrowRight /></Button><Button kind="ghost" onClick={() => download("green-street-portfolio.json", JSON.stringify(p, null, 2), "application/json")}>Export portfolio</Button><Button kind="ghost" onClick={() => { setState(s => ({ ...initialState, risk: s.risk, green: s.green, maxInvestment: s.maxInvestment })); setSimulationOpen(false); setNotice("Portfolio and simulation removed from this browser."); }}>Clear portfolio</Button></div></> : <section className="workspace-panel empty-workspace"><FileArrowUp size={44} /><h2>Bring your holdings together.</h2><p>Use Upload portfolio above to add a CSV file and start reviewing your investments.</p><div className="empty-file-hint">CSV · Equities, funds and cash · Up to 10 MB</div></section>}
        </div>}
        {p && view === "recommendations" && <div className="workspace-page">
          <div className="workspace-heading recommendations-heading"><div><span className="workspace-eyebrow">RECOMMENDATIONS</span><h1>{simulationOpen ? "Simulate an investment." : "Explore a potential investment."}</h1><p>{simulationOpen ? "Choose an amount and funding source, then compare your old and new portfolios." : "Explore candidates with your current holdings and investment preferences."}</p></div><div className="recommendation-heading-actions">{simulationOpen ? <Button kind="secondary" onClick={() => { setSimulationOpen(false); setError(""); }}><ArrowLeft />All recommendations</Button> : <label className="workspace-search"><MagnifyingGlass size={18} /><input aria-label="Search recommendations" placeholder="Search company or ticker" value={query} onChange={e => setQuery(e.target.value)} /></label>}<Button onClick={() => setExportOpen(true)}><DownloadSimple size={18} />Export portfolio</Button></div></div>
          <div className="recommendation-summary"><RiskBadge value={state.risk} /><span>Green preference · Level {state.green}</span><span>Maximum investment · {money(state.maxInvestment, currency)}</span><button onClick={() => go("settings")}>Edit settings</button></div>
          {!simulationOpen ? <><div className="recommendation-grid">{filteredCandidates.map(c => <article className="recommendation-card" key={c.id}><div className="rec-company"><i style={{ background: c.color }}>{displayTicker(c.ticker).slice(0, 2)}</i><div><h2>{c.name}</h2><p>{displayTicker(c.ticker)} · {c.exchange}</p></div></div><div className="rec-metrics"><span>Expected return<strong>{percent(c.expectedReturn)}</strong><small>Annual expected return</small></span><span>E-score<strong>{score(c.eScore)}</strong><small>Environmental performance</small></span></div><Button onClick={() => select(c)}>Simulate {displayTicker(c.ticker)} <ArrowRight /></Button><Button kind="ghost" onClick={() => setDetail(c)}>Company details</Button></article>)}</div>{!filteredCandidates.length && <p role="status">No matching companies. Try another name or ticker.</p>}</> : <div className="simulator-grid">
            <section className="workspace-panel simulation-input" aria-labelledby="simulation-heading">
              <h2 id="simulation-heading" ref={simulationHeadingRef} tabIndex={-1}>Investment simulator</h2>
              <label className="selection-label">Selected stock<select aria-label="Selected stock" value={selected.id} onChange={e => updateDraft({ selectedId: e.target.value })}>{candidates.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
              <div className="rec-company"><i style={{ background: selected.color }}>{displayTicker(selected.ticker).slice(0, 2)}</i><div><h2>{selected.name}</h2><p>{displayTicker(selected.ticker)} · {selected.exchange}</p></div></div>
              <fieldset className="funding-options"><legend>Funding source</legend><label><input type="radio" name="funding" checked={state.funding === "new_money"} onChange={() => updateDraft({ funding: "new_money" })} />Add new money</label><label><input type="radio" name="funding" checked={state.funding === "rebalance"} onChange={() => updateDraft({ funding: "rebalance" })} />Rebalance existing holdings</label></fieldset>
              <div className="input-mode"><button aria-pressed={state.inputMode === "amount"} onClick={() => updateDraft({ inputMode: "amount", amount: String(Math.min(10000, state.maxInvestment)) })}>Amount</button><button aria-pressed={state.inputMode === "units"} disabled={!p.isDemo} onClick={() => updateDraft({ inputMode: "units", amount: String(Math.min(10, Math.floor(state.maxInvestment / selected.demoPrice))) })}>Units</button></div>
              <label className="investment-amount">{state.inputMode === "amount" ? `Investment amount (${currency})` : "Number of units"}<input aria-label="Investment amount" type="number" min={state.inputMode === "units" ? "1" : "0.01"} max={state.inputMode === "units" ? Math.floor(state.maxInvestment / selected.demoPrice) : state.maxInvestment} step={state.inputMode === "units" ? "1" : "0.01"} value={state.amount} onChange={e => updateDraft({ amount: e.target.value })} /></label>
              <p className="investment-limit">Maximum investment: <strong>{money(state.maxInvestment, currency)}</strong><button onClick={() => go("settings")}>Change</button></p>
              {state.inputMode === "units" && <p className="simulation-help">{money(selected.demoPrice, currency)} per unit · total {money(Number.isFinite(amount) ? amount : 0, currency)}</p>}
              {state.funding === "rebalance" && <div className="sale-inputs"><h3>Choose amounts to release</h3>{p.holdings.map(h => <label key={h.id}><span>{h.name}<small>Available {money(h.value, currency)}</small></span><input aria-label={`Sell ${h.name}`} type="number" min="0" max={h.value} step="0.01" value={state.sales[h.id] ?? ""} placeholder="0" onChange={e => updateDraft({ sales: { ...state.sales, [h.id]: e.target.value } })} /></label>)}<label><span>Additional money ({currency})</span><input aria-label="Additional money" type="number" min="0" step="0.01" value={state.additional} onChange={e => updateDraft({ additional: e.target.value })} /></label><p className="simulation-help">Sales plus additional money must equal your investment amount.</p></div>}
              {error && <p className="form-error" role="alert">{error}</p>}
              <Button onClick={runSimulation}>Simulate investment <ArrowRight /></Button>
            </section>
            <section ref={comparisonRef} tabIndex={-1} className="workspace-panel comparison-panel" aria-labelledby="comparison-heading">
              <div className="panel-heading"><div><span className="comparison-kicker">PORTFOLIO COMPARISON</span><h2 id="comparison-heading">Old portfolio vs. new portfolio</h2><p>{state.result ? "Review the impact of your proposed investment." : "Run a simulation to compare portfolios."}</p></div></div>
              {state.result ? <><Comparison baseline={p} result={state.result} /><Button kind="ghost" onClick={() => updateDraft({ result: null })}>Reset comparison</Button></> : <div className="comparison-empty"><ArrowsLeftRight size={35} /><h3>See how your portfolio could change.</h3><p>Compare expected return, green score, total value and holding weights after your investment.</p></div>}
            </section>
          </div>}
        </div>}
        {view === "settings" && <Settings risk={state.risk} green={state.green} maxInvestment={state.maxInvestment} currency={currency} onSave={(risk, green, maxInvestment) => { setState(s => ({ ...s, risk, green, maxInvestment, result: null })); setNotice("Settings saved."); }} />}
        {view === "method" && <Methodology />}
      </main>
    </div>
    {uploadOpen && <Dialog title="Upload portfolio" onClose={() => setUploadOpen(false)}><ImportFlow onImport={load} /></Dialog>}
    {exportOpen && <Dialog title="Export portfolio" onClose={() => setExportOpen(false)}><div className="export-body">
      <p>Download your recommended portfolio or the full old vs. new comparison.</p>
      <label className="export-format">File format<select aria-label="Export format" value={exportFormat} onChange={e => setExportFormat(e.target.value as ExportFormat)}><option value="csv">CSV · Spreadsheet</option><option value="json">JSON · Structured data</option></select></label>
      {!state.result && <p className="export-empty">Run an investment simulation to generate a portfolio and comparison for export.</p>}
      <div className="export-options">
        <section><span className="export-icon"><SquaresFour size={24} /></span><h3>Recommended portfolio</h3><p>New holdings, investment values, weights and portfolio metrics.</p><Button disabled={!state.result} onClick={() => exportPortfolio("recommended")}><DownloadSimple size={18} />Export recommended portfolio</Button></section>
        <section><span className="export-icon"><ArrowsLeftRight size={24} /></span><h3>Portfolio comparison</h3><p>Old and new holdings, metrics and the changes between both portfolios.</p><Button disabled={!state.result} onClick={() => exportPortfolio("comparison")}><DownloadSimple size={18} />Export portfolio comparison</Button></section>
      </div>
    </div></Dialog>}
    {detail && <Dialog title="Company details" onClose={() => setDetail(null)}><CompanyDetails company={detail} onSimulate={"demoPrice" in detail ? () => select(detail) : undefined} /></Dialog>}
    {notice && <div className="toast" role="status"><CheckCircle size={18} />{notice}</div>}
  </div>;
}

function Comparison({ baseline, result }: { baseline: Portfolio; result: Portfolio }) {
  const before = metrics(baseline), after = metrics(result);
  const change = (a: number | null, b: number | null, percentUnit: boolean) => a === null || b === null ? "Unavailable" : `${b - a >= 0 ? "+" : ""}${((b - a) * (percentUnit ? 100 : 1)).toFixed(percentUnit ? 3 : 2)} ${percentUnit ? "pp" : "points"}`;
  const rows = [
    ["Portfolio value", money(totalValue(baseline), baseline.baseCurrency), money(totalValue(result), result.baseCurrency), money(totalValue(result) - totalValue(baseline), result.baseCurrency)],
    ["Expected return · annual", percent(before.expectedReturn.value, 3), percent(after.expectedReturn.value, 3), change(before.expectedReturn.value, after.expectedReturn.value, true)],
    ["Portfolio green score", score(before.greenScore.value), score(after.greenScore.value), change(before.greenScore.value, after.greenScore.value, false)],
    ["Portfolio volatility", "Unavailable", "Unavailable", "Unavailable"],
    ["E-score coverage", percent(before.greenScore.coverage, 1), percent(after.greenScore.coverage, 1), change(before.greenScore.coverage, after.greenScore.coverage, true)],
  ];
  return <><p className="table-scroll-hint">Swipe the tables to see the full comparison →</p><div className="table-scroll"><table className="comparison-table"><thead><tr><th>Metric</th><th>Old portfolio</th><th>New portfolio</th><th>Change</th></tr></thead><tbody>{rows.map(row => <tr key={row[0]}>{row.map((v, i) => i === 0 ? <th key={i} scope="row">{v}</th> : <td key={i}>{v}</td>)}</tr>)}</tbody></table></div><div className="table-scroll"><table className="comparison-table"><caption>Holding weights</caption><thead><tr><th>Asset</th><th>Old portfolio</th><th>New portfolio</th></tr></thead><tbody>{[...new Set([...baseline.holdings, ...result.holdings].map(h => h.id))].map(id => { const a = baseline.holdings.find(h => h.id === id), b = result.holdings.find(h => h.id === id); return <tr key={id}><th scope="row">{b?.name ?? a?.name}</th><td>{percent((a?.value ?? 0) / totalValue(baseline), 1)}</td><td>{percent((b?.value ?? 0) / totalValue(result), 1)}</td></tr>; })}</tbody></table></div></>;
}
