import { useEffect, useMemo, useState } from "react";
import { ArrowRight, ArrowsLeftRight, CheckCircle, DownloadSimple, FileArrowUp, GearSix, Info, Leaf, Sparkle, SquaresFour, WarningCircle } from "@phosphor-icons/react";
import { fetchCompanies, fetchFilterOptions, recommendPortfolio } from "./api";
import type { Recommendation, SectorOption } from "./api";
import Brand from "./Brand";
import Comparison from "./Comparison";
import ImportFlow from "./ImportFlow";
import { holdingsRequest, lookupIn, POOLED_MARKET, newCapital, recommendedPortfolio, samplePortfolio, withPrices } from "./live";
import type { Plan, Universe } from "./live";
import { HoldingsTable, MetricCards, UniverseSearch } from "./Overview";
import { download, money, totalValue } from "./portfolio";
import type { Portfolio } from "./portfolio";
import { createPortfolioExport } from "./portfolioExport";
import { exportTables, renderTable, TABLE_FORMATS } from "./tableExport";
import type { ExportTable, TableFormat } from "./tableExport";
import RecommendationsBuilder from "./RecommendationsBuilder";
import Settings from "./Settings";
import { Button, Dialog, HighlightBadge, RiskBadge } from "./ui";
import AnalysisDrawer from "./explainability/AnalysisDrawer";
import type { AnalysisInput, AnalysisSnapshot } from "./explainability/AnalysisDrawer";
import explanationStyles from "./explainability/AnalysisDrawer.module.css";

type View = "overview" | "recommendations" | "settings";
type State = { version: 3; portfolio: Portfolio | null; risk: number; green: number; maxInvestment: number; plan: Plan };
const initialState: State = { version: 3, portfolio: null, risk: 3, green: 4, maxInvestment: 100000, plan: { industries: null, tolerancePercent: 0 } };
const storageKey = "green-street-workspace-v3";
const nav = [["overview", SquaresFour, "Current portfolio"], ["recommendations", Sparkle, "Recommendations"], ["settings", GearSix, "Settings"]] as const;

function restore(): State | null {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) ?? "null");
    return saved?.version === 3 && saved.risk >= 1 && saved.risk <= 5 && saved.green >= 1 && saved.green <= 5 ? { ...initialState, ...saved } : null;
  } catch { return null; /* Start fresh when storage is unavailable. */ }
}

export default function Workbench({ entry, onHome }: { entry: "demo" | "resume" | "settings"; onHome: () => void }) {
  const [state, setState] = useState<State>(() => restore() ?? initialState);
  const [view, setView] = useState<View>(entry === "settings" ? "settings" : "overview");
  const [universe, setUniverse] = useState<Universe | null>(null), [engineDown, setEngineDown] = useState(false);
  const [sectors, setSectors] = useState<SectorOption[]>([]);
  const [rec, setRec] = useState<Recommendation | null>(null), [loading, setLoading] = useState(false), [recError, setRecError] = useState("");
  const [analysisOpen, setAnalysisOpen] = useState(false);
  const [analysisSnapshot, setAnalysisSnapshot] = useState<AnalysisSnapshot | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false), [exportOpen, setExportOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState<TableFormat>("pdf"), [exportBusy, setExportBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [recTab, setRecTab] = useState<"builder" | "comparison">("builder");
  useEffect(() => { try { localStorage.setItem(storageKey, JSON.stringify(state)); } catch { /* Continue without persistence. */ } }, [state]);
  useEffect(() => { if (!notice) return; const id = window.setTimeout(() => setNotice(""), 4000); return () => window.clearTimeout(id); }, [notice]);

  // The scored universe; the demo entry starts from a sample of real companies.
  useEffect(() => {
    let live = true;
    fetchCompanies("all").then(list => {
      if (!live) return;
      if (!list?.length) { setEngineDown(true); return; }
      const u: Universe = new Map(list.map(c => [c.ticker, c]));
      setUniverse(u);
      if (entry === "demo") setState(s => (s.portfolio ? s : { ...s, portfolio: samplePortfolio(u) }));
    });
    return () => { live = false; };
  }, [entry]);

  const stored = state.portfolio, market = POOLED_MARKET;
  const analysisInput = useMemo<AnalysisInput | null>(() => stored ? {
    request: { holdings: holdingsRequest(stored), risk_score: state.risk, green_score: state.green, market,
      max_new_capital: newCapital(stored, state.plan, state.maxInvestment),
      ...(state.plan.industries ? { filters: { include_industries: state.plan.industries } } : {}) },
    currency: stored.baseCurrency,
    cashValue: stored.holdings.filter(h => h.assetClass.toLowerCase() === "cash").reduce((sum, h) => sum + h.value, 0),
  } : null, [stored, state.risk, state.green, state.maxInvestment, state.plan, market]);
  useEffect(() => { let live = true; fetchFilterOptions(market).then(s => { if (live) setSectors(s); }); return () => { live = false; }; }, [market]);

  // One engine call serves both pages: `before` describes the current portfolio, the rest the recommendation.
  useEffect(() => {
    if (!analysisInput) { setRec(null); setAnalysisSnapshot(null); return; }
    let live = true;
    setLoading(true); setRecError("");
    setAnalysisSnapshot({ input: analysisInput, status: "waiting" });
    recommendPortfolio(analysisInput.request).then(res => {
      if (!live) return;
      if ("error" in res) {
        setRec(null); setRecError(res.error);
        setAnalysisSnapshot({ input: analysisInput, status: "error", error: res.error });
      } else {
        setRec(res);
        setAnalysisSnapshot({ input: analysisInput, status: "completed", result: res });
      }
      setLoading(false);
    });
    return () => { live = false; };
  }, [analysisInput]);

  const p = useMemo(() => (stored ? withPrices(stored, rec) : null), [stored, rec]);
  const result = useMemo(() => (p && rec && universe ? recommendedPortfolio(p, rec, universe) : null), [p, rec, universe]);
  const currency = p?.baseCurrency ?? "HKD";
  const go = (next: View) => { setView(next); window.scrollTo(0, 0); };
  const load = (portfolio: Portfolio) => {
    setState(s => ({ ...s, portfolio, plan: initialState.plan }));
    setUploadOpen(false); go("overview"); setNotice("Current portfolio updated.");
  };
  const exportCurrent = async () => {
    if (!p || exportBusy) return;
    setExportBusy(true);
    try {
      const file = await createPortfolioExport("current", "pdf", p, p, { riskLevel: state.risk, greenPreference: state.green, maxInvestment: state.maxInvestment });
      download(file.name, file.content, file.mimeType); setNotice("Current portfolio exported.");
    } catch { setNotice("Could not generate the report. Please try again."); } finally { setExportBusy(false); }
  };
  // the three tables of the recommendation page, each in the format picked in the dialog
  const tables = useMemo(() => (p && result && rec && universe ? exportTables(p, result, rec, universe) : []), [p, result, rec, universe]);
  const exportTable = async (table: ExportTable) => {
    if (exportBusy || !p) return;
    setExportBusy(true);
    try {
      const context = `Valuation: ${p.asOf}  |  Currency: ${currency}  |  Risk level ${state.risk}  |  Green preference ${state.green}  |  Maximum investment ${money(state.maxInvestment, currency)}`;
      const file = await renderTable(table, exportFormat, context);
      download(file.name, file.content, file.mimeType); setNotice(`${table.title} exported.`);
    } catch { setNotice("Could not generate the file. Please try again."); } finally { setExportBusy(false); }
  };
  const status = engineDown ? <p className="engine-status error" role="alert"><WarningCircle size={16} />The analysis engine is not reachable. Scores and recommendations are unavailable.</p>
    : recError ? <p className="engine-status error" role="alert"><WarningCircle size={16} />{recError}</p> : null;

  return <div className={view === "recommendations" ? "workbench recommendation-workspace" : "workbench"}><aside className="app-sidebar"><Brand onHome={onHome} />{view !== "recommendations" && <span className="nav-label">ANALYSIS WORKSPACE</span>}<nav aria-label="Workspace navigation">{nav.map(([id, Icon, label]) => <button key={id} aria-label={label} aria-current={view === id ? "page" : undefined} className={view === id ? "active" : ""} onClick={() => go(id)} disabled={!p && id === "recommendations"}><Icon size={20} />{label}</button>)}</nav><button className="back-landing" onClick={onHome}><Leaf />Back to website</button></aside>
    <div className="app-main"><main>
      {view === "overview" && <div className="workspace-page"><div className="workspace-heading portfolio-heading"><div><span className="workspace-eyebrow">PORTFOLIO ASSESSMENT</span><h1>Current portfolio</h1><p>Manage your holdings and review their financial and environmental performance.</p></div><Button onClick={() => setUploadOpen(true)} disabled={!universe}><FileArrowUp size={20} />Upload portfolio</Button></div>
        {status}
        {p ? <><MetricCards portfolio={p} stats={rec?.before ?? null} /><div className="analysis-meta"><HighlightBadge variant="assets">{p.holdings.length} assets · {money(totalValue(p), currency)}</HighlightBadge><RiskBadge value={state.risk} /><HighlightBadge variant="green">Green preference · Level {state.green}</HighlightBadge></div><HoldingsTable portfolio={p} />
          <div className="workspace-actions"><Button onClick={() => go("recommendations")}>View recommendations <ArrowRight /></Button><Button kind="ghost" disabled={exportBusy} onClick={() => void exportCurrent()}>Export portfolio</Button><Button kind="ghost" onClick={() => { setState(s => ({ ...s, portfolio: null, plan: initialState.plan })); setNotice("Portfolio removed from this browser."); }}>Clear portfolio</Button></div></>
          : <section className="workspace-panel empty-workspace"><FileArrowUp size={44} /><h2>Bring your holdings together.</h2><p>Use Upload portfolio above to add a CSV file and start reviewing your investments.</p><div className="empty-file-hint">CSV · Ticker, current value and currency · Up to 10 MB</div></section>}
        {universe && <UniverseSearch universe={universe} portfolio={p} />}
      </div>}
      {p && universe && view === "recommendations" && <div className="workspace-page recommendations-page">
        <div className="workspace-heading recommendations-heading"><div><span className="workspace-eyebrow">RECOMMENDATIONS</span><h1>Build your recommended portfolio.</h1><p>Choose your industries. The engine balances risk, greenness and trading cost.</p></div><button type="button" className={explanationStyles.entry} aria-haspopup="dialog" aria-expanded={analysisOpen} onClick={() => setAnalysisOpen(true)}><Info size={16} />Analysis details</button></div>
        <div className="recommendation-summary"><RiskBadge value={state.risk} /><HighlightBadge variant="green">Green preference · Level {state.green}</HighlightBadge><HighlightBadge variant="budget">Maximum investment · {money(state.maxInvestment, currency)}</HighlightBadge><button onClick={() => go("settings")}>Edit settings</button></div>
        <div className="view-tabs"><div role="tablist" aria-label="Recommendation views">
          <button role="tab" id="tab-builder" aria-selected={recTab === "builder"} aria-controls="panel-builder" onClick={() => setRecTab("builder")}><Sparkle size={17} />Recommended portfolio</button>
          <button role="tab" id="tab-comparison" aria-selected={recTab === "comparison"} aria-controls="panel-comparison" onClick={() => setRecTab("comparison")} disabled={!result || !rec}><ArrowsLeftRight size={17} />Compare with current portfolio</button>
          </div>
          <Button onClick={() => setExportOpen(true)}><DownloadSimple size={18} />Export portfolio</Button>
        </div>
        {/* the builder stays mounted so an unsaved setup survives a look at the tables */}
        <div role="tabpanel" id="panel-builder" aria-labelledby="tab-builder" hidden={recTab !== "builder"}>
          <RecommendationsBuilder key={stored ? stored.name + stored.holdings.length : ""} baseline={p} universe={universe} sectors={sectors} maximum={state.maxInvestment} plan={state.plan} rec={rec} portfolio={result} loading={loading} error={recError} onPlanChange={plan => setState(s => ({ ...s, plan }))} />
        </div>
        {recTab === "comparison" && result && rec && <section role="tabpanel" id="panel-comparison" aria-labelledby="tab-comparison" className="workspace-panel builder-comparison comparison-tab"><Comparison baseline={p} result={result} rec={rec} universe={universe} /></section>}
      </div>}
      {view === "settings" && <Settings risk={state.risk} green={state.green} maxInvestment={state.maxInvestment} currency={currency} onSave={(risk, green, maxInvestment) => { setState(s => ({ ...s, risk, green, maxInvestment })); setNotice("Settings saved."); }} />}
    </main></div>
    {analysisOpen && analysisInput && <AnalysisDrawer input={analysisInput} snapshot={analysisSnapshot} onClose={() => setAnalysisOpen(false)} />}
    {uploadOpen && universe && <Dialog title="Upload portfolio" onClose={() => setUploadOpen(false)}><ImportFlow lookup={lookupIn(universe)} onImport={load} /></Dialog>}
    {exportOpen && <Dialog title="Export portfolio" onClose={() => setExportOpen(false)}><div className="export-body"><p>Choose a file format, then the table to download.</p>
      <label className="export-format">File format<select aria-label="Export format" value={exportFormat} onChange={e => setExportFormat(e.target.value as TableFormat)}>{TABLE_FORMATS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}</select></label>
      {!tables.length && <p className="export-empty">Generate recommendations to export your portfolio.</p>}
      <div className="export-table-list">{tables.map(t => <div key={t.file}><div><strong>{t.title}</strong><small>{t.detail}</small></div><Button disabled={exportBusy} onClick={() => void exportTable(t)}><DownloadSimple size={16} />{exportBusy ? "Preparing…" : `Export ${exportFormat.toUpperCase()}`}</Button></div>)}</div>
    </div></Dialog>}
    {notice && <div className="toast" role="status"><CheckCircle size={18} />{notice}</div>}
  </div>;
}
