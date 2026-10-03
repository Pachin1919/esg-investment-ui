import type { PortfolioStats as Stats } from "./api";

const FACTORS: Record<string, string> = {
  mkt_rf: "Market beta",
  smb: "Size · SMB",
  hml: "Value · HML",
  rmw: "Profitability · RMW",
  cma: "Investment · CMA",
  mom: "Momentum · MOM",
  gmb: "Green · GMB",
};
const MARKETS: Record<string, string> = { hk: "Hong Kong", tw: "Taiwan" };

type Row = { label: string; before: number | null; after: number | null; fmt: (x: number) => string; group?: string };
const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
const dec = (d: number) => (x: number) => x.toFixed(d);
const cell = (r: Row, x: number | null) => (x === null ? "—" : r.fmt(x));

/** Key figures of the current and the recommended portfolio next to each other. */
export function PortfolioStats({ before, after, volTarget }: { before: Stats; after: Stats; volTarget: number | null }) {
  const rows: Row[] = [
    { label: `Volatility (annual)${volTarget ? ` · target ${pct(volTarget)}` : ""}`, before: before.ann_vol, after: after.ann_vol, fmt: pct, group: "Risk and return" },
    { label: "Model-implied return (estimate, not a forecast)", before: before.ann_ret, after: after.ann_ret, fmt: pct },
    { label: "Greenness · g (closer to zero is greener)", before: before.g_avg, after: after.g_avg, fmt: dec(2) },
    { label: "Positions", before: before.n_positions, after: after.n_positions, fmt: dec(0), group: "Concentration" },
    { label: "Largest position", before: before.top_weight, after: after.top_weight, fmt: pct },
    { label: "Effective positions (equal-weight equivalent)", before: before.effective_n, after: after.effective_n, fmt: dec(1) },
    // pooled markets report one beta per market factor ("hk_mkt_rf", "tw_mkt_rf")
    ...Object.keys({ ...before.exposures, ...after.exposures }).map((k, i) => {
      const [, market, factor] = k.match(/^(?:(hk|tw)_)?(.+)$/)!;
      return {
        label: `${market ? `${MARKETS[market]} · ` : ""}${FACTORS[factor] ?? factor}`,
        before: before.exposures[k] ?? null,
        after: after.exposures[k] ?? null,
        fmt: dec(2),
        group: i === 0 ? "Factor exposures (portfolio beta)" : undefined,
      };
    }),
  ];
  return (
    <div className="portfolio-stats">
      <h3>Key figures</h3>
      <table className="compare-table">
        <thead>
          <tr>
            <th>Measure</th>
            <th>Current</th>
            <th>Recommended</th>
            <th>Change</th>
          </tr>
        </thead>
        <tbody>
          {rows.flatMap((r) => [
            ...(r.group
              ? [
                  <tr key={r.group} className="compare-group">
                    <td colSpan={4}>{r.group}</td>
                  </tr>,
                ]
              : []),
            <tr key={r.label}>
              <td>{r.label}</td>
              <td>{cell(r, r.before)}</td>
              <td className="compare-new">{cell(r, r.after)}</td>
              <td>
                {r.before === null || r.after === null
                  ? "—"
                  : `${r.after - r.before >= 0 ? "+" : "−"}${r.fmt(Math.abs(r.after - r.before))}`}
              </td>
            </tr>,
          ])}
        </tbody>
      </table>
    </div>
  );
}
