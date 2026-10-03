import type { PortfolioStats as Stats } from "./api";

const FACTORS: [string, string, string][] = [
  ["mkt_rf", "Market", "Sensitivity to the equity market"],
  ["smb", "Size · SMB", "Small minus big companies"],
  ["hml", "Value · HML", "Cheap minus expensive companies"],
  ["rmw", "Profitability · RMW", "Robust minus weak profitability"],
  ["cma", "Investment · CMA", "Conservative minus aggressive investment"],
  ["mom", "Momentum · MOM", "Recent winners minus losers"],
  ["gmb", "Green · GMB", "Green minus brown companies"],
];

const signed = (x: number | undefined) => (x === undefined ? "—" : `${x >= 0 ? "+" : ""}${x.toFixed(2)}`);

/** Before/after key figures of the whole portfolio: factor betas and concentration. */
export function PortfolioStats({ before, after }: { before: Stats; after: Stats }) {
  const rows = FACTORS.filter(([key]) => key in before.exposures || key in after.exposures);
  return (
    <div className="portfolio-stats">
      <h3>Factor exposures</h3>
      <p className="muted small">Portfolio beta to each factor. Zero means no exposure.</p>
      <table>
        <thead>
          <tr>
            <th>Factor</th>
            <th>Before</th>
            <th>After</th>
            <th>Change</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([key, label, desc]) => (
            <tr key={key}>
              <td>
                <strong>{label}</strong>
                <br />
                <small>{desc}</small>
              </td>
              <td>{signed(before.exposures[key])}</td>
              <td>{signed(after.exposures[key])}</td>
              <td>{signed((after.exposures[key] ?? 0) - (before.exposures[key] ?? 0))}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3>Concentration</h3>
      <div className="esg-scorecard-grid">
        <div className="esg-scorecard-card">
          <span>Positions</span>
          <strong>
            {before.n_positions} → {after.n_positions}
          </strong>
        </div>
        <div className="esg-scorecard-card">
          <span>Largest position</span>
          <strong>
            {(before.top_weight * 100).toFixed(0)}% → {(after.top_weight * 100).toFixed(0)}%
          </strong>
        </div>
        <div className="esg-scorecard-card">
          <span>Effective positions</span>
          <strong>
            {before.effective_n.toFixed(1)} → {after.effective_n.toFixed(1)}
          </strong>
          <small className="neutral">Equal-weight equivalent</small>
        </div>
      </div>
    </div>
  );
}
