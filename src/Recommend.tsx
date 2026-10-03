import { useState } from "react";
import { ArrowRight, WarningCircle } from "@phosphor-icons/react";
import type { Company } from "./data";
import { recommendPortfolio } from "./api";
import type { Recommendation } from "./api";
import { IndustryFilter } from "./IndustryFilter";

const MIN_TRADE = 0.001;

const pct = (x: number | null | undefined, digits = 1) =>
  x === null || x === undefined ? "—" : `${(x * 100).toFixed(digits)}%`;
const money = (x: number) => Math.round(Math.abs(x)).toLocaleString("en-US");

function Preference({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="preference">
      <span className="preference-head">
        <strong>{label}</strong>
        <em>{value} / 5</em>
      </span>
      <input type="range" min={1} max={5} step={1} value={value} onChange={(e) => onChange(Number(e.target.value))} />
      <small>{hint}</small>
    </label>
  );
}

export function Recommend({
  portfolio,
  universe,
  market,
}: {
  portfolio: Company[];
  universe: Company[];
  market: "hk" | "tw";
}) {
  const [risk, setRisk] = useState(3);
  const [green, setGreen] = useState(4);
  const [capital, setCapital] = useState(100000);
  const [newCapital, setNewCapital] = useState(0);
  const [industries, setIndustries] = useState<string[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Recommendation | null>(null);

  const names = new Map([...universe, ...portfolio].map((c) => [c.ticker, c]));
  const run = async () => {
    setLoading(true);
    setError(null);
    const holdings = Object.fromEntries(
      portfolio.filter((c) => c.allocation > 0).map((c) => [c.ticker, (c.allocation / 100) * capital]),
    );
    const res = await recommendPortfolio({
      holdings,
      risk_score: risk,
      green_score: green,
      max_new_capital: newCapital,
      market,
      ...(industries ? { filters: { include_industries: industries } } : {}),
    });
    if ("error" in res) {
      setError(res.error);
      setResult(null);
    } else setResult(res);
    setLoading(false);
  };

  const kept = (result?.trades ?? []).filter((t) => t.side.startsWith("hold (outside"));
  const trades = (result?.trades ?? [])
    .filter((t) => Math.abs(t.dw) >= MIN_TRADE)
    .sort((a, b) => Math.abs(b.capital_delta) - Math.abs(a.capital_delta));

  return (
    <div className="explore-page enter">
      <div className="page-heading">
        <div className="eyebrow">FROM PREFERENCE TO PORTFOLIO</div>
        <h1>Recommendations for your portfolio.</h1>
        <p>Set your risk and green preference. The engine proposes trades across the whole universe.</p>
      </div>
      <div className="explore-grid">
        <section className="panel allocation-editor">
          <div className="section-top">
            <div>
              <h2>Your preferences</h2>
              <p>
                Based on your {portfolio.length} current holdings.
              </p>
            </div>
          </div>
          <Preference
            label="Risk appetite"
            hint="Sets the volatility target of the recommended portfolio."
            value={risk}
            onChange={setRisk}
          />
          <Preference
            label="Green preference"
            hint="Sets how green the portfolio must be relative to the universe."
            value={green}
            onChange={setGreen}
          />
          <IndustryFilter market={market} onChange={setIndustries} />
          <div className="preference-amounts">
            <label>
              <span>Portfolio value (HKD)</span>
              <input type="number" min={1} step={1000} value={capital} onChange={(e) => setCapital(Number(e.target.value) || 0)} />
            </label>
            <label>
              <span>New capital to add</span>
              <input type="number" min={0} step={1000} value={newCapital} onChange={(e) => setNewCapital(Number(e.target.value) || 0)} />
            </label>
          </div>
          <div className="editor-actions">
            <button className="primary" onClick={run} disabled={loading || capital <= 0 || portfolio.length === 0 || industries?.length === 0}>
              {loading ? "Optimising…" : "Get recommendations"} <ArrowRight size={16} />
            </button>
          </div>
          {error && (
            <p className="form-help" role="alert">
              <WarningCircle size={15} /> {error}
            </p>
          )}
        </section>
        <section className="panel comparison-panel">
          <div className="section-top">
            <div>
              <h2>{result ? "Recommended trades" : "Nothing recommended yet"}</h2>
              <p>
                {result
                  ? `${trades.length} trades · ${pct(result.turnover, 0)} turnover · ${result.params.n_candidates} candidates considered`
                  : "Choose your preferences and run the engine."}
              </p>
            </div>
          </div>
          {result && (
            <>
              <div className="esg-scorecard-grid">
                <div className="esg-scorecard-card">
                  <span>Volatility (annual)</span>
                  <strong>
                    {pct(result.before.ann_vol)} → {pct(result.after.ann_vol)}
                  </strong>
                  <small className="neutral">Target {pct(result.params.vol_target_ann, 0)}</small>
                </div>
                <div className="esg-scorecard-card">
                  <span>Greenness · g</span>
                  <strong>
                    {result.before.g_avg?.toFixed(2) ?? "—"} → {result.after.g_avg?.toFixed(2) ?? "—"}
                  </strong>
                  <small className="positive">Closer to zero is greener</small>
                </div>
                <div className="esg-scorecard-card">
                  <span>Model-implied return</span>
                  <strong>
                    {pct(result.before.ann_ret)} → {pct(result.after.ann_ret)}
                  </strong>
                  <small className="neutral">Factor-model estimate, not a forecast</small>
                </div>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Action</th>
                      <th>Amount (HKD)</th>
                      <th>Weight</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t) => (
                      <tr key={t.firm_id}>
                        <td>
                          <strong>{names.get(t.firm_id)?.name ?? t.firm_id}</strong>
                          <br />
                          <small>{t.firm_id}</small>
                        </td>
                        <td>
                          <span className={`badge ${t.side === "buy" ? "mint" : "amber"}`}>
                            {t.side === "buy" ? "Buy" : "Sell"}
                          </span>
                        </td>
                        <td>{money(t.capital_delta)}</td>
                        <td>
                          {pct(t.w_current)} → {pct(t.w_target)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {kept.length > 0 && (
                <p className="muted small">
                  Kept unchanged (outside the selected industries): {kept.map((t) => names.get(t.firm_id)?.name ?? t.firm_id).join(", ")}
                </p>
              )}
              {result.unmodeled.length > 0 && (
                <p className="muted small">
                  Kept unchanged (no return history in the model): {result.unmodeled.map((u) => u.firm_id).join(", ")}
                </p>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
