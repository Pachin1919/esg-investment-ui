import { useEffect, useMemo, useState } from "react";
import { ArrowRight, ArrowsLeftRight, CheckCircle, DownloadSimple, FileArrowUp, GearSix, Leaf, Sparkle, SquaresFour, WarningCircle } from "@phosphor-icons/react";
import { fetchCompanies, fetchFilterOptions, recommendPortfolio } from "./api";
import type { Recommendation, SectorOption } from "./api";
import Brand from "./Brand";
import Comparison from "./Comparison";
import { performanceCsv, positionsCsv, recommendedPositionsCsv } from "./comparisonExport";
import ImportFlow from "./ImportFlow";
import { holdingsRequest, lookupIn, marketOf, newCapital, recommendedPortfolio, samplePortfolio, withPrices } from "./live";
import type { Plan, Universe } from "./live";
import { HoldingsTable, MetricCards, UniverseSearch } from "./Overview";
import { download, money, totalValue } from "./portfolio";
import type { Portfolio } from "./portfolio";
import { createPortfolioExport } from "./portfolioExport";
import type { ExportFormat, ExportKind } from "./portfolioExport";
import RecommendationsBuilder from "./RecommendationsBuilder";
import Settings from "./Settings";
import { Button, Dialog, HighlightBadge, RiskBadge } from "./ui";

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
  const [uploadOpen, setUploadOpen] = useState(false), [exportOpen, setExportOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState<ExportFormat>("pdf"), [exportBusy, setExportBusy] = useState(false);
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

  const stored = state.portfolio, market = stored ? marketOf(stored) : "hk";
  useEffect(() => { let live = true; fetchFilterOptions(market).then(s => { if (live) setSectors(s); }); return () => { live = false; }; }, [market]);

  // One engine call serves both pages: `before` describes the current portfolio, the rest the recommendation.
  useEffect(() => {
    if (!stored) { setRec(null); return; }
    let live = true;
    setLoading(true); setRecError("");
    recommendPortfolio({ holdings: holdingsRequest(stored), risk_score: state.risk, green_score: state.green, market,
      max_new_capital: newCapital(stored, state.plan, state.maxInvestment),
      ...(state.plan.industries ? { filters: { include_industries: state.plan.industries } } : {}) }).then(res => {
      if (!live) return;
      if ("error" in res) { setRec(null); setRecError(res.error); } else setRec(res);
      setLoading(false);
    });
    return () => { live = false; };
  }, [stored, state.risk, state.green, state.maxInvestment, state.plan, market]);

  const p = useMemo(() => (stored ? withPrices(stored, rec) : null), [stored, rec]);
  const result = useMemo(() => (p && rec && universe ? recommendedPortfolio(p, rec, universe) : null), [p, rec, universe]);
  const currency = p?.baseCurrency ?? "HKD";
  const go = (next: View) => { setView(next); window.scrollTo(0, 0); };
  const load = (portfolio: Portfolio) => {
    setState(s => ({ ...s, portfolio, plan: initialState.plan }));
    setUploadOpen(false); go("overview"); setNotice("Current portfolio updated.");
  };
  const exportPortfolio = async (kind: ExportKind) => {
    if (!p || (!result && kind !== "current") || exportBusy) return;
    setExportBusy(true);
    try {
      const file = await createPortfolioExport(kind, kind === "current" ? "pdf" : exportFormat, p, kind === "current" ? p : result!, { riskLevel: state.risk, greenPreference: state.green, maxInvestment: state.maxInvestment });
      download(file.name, file.content, file.mimeType); setNotice(kind === "current" ? "Current portfolio exported." : kind === "recommended" ? "Recommended portfolio exported." : "Portfolio comparison exported.");
    } catch { setNotice("Could not generate the report. Please try again."); } finally { setExportBusy(false); }
  };
  // the three tables of the recommendation page, each as CSV
  const tableExports = p && result && rec && universe ? [
    { label: "Recommended positions", detail: "What to hold after the trades: action, shares, value and weight.", onExport: () => { download("recommended-positions.csv", recommendedPositionsCsv(rec, universe, currency)); setNotice("Recommended positions exported."); } },
    { label: "Portfolio performance", detail: "Old vs new key figures: risk, return, environment, concentration, factor exposures.", onExport: () => { download("portfolio-performance.csv", performanceCsv(p, result, rec)); setNotice("Portfolio performance exported."); } },
    { label: "Each company / share", detail: "Every position with old and new units, totals and weights.", onExport: () => { download("company-shares.csv", positionsCsv(rec, universe, currency)); setNotice("Company table exported."); } },
  ] : [];
  const status = engineDown ? <p className="engine-status error" role="alert"><WarningCircle size={16} />The analysis engine is not reachable. Scores and recommendations are unavailable.</p>
    : recError ? <p className="engine-status error" role="alert"><WarningCircle size={16} />{recError}</p> : null;

  return <div className={view === "recommendations" ? "workbench recommendation-workspace" : "workbench"}><aside className="app-sidebar"><Brand onHome={onHome} />{view !== "recommendations" && <span className="nav-label">ANALYSIS WORKSPACE</span>}<nav aria-label="Workspace navigation">{nav.map(([id, Icon, label]) => <button key={id} aria-label={label} aria-current={view === id ? "page" : undefined} className={view === id ? "active" : ""} onClick={() => go(id)} disabled={!p && id === "recommendations"}><Icon size={20} />{label}</button>)}</nav><button className="back-landing" onClick={onHome}><Leaf />Back to website</button></aside>
    <div className="app-main"><main>
      {view === "overview" && <div className="workspace-page"><div className="workspace-heading portfolio-heading"><div><span className="workspace-eyebrow">PORTFOLIO ASSESSMENT</span><h1>Current portfolio</h1><p>Manage your holdings and review their financial and environmental performance.</p></div><Button onClick={() => setUploadOpen(true)} disabled={!universe}><FileArrowUp size={20} />Upload portfolio</Button></div>
        {status}
        {p ? <><MetricCards portfolio={p} stats={rec?.before ?? null} /><div className="analysis-meta"><HighlightBadge variant="assets">{p.holdings.length} assets · {money(totalValue(p), currency)}</HighlightBadge><RiskBadge value={state.risk} /><HighlightBadge variant="green">Green preference · Level {state.green}</HighlightBadge></div><HoldingsTable portfolio={p} />
          <div className="workspace-actions"><Button onClick={() => go("recommendations")}>View recommendations <ArrowRight /></Button><Button kind="ghost" disabled={exportBusy} onClick={() => void exportPortfolio("current")}>Export portfolio</Button><Button kind="ghost" onClick={() => { setState(s => ({ ...s, portfolio: null, plan: initialState.plan })); setNotice("Portfolio removed from this browser."); }}>Clear portfolio</Button></div></>
          : <section className="workspace-panel empty-workspace"><FileArrowUp size={44} /><h2>Bring your holdings together.</h2><p>Use Upload portfolio above to add a CSV file and start reviewing your investments.</p><div className="empty-file-hint">CSV · Ticker, current value and currency · Up to 10 MB</div></section>}
        {universe && <UniverseSearch universe={universe} portfolio={p} />}
      </div>}
      {p && universe && view === "recommendations" && <div className="workspace-page recommendations-page">
        <div className="workspace-heading recommendations-heading"><div><span className="workspace-eyebrow">RECOMMENDATIONS</span><h1>Build your recommended portfolio.</h1><p>Choose your industries. The engine balances risk, greenness and trading cost.</p></div></div>
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
    {uploadOpen && universe && <Dialog title="Upload portfolio" onClose={() => setUploadOpen(false)}><ImportFlow lookup={lookupIn(universe)} onImport={load} /></Dialog>}
    {exportOpen && <Dialog title="Export portfolio" onClose={() => setExportOpen(false)}><div className="export-body"><p>Download a formatted portfolio report with share prices, whole units and total values.</p><label className="export-format">File format<select aria-label="Export format" value={exportFormat} onChange={e => setExportFormat(e.target.value as ExportFormat)}><option value="pdf">PDF · Portfolio report</option><option value="json">JSON · Structured data</option></select></label>{!result && <p className="export-empty">Generate recommendations to export your portfolio.</p>}<div className="export-options"><section><span className="export-icon"><SquaresFour size={24} /></span><h3>Recommended portfolio</h3><p>Share prices, units, totals, environmental scores and explanations.</p><Button disabled={!result || exportBusy} onClick={() => void exportPortfolio("recommended")}><DownloadSimple size={18} />{exportBusy ? "Preparing report…" : "Export recommended portfolio"}</Button></section><section><span className="export-icon"><ArrowsLeftRight size={24} /></span><h3>Portfolio comparison</h3><p>Old and new holdings, share quantities and performance changes.</p><Button disabled={!result || exportBusy} onClick={() => void exportPortfolio("comparison")}><DownloadSimple size={18} />{exportBusy ? "Preparing report…" : "Export portfolio comparison"}</Button></section>
      <section className="export-tables"><span className="export-icon"><DownloadSimple size={24} /></span><h3>Tables · CSV</h3><p>The raw tables from this page, for a spreadsheet. Not affected by the file format above.</p><div className="export-table-list">{tableExports.map(t => <div key={t.label}><div><strong>{t.label}</strong><small>{t.detail}</small></div><Button kind="secondary" onClick={t.onExport}><DownloadSimple size={16} />CSV</Button></div>)}</div></section></div></div></Dialog>}
    {notice && <div className="toast" role="status"><CheckCircle size={18} />{notice}</div>}
  </div>;
}
