import type { PortfolioStats, Recommendation } from "./api";
import { CompanyInfo, InfoPopover, metricExplanations } from "./InfoPopover";
import { MIN_WEIGHT, toHolding, tradeAction } from "./live";
import type { Universe } from "./live";
import { displayTicker, metrics, money, percent, score, totalValue, unitMoney } from "./portfolio";
import type { Portfolio } from "./portfolio";

const FACTORS: Record<string, string> = { mkt_rf: "Market beta", smb: "Size · SMB", hml: "Value · HML", rmw: "Profitability · RMW", cma: "Investment · CMA", mom: "Momentum · MOM", gmb: "Green · GMB" };
const MARKETS: Record<string, string> = { hk: "Hong Kong", tw: "Taiwan" };
type Row = { label: string; info?: string; before: number | null; after: number | null; fmt: (x: number) => string; section?: string };
const pct = (digits: number) => (x: number) => `${(x * 100).toFixed(digits)}%`;
const dec = (digits: number) => (x: number) => x.toFixed(digits);

function rows(baseline: Portfolio, result: Portfolio, before: PortfolioStats, after: PortfolioStats, targetCapital: number): Row[] {
  const a = metrics(baseline), b = metrics(result), ccy = baseline.baseCurrency;
  return [
    { label: "Portfolio value", info: "Portfolio value", before: totalValue(baseline), after: totalValue(result) > 0 ? targetCapital : 0, fmt: x => money(x, ccy), section: "Risk and return" },
    { label: "Expected return · annual", info: "Expected return · annual", before: before.ann_ret, after: after.ann_ret, fmt: pct(2) },
    { label: "Portfolio volatility", info: "Portfolio volatility", before: before.ann_vol, after: after.ann_vol, fmt: pct(1) },
    { label: "Portfolio green score", info: "Portfolio green score", before: a.greenScore.value, after: b.greenScore.value, fmt: dec(2), section: "Environment" },
    { label: "Greenness · g", info: "Greenness · g", before: before.g_avg, after: after.g_avg, fmt: dec(2) },
    { label: "E-score coverage", info: "E-score coverage", before: a.greenScore.coverage, after: b.greenScore.coverage, fmt: pct(1) },
    { label: "Positions", info: "Positions", before: before.n_positions, after: after.n_positions, fmt: dec(0), section: "Concentration" },
    { label: "Largest position", info: "Largest position", before: before.top_weight, after: after.top_weight, fmt: pct(1) },
    { label: "Effective positions", info: "Effective positions", before: before.effective_n, after: after.effective_n, fmt: dec(1) },
    // pooled markets report one beta per market factor ("hk_mkt_rf", "tw_mkt_rf")
    ...Object.keys({ ...before.exposures, ...after.exposures }).map((k, i): Row => {
      const [, market, factor] = k.match(/^(?:(hk|tw)_)?(.+)$/)!;
      return { label: `${market ? `${MARKETS[market]} · ` : ""}${FACTORS[factor] ?? factor}`, before: before.exposures[k] ?? null, after: after.exposures[k] ?? null, fmt: dec(2), section: i === 0 ? "Factor exposures (portfolio beta)" : undefined };
    }),
  ];
}

/** Current and recommended portfolio side by side: key figures, then every position. */
export default function Comparison({ baseline, result, rec, universe }: { baseline: Portfolio; result: Portfolio; rec: Recommendation; universe: Universe }) {
  const ccy = result.baseCurrency;
  const cell = (r: Row, x: number | null) => (x === null ? "Unavailable" : r.fmt(x));
  const positions = rec.trades.filter(t => t.w_current >= MIN_WEIGHT || t.w_target >= MIN_WEIGHT).sort((a, b) => Math.max(b.w_current, b.w_target) - Math.max(a.w_current, a.w_target));
  return <><div className="table-scroll"><table className="comparison-table"><caption>Portfolio performance</caption><thead><tr><th>Metric</th><th>Old portfolio</th><th>New portfolio</th><th>Change</th></tr></thead>
    <tbody>{rows(baseline, result, rec.before, rec.after, rec.target_capital).flatMap(r => [
      ...(r.section ? [<tr key={r.section} className="comparison-section"><th scope="rowgroup" colSpan={4}>{r.section}</th></tr>] : []),
      <tr key={r.label}><th scope="row">{r.info ? <InfoPopover label={r.label} content={<><strong>{r.label}</strong><p>{metricExplanations[r.info]}</p></>}>{r.label}</InfoPopover> : r.label}</th>
        <td>{cell(r, r.before)}</td><td>{cell(r, r.after)}</td><td>{r.before === null || r.after === null ? "Unavailable" : `${r.after - r.before >= 0 ? "+" : "−"}${r.fmt(Math.abs(r.after - r.before))}`}</td></tr>,
    ])}</tbody></table></div>
    <p className="holding-table-hint">Company details · Scroll for all share values →</p>
    <div className="table-scroll"><table className="comparison-table company-comparison"><caption>Each company / share</caption><thead><tr><th>Company</th><th>Unit price</th><th>Old units</th><th>New units</th><th>Old total</th><th>New total</th><th>E-score</th><th>Old weight</th><th>New weight</th><th>Action</th></tr></thead>
      <tbody>{positions.map(t => {
        const c = universe.get(t.firm_id), a = tradeAction(t.side, t.w_current, t.w_target);
        return <tr key={t.firm_id}><th scope="row">{c ? <CompanyInfo company={toHolding(c, 0)} /> : t.firm_id}<small className="comparison-symbol">{displayTicker(t.firm_id)}{c ? ` · ${c.sector}` : ""}</small></th>
          <td>{t.price == null ? "Unavailable" : unitMoney(t.price, ccy)}</td><td>{t.shares_current ?? "Unavailable"}</td><td>{t.shares_target ?? "Unavailable"}</td>
          <td>{money(t.capital_current, ccy)}</td><td>{money(t.capital_target, ccy)}</td><td>{score(c?.score ?? null)}</td>
          <td>{percent(t.capital_current / rec.total_capital, 1)}</td><td>{percent(t.w_target, 1)}</td><td><span className={`trade-action ${a.tone}`}>{a.label}</span></td></tr>;
      })}</tbody></table></div></>;
}
