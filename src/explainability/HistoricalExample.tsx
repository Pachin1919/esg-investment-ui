import { useId, useState } from "react";
import styles from "./AnalysisDrawer.module.css";

// Frozen USD-consistent example from the stored CLP prices, French USD factors and ECB FX.
// Recomputed 2026-10-10; columns: month, market USD excess return, CLP USD excess return.
const months: [string, number, number][] = [
  ["2021-08", 0.01, -0.031370587521656],
  ["2021-09", -0.0393, -0.02841692668284035],
  ["2021-10", 0.038599999999999995, 0.01684786542500727],
  ["2021-11", -0.056799999999999996, 0.0006708397914432229],
  ["2021-12", 0.022400000000000003, 0.03899555053200164],
  ["2022-01", -0.049699999999999994, -0.00620869693241366],
  ["2022-02", 0.0163, 0.014479424494829196],
  ["2022-03", 0.051, -0.02714427862482105],
  ["2022-04", -0.051699999999999996, -0.00019313822926070312],
  ["2022-05", -0.0052, 0.02254952161262743],
  ["2022-06", -0.07429999999999999, -0.16178102725398896],
  ["2022-07", 0.0308, 0.0201456921466078],
  ["2022-08", -0.010700000000000001, 0.01630084238271802],
  ["2022-09", -0.105, -0.11712757152130081],
  ["2022-10", -0.0125, -0.11432449920608226],
  ["2022-11", 0.1418, 0.07779462783090331],
  ["2022-12", 0.0079, 0.014565125078682097],
  ["2023-01", 0.0709, 0.013232951292266041],
  ["2023-02", -0.0663, -0.050416085032716815],
  ["2023-03", 0.0011, 0.0389242106130177],
  ["2023-04", -0.0001, 0.026482584915930977],
  ["2023-05", -0.059800000000000006, -0.024808881971767067],
  ["2023-06", 0.031400000000000004, 0.07514530467176783],
  ["2023-07", 0.0364, 0.04247516382437383],
  ["2023-08", -0.065, -0.040830412352493684],
  ["2023-09", -0.0354, -0.050654000641424585],
  ["2023-10", -0.050499999999999996, -0.015870377492759064],
  ["2023-11", 0.0475, 0.05841993616528969],
  ["2023-12", 0.0785, 0.06800712966579311],
  ["2024-01", -0.0501, -0.04134854342204548],
  ["2024-02", 0.0109, 0.04460619811274411],
  ["2024-03", 0.0098, -0.030415949452009455],
  ["2024-04", -0.0103, -0.014542919667830573],
  ["2024-05", 0.029900000000000003, 0.008488520487934317],
  ["2024-06", -0.0108, 0.01725983912307027],
  ["2024-07", 0.0069, 0.05766401645195679],
  ["2024-08", 0.032799999999999996, 0.03960400255474297],
  ["2024-09", 0.07200000000000001, -0.005800643857579165],
  ["2024-10", -0.0541, -0.04574038234160281],
  ["2024-11", 0.0131, -0.01657442680010956],
  ["2024-12", -0.046900000000000004, 0.009827648572724038],
  ["2025-01", 0.020099999999999996, -0.01849145718393471],
  ["2025-02", -0.009899999999999999, -0.004548000186742981],
  ["2025-03", -0.013300000000000001, -0.0007101016851058101],
  ["2025-04", 0.027999999999999997, 0.04528845290351541],
  ["2025-05", 0.0518, -0.011049426417029858],
  ["2025-06", 0.0395, -0.001614719497706238],
  ["2025-07", 0.018799999999999997, 0.027500479408480608],
  ["2025-08", 0.0461, -0.030756286954380683],
  ["2025-09", 0.0074, -0.013350095933496262],
  ["2025-10", -0.0051, 0.026341617471036506],
  ["2025-11", -0.0127, 0.02104651744918218],
  ["2025-12", 0.0128, 0.026564378474748754],
  ["2026-01", 0.0632, 0.05927317931094056],
  ["2026-02", 0.0431, -0.001394416342825975],
  ["2026-03", -0.0872, 0.0033291101612568236],
  ["2026-04", 0.0521, 0.01969048079792736],
  ["2026-05", 0.0037, 0.01520382448450707],
  ["2026-06", -0.040999999999999995, -0.03867812780035794],
  ["2026-07", 0.0527, 0.06344951077540104],
];

// Ordinary least squares with an intercept; no observations are excluded.
const count = months.length;
const meanX = months.reduce((sum, [, x]) => sum + x, 0) / count;
const meanY = months.reduce((sum, [, , y]) => sum + y, 0) / count;
const sxx = months.reduce((sum, [, x]) => sum + (x - meanX) ** 2, 0);
const syy = months.reduce((sum, [, , y]) => sum + (y - meanY) ** 2, 0);
const sxy = months.reduce((sum, [, x, y]) => sum + (x - meanX) * (y - meanY), 0);
const beta = sxy / sxx;
const intercept = meanY - beta * meanX;
const correlation = sxy / Math.sqrt(sxx * syy);
const residualVariance = months.reduce((sum, [, x, y]) => sum + (y - intercept - beta * x) ** 2, 0) / (count - 2);
const points = months.map(([month, x, y]) => {
  const leverage = 1 / count + (x - meanX) ** 2 / sxx;
  const residual = (y - intercept - beta * x) / Math.sqrt(residualVariance * (1 - leverage));
  return { month, x, y, flagged: Math.abs(residual) > 2 };
});
const flagged = points.filter(point => point.flagged);
const variationExplained = Math.round(correlation ** 2 * 100);
const px = (x: number) => 50 + ((x + .12) / .28) * 336;
const py = (y: number) => 194 - ((y + .18) / .28) * 164;
const pct = (value: number) => `${(value * 100).toFixed(1)}%`;

export default function HistoricalExample() {
  const captionId = useId();
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const selected = points.find(point => point.month === selectedMonth);
  return <details className={styles.historical}>
    <summary>Explore a historical method example</summary>
    <div>
      <h4>CLP · 0002.HK</h4>
      <p className={styles.exampleNote}>Historical illustration · {count} monthly observations · Aug 2021–Jul 2026. CLP and market excess returns both use USD. This single-factor example is separate from your portfolio recommendation.</p>
      <svg viewBox="0 0 420 245" role="img" aria-labelledby={captionId}>
        <title id={captionId}>CLP historical USD excess returns against market USD excess returns, with a fitted line. {flagged.length} unusual residuals: {flagged.map(point => point.month).join(", ")}. All {count} months are retained.</title>
        {[-.15, 0, .05].map(tick => <g key={tick}><line x1="50" x2="386" y1={py(tick)} y2={py(tick)} stroke="#edf1f4" /><text x="43" y={py(tick) + 3} textAnchor="end">{Math.round(tick * 100)}%</text></g>)}
        <line x1="50" x2="386" y1="194" y2="194" stroke="#cfdce3" />
        <line x1="50" x2="50" y1="30" y2="194" stroke="#cfdce3" />
        {[-.1, 0, .1].map(tick => <text key={tick} x={px(tick)} y="210" textAnchor="middle">{Math.round(tick * 100)}%</text>)}
        <text x="50" y="17">CLP excess return · USD</text>
        <text x="218" y="236" textAnchor="middle">Market excess return · USD</text>
        <line x1={px(-.12)} y1={py(intercept + beta * -.12)} x2={px(.16)} y2={py(intercept + beta * .16)} stroke="#287355" strokeWidth="2" />
        {points.map(point => <g key={point.month}>
          {point.flagged && <line x1={px(point.x)} x2={px(point.x)} y1={py(point.y)} y2={py(intercept + beta * point.x)} stroke="#b78645" strokeDasharray="3 3" />}
          <circle cx={px(point.x)} cy={py(point.y)} r={point.month === selectedMonth ? 6 : point.flagged ? 4.5 : 3} fill={point.flagged ? "#b78645" : "#789caf"} fillOpacity={point.flagged ? 1 : .65}
            className={point.flagged ? styles.selectablePoint : undefined} onClick={point.flagged ? () => setSelectedMonth(point.month) : undefined}><title>{point.month}: market {pct(point.x)}, CLP {pct(point.y)}{point.flagged ? "; unusual residual; use month buttons below to inspect" : ""}</title></circle>
          {point.flagged && <text x={px(point.x) + 8} y={py(point.y) + 4} className={styles.flagLabel}>{point.month}</text>}
        </g>)}
      </svg>
      <div className={styles.indicators}><div><span>Correlation</span><strong>{correlation.toFixed(2)}</strong></div><div><span>Variation explained</span><strong>{variationExplained}%</strong></div><div><span>Market sensitivity</span><strong>{beta.toFixed(2)}</strong></div></div>
      <p className={styles.note}>Dots are monthly observations; the green line is the fitted relationship. Orange marks {flagged.length} unusual residuals. All observations remain included.</p>
      <details className={styles.industryDetails}><summary>Inspect {flagged.length} unusual months</summary>
        <div className={styles.flagControls}>{flagged.map(point => <button type="button" key={point.month} aria-pressed={selectedMonth === point.month} onClick={() => setSelectedMonth(point.month)}>{point.month}</button>)}</div>
        <p className={styles.exampleNote} aria-live="polite">{selected ? <><strong>{selected.month}</strong> · Market {pct(selected.x)} · CLP {pct(selected.y)}.<br />CLP was {Math.abs((selected.y - intercept - beta * selected.x) * 100).toFixed(1)} percentage points {selected.y < intercept + beta * selected.x ? "below" : "above"} the fitted line. This month remains included.</> : "Choose a month to inspect its returns and distance from the fitted line."}</p>
      </details>
      <p className={styles.note}>The fitted relationship explains about {variationExplained}% of historical variation here. This does not establish causation or predict future performance. The recommendation uses multiple factors.</p>
      <details className={styles.industryDetails}><summary>Sample & technical note</summary><p className={styles.exampleNote}>Sources: stored CLP monthly prices, Kenneth R. French Asia Pacific ex Japan USD factors and risk-free rates, and ECB USD/HKD reference FX. FX provenance is recorded in docs/fx-snapshot-provenance.json. Ordinary least squares includes an intercept; unusual points have absolute studentized residuals above 2. Both axes use USD excess returns.</p></details>
    </div>
  </details>;
}
