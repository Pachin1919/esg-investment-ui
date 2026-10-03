// Live markets view: real scores from the ESG Exposure Engine backend, with the
// Hong Kong / Taiwan market switch (the backend serves both via ?market=hk|tw).
// Purely additive: it touches no demo composition and needs only VITE_API_BASE.
import { useEffect, useState } from "react";
import { Leaf, WarningCircle } from "@phosphor-icons/react";
import { api, API_BASE } from "./api";
import type { Firm, GreennessResponse, Market } from "./api";

function MarketSwitch({ market, onChange }: { market: Market; onChange: (m: Market) => void }) {
  return (
    <div className="badge" role="group" aria-label="Market">
      {(["hk", "tw"] as Market[]).map((m) => (
        <button
          key={m}
          type="button"
          className={m === market ? "active" : undefined}
          aria-pressed={m === market}
          onClick={() => onChange(m)}
        >
          {m === "hk" ? "Hong Kong" : "Taiwan"}
        </button>
      ))}
    </div>
  );
}

export function LiveDataPage() {
  const [market, setMarket] = useState<Market>("hk");
  const [greenness, setGreenness] = useState<GreennessResponse | null>(null);
  const [firms, setFirms] = useState<Firm[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!API_BASE) return;
    setLoading(true);
    setError(null);
    Promise.all([api.greenness(market), api.firms()])
      .then(([g, f]) => {
        setGreenness(g);
        setFirms(f);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [market]);

  const twCount = firms?.filter((f) => f.firm_id.endsWith(".TW") || f.firm_id.endsWith(".TWO")).length ?? 0;

  if (!API_BASE) {
    return (
      <section className="panel" aria-label="Backend not configured">
        <h2>Live markets need the backend URL</h2>
        <p>
          Set <code>VITE_API_BASE</code> to the ESG Exposure Engine API (see <code>.env.example</code>),
          e.g. a local <code>make api</code> on port 8000 or the deployed service. The backend also
          needs this origin in <code>ESGX_CORS_ORIGINS</code>.
        </p>
      </section>
    );
  }

  return (
    <section aria-label="Live markets">
      <header className="green-section-title">
        <div>
          <h1>Live markets</h1>
          <p>
            Real greenness scores from the ESG Exposure Engine — {firms?.length ?? "…"} firms tracked
            ({twCount} in Taiwan). g = −(10 − E score) · E weight / 100 (Pástor–Stambaugh–Taylor 2022).
          </p>
        </div>
        <MarketSwitch market={market} onChange={setMarket} />
      </header>

      {loading && <p className="badge blue">Loading {market === "hk" ? "Hong Kong" : "Taiwan"}…</p>}
      {error && (
        <p className="badge amber" role="alert">
          <WarningCircle size={15} /> Backend error: {error}
        </p>
      )}

      {greenness && !loading && !error && (
        <div className="panel table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Ticker</th>
                <th scope="col">Name</th>
                <th scope="col">Sector</th>
                <th scope="col" style={{ textAlign: "right" }}>E score</th>
                <th scope="col" style={{ textAlign: "right" }}>E weight</th>
                <th scope="col" style={{ textAlign: "right" }}>g</th>
              </tr>
            </thead>
            <tbody>
              {greenness.firms.slice(0, 25).map((r) => (
                <tr key={r.firm_id}>
                  <td>
                    <code>{r.firm_id}</code>
                  </td>
                  <td>{r.name ?? ""}</td>
                  <td>{r.sector ?? ""}</td>
                  <td style={{ textAlign: "right" }}>{r.e_score.toFixed(1)}</td>
                  <td style={{ textAlign: "right" }}>{r.e_weight.toFixed(0)}</td>
                  <td style={{ textAlign: "right" }}>{r.g.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="table-foot">
            <Leaf size={14} /> Brownest 25 of {greenness.firms.length} scored firms,{" "}
            {market === "hk" ? "Hong Kong" : "Taiwan"} {greenness.year}. Source: ESG Exposure Engine API
            (walk-based E score from scope 1+2 intensity).
          </p>
        </div>
      )}
    </section>
  );
}
