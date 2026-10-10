import { useState } from "react";
import { ArrowRight, CaretDown, ChartDonut, CheckCircle, Leaf, MagnifyingGlass, Sparkle, X } from "@phosphor-icons/react";
import type { Recommendation, SectorOption } from "./api";
import { modelContext } from "./api";
import IndustryDropdown from "./IndustryDropdown";
import { CompanyInfo, InfoPopover, metricExplanations } from "./InfoPopover";
import { MIN_WEIGHT, newCapital, sectorColor, toHolding, tradeAction } from "./live";
import type { Plan, Universe } from "./live";
import { displayTicker, metrics, money, percent, score, totalValue, unitMoney } from "./portfolio";
import type { Portfolio } from "./portfolio";
import dataStyles from "./DataWorkspace.module.css";

type Props = {
  baseline: Portfolio; universe: Universe; sectors: SectorOption[]; maximum: number; plan: Plan;
  rec: Recommendation | null; portfolio: Portfolio | null; loading: boolean; error: string;
  dataStatusLabel: string; disabled: boolean;
  onPlanChange: (plan: Plan) => void;
};
const collapsedCompanyLimit = 6;

function AllocationChart({ portfolio }: { portfolio: Portfolio }) {
  const total = totalValue(portfolio);
  const names = [...new Set(portfolio.holdings.map(h => h.sector ?? "Other"))].sort();
  const segments = names.map(sector => ({ sector, color: sectorColor(sector, names), value: portfolio.holdings.filter(h => (h.sector ?? "Other") === sector).reduce((sum, h) => sum + h.value, 0) })).sort((a, b) => b.value - a.value);
  const circumference = 2 * Math.PI * 62;
  let offset = 0;
  return <div className="industry-allocation"><div className="allocation-ring">
    <svg viewBox="0 0 168 168" role="img" aria-label="Recommended portfolio sector allocation"><circle cx="84" cy="84" r="62" fill="none" stroke="#eaf0f4" strokeWidth="20" />
      {segments.map(s => { const length = s.value / total * circumference; const previous = offset; offset += length; return <circle key={s.sector} cx="84" cy="84" r="62" fill="none" stroke={s.color} strokeWidth="20" strokeDasharray={`${length} ${circumference - length}`} strokeDashoffset={-previous} transform="rotate(-90 84 84)"><title>{s.sector}: {percent(s.value / total, 1)}</title></circle>; })}
    </svg><span><strong>{portfolio.holdings.length}</strong><small>companies</small></span></div>
    <ul>{segments.map(s => <li key={s.sector}><i style={{ background: s.color }} /><span>{s.sector}</span><strong>{percent(s.value / total, 1)}</strong></li>)}</ul>
  </div>;
}

export default function RecommendationsBuilder({ baseline, universe, sectors, maximum, plan, rec, portfolio, loading, error, dataStatusLabel, disabled, onPlanChange }: Props) {
  const [focus, setFocus] = useState<string[] | null>(plan.industries);
  const [tolerance, setTolerance] = useState(String(plan.tolerancePercent));
  const [query, setQuery] = useState(""), [formError, setFormError] = useState("");
  const [showAll, setShowAll] = useState(false);
  const toleranceValid = tolerance.trim() !== "" && Number.isFinite(Number(tolerance)) && Number(tolerance) >= 0 && Number(tolerance) <= 100;
  const draft: Plan = { industries: focus, tolerancePercent: toleranceValid ? Number(tolerance) : 0 };
  const dirty = draft.tolerancePercent !== plan.tolerancePercent || (focus ?? []).join() !== (plan.industries ?? []).join() || (focus === null) !== (plan.industries === null);
  const added = newCapital(baseline, draft, maximum);
  const words = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  const positions = (rec?.trades ?? []).filter(t => t.w_current >= MIN_WEIGHT || t.w_target >= MIN_WEIGHT).sort((a, b) => b.w_target - a.w_target);
  const filtered = positions.filter(t => { const c = universe.get(t.firm_id); return words.every(w => `${c?.name ?? ""} ${t.firm_id} ${c?.sector ?? ""}`.toLowerCase().includes(w)); });
  const visible = showAll ? filtered : filtered.slice(0, collapsedCompanyLimit);
  const summary = portfolio ? metrics(portfolio) : null;
  return <div className="recommendation-builder">
    <section className="workspace-panel builder-setup" aria-labelledby="setup-heading">
      <div className="builder-panel-heading"><span className="builder-step">01</span><div><h2 id="setup-heading">Setup</h2></div></div>
      <form onSubmit={e => {
        e.preventDefault();
        if (focus && !focus.length) { setFormError("Choose at least one industry."); return; }
        if (!toleranceValid) { setFormError("Enter new money between 0% and 100% of your portfolio value."); return; }
        onPlanChange(draft); setFormError(""); setQuery(""); setShowAll(false);
      }}>
        <IndustryDropdown sectors={sectors} value={focus} onChange={v => { setFocus(v); setFormError(""); }} />
        <div className="builder-budget"><label htmlFor="value-tolerance">New money to add</label><p>As a share of your current portfolio. Zero rebalances what you hold.</p><div className="tolerance-input"><input id="value-tolerance" aria-label="New money to add" type="number" min="0" max="100" step="1" required value={tolerance} onChange={e => { setTolerance(e.target.value); setFormError(""); }} /><span>%</span></div>
          <dl><div><dt>Current value</dt><dd>{money(totalValue(baseline), baseline.baseCurrency)}</dd></div><div><dt>New money</dt><dd>{toleranceValid ? money(added, baseline.baseCurrency) : "—"}</dd></div></dl>
          {toleranceValid && totalValue(baseline) * Number(tolerance) / 100 > maximum && <p className="budget-capped"><CheckCircle size={14} />Limited by your maximum investment.</p>}
        </div>
        {dirty && <p className="builder-draft-note">Setup changed. Generate again to apply it.</p>}
        {(formError || error) && <p className="form-error" role="alert">{formError || error}</p>}
        <button type="submit" className="button primary generate-recommendations" disabled={loading || disabled}><Sparkle size={18} />{loading ? "Optimising…" : "Generate recommendations"} <ArrowRight size={17} /></button>
        <p className="builder-footnote">Only the ticked industries are bought or rebalanced. Holdings outside them are left untouched.</p>
      </form>
    </section>

    <section className="workspace-panel builder-companies" aria-labelledby="companies-heading">
      <div className="builder-panel-heading"><span className="builder-step">02</span><div><h2 id="companies-heading">Recommended positions</h2></div></div>
      <div className="builder-company-tools"><div className="company-keyword-input"><MagnifyingGlass size={19} /><input aria-label="Search recommendations" placeholder="Search company, ticker or sector" value={query} onChange={e => { setQuery(e.target.value); setShowAll(false); }} disabled={!rec} />{query && <button type="button" aria-label="Clear company search" onClick={() => { setQuery(""); setShowAll(false); }}><X size={16} /></button>}</div></div>
      {!rec ? <div className="builder-empty"><Sparkle size={32} /><h3>{loading ? "Optimising your portfolio…" : "Your next portfolio starts here."}</h3><p>{loading ? "The engine is weighing risk, greenness and trading cost." : "Choose industries on the left, then generate your recommendations."}</p></div> : <>
        <div className="company-selection-toolbar"><span>{rec.params.n_candidates} candidates considered · {percent(rec.turnover, 0)} turnover</span><span className="selection-status" role="status">{positions.filter(t => t.w_target >= MIN_WEIGHT).length} positions</span></div>
        <div className="table-scroll"><table id="recommended-company-list" className="builder-company-table"><thead><tr><th><span className="sr-only">Position</span></th><th>Company / price</th><th>Action</th><th>Shares</th><th>Total / weight</th><th>E-score</th></tr></thead><tbody>
          {visible.map(t => { const c = universe.get(t.firm_id); const a = tradeAction(t.side, t.w_current, t.w_target); return <tr key={t.firm_id} className={t.w_target >= MIN_WEIGHT ? "company-selected" : ""}><td />
            <th scope="row">{c ? <CompanyInfo company={toHolding(c, 0)} /> : t.firm_id}<small>{displayTicker(t.firm_id)}{c ? ` · ${c.sector}` : ""}</small>{t.price != null && <span className="builder-share-price">{unitMoney(t.price, baseline.baseCurrency)} / share</span>}</th>
            <td><span className={`trade-action ${a.tone}`}>{a.label}</span></td>
            <td className="company-units">{t.shares_target ?? "—"}{t.shares_delta ? <small>{t.shares_delta > 0 ? "+" : ""}{t.shares_delta}</small> : null}</td>
            <td className="company-allocation">{money(t.capital_target, baseline.baseCurrency)}<small>{percent(t.w_target, 1)}</small></td>
            <td><span className="company-score"><Leaf size={14} />{score(c?.score ?? null)}</span></td></tr>; })}
        </tbody></table></div>
        {filtered.length > collapsedCompanyLimit && <button type="button" className="company-list-toggle" aria-expanded={showAll} aria-controls="recommended-company-list" onClick={() => setShowAll(s => !s)}>{showAll ? "Show fewer positions" : `Show ${filtered.length - collapsedCompanyLimit} more`}<CaretDown size={16} /></button>}
        {!filtered.length && <p className="builder-search-empty" role="status">No matching positions. Try another keyword.</p>}
      </>}
    </section>

    <section className="workspace-panel builder-portfolio" aria-labelledby="live-portfolio-heading">
      <div className="builder-panel-heading"><span className="builder-step">03</span><div><h2 id="live-portfolio-heading">Your portfolio</h2></div><span className={dataStyles.snapshotIndicator} title={dataStatusLabel}>{dataStatusLabel.startsWith("Latest database data") ? "Database" : dataStatusLabel.split(" · ")[0]}</span></div>
      {!portfolio || !rec ? <div className="builder-empty"><ChartDonut size={34} /><h3>See your choices come together.</h3><p>Your recommended holdings, performance and sector allocation will appear here.</p></div> : <>
        <div className="live-portfolio-value"><InfoPopover label="Portfolio value" content={<><strong>Portfolio value</strong><p>{metricExplanations["Portfolio value"]}</p></>}>Portfolio value</InfoPopover><strong aria-live="polite" aria-atomic="true">{money(rec.target_capital, portfolio.baseCurrency)}</strong></div>
        <div className="live-portfolio-metrics">{[
          ["Expected return · annual", percent(rec.after.ann_ret), "USD excess return · annual"],
          ["Portfolio green score", score(summary!.greenScore.value), "Environmental score"],
          ["Portfolio volatility", percent(rec.after.ann_vol, 1), "USD volatility · annual"],
        ].map(([key, value, label]) => <div key={key}><InfoPopover label={key} content={<><strong>{label}</strong><p>{metricExplanations[key]}</p></>}>{label}</InfoPopover><strong>{value}</strong></div>)}</div>
        <div className="portfolio-budget-note"><span>Volatility target <strong>{percent(rec.params.vol_target_ann, 0)}</strong></span><span>New money <strong>{money(rec.new_capital, portfolio.baseCurrency)}</strong></span></div>
        <h3 className="builder-subheading">Sector allocation</h3><AllocationChart portfolio={portfolio} />
        <p className="builder-footnote">{modelContext(rec)} Shares use dated database closes and FX; board lots are not modeled.</p>
      </>}
    </section>
  </div>;
}
