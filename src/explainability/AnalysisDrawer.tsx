import { useEffect, useId, useRef } from "react";
import { ArrowRight, CheckCircle, Info, X } from "@phosphor-icons/react";
import type { Recommendation, recommendPortfolio } from "../api";
import { tradeAction } from "../live";
import { money, percent } from "../portfolio";
import HistoricalExample from "./HistoricalExample";
import styles from "./AnalysisDrawer.module.css";

export type AnalysisInput = {
  request: Parameters<typeof recommendPortfolio>[0];
  currency: string;
  cashValue: number;
};
export type AnalysisSnapshot =
  | { input: AnalysisInput; status: "waiting" }
  | { input: AnalysisInput; status: "completed"; result: Recommendation }
  | { input: AnalysisInput; status: "error"; error: string };

function MetricChange({ label, before, after, format, hint }: {
  label: string; before: number | null; after: number | null; format: (value: number) => string; hint: string;
}) {
  const valid = before != null && after != null && Number.isFinite(before) && Number.isFinite(after);
  const low = valid ? Math.min(0, before, after) : 0;
  const high = valid ? Math.max(0, before, after) : 1;
  const spread = high - low || 1;
  const position = (value: number) => 14 + ((value - low) / spread) * 272;
  return <div className={styles.metric}>
    <div className={styles.metricHeading}><strong>{label}</strong><span>{valid ? `${format(before)} → ${format(after)}` : "Unavailable"}</span></div>
    {valid && <svg viewBox="0 0 300 28" role="img" aria-label={`${label}: current ${format(before)}, recommended ${format(after)}`}>
      <line x1="14" y1="14" x2="286" y2="14" stroke="#e3eaf0" strokeWidth="3" />
      <line x1={position(before)} y1="14" x2={position(after)} y2="14" stroke="#7f9b90" strokeWidth="3" />
      <circle cx={position(before)} cy="14" r="6" fill="#fff" stroke="#71869a" strokeWidth="2" />
      <circle cx={position(after)} cy="14" r="5" fill="#287355" />
    </svg>}
    <small>{hint}</small>
  </div>;
}

function Changes({ result, currency }: { result: Recommendation; currency: string }) {
  const traded = result.trades.filter(t => t.side === "buy" || t.side.startsWith("sell"));
  const largest = [...traded].sort((a, b) => Math.abs(b.capital_delta) - Math.abs(a.capital_delta)).slice(0, 3);
  return <>
    <div className={styles.key}><span><i />Current</span><span><i />Recommended</span></div>
    <MetricChange label="USD excess return · annual" before={result.before.ann_ret} after={result.after.ann_ret} format={v => percent(v, 1)} hint="Model-implied return above the risk-free rate, on a USD basis; monetary holdings remain in HKD." />
    <MetricChange label="USD volatility · annual" before={result.before.ann_vol} after={result.after.ann_vol} format={v => percent(v, 1)} hint="USD-based risk. Lower means less modeled fluctuation." />
    <MetricChange label="Largest position" before={result.before.top_weight} after={result.after.top_weight} format={v => percent(v, 1)} hint="A smaller largest holding can reduce concentration." />
    <details className={styles.industryDetails}><summary>Environmental measure</summary><MetricChange label="Modeled greenness" before={result.before.g_avg} after={result.after.g_avg} format={v => v.toFixed(2)} hint="Higher is greener. This industry-weighted model measure is distinct from the company E-score." /></details>
    <p className={styles.note}>Each line uses its own scale. Risk and return cover holdings with estimated factor exposures, weighted against total portfolio capital.</p>
    <div className={styles.tradeSummary}><span><strong>{traded.filter(t => t.side === "buy").length}</strong> buys</span><span><strong>{traded.filter(t => t.side.startsWith("sell")).length}</strong> sells</span><span><strong>{percent(result.turnover, 0)}</strong> turnover</span></div>
    {largest.length > 0 && <div className={styles.movements}><h4>Largest proposed trades</h4>{largest.map(t => <div key={t.firm_id}><span><strong>{t.firm_id}</strong><small>{tradeAction(t.side, t.w_current, t.w_target).label}</small></span><span>{t.capital_delta > 0 ? "+" : "−"}{money(Math.abs(t.capital_delta), currency)}</span></div>)}</div>}
    <p className={styles.note}>These are the engine’s returned changes. The response does not identify a single reason for each trade. Recommendations have not executed any trades.</p>
    {result.unmodeled.length > 0 && <div className={styles.coverage}><strong>{result.unmodeled.length} holdings could not be modeled</strong><p>The engine keeps their capital unchanged. Their missing return histories leave risk and return incomplete.</p><details><summary>View affected holdings</summary><ul>{result.unmodeled.map(h => <li key={h.firm_id}>{h.firm_id} · {money(h.capital, currency)}</li>)}</ul></details></div>}
  </>;
}

export default function AnalysisDrawer({ input, snapshot, onClose }: {
  input: AnalysisInput; snapshot: AnalysisSnapshot | null; onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  // A changed input invalidates the displayed result immediately, before the request effect runs.
  const current = snapshot?.input === input ? snapshot : null;
  const result = current?.status === "completed" ? current.result : null;
  const request = input.request;
  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = dialogRef.current!;
    const overflow = document.body.style.overflow;
    const paddingRight = document.body.style.paddingRight;
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    const currentPadding = parseFloat(window.getComputedStyle(document.body).paddingRight) || 0;
    dialog.showModal();
    document.body.style.overflow = "hidden";
    if (scrollbarWidth > 0) document.body.style.paddingRight = `${currentPadding + scrollbarWidth}px`;
    return () => {
      dialog.close();
      document.body.style.overflow = overflow;
      document.body.style.paddingRight = paddingRight;
      if (opener?.isConnected) opener.focus();
    };
  }, []);
  return <dialog ref={dialogRef} className={styles.drawer} aria-labelledby={titleId}
    onCancel={event => { event.preventDefault(); onClose(); }}
    onKeyDown={event => {
      if (event.key !== "Tab") return;
      const focusable = [...event.currentTarget.querySelectorAll<HTMLElement>("button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]")]
        .filter(element => element.tabIndex >= 0 && element.getClientRects().length > 0 && window.getComputedStyle(element).visibility !== "hidden");
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    }}
    onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div className={styles.surface}>
      <header className={styles.header}><div><span>BEHIND THE RECOMMENDATION</span><h2 id={titleId}>Analysis details</h2></div><button type="button" className={styles.close} aria-label="Close analysis details" onClick={onClose} autoFocus><X size={21} /></button></header>
      <div className={styles.body}>
        <div className={styles.status} role="status" aria-live="polite">{current?.status === "error" ? <><Info size={18} /><span><strong>Analysis unavailable</strong>{current.error}</span></> : result ? <><CheckCircle size={18} /><span><strong>Analysis completed</strong>Showing the result for the inputs below.</span></> : <><Info size={18} /><span><strong>Waiting for the engine</strong>Your recommendation is being calculated. Results will appear when the request completes.</span></>}</div>
        <section className={styles.section}><h3><span>01</span>Inputs & preferences</h3><p>These are the submitted inputs. Unsubmitted edits in Setup are not included.</p>
          <div className={styles.preferences}><div><span>Risk preference</span><strong>Level {request.risk_score} <small>/ 5</small></strong></div><div><span>Green preference</span><strong>Level {request.green_score} <small>/ 5</small></strong></div></div>
          <dl className={styles.inputs}><div><dt>Current holdings sent</dt><dd>{Object.keys(request.holdings).length} · {money(Object.values(request.holdings).reduce((sum, value) => sum + value, 0), input.currency)}</dd></div><div><dt>New capital allowed</dt><dd>{money(request.max_new_capital, input.currency)}</dd></div><div><dt>Candidate markets</dt><dd>{request.market === "all" ? "Hong Kong & Taiwan" : request.market === "hk" ? "Hong Kong" : "Taiwan"}</dd></div></dl>
          <details className={styles.industryDetails}><summary>{request.filters ? `${request.filters.include_industries.length} selected industries` : "All industries"}</summary><p>{request.filters?.include_industries.join(" · ") ?? "No industry filter was sent."}</p></details>
          {input.cashValue > 0 && <p className={styles.note}>Cash rows ({money(input.cashValue, input.currency)}) are not sent to the optimizer and carry over unchanged.</p>}
        </section>
        <section className={styles.section}><h3><span>02</span>How the method works</h3>
          <div className={styles.method}><div><strong>Estimate</strong><span>Historical returns reveal exposure to market and other factors.</span></div><ArrowRight size={17} aria-hidden="true" /><div><strong>Balance</strong><span>The engine weighs modeled return, risk, greenness and a penalty for trading.</span></div></div>
          <p>Risk preference sets an annual volatility target. Green preference guides portfolio greenness among eligible companies. Industry choices limit what can be bought or rebalanced; existing holdings outside the filter stay unchanged.</p>
          {result && <div className={styles.targets}><span>Volatility target <strong>{percent(result.params.vol_target_ann, 0)}</strong></span><span>Candidates considered <strong>{result.params.n_candidates}</strong></span></div>}
          <p className={styles.note}>Targets guide the optimization and are not promises. Environmental greenness is not a full ESG rating.</p>
          <HistoricalExample />
        </section>
        <section className={styles.section}><h3><span>03</span>What actually changed</h3>{result ? <Changes result={result} currency={input.currency} /> : <p>{current?.status === "error" ? "No completed result is available for these inputs." : "Before-and-after metrics will appear once the engine returns a result."}</p>}</section>
      </div>
    </div>
  </dialog>;
}
