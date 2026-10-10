import { useId, useState } from "react";
import styles from "./AnalysisDrawer.module.css";

// Frozen historical example, transcribed from market-regression-60months.csv.
// Columns: month, market excess return, CLP (0002.HK) excess return.
const months: [string, number, number][] = [
  ["2021-08", 0.01, -0.03054833204282581],
  ["2021-09", -0.0393, -0.02753043438436953],
  ["2021-10", 0.038599999999999995, 0.01533341671292443],
  ["2021-11", -0.056799999999999996, 0.0032828518845080534],
  ["2021-12", 0.022400000000000003, 0.03923542484631025],
  ["2022-01", -0.049699999999999994, -0.006348863161000917],
  ["2022-02", 0.0163, 0.016612979580968634],
  ["2022-03", 0.051, -0.025239501221944405],
  ["2022-04", -0.051699999999999996, 0.0019648928528912535],
  ["2022-05", -0.0052, 0.022575592765014828],
  ["2022-06", -0.07429999999999999, -0.16189861670064493],
  ["2022-07", 0.0308, 0.020705242789154667],
  ["2022-08", -0.010700000000000001, 0.016145193846302655],
  ["2022-09", -0.105, -0.117003571716066],
  ["2022-10", -0.0125, -0.11434712307392239],
  ["2022-11", 0.1418, 0.07110370220156938],
  ["2022-12", 0.0079, 0.01403016885291616],
  ["2023-01", 0.0709, 0.018448972589135307],
  ["2023-02", -0.0663, -0.04893255769284181],
  ["2023-03", 0.0011, 0.039003902113599546],
  ["2023-04", -0.0001, 0.026482584915930977],
  ["2023-05", -0.059800000000000006, -0.026716638106424058],
  ["2023-06", 0.031400000000000004, 0.07548966146054559],
  ["2023-07", 0.0364, 0.037371877967784684],
  ["2023-08", -0.065, -0.03523285473844645],
  ["2023-09", -0.0354, -0.05227094736462681],
  ["2023-10", -0.050499999999999996, -0.01677955321963916],
  ["2023-11", 0.0475, 0.05673542172073116],
  ["2023-12", 0.0785, 0.06800712966579311],
  ["2024-01", -0.0501, -0.04038657325596258],
  ["2024-02", 0.0109, 0.04567928285310761],
  ["2024-03", 0.0098, -0.030689687143488437],
  ["2024-04", -0.0103, -0.015125007717304923],
  ["2024-05", 0.029900000000000003, 0.008164715303767792],
  ["2024-06", -0.0108, 0.016110144636931827],
  ["2024-07", 0.0069, 0.05809927940226295],
  ["2024-08", 0.032799999999999996, 0.03770559664131681],
  ["2024-09", 0.07200000000000001, -0.010063334910239693],
  ["2024-10", -0.0541, -0.04456807258092575],
  ["2024-11", 0.0131, -0.015355084946683358],
  ["2024-12", -0.046900000000000004, 0.007588009897614248],
  ["2025-01", 0.020099999999999996, -0.015167892666870094],
  ["2025-02", -0.009899999999999999, -0.006393577303443618],
  ["2025-03", -0.013300000000000001, -0.0006198656529625007],
  ["2025-04", 0.027999999999999997, 0.04224145212762914],
  ["2025-05", 0.0518, -2.9388205295940387e-05],
  ["2025-06", 0.0395, -0.0006694582830785584],
  ["2025-07", 0.018799999999999997, 0.027513613339860635],
  ["2025-08", 0.0461, -0.03754899975373102],
  ["2025-09", 0.0074, -0.015128023203730554],
  ["2025-10", -0.0051, 0.02500462313385724],
  ["2025-11", -0.0127, 0.02264101023156007],
  ["2025-12", 0.0128, 0.026696710212141442],
  ["2026-01", 0.0632, 0.06256199301323406],
  ["2026-02", 0.0431, 0.0005806161211316073],
  ["2026-03", -0.0872, 0.005335472127911425],
  ["2026-04", 0.0521, 0.018868682929619532],
  ["2026-05", 0.0037, 0.015541829073254623],
  ["2026-06", -0.040999999999999995, -0.03791517721487157],
  ["2026-07", 0.0527, 0.06363995803433217],
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
      <p className={styles.exampleNote}>60 monthly observations · Aug 2021–Jul 2026. A single-factor illustration, separate from your live portfolio analysis.</p>
      <svg viewBox="0 0 420 245" role="img" aria-labelledby={captionId}>
        <title id={captionId}>CLP historical excess returns against market excess returns, with a fitted line. Two unusual residuals: June and October 2022. All 60 months are retained.</title>
        {[-.15, 0, .05].map(tick => <g key={tick}><line x1="50" x2="386" y1={py(tick)} y2={py(tick)} stroke="#edf1f4" /><text x="43" y={py(tick) + 3} textAnchor="end">{Math.round(tick * 100)}%</text></g>)}
        <line x1="50" x2="386" y1="194" y2="194" stroke="#cfdce3" />
        <line x1="50" x2="50" y1="30" y2="194" stroke="#cfdce3" />
        {[-.1, 0, .1].map(tick => <text key={tick} x={px(tick)} y="210" textAnchor="middle">{Math.round(tick * 100)}%</text>)}
        <text x="50" y="17">CLP excess return</text>
        <text x="218" y="236" textAnchor="middle">Market excess return</text>
        <line x1={px(-.12)} y1={py(intercept + beta * -.12)} x2={px(.16)} y2={py(intercept + beta * .16)} stroke="#287355" strokeWidth="2" />
        {points.map(point => <g key={point.month}>
          {point.flagged && <line x1={px(point.x)} x2={px(point.x)} y1={py(point.y)} y2={py(intercept + beta * point.x)} stroke="#b78645" strokeDasharray="3 3" />}
          <circle cx={px(point.x)} cy={py(point.y)} r={point.month === selectedMonth ? 6 : point.flagged ? 4.5 : 3} fill={point.flagged ? "#b78645" : "#789caf"} fillOpacity={point.flagged ? 1 : .65}
            className={point.flagged ? styles.selectablePoint : undefined} onClick={point.flagged ? () => setSelectedMonth(point.month) : undefined}><title>{point.month}: market {pct(point.x)}, CLP {pct(point.y)}{point.flagged ? "; unusual residual; use month buttons below to inspect" : ""}</title></circle>
          {point.flagged && <text x={px(point.x) + 8} y={py(point.y) + 4} className={styles.flagLabel}>{point.month}</text>}
        </g>)}
      </svg>
      <div className={styles.indicators}><div><span>Correlation</span><strong>{correlation.toFixed(2)}</strong></div><div><span>Variation explained</span><strong>{Math.round(correlation ** 2 * 100)}%</strong></div><div><span>Market sensitivity</span><strong>{beta.toFixed(2)}</strong></div></div>
      <p className={styles.note}>Dots are monthly observations; the green line is the fitted relationship. Orange marks two unusual residuals, not errors. All observations remain included.</p>
      <details className={styles.industryDetails}><summary>Inspect the two unusual months</summary>
        <div className={styles.flagControls}>{points.filter(point => point.flagged).map(point => <button type="button" key={point.month} aria-pressed={selectedMonth === point.month} onClick={() => setSelectedMonth(point.month)}>{point.month}</button>)}</div>
        <p className={styles.exampleNote} aria-live="polite">{selected ? <><strong>{selected.month}</strong> · Market {pct(selected.x)} · CLP {pct(selected.y)}.<br />CLP was {Math.abs((selected.y - intercept - beta * selected.x) * 100).toFixed(1)} percentage points {selected.y < intercept + beta * selected.x ? "below" : "above"} the fitted line. This month remains included.</> : "Choose a month to inspect its returns and distance from the fitted line."}</p>
      </details>
      <p className={styles.note}>A positive relationship explains about 37% of historical variation here. This does not establish causation or predict future performance. The recommendation uses multiple factors.</p>
      <details className={styles.industryDetails}><summary>Sample & technical note</summary><p className={styles.exampleNote}>Source: market-regression-60months.csv. Ordinary least squares with an intercept; unusual points have absolute studentized residuals above 2. This illustrative sample mixes HKD stock returns with USD factor returns, so its market sensitivity is not a currency-consistent investment estimate.</p></details>
    </div>
  </details>;
}
