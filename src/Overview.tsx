import { useState } from "react";
import { Gauge, Leaf, MagnifyingGlass, SquaresFour, X } from "@phosphor-icons/react";
import type { PortfolioStats } from "./api";
import { CompanyInfo, InfoPopover, metricExplanations } from "./InfoPopover";
import { toHolding } from "./live";
import type { Universe } from "./live";
import { displayTicker, initials, metrics, money, percent, score, totalValue, unitMoney } from "./portfolio";
import type { Portfolio } from "./portfolio";

const MAX_HITS = 25;

/** Headline figures: return and volatility come from the engine's risk model, the green score from the holdings. */
export function MetricCards({ portfolio, stats }: { portfolio: Portfolio; stats: PortfolioStats | null }) {
  const m = metrics(portfolio);
  const cards = [
    ["Expected return", "Expected return · annual", percent(stats?.ann_ret ?? null), "Model-implied annual return", SquaresFour],
    ["Portfolio green score", "Portfolio green score", score(m.greenScore.value), "Environmental performance", Leaf],
    ["Portfolio volatility", "Portfolio volatility", percent(stats?.ann_vol ?? null, 1), "Portfolio risk", Gauge],
  ] as const;
  return <div className="workspace-metrics">{cards.map(([label, key, value, description, Icon]) => <article className="workspace-metric" key={key}><div><InfoPopover label={label} content={<><strong>{label}</strong><p>{metricExplanations[key]}</p></>}>{label}</InfoPopover><Icon /></div><strong>{value}</strong><p>{description}</p></article>)}</div>;
}

export function HoldingsTable({ portfolio }: { portfolio: Portfolio }) {
  const total = totalValue(portfolio);
  return <section className="workspace-panel"><div className="panel-heading"><div><h2>Current holdings</h2><p>Current market value · {portfolio.baseCurrency} · {portfolio.asOf}</p></div><strong>{money(total, portfolio.baseCurrency)}</strong></div><p className="table-scroll-hint">Scroll to see all holding details →</p>
    <div className="table-scroll"><table className="analysis-table"><thead><tr><th>Company / asset</th><th>Unit price</th><th>Units</th><th>Total value</th><th>Weight</th><th>E-score</th></tr></thead>
      <tbody>{portfolio.holdings.map(h => <tr key={h.id}><td><div className="holding-company"><i style={{ background: h.color }}>{initials(h.name)}</i><span><CompanyInfo company={h} /><small>{displayTicker(h.ticker)} · {h.sector ?? h.assetClass}</small></span></div></td>
        <td>{h.unitPrice == null ? "Unavailable" : unitMoney(h.unitPrice, portfolio.baseCurrency)}</td><td>{h.units ?? "Unavailable"}</td><td>{money(h.value, portfolio.baseCurrency)}</td><td>{percent(h.value / total, 1)}</td><td>{score(h.eScore)}</td></tr>)}</tbody></table></div></section>;
}

/** Every scored company in the universe, not only the holdings. */
export function UniverseSearch({ universe, portfolio }: { universe: Universe; portfolio: Portfolio | null }) {
  const [query, setQuery] = useState("");
  const held = new Set(portfolio?.holdings.map(h => h.ticker));
  const words = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  const hits = words.length ? [...universe.values()].filter(c => words.every(w => `${c.name} ${c.ticker} ${c.sector} ${c.region}`.toLowerCase().includes(w))) : [];
  return <section className="workspace-panel"><div className="panel-heading"><div><h2>All companies</h2><p>Look up any of the {universe.size} scored companies, held or not.</p></div></div>
    <div className="builder-company-tools"><div className="company-keyword-input"><MagnifyingGlass size={19} /><input aria-label="Search all companies" placeholder="Search company, ticker, sector or market" value={query} onChange={e => setQuery(e.target.value)} />{query && <button type="button" aria-label="Clear company search" onClick={() => setQuery("")}><X size={16} /></button>}</div></div>
    {hits.length > 0 && <div className="table-scroll"><table className="analysis-table"><thead><tr><th>Company</th><th>Sector</th><th>Market</th><th>E-score</th><th>Talk</th><th>Talk–walk gap</th><th>In portfolio</th></tr></thead>
      <tbody>{hits.slice(0, MAX_HITS).map(c => <tr key={c.id}><td><div className="holding-company"><i style={{ background: c.color }}>{c.initials}</i><span><CompanyInfo company={toHolding(c, 0)} /><small>{c.ticker}{c.greenwasher ? " · Greenwash risk" : c.greenhusher ? " · Quiet action" : ""}</small></span></div></td>
        <td>{c.sector}</td><td>{c.region}</td><td>{score(c.score)}</td><td>{score(c.talk)}</td><td>{c.gap == null ? "Unavailable" : `${c.gap > 0 ? "+" : ""}${c.gap.toFixed(1)}`}</td><td>{held.has(c.ticker) ? "Held" : "Not held"}</td></tr>)}</tbody></table></div>}
    {hits.length > MAX_HITS && <p className="builder-footnote">Showing {MAX_HITS} of {hits.length} matches. Refine the search to narrow it down.</p>}
    {words.length > 0 && !hits.length && <p className="builder-search-empty" role="status">No matching companies. Try another keyword.</p>}
  </section>;
}
