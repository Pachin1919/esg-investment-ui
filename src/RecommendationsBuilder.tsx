import { useEffect, useRef, useState } from "react";
import { ArrowRight, CaretDown, ChartDonut, CheckCircle, Leaf, MagnifyingGlass, Sparkle, X } from "@phosphor-icons/react";
import { CompanyInfo, InfoPopover, metricExplanations } from "./InfoPopover";
import { displayTicker, metrics, money, percent, score, sharePrice, totalValue, unitMoney } from "./portfolio";
import type { Candidate, Portfolio } from "./portfolio";
import { industries, industryRecommendations, recommendationBudget } from "./recommendationBuilder";
import type { RecommendationPlan } from "./recommendationBuilder";

type Props = {
  baseline:Portfolio; risk:number; green:number; maximum:number; plan:RecommendationPlan|null;
  companies:Candidate[]; portfolio:Portfolio|null; budget:number;
  onPlanChange:(plan:RecommendationPlan)=>void;
};
const collapsedCompanyLimit=6;

function AllocationChart({portfolio}:{portfolio:Portfolio}) {
  const total=totalValue(portfolio);
  const segments=industries.map(industry=>({...industry,value:portfolio.holdings.filter(h=>h.industryId===industry.id).reduce((sum,h)=>sum+h.value,0)})).filter(s=>s.value>0);
  const circumference=2*Math.PI*62;
  let offset=0;
  return <div className="industry-allocation"><div className="allocation-ring">
    <svg viewBox="0 0 168 168" role="img" aria-label="Selected portfolio industry allocation"><circle cx="84" cy="84" r="62" fill="none" stroke="#eaf0f4" strokeWidth="20"/>
      {segments.map(segment=>{const length=segment.value/total*circumference;const previous=offset;offset+=length;return <circle key={segment.id} cx="84" cy="84" r="62" fill="none" stroke={segment.color} strokeWidth="20" strokeDasharray={`${length} ${circumference-length}`} strokeDashoffset={-previous} transform="rotate(-90 84 84)"><title>{segment.label}: {percent(segment.value/total,1)}</title></circle>;})}
    </svg><span><strong>{portfolio.holdings.length}</strong><small>companies</small></span></div>
    <ul>{segments.map(segment=><li key={segment.id}><i style={{background:segment.color}}/><span>{segment.label}</span><strong>{percent(segment.value/total,1)}</strong></li>)}</ul>
  </div>;
}

export default function RecommendationsBuilder({baseline,risk,green,maximum,plan,companies,portfolio,budget,onPlanChange}:Props) {
  const [focus,setFocus]=useState<string[]>(plan?.industries??industries.map(i=>i.id));
  const [tolerance,setTolerance]=useState(String(plan?.tolerancePercent??10));
  const [query,setQuery]=useState(""),[error,setError]=useState("");
  const [industryOpen,setIndustryOpen]=useState(false);
  const [showAllCompanies,setShowAllCompanies]=useState(false);
  const industryDropdown=useRef<HTMLDivElement>(null),industryTrigger=useRef<HTMLButtonElement>(null);
  const selectAll=useRef<HTMLInputElement>(null),allIndustries=useRef<HTMLInputElement>(null);
  const chosen=companies.filter(c=>plan?.selectedIds.includes(c.id));
  useEffect(()=>{if(selectAll.current)selectAll.current.indeterminate=chosen.length>0&&chosen.length<companies.length;},[chosen.length,companies.length]);
  useEffect(()=>{if(allIndustries.current)allIndustries.current.indeterminate=focus.length>0&&focus.length<industries.length;},[focus.length,industryOpen]);
  useEffect(()=>{
    if(!industryOpen)return;
    const dismiss=(event:MouseEvent)=>{if(!industryDropdown.current?.contains(event.target as Node))setIndustryOpen(false);};
    const escape=(event:KeyboardEvent)=>{if(event.key==="Escape"){event.preventDefault();setIndustryOpen(false);industryTrigger.current?.focus();}};
    document.addEventListener("mousedown",dismiss);document.addEventListener("keydown",escape);
    return()=>{document.removeEventListener("mousedown",dismiss);document.removeEventListener("keydown",escape);};
  },[industryOpen]);
  const focusedIndustries=industries.filter(industry=>focus.includes(industry.id));
  const industryLabel=focus.length===industries.length?"All industries":focus.length?`${focusedIndustries[0].label}${focus.length>1?` +${focus.length-1}`:""}`:"Choose industries";
  const toleranceValid=tolerance.trim()!==""&&Number.isFinite(Number(tolerance))&&Number(tolerance)>=-50&&Number(tolerance)<=100;
  const previewBudget=toleranceValid?recommendationBudget(baseline,Number(tolerance),maximum):0;
  const dirty=!!plan&&(Number(tolerance)!==plan.tolerancePercent||[...focus].sort().join()!==[...plan.industries].sort().join());
  const words=query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  const filtered=companies.filter(c=>words.every(word=>`${c.name} ${displayTicker(c.ticker)} ${c.keywords} ${industries.find(i=>i.id===c.industryId)?.label}`.toLowerCase().includes(word)));
  const visibleCompanies=showAllCompanies?filtered:filtered.slice(0,collapsedCompanyLimit);
  const summary=portfolio?metrics(portfolio):null;
  const invested=portfolio?totalValue(portfolio):0;
  const toggle=(id:string)=>{if(plan)onPlanChange({...plan,selectedIds:plan.selectedIds.includes(id)?plan.selectedIds.filter(value=>value!==id):[...plan.selectedIds,id]});};
  return <div className="recommendation-builder">
    <section className="workspace-panel builder-setup" aria-labelledby="setup-heading">
      <div className="builder-panel-heading"><span className="builder-step">01</span><div><h2 id="setup-heading">Setup</h2></div></div>
      <form onSubmit={e=>{
        e.preventDefault();
        if(!focus.length){setError("Choose at least one industry.");return;}
        if(!toleranceValid){setError("Enter a portfolio value change between −50% and +100%.");return;}
        const recommended=industryRecommendations(baseline,risk,green,maximum,focus,Number(tolerance));
        onPlanChange({industries:[...focus],tolerancePercent:Number(tolerance),selectedIds:recommended.map(c=>c.id)});setError("");setQuery("");setIndustryOpen(false);setShowAllCompanies(false);
      }}>
        <fieldset className="industry-options"><legend>Industry focus</legend>
          <div ref={industryDropdown} className="industry-dropdown">
            <button ref={industryTrigger} type="button" className="industry-dropdown-trigger" aria-label="Choose industries" aria-expanded={industryOpen} aria-controls="industry-dropdown-options" onClick={()=>setIndustryOpen(open=>!open)}><span>{industryLabel}</span><CaretDown size={16}/></button>
            {industryOpen&&<div id="industry-dropdown-options" className="industry-dropdown-options" role="group" aria-label="Investment industries">
          <label className="all-industries"><input ref={allIndustries} type="checkbox" aria-label="All industries" checked={focus.length===industries.length} onChange={e=>{setFocus(e.target.checked?industries.map(i=>i.id):[]);setError("");}}/><span>All industries</span></label>
          {industries.map(industry=><label key={industry.id} className={focus.includes(industry.id)?"industry-option selected":"industry-option"}>
            <input type="checkbox" aria-label={industry.label} checked={focus.includes(industry.id)} onChange={()=>{setFocus(current=>current.includes(industry.id)?current.filter(id=>id!==industry.id):[...current,industry.id]);setError("");}}/>
            <i style={{background:industry.color}}/><span><strong>{industry.label}</strong><small>{industry.description}</small></span>
          </label>)}
            </div>}
          </div>
          <p className="industry-selection-hint">{focus.length} of {industries.length} industries selected · Choose one or more.</p>
        </fieldset>
        <div className="builder-budget"><label htmlFor="value-tolerance">Portfolio value change</label><p>Relative to your current portfolio.</p><div className="tolerance-input"><input id="value-tolerance" aria-label="Portfolio value change" type="number" min="-50" max="100" step="1" required value={tolerance} onChange={e=>{setTolerance(e.target.value);setError("");}}/><span>%</span></div>
          <dl><div><dt>Current value</dt><dd>{money(totalValue(baseline),baseline.baseCurrency)}</dd></div><div><dt>Target budget</dt><dd>{toleranceValid?money(previewBudget,baseline.baseCurrency):"—"}</dd></div></dl>
          {toleranceValid&&totalValue(baseline)*(1+Number(tolerance)/100)>maximum&&<p className="budget-capped"><CheckCircle size={14}/>Limited by your maximum investment.</p>}
        </div>
        {dirty&&<p className="builder-draft-note">Setup changed. Generate again to apply it.</p>}
        {error&&<p className="form-error" role="alert">{error}</p>}
        <button type="submit" className="button primary generate-recommendations"><Sparkle size={18}/>Generate recommendations <ArrowRight size={17}/></button>
        <p className="builder-footnote">Recommendations respect your risk and green settings.</p>
      </form>
    </section>

    <section className="workspace-panel builder-companies" aria-labelledby="companies-heading">
      <div className="builder-panel-heading"><span className="builder-step">02</span><div><h2 id="companies-heading">Recommended companies</h2></div></div>
      <div className="builder-company-tools"><div className="company-keyword-input"><MagnifyingGlass size={19}/><input aria-label="Search recommendations" placeholder="Search company, ticker or keyword" value={query} onChange={e=>{setQuery(e.target.value);setShowAllCompanies(false);}} disabled={!plan}/>{query&&<button type="button" aria-label="Clear company search" onClick={()=>{setQuery("");setShowAllCompanies(false);}}><X size={16}/></button>}</div>
      </div>
      {!plan?<div className="builder-empty"><Sparkle size={32}/><h3>Your next portfolio starts here.</h3><p>Choose industries on the left, then generate your recommendations.</p></div>:!companies.length?<div className="builder-empty"><MagnifyingGlass size={30}/><h3>No companies match this setup.</h3><p>Try other industries, a larger budget or different Settings.</p></div>:<>
        <div className="company-selection-toolbar"><label><input ref={selectAll} type="checkbox" aria-label="Select all recommended companies" checked={chosen.length===companies.length} onChange={e=>onPlanChange({...plan,selectedIds:e.target.checked?companies.map(c=>c.id):[]})}/>Select all</label><span className="selection-status" role="status">{chosen.length} of {companies.length} selected</span></div>
        <div className="table-scroll"><table id="recommended-company-list" className="builder-company-table"><thead><tr><th><span className="sr-only">Include</span></th><th>Company / price</th><th>E-score</th><th><InfoPopover label="P/E ratio" content={<><strong>Price-to-earnings ratio</strong><p>Share price divided by annual earnings per share. It is a valuation measure, not an environmental score or a guarantee of future returns.</p></>}>P/E</InfoPopover></th><th>Return</th><th>Shares</th><th>Total / weight</th></tr></thead><tbody>
          {visibleCompanies.map(company=>{const holding=portfolio?.holdings.find(h=>displayTicker(h.ticker)===displayTicker(company.ticker)&&h.exchange===company.exchange);return <tr key={company.id} className={plan.selectedIds.includes(company.id)?"company-selected":""}><td><input type="checkbox" aria-label={`Include ${company.name}`} checked={plan.selectedIds.includes(company.id)} onChange={()=>toggle(company.id)}/></td>
            <th scope="row"><CompanyInfo company={{...company,value:0}}/><small>{displayTicker(company.ticker)} · {industries.find(i=>i.id===company.industryId)?.label}</small><span className="builder-share-price">{unitMoney(sharePrice(company,baseline.baseCurrency)!,baseline.baseCurrency)} / share</span></th>
            <td><span className="company-score"><Leaf size={14}/>{score(company.eScore)}</span></td><td>{company.peRatio.toFixed(1)}×</td><td>{percent(company.expectedReturn)}</td><td className="company-units">{holding?.units??0}</td><td className="company-allocation">{money(holding?.value??0,baseline.baseCurrency)}<small>{percent(holding&&invested?holding.value/invested:0,1)}</small></td></tr>;})}
        </tbody></table></div>
        {filtered.length>collapsedCompanyLimit&&<button type="button" className="company-list-toggle" aria-expanded={showAllCompanies} aria-controls="recommended-company-list" onClick={()=>setShowAllCompanies(show=>!show)}>{showAllCompanies?"Show fewer companies":`Show ${filtered.length-collapsedCompanyLimit} more ${filtered.length-collapsedCompanyLimit===1?"company":"companies"}`}<CaretDown size={16}/></button>}
        {!filtered.length&&<p className="builder-search-empty" role="status">No matching companies. Try another keyword.</p>}
      </>}
    </section>

    <section className="workspace-panel builder-portfolio" aria-labelledby="live-portfolio-heading">
      <div className="builder-panel-heading"><span className="builder-step">03</span><div><h2 id="live-portfolio-heading">Your portfolio</h2></div><span className="live-indicator"><i/>Live</span></div>
      {!portfolio?<div className="builder-empty"><ChartDonut size={34}/><h3>{plan&&companies.length?"Choose companies to build a portfolio.":"See your choices come together."}</h3><p>{plan&&companies.length?"Select at least one company in the middle panel. Your allocation will update automatically.":"Your selected holdings, performance and industry allocation will appear here."}</p></div>:<>
        <div className="live-portfolio-value"><InfoPopover label="Portfolio value" content={<><strong>Portfolio value</strong><p>{metricExplanations["Portfolio value"]}</p></>}>Portfolio value</InfoPopover><strong aria-live="polite" aria-atomic="true">{money(invested,portfolio.baseCurrency)}</strong></div>
        <div className="live-portfolio-metrics">{[
          ["Expected return · annual",percent(summary!.expectedReturn.value),"Annual expected return"],
          ["Portfolio green score",score(summary!.greenScore.value),"Environmental score"],
          ["Portfolio volatility","Unavailable","Portfolio risk"],
        ].map(([key,value,label])=><div key={key}><InfoPopover label={key} content={<><strong>{label}</strong><p>{metricExplanations[key]}</p></>}>{label}</InfoPopover><strong>{value}</strong></div>)}</div>
        <div className="portfolio-budget-note"><span>Target budget <strong>{money(budget,portfolio.baseCurrency)}</strong></span><span>Unallocated <strong>{money(Math.max(0,budget-invested),portfolio.baseCurrency)}</strong></span></div>
        <h3 className="builder-subheading">Industry allocation</h3><AllocationChart portfolio={portfolio}/>
        <p className="builder-footnote">The budget is redistributed across checked companies using whole shares. Unallocated money is excluded from these holdings and metrics.</p>
      </>}
    </section>
  </div>;
}
