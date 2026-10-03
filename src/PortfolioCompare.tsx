import type { Company } from "./data";
import type { Trade } from "./api";

const MIN_WEIGHT = 0.0005;
const pct = (w: number) => `${(w * 100).toFixed(1)}%`;
const num = (x: number | null | undefined) => (x === null || x === undefined ? "—" : Math.round(x).toLocaleString("en-US"));
const signedNum = (x: number | null | undefined) =>
  x === null || x === undefined ? "—" : `${x > 0 ? "+" : ""}${Math.round(x).toLocaleString("en-US")}`;

function action(t: Trade) {
  if (t.side.startsWith("hold (outside")) return { label: "Kept · outside filter", tone: "neutral" };
  if (t.side.startsWith("frozen")) return { label: "Kept · not modeled", tone: "neutral" };
  if (t.side === "buy") return { label: t.w_current < MIN_WEIGHT ? "New" : "Buy more", tone: "mint" };
  if (t.side.startsWith("sell")) return { label: t.w_target < MIN_WEIGHT ? "Sell all" : "Reduce", tone: "amber" };
  return { label: "Hold", tone: "neutral" };
}

/** Current and recommended portfolio next to each other, one row per position. */
export function PortfolioCompare({ trades, names }: { trades: Trade[]; names: Map<string, Company> }) {
  const rows = trades
    .filter((t) => t.w_current >= MIN_WEIGHT || t.w_target >= MIN_WEIGHT)
    .sort((a, b) => Math.max(b.w_current, b.w_target) - Math.max(a.w_current, a.w_target));
  return (
    <div className="table-scroll">
      <table className="compare-table">
        <thead>
          <tr>
            <th rowSpan={2}>Company</th>
            <th colSpan={3}>Current portfolio</th>
            <th colSpan={3}>Recommended portfolio</th>
            <th colSpan={2}>Change</th>
          </tr>
          <tr>
            <th>Weight</th>
            <th>Shares</th>
            <th>Value</th>
            <th>Weight</th>
            <th>Shares</th>
            <th>Value</th>
            <th>Shares</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => {
            const a = action(t);
            return (
              <tr key={t.firm_id}>
                <td>
                  <strong>{names.get(t.firm_id)?.name ?? t.firm_id}</strong>
                  <br />
                  <small>
                    {t.firm_id}
                    {t.price ? ` · ${t.price.toFixed(2)}` : ""}
                  </small>
                </td>
                <td>{pct(t.w_current)}</td>
                <td>{num(t.shares_current)}</td>
                <td>{num(t.capital_current)}</td>
                <td className="compare-new">{pct(t.w_target)}</td>
                <td className="compare-new">{num(t.shares_target)}</td>
                <td className="compare-new">{num(t.capital_target)}</td>
                <td>{signedNum(t.shares_delta)}</td>
                <td>
                  <span className={`badge ${a.tone}`}>{a.label}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
