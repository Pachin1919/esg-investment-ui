import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { ArrowLeft, ArrowRight, ArrowsLeftRight, CheckCircle, DownloadSimple, FileArrowUp, Gauge, GearSix, Leaf, MagnifyingGlass, Sparkle, SquaresFour, X } from "@phosphor-icons/react";
import { candidates, displayTicker, download, greenExplanation, hydratePortfolio, importTemplate, metrics, money, normalizeImport, parsePortfolioImport, percent, recommendStocks, samplePortfolio, score, sharePrice, simulate, totalValue, unitMoney } from "./portfolio";
import type { Candidate, Holding, ParsedImport, Portfolio } from "./portfolio";
import { exchangeRate } from "./marketData";
import Brand from "./Brand";
import { CompanyInfo, InfoPopover, metricExplanations } from "./InfoPopover";
import { createPortfolioExport } from "./portfolioExport";
import type { ExportFormat, ExportKind } from "./portfolioExport";

type View = "overview" | "recommendations" | "settings";
type State = {
  calculationVersion:1;
  portfolio:Portfolio|null;risk:number;green:number;maxInvestment:number;
  selectedId:string;amount:string;inputMode:"amount"|"units";funding:"new_money"|"rebalance";
  additional:string;sales:Record<string,string>;result:Portfolio|null;
};
const initialState:State={calculationVersion:1,portfolio:null,risk:3,green:4,maxInvestment:100000,selectedId:candidates[0].id,amount:"10",inputMode:"units",funding:"new_money",additional:"0",sales:{},result:null};
const storageKey="verdant-analysis-v2";
const riskColors=["#287b53","#326bbb","#a97808","#be621e","#b13c46"];
const nav=[["overview",SquaresFour,"Current portfolio"],["recommendations",Sparkle,"Recommendations"],["settings",GearSix,"Settings"]] as const;
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
      const data = parsePortfolioImport(await file.text()); setParsed(data); setFileName(file.name);
      if (data.sourceCurrency) setBase(data.sourceCurrency);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not read this file."); }
    finally { setReading(false); if (input.current) input.current.value = ""; }
  }
  return <div className="setup-body import-body"><span className="setup-icon"><FileArrowUp /></span><h3>Import your current holdings.</h3><p>Use current market value, not original purchase cost. Broker exports with “Total Market Value (SEK)” are supported, including equities, funds and cash.</p>
    <input ref={input} type="file" accept=".csv,text/csv" aria-label="Portfolio CSV" className="sr-only" onChange={e => { void read(e.target.files?.[0]); }} />
    <Button kind="secondary" onClick={() => input.current?.click()} disabled={reading}><FileArrowUp />{reading ? "Reading CSV…" : parsed ? "Choose another CSV" : "Choose a CSV file"}</Button>
    <div className="import-format"><span>Required: ticker, current value, currency · Optional: units, unit_price</span><button onClick={() => download("green-street-portfolio-template.csv", importTemplate)}><DownloadSimple size={16} />Download template</button></div>
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



function MetricCards({portfolio}:{portfolio:Portfolio}) {
  const m=metrics(portfolio);
  const cards=[["Expected return","Expected return · annual",percent(m.expectedReturn.value),"Annual expected return",SquaresFour],["Portfolio green score","Portfolio green score",score(m.greenScore.value),"Environmental performance",Leaf],["Portfolio volatility","Portfolio volatility","Unavailable","Portfolio risk",Gauge]] as const;
  return <div className="workspace-metrics">{cards.map(([label,key,value,description,Icon])=><article className="workspace-metric" key={key}><div><InfoPopover label={label} content={<><strong>{label}</strong><p>{metricExplanations[key]}</p></>}>{label}</InfoPopover><Icon/></div><strong>{value}</strong><p>{description}</p></article>)}</div>;
}
function HoldingsTable({portfolio}:{portfolio:Portfolio}) {
  return <section className="workspace-panel"><div className="panel-heading"><div><h2>Current holdings</h2><p>Current market value · {portfolio.baseCurrency} · {portfolio.asOf}</p></div><strong>{money(totalValue(portfolio),portfolio.baseCurrency)}</strong></div><p className="table-scroll-hint">Scroll to see all holding details →</p><div className="table-scroll"><table className="analysis-table"><thead><tr><th>Company / asset</th><th>Unit price</th><th>Units</th><th>Total value</th><th>Weight</th><th>Annual return</th><th>E-score</th></tr></thead><tbody>{portfolio.holdings.map(h=><tr key={h.id}><td><div className="holding-company"><i style={{background:h.color}}>{displayTicker(h.ticker).slice(0,2)}</i><span><CompanyInfo company={h}/><small>{displayTicker(h.ticker)} · {h.assetClass}</small></span></div></td><td>{h.unitPrice==null?"Unavailable":unitMoney(h.unitPrice,portfolio.baseCurrency)}</td><td>{h.units??"Unavailable"}</td><td>{money(h.value,portfolio.baseCurrency)}</td><td>{percent(h.value/totalValue(portfolio),1)}</td><td>{percent(h.expectedReturn)}</td><td>{score(h.eScore)}</td></tr>)}</tbody></table></div></section>;
}
function CompanyDetails({company,onSimulate}:{company:Holding|Candidate;onSimulate?:()=>void}) {
  return <div className="setup-body company-details"><h3>{company.name}</h3><p>{displayTicker(company.ticker)} · {company.exchange}</p><div className="company-key-metrics"><article><span>Expected return</span><strong>{percent(company.expectedReturn)}</strong></article><article><span>E-score</span><strong>{score(company.eScore)}</strong></article></div><p>{greenExplanation(company)}</p><p>Share price: {company.unitPrice==null?"Unavailable":money(company.unitPrice,company.currency)}</p>{onSimulate&&<Button onClick={onSimulate}>Select company <ArrowRight/></Button>}</div>;
}
export default function Workbench({entry,onHome}:{entry:"demo"|"resume"|"settings";onHome:()=>void}) {
  const [state,setState]=useState<State>(()=>{
    try {
      const saved=JSON.parse(localStorage.getItem(storageKey)??"null");
      if(saved&&saved.risk>=1&&saved.risk<=5&&saved.green>=1&&saved.green<=5){
        return {...initialState,...saved,calculationVersion:1,portfolio:saved.portfolio?hydratePortfolio(saved.portfolio):null,result:saved.calculationVersion===1?saved.result:null,
          maxInvestment:Number.isFinite(saved.maxInvestment)&&saved.maxInvestment>0?saved.maxInvestment:initialState.maxInvestment};
      }
    }catch{/* Start fresh when storage is unavailable. */}
    return entry==="demo"?{...initialState,portfolio:samplePortfolio()}:initialState;
  });
  const [view,setView]=useState<View>(entry==="settings"?"settings":"overview");
  const [uploadOpen,setUploadOpen]=useState(false),[exportOpen,setExportOpen]=useState(false);
  const [exportFormat,setExportFormat]=useState<ExportFormat>("pdf"),[exportBusy,setExportBusy]=useState(false);
  const [simulationOpen,setSimulationOpen]=useState(false),[detail,setDetail]=useState<Candidate|null>(null);
  const [error,setError]=useState(""),[query,setQuery]=useState(""),[notice,setNotice]=useState("");
  const comparisonRef=useRef<HTMLElement>(null);
  const simulationHeadingRef=useRef<HTMLHeadingElement>(null);
  useEffect(()=>{try{localStorage.setItem(storageKey,JSON.stringify(state));}catch{/* Continue without persistence. */}},[state]);
  useEffect(()=>{if(!notice)return;const id=window.setTimeout(()=>setNotice(""),4000);return()=>window.clearTimeout(id);},[notice]);
  const p=state.portfolio,currency=p?.baseCurrency??"HKD";
  const recommended=recommendStocks(state.risk,state.green,state.maxInvestment,currency);
  const selected=recommended.find(c=>c.id===state.selectedId)??recommended[0]??null;
  const price=selected?sharePrice(selected,currency)!:0;
  const units=state.inputMode==="units"?Number(state.amount):price>0?Math.floor(Number(state.amount)/price):0;
  const amount=Math.round(price*units*100)/100;
  const unitsValid=Number.isSafeInteger(units)&&units>0;
  useEffect(()=>{if(selected&&selected.id!==state.selectedId)setState(s=>({...s,selectedId:selected.id,result:null}));},[selected?.id,state.selectedId]);
  useEffect(()=>{if(view==="recommendations"&&simulationOpen)simulationHeadingRef.current?.focus({preventScroll:true});},[view,simulationOpen]);
  const updateDraft=(fields:Partial<State>)=>{setState(s=>({...s,...fields,result:null}));setError("");};
  const go=(next:View)=>{setView(next);setError("");window.scrollTo(0,0);};
  const select=(c:Candidate)=>{
    const defaultUnits=Math.max(1,Math.min(10,Math.floor(state.maxInvestment/sharePrice(c,currency)!)));
    updateDraft({selectedId:c.id,inputMode:"units",amount:String(defaultUnits)});
    setDetail(null);setSimulationOpen(true);go("recommendations");
  };
  const load=(portfolio:Portfolio)=>{
    setState(s=>({...initialState,risk:s.risk,green:s.green,maxInvestment:Math.max(.01,Math.round(s.maxInvestment*exchangeRate(s.portfolio?.baseCurrency??"HKD",portfolio.baseCurrency)*100)/100),portfolio}));
    setUploadOpen(false);setSimulationOpen(false);go("overview");setNotice("Current portfolio updated.");
  };
  const runSimulation=()=>{
    if(!p||!selected)return;
    try {
      if(state.inputMode==="amount"&&(!Number.isFinite(Number(state.amount))||Number(state.amount)>state.maxInvestment))throw new Error("Investment budget exceeds your maximum. Update the amount or Settings.");
      const sales=Object.fromEntries(p.holdings.map(h=>{
        const value=Number(state.sales[h.id]||0);
        if(state.funding==="rebalance"&&h.units!=null&&!Number.isSafeInteger(value))throw new Error(`Sell a whole number of shares of ${h.name}.`);
        return [h.id,String(h.units!=null&&h.unitPrice?value*h.unitPrice:value)];
      }));
      const result=simulate(p,selected,units,state.funding,sales,state.funding==="rebalance"?Number(state.additional||0):0,state.maxInvestment);
      setState(s=>({...s,result}));setError("");setNotice("Portfolio comparison updated.");
      window.requestAnimationFrame(()=>{comparisonRef.current?.focus({preventScroll:true});if(window.matchMedia("(max-width: 1180px)").matches)comparisonRef.current?.scrollIntoView({behavior:"smooth",block:"start"});});
    }catch(e){setError((e as Error).message);}
  };
  const words=query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  const filtered=recommended.filter(c=>words.every(word=>`${c.name} ${displayTicker(c.ticker)} ${c.keywords}`.toLowerCase().includes(word)));
  const exportPortfolio=async(kind:ExportKind)=>{
    if(!p||(!state.result&&kind!=="current")||exportBusy)return;
    setExportBusy(true);
    try{
      const file=await createPortfolioExport(kind,kind==="current"?"pdf":exportFormat,p,kind==="current"?p:state.result!,{riskLevel:state.risk,greenPreference:state.green,maxInvestment:state.maxInvestment});
      download(file.name,file.content,file.mimeType);setNotice(kind==="current"?"Current portfolio exported.":kind==="recommended"?"Recommended portfolio exported.":"Portfolio comparison exported.");
    }catch{setNotice("Could not generate the report. Please try again.");}finally{setExportBusy(false);}
  };
  return <div className="workbench"><aside className="app-sidebar"><Brand onHome={onHome}/><span className="nav-label">ANALYSIS WORKSPACE</span><nav aria-label="Workspace navigation">{nav.map(([id,Icon,label])=><button key={id} aria-label={label} aria-current={view===id?"page":undefined} className={view===id?"active":""} onClick={()=>go(id)} disabled={!p&&id==="recommendations"}><Icon size={20}/>{label}</button>)}</nav><button className="back-landing" onClick={onHome}><Leaf/>Back to website</button></aside>
    <div className="app-main"><header className="app-topbar"><span className="breadcrumb">Workspace / {nav.find(n=>n[0]===view)?.[2]}</span><span className="workspace-title">Green Street</span></header><main>
      {view==="overview"&&<div className="workspace-page"><div className="workspace-heading portfolio-heading"><div><span className="workspace-eyebrow">PORTFOLIO ASSESSMENT</span><h1>Current portfolio</h1><p>Manage your holdings and review their financial and environmental performance.</p></div><Button onClick={()=>setUploadOpen(true)}><FileArrowUp size={20}/>Upload portfolio</Button></div>{p?<><MetricCards portfolio={p}/><div className="analysis-meta"><span>{p.holdings.length} assets · {money(totalValue(p),currency)}</span><RiskBadge value={state.risk}/><span>Green preference · Level {state.green}</span></div><HoldingsTable portfolio={p}/><div className="workspace-actions"><Button onClick={()=>{setSimulationOpen(false);go("recommendations");}}>View recommendations <ArrowRight/></Button><Button kind="ghost" disabled={exportBusy} onClick={()=>void exportPortfolio("current")}>Export portfolio</Button><Button kind="ghost" onClick={()=>{setState(s=>({...initialState,risk:s.risk,green:s.green,maxInvestment:Math.max(.01,Math.round(s.maxInvestment*exchangeRate(currency,"HKD")*100)/100)}));setSimulationOpen(false);setNotice("Portfolio removed from this browser.");}}>Clear portfolio</Button></div></>:<section className="workspace-panel empty-workspace"><FileArrowUp size={44}/><h2>Bring your holdings together.</h2><p>Use Upload portfolio above to add a CSV file and start reviewing your investments.</p><div className="empty-file-hint">CSV · Equities, funds and cash · Up to 10 MB</div></section>}</div>}
      {p&&view==="recommendations"&&<div className="workspace-page">
        <div className="workspace-heading recommendations-heading"><div><span className="workspace-eyebrow">RECOMMENDATIONS</span><h1>{simulationOpen?"Build your recommended portfolio.":"Explore a potential investment."}</h1><p>Companies selected for your risk tolerance, environmental priority and investment budget.</p></div><div className="recommendation-heading-actions">{simulationOpen&&<Button kind="secondary" onClick={()=>{setSimulationOpen(false);setError("");}}><ArrowLeft/>All recommendations</Button>}<Button onClick={()=>setExportOpen(true)}><DownloadSimple size={18}/>Export portfolio</Button></div></div>
        <div className="recommendation-summary"><RiskBadge value={state.risk}/><span>Green preference · Level {state.green}</span><span>Maximum investment · {money(state.maxInvestment,currency)}</span><button onClick={()=>go("settings")}>Edit settings</button></div>
        <section className="company-search-panel" aria-label="Search recommended companies"><label htmlFor="company-keyword">Find a recommended company</label><div className="company-search-row"><div className="company-keyword-input"><MagnifyingGlass size={21}/><input id="company-keyword" aria-label="Search recommendations" placeholder="Search company, ticker or keyword — e.g. solar, water, technology" value={query} onChange={e=>setQuery(e.target.value)}/>{query&&<button aria-label="Clear company search" onClick={()=>setQuery("")}><X size={17}/></button>}</div><span>{filtered.length} {filtered.length===1?"company":"companies"}</span></div></section>
        {!recommended.length&&<div className="workspace-panel no-recommendations"><h2>No companies match these settings.</h2><p>Adjust your risk tolerance, green preference or investment budget to explore more companies.</p><Button kind="secondary" onClick={()=>go("settings")}>Open settings</Button></div>}
        {recommended.length>0&&!filtered.length&&<p role="status">No matching recommended companies. Try another keyword.</p>}
        {simulationOpen&&query&&filtered.length>0&&<div className="company-search-results">{filtered.map(c=><button key={c.id} onClick={()=>select(c)} className={selected?.id===c.id?"selected":""}><span>{c.name}</span><small>{displayTicker(c.ticker)} · E-score {score(c.eScore)}</small></button>)}</div>}
        {!simulationOpen?<div className="recommendation-grid">{filtered.map(c=><article className="recommendation-card" key={c.id}><div className="rec-company"><i style={{background:c.color}}>{displayTicker(c.ticker)}</i><div><h2>{c.name}</h2><p>{displayTicker(c.ticker)} · {c.exchange}</p></div></div><p className="candidate-fit">Risk level {c.riskLevel} · Share price {money(sharePrice(c,currency)!,currency)}</p><div className="rec-metrics"><span>Expected return<strong>{percent(c.expectedReturn)}</strong></span><span>E-score<strong>{score(c.eScore)}</strong></span></div><Button onClick={()=>select(c)}>Select {displayTicker(c.ticker)} <ArrowRight/></Button><Button kind="ghost" onClick={()=>setDetail(c)}>Company details</Button></article>)}</div>:selected&&<div className="simulator-grid">
          <section className="workspace-panel simulation-input" aria-labelledby="simulation-heading"><h2 id="simulation-heading" ref={simulationHeadingRef} tabIndex={-1}>Investment simulator</h2>
            <label className="selection-label">Selected stock<select aria-label="Selected stock" value={selected.id} onChange={e=>{const c=recommended.find(c=>c.id===e.target.value);if(c)select(c);}}>{recommended.map(c=><option key={c.id} value={c.id}>{c.name} · Risk {c.riskLevel} · E-score {score(c.eScore)}</option>)}</select></label>
            <div className="rec-company"><i style={{background:selected.color}}>{displayTicker(selected.ticker)}</i><div><h2>{selected.name}</h2><p>{displayTicker(selected.ticker)} · {selected.exchange}</p></div></div>
            <fieldset className="funding-options"><legend>Funding source</legend><label><input type="radio" name="funding" checked={state.funding==="new_money"} onChange={()=>updateDraft({funding:"new_money"})}/>Add new money</label><label><input type="radio" name="funding" checked={state.funding==="rebalance"} onChange={()=>updateDraft({funding:"rebalance"})}/>Rebalance existing holdings</label></fieldset>
            <div className="input-mode"><button aria-pressed={state.inputMode==="units"} onClick={()=>updateDraft({inputMode:"units",amount:String(Math.max(1,Math.min(10,Math.floor(state.maxInvestment/price))))})}>Units</button><button aria-pressed={state.inputMode==="amount"} onClick={()=>updateDraft({inputMode:"amount",amount:String(Math.min(10000,state.maxInvestment))})}>Amount</button></div>
            <label className="investment-amount">{state.inputMode==="units"?"Number of shares":`Investment budget (${currency})`}<input aria-label="Investment amount" type="number" min={state.inputMode==="units"?1:price} max={state.inputMode==="units"?Math.floor(state.maxInvestment/price):state.maxInvestment} step={state.inputMode==="units"?1:.01} value={state.amount} onChange={e=>updateDraft({amount:e.target.value})}/></label>
            <div className="share-calculation"><div><span>Unit price</span><strong>{money(price,currency)}</strong></div><i>×</i><div><span>Whole shares</span><strong>{unitsValid?units:"—"}</strong></div><i>=</i><div><span>Total value</span><strong>{unitsValid?money(amount,currency):"—"}</strong></div></div>
            {state.inputMode==="amount"&&unitsValid&&<p className="budget-remainder">Unused budget: {money(Math.max(0,Number(state.amount)-amount),currency)}</p>}
            <p className="investment-limit">Maximum investment: <strong>{money(state.maxInvestment,currency)}</strong><button onClick={()=>go("settings")}>Change</button></p>
            {state.funding==="rebalance"&&<div className="sale-inputs"><h3>Choose holdings to sell</h3>{p.holdings.map(h=><label key={h.id}><span>{h.name}<small>{h.units!=null?`Available: ${h.units} shares`:`Available: ${money(h.value,currency)}`}</small></span><input aria-label={`Sell ${h.name}`} type="number" min="0" max={h.units??h.value} step={h.units==null ? .01 : 1} value={state.sales[h.id]??""} placeholder="0" onChange={e=>updateDraft({sales:{...state.sales,[h.id]:e.target.value}})}/></label>)}<label><span>Additional money ({currency})</span><input aria-label="Additional money" type="number" min="0" step=".01" value={state.additional} onChange={e=>updateDraft({additional:e.target.value})}/></label><p className="simulation-help">Sales plus additional money must equal the total value above.</p></div>}
            {error&&<p className="form-error" role="alert">{error}</p>}<Button onClick={runSimulation}>Compare portfolios <ArrowRight/></Button>
          </section>
          <section ref={comparisonRef} tabIndex={-1} className="workspace-panel comparison-panel" aria-labelledby="comparison-heading"><div className="panel-heading"><div><span className="comparison-kicker">PORTFOLIO COMPARISON</span><h2 id="comparison-heading">Old portfolio vs. new portfolio</h2><p>Hover or tap a company or metric to explore its meaning.</p></div></div>{state.result?<><Comparison baseline={p} result={state.result}/><Button kind="ghost" onClick={()=>updateDraft({result:null})}>Reset comparison</Button></>:<div className="comparison-empty"><ArrowsLeftRight size={35}/><h3>See how your portfolio could change.</h3><p>Select whole shares and compare your portfolio performance and each company's holdings.</p></div>}</section>
        </div>}
      </div>}
      {view==="settings"&&<Settings risk={state.risk} green={state.green} maxInvestment={state.maxInvestment} currency={currency} onSave={(risk,green,maxInvestment)=>{setState(s=>({...s,risk,green,maxInvestment,result:null}));setNotice("Settings saved.");}}/>}
    </main></div>
    {uploadOpen&&<Dialog title="Upload portfolio" onClose={()=>setUploadOpen(false)}><ImportFlow onImport={load}/></Dialog>}
    {exportOpen&&<Dialog title="Export portfolio" onClose={()=>setExportOpen(false)}><div className="export-body"><p>Download a formatted portfolio report with share prices, whole units and total values.</p><label className="export-format">File format<select aria-label="Export format" value={exportFormat} onChange={e=>setExportFormat(e.target.value as ExportFormat)}><option value="pdf">PDF · Portfolio report</option><option value="json">JSON · Structured data</option></select></label>{!state.result&&<p className="export-empty">Compare portfolios first to generate your recommended holdings and report.</p>}<div className="export-options"><section><span className="export-icon"><SquaresFour size={24}/></span><h3>Recommended portfolio</h3><p>Share prices, units, totals, environmental scores and explanations.</p><Button disabled={!state.result||exportBusy} onClick={()=>void exportPortfolio("recommended")}><DownloadSimple size={18}/>{exportBusy?"Preparing report…":"Export recommended portfolio"}</Button></section><section><span className="export-icon"><ArrowsLeftRight size={24}/></span><h3>Portfolio comparison</h3><p>Old and new holdings, share quantities and performance changes.</p><Button disabled={!state.result||exportBusy} onClick={()=>void exportPortfolio("comparison")}><DownloadSimple size={18}/>{exportBusy?"Preparing report…":"Export portfolio comparison"}</Button></section></div></div></Dialog>}
    {detail&&<Dialog title="Company details" onClose={()=>setDetail(null)}><CompanyDetails company={detail} onSimulate={()=>select(detail)}/></Dialog>}
    {notice&&<div className="toast" role="status"><CheckCircle size={18}/>{notice}</div>}
  </div>;
}
function Comparison({baseline,result}:{baseline:Portfolio;result:Portfolio}) {
  const before=metrics(baseline),after=metrics(result);
  const change=(a:number|null,b:number|null,percentage:boolean)=>{
    if(a===null||b===null)return "Unavailable";
    const delta=Number(((b-a)*(percentage?100:1)).toFixed(percentage?3:2));
    return `${delta>=0?"+":""}${delta.toFixed(percentage?3:2)} ${percentage?"pp":"points"}`;
  };
  const rows=[
    ["Portfolio value",money(totalValue(baseline),baseline.baseCurrency),money(totalValue(result),result.baseCurrency),money(totalValue(result)-totalValue(baseline),result.baseCurrency)],
    ["Expected return · annual",percent(before.expectedReturn.value,3),percent(after.expectedReturn.value,3),change(before.expectedReturn.value,after.expectedReturn.value,true)],
    ["Portfolio green score",score(before.greenScore.value),score(after.greenScore.value),change(before.greenScore.value,after.greenScore.value,false)],
    ["Portfolio volatility","Unavailable","Unavailable","Unavailable"],
    ["E-score coverage",percent(before.greenScore.coverage,1),percent(after.greenScore.coverage,1),change(before.greenScore.coverage,after.greenScore.coverage,true)],
  ];
  return <><div className="table-scroll"><table className="comparison-table"><caption>Portfolio performance</caption><thead><tr><th>Metric</th><th>Old portfolio</th><th>New portfolio</th><th>Change</th></tr></thead><tbody>{rows.map(([label,...values])=><tr key={label}><th scope="row"><InfoPopover label={label} content={<><strong>{label}</strong><p>{metricExplanations[label]}</p></>}>{label}</InfoPopover></th>{values.map((value,i)=><td key={i}>{value}</td>)}</tr>)}</tbody></table></div>
    <p className="holding-table-hint">Company details · Scroll for all share values →</p>
    <div className="table-scroll"><table className="comparison-table company-comparison"><caption>Each company / share</caption><thead><tr><th>Company</th><th>Unit price</th><th>Old units</th><th>New units</th><th>Old total</th><th>New total</th><th>E-score</th><th>Old weight</th><th>New weight</th></tr></thead><tbody>{[...new Set([...baseline.holdings,...result.holdings].map(h=>h.id))].map(id=>{
      const a=baseline.holdings.find(h=>h.id===id),b=result.holdings.find(h=>h.id===id),h=b??a!;
      return <tr key={id}><th scope="row"><CompanyInfo company={h}/><small className="comparison-symbol">{displayTicker(h.ticker)} · {h.exchange}</small></th><td>{h.unitPrice==null?"Unavailable":unitMoney(h.unitPrice,result.baseCurrency)}</td><td>{a?a.units??"Unavailable":0}</td><td>{b?b.units??"Unavailable":0}</td><td>{money(a?.value??0,baseline.baseCurrency)}</td><td>{money(b?.value??0,result.baseCurrency)}</td><td>{score(h.eScore)}</td><td>{percent((a?.value??0)/totalValue(baseline),1)}</td><td>{percent((b?.value??0)/totalValue(result),1)}</td></tr>;
    })}</tbody></table></div></>;
}
