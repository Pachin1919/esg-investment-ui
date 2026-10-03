import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  ArrowsLeftRight,
  ChartDonut,
  Check,
  CheckCircle,
  Compass,
  DownloadSimple,
  FileText,
  Info,
  Leaf,
  MagnifyingGlass,
  SlidersHorizontal,
  Sparkle,
  SquaresFour,
  UploadSimple,
  WarningCircle,
  X,
} from "@phosphor-icons/react";
import {
  alternative,
  capabilities,
  companies,
  coverage,
} from "./data";
import type { Company } from "./data";
import {
  analyzePortfolioApi,
  downloadCsvFile,
  fetchCompanies,
  fetchHealth,
  fetchSampleCsv,
  uploadPortfolioCsv,
} from "./api";
import type { PortfolioAnalysis } from "./api";

type View = "portfolio" | "explore" | "method";
type DemoState = "partial" | "loading" | "empty" | "error";
const navItems = [
  { id: "portfolio" as View, label: "My portfolio", icon: SquaresFour },
  { id: "explore" as View, label: "Explore changes", icon: ArrowsLeftRight },
  { id: "method" as View, label: "Our methodology", icon: Compass },
];

function Logo({ version }: { version: string }) {
  return (
    <a className="brand" href={"?v=" + version} aria-label="Green Street home">
      <span className="brand-symbol">
        <Leaf size={24} weight="fill" />
      </span>
      Green Street
    </a>
  );
}
function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
function Score({ value }: { value: number | null }) {
  return value === null ? (
    <span className="missing">Not available</span>
  ) : (
    <span className={`score ${value < 5 ? "caution" : ""}`}>
      <span>{value.toFixed(1)}</span>
      <small>/ 10</small>
    </span>
  );
}
function CompanyMark({ company }: { company: Company }) {
  return (
    <span
      className="company-mark"
      style={{ "--company-color": company.color } as React.CSSProperties}
    >
      {company.initials}
    </span>
  );
}

function Modal({
  children,
  title,
  onClose,
  wide = false,
}: {
  children: ReactNode;
  title: string;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const opener = useRef(document.activeElement as HTMLElement | null);
  useEffect(() => {
    const el = ref.current!;
    el.showModal();
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      el.close();
      document.body.style.overflow = original;
      requestAnimationFrame(() => {
        if (!el.isConnected && opener.current?.isConnected)
          opener.current.focus({ preventScroll: true });
      });
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={wide ? "modal wide" : "modal drawer"}
      aria-labelledby="dialog-title"
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-head">
        <span id="dialog-title">{title}</span>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Close dialog"
        >
          <X size={21} />
        </button>
      </div>
      {children}
    </dialog>
  );
}

function AllocationRing({
  weights,
  companiesList = companies,
  large = false,
}: {
  weights?: number[];
  companiesList?: Company[];
  large?: boolean;
}) {
  const w = weights ?? companiesList.map((c) => c.allocation);
  let accumulated = 0;
  const stops = companiesList
    .map((c, i) => {
      const from = accumulated;
      accumulated += (w[i] ?? 0);
      return `${c.color} ${from}% ${accumulated}%`;
    })
    .join(",");
  return (
    <div
      className={`allocation-ring ${large ? "large" : ""}`}
      style={{ background: `conic-gradient(from -90deg, ${stops})` }}
      role="img"
      aria-label={`Portfolio allocation: ${companiesList.map((c, i) => `${c.name} ${w[i] ?? 0}%`).join(", ")}`}
    >
      <div className="ring-center">
        <Leaf size={24} />
        <strong>{companiesList.length}</strong>
        <span>companies</span>
      </div>
    </div>
  );
}

function ProfileChart({
  onSelect,
  companiesList = companies,
}: {
  onSelect: (c: Company) => void;
  companiesList?: Company[];
}) {
  return (
    <div className="profile-chart">
      <div className="chart-axis-title">
        Environmental score <span>Higher is greener</span>
      </div>
      <div className="plot">
        <svg viewBox="0 0 640 260" role="img" aria-labelledby="plot-title">
          <title id="plot-title">
            Company environmental score versus industry environmental
            importance. Bubble size indicates portfolio allocation.
          </title>
          <rect
            x="38"
            y="10"
            width="585"
            height="106"
            rx="3"
            fill="var(--chart-zone)"
          />
          <text x="590" y="30" textAnchor="end" fill="var(--muted)" fontSize="10" opacity="0.65">
            Transition Leader
          </text>
          <text x="590" y="215" textAnchor="end" fill="var(--muted)" fontSize="10" opacity="0.65">
            Transition Risk
          </text>
          <text x="80" y="30" textAnchor="start" fill="var(--muted)" fontSize="10" opacity="0.65">
            Clean / Low Impact
          </text>
          {[0, 2, 4, 6, 8, 10].map((n) => (
            <g key={n}>
              <line
                x1="38"
                x2="623"
                y1={230 - n * 22}
                y2={230 - n * 22}
                stroke="var(--line)"
                strokeDasharray="3 5"
              />
              <text x="21" y={234 - n * 22} textAnchor="end">
                {n}
              </text>
            </g>
          ))}
          {[0, 25, 50, 75, 100].map((n) => (
            <g key={n}>
              <line
                x1={38 + n * 5.85}
                x2={38 + n * 5.85}
                y1="10"
                y2="230"
                stroke="var(--line)"
                strokeDasharray="3 5"
              />
              <text x={38 + n * 5.85} y="252" textAnchor="middle">
                {n}
              </text>
            </g>
          ))}
          {companiesList
            .filter((c) => c.score !== null)
            .map((c) => (
              <g key={c.id}>
                <circle
                  cx={38 + c.materiality * 5.85}
                  cy={230 - c.score! * 22}
                  r={Math.sqrt(c.allocation) * 4.4}
                  fill={c.color}
                  fillOpacity=".6"
                  stroke={c.color}
                  strokeWidth="2"
                />
                <text
                  className="bubble-label"
                  x={38 + c.materiality * 5.85}
                  y={230 - c.score! * 22 + 4}
                  textAnchor="middle"
                >
                  {c.initials}
                </text>
              </g>
            ))}
        </svg>
        {companiesList
          .filter((c) => c.score !== null)
          .map((c) => (
            <button
              key={c.id}
              className="bubble-hit"
              aria-label={`Inspect ${c.name}, score ${c.score}`}
              style={{
                left: `${((38 + c.materiality * 5.85) / 640) * 100}%`,
                top: `${((230 - c.score! * 22) / 260) * 100}%`,
              }}
              onClick={() => onSelect(c)}
            />
          ))}
      </div>
      <div className="chart-bottom">
        <span>Bubble size = portfolio allocation</span>
        <span>Industry environmental importance →</span>
      </div>
      <div className="chart-legend">
        {companiesList
          .filter((c) => c.score !== null)
          .map((c) => (
            <button key={c.id} onClick={() => onSelect(c)}>
              <i style={{ background: c.color }} />
              {c.name.split(" ")[0]}
            </button>
          ))}
      </div>
    </div>
  );
}

function HoldingTable({
  query,
  onQuery,
  onSelect,
  companiesList = companies,
}: {
  query: string;
  onQuery: (q: string) => void;
  onSelect: (c: Company) => void;
  companiesList?: Company[];
}) {
  const [sort, setSort] = useState<"allocation" | "score">("allocation");
  const filtered = companiesList
    .filter((c) =>
      `${c.name} ${c.ticker} ${c.sector} ${c.region}`
        .toLowerCase()
        .includes(query.toLowerCase()),
    )
    .sort((a, b) =>
      sort === "allocation"
        ? b.allocation - a.allocation
        : (b.score ?? -1) - (a.score ?? -1),
    );
  return (
    <section className="panel holdings">
      <div className="section-top">
        <div>
          <h2>
            Your holdings <span className="count">{String(companiesList.length).padStart(2, "0")}</span>
          </h2>
          <p>See the companies behind your portfolio.</p>
        </div>
        <label className="search">
          <MagnifyingGlass size={17} />
          <input
            value={query}
            onChange={(e) => onQuery(e.target.value)}
            placeholder="Find a company"
            aria-label="Find a company"
          />
          {query && (
            <button aria-label="Clear search" onClick={() => onQuery("")}>
              <X />
            </button>
          )}
        </label>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Company</th>
              <th>Sector</th>
              <th>
                <button onClick={() => setSort("allocation")}>
                  Allocation {sort === "allocation" && <ArrowDown size={12} />}
                </button>
              </th>
              <th>
                <button onClick={() => setSort("score")}>
                  Environmental score{" "}
                  {sort === "score" && <ArrowDown size={12} />}
                </button>
              </th>
              <th>Analysis status</th>
              <th>
                <span className="sr-only">Details</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((c) => (
              <tr key={c.id}>
                <td>
                  <button
                    className="company-button"
                    onClick={() => onSelect(c)}
                  >
                    <CompanyMark company={c} />
                    <span>
                      <strong>{c.name}</strong>
                      <small>
                        {c.ticker} · {c.region}
                      </small>
                    </span>
                  </button>
                </td>
                <td className="sector-cell">{c.sector}</td>
                <td>
                  <div className="allocation-cell">
                    <span>{c.allocation}%</span>
                    <i
                      style={{
                        width: `${c.allocation * 2}px`,
                        background: c.color,
                      }}
                    />
                  </div>
                </td>
                <td>
                  <Score value={c.score} />
                </td>
                <td>
                  <Badge
                    tone={
                      c.score === null
                        ? "neutral"
                        : c.greenwasher
                          ? "amber"
                          : "mint"
                    }
                  >
                    {c.score === null
                      ? "Missing data"
                      : c.greenwasher
                        ? "⚠️ Greenwash Risk"
                        : c.greenhusher
                          ? "🌱 Quiet Action"
                          : "Complete"}
                  </Badge>
                </td>
                <td>
                  <button
                    className="icon-button"
                    aria-label={`View ${c.name}`}
                    onClick={() => onSelect(c)}
                  >
                    <ArrowUpRight size={17} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="no-results">
            <MagnifyingGlass size={24} />
            <h3>No matching companies</h3>
            <p>Try a name, sector, or market.</p>
            <button className="text-button" onClick={() => onQuery("")}>
              Clear search
            </button>
          </div>
        )}
      </div>
      <div className="table-foot">
        <span>
          {filtered.length} of {companiesList.length} companies
        </span>
        <span>Quantitative emissions & filing analysis</span>
      </div>
    </section>
  );
}

function CompanyDetail({
  company: c,
  onClose,
  onExplore,
}: {
  company: Company;
  onClose: () => void;
  onExplore: () => void;
}) {
  return (
    <Modal title="Company analysis" onClose={onClose}>
      <div className="detail-content">
        <Badge tone="blue">Fictional company · Demo data</Badge>
        <div className="detail-identity">
          <CompanyMark company={c} />
          <div>
            <h2>{c.name}</h2>
            <p>
              {c.ticker} · {c.region}
            </p>
          </div>
        </div>
        <div className="detail-summary">
          <div>
            <p>Environmental score</p>
            <Score value={c.score} />
          </div>
          <Leaf size={40} weight="duotone" />
        </div>
        {c.greenwasher && (
          <div style={{ marginTop: "8px" }}>
            <Badge tone="amber">⚠️ High Greenwash Risk · Talk outpaces Walk</Badge>
          </div>
        )}
        {c.greenhusher && (
          <div style={{ marginTop: "8px" }}>
            <Badge tone="mint">🌱 Quiet Decarbonization · Walk exceeds Talk</Badge>
          </div>
        )}
        <p className="detail-note">{c.note}</p>
        <div className="detail-facts">
          <div>
            <span>Portfolio allocation</span>
            <strong>{c.allocation}%</strong>
          </div>
          <div>
            <span>Industry importance · E_weight</span>
            <strong>{c.materiality} / 100</strong>
          </div>
          <div>
            <span>Greenness · g</span>
            <strong>
              {c.score === null
                ? "Not available"
                : ((-(10 - c.score) * c.materiality) / 100).toFixed(2)}
            </strong>
          </div>
          {c.gap !== undefined && c.gap !== null && (
            <div>
              <span>Talk–Walk Gap</span>
              <strong>{c.gap > 0 ? `+${c.gap}` : c.gap}</strong>
            </div>
          )}
        </div>
        <h3>Behind the score</h3>
        <p className="muted">Separate sample signals, each on a 0–10 scale.</p>
        {[
          {
            label: "Carbon performance",
            value: c.carbon,
            desc: "Industry-relative emissions signal",
          },
          {
            label: "Actions · Walk",
            value: c.walk,
            desc: "Documented environmental action",
          },
          {
            label: "Commitments · Talk",
            value: c.talk,
            desc: "Stated ambitions, shown separately",
          },
        ].map((m) => (
          <div className="signal" key={m.label}>
            <div>
              <strong>{m.label}</strong>
              <span>{m.value === null ? "—" : m.value.toFixed(1)}</span>
            </div>
            <div className="signal-track">
              <i style={{ width: `${(m.value ?? 0) * 10}%` }} />
            </div>
            <small>{m.desc}</small>
          </div>
        ))}
        <details className="evidence">
          <summary>
            <FileText size={18} />
            Evidence & limitations
          </summary>
          <p>
            These values are fictional UI fixtures. No source document or
            verified company evidence is attached.
          </p>
          <p>
            E_score is supplied independently for this demo; the values above do
            not reproduce a validated scoring model. Talk is not directly added
            to E_score.
          </p>
          <p>Period: FY 2025 · Method: illustrative fixture v1.</p>
        </details>
        <details className="evidence">
          <summary>
            <Info size={18} />
            How is greenness different?
          </summary>
          <p>
            g = −(10 − E_score) × E_weight / 100. A value closer to zero
            represents greater greenness under this formula. Industry importance
            is not your investment allocation.
          </p>
        </details>
        <button className="primary full" onClick={onExplore}>
          Explore allocation changes <ArrowRight size={17} />
        </button>
      </div>
    </Modal>
  );
}

function Explore({
  companiesList = companies,
  onNotice,
}: {
  companiesList?: Company[];
  onNotice?: (msg: string) => void;
}) {
  const initialWeights = companiesList.map((c) => c.allocation);
  const [weights, setWeights] = useState<number[]>(initialWeights);
  const [compared, setCompared] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<PortfolioAnalysis | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    setWeights(companiesList.map((c) => c.allocation));
    setCompared(false);
    setAnalysisResult(null);
  }, [companiesList]);

  const total = weights.reduce((a, b) => a + b, 0);
  const valid =
    weights.every((w) => Number.isFinite(w) && w >= 0 && w <= 100) &&
    Math.abs(total - 100) < 0.001;

  const change = (index: number, value: number) => {
    setWeights((old) => old.map((w, i) => (i === index ? value : w)));
    setCompared(false);
    setAnalysisResult(null);
  };

  const handleCompare = async () => {
    setCompared(true);
    const allocMap: Record<string, number> = {};
    companiesList.forEach((c, i) => {
      allocMap[c.id] = weights[i] ?? 0;
    });
    setAnalyzing(true);
    const res = await analyzePortfolioApi(allocMap);
    setAnalysisResult(res);
    setAnalyzing(false);
  };

  const exportRebalancedCsv = () => {
    const rows = ["ticker,name,allocation,e_score,e_weight"];
    companiesList.forEach((c, i) => {
      rows.push(`${c.ticker},"${c.name}",${weights[i]},${c.score ?? ""},${c.materiality}`);
    });
    downloadCsvFile("green_street_rebalanced.csv", rows.join("\n"));
    onNotice?.("Rebalanced portfolio CSV downloaded.");
  };

  return (
    <div className="explore-page enter">
      <div className="page-heading">
        <div className="eyebrow">A LITTLE CURIOSITY GOES A LONG WAY</div>
        <h1>Explore a different balance.</h1>
        <p>Adjust your holdings and see how the allocation changes.</p>
      </div>
      <div className="explore-grid">
        <section className="panel allocation-editor">
          <div className="section-top">
            <div>
              <h2>Your allocation</h2>
              <p>The original portfolio stays unchanged.</p>
            </div>
            <button
              className="text-button"
              onClick={() => {
                setWeights(companiesList.map((c) => c.allocation));
                setCompared(false);
                setAnalysisResult(null);
              }}
            >
              Reset
            </button>
          </div>
          {companiesList.map((c, i) => (
            <div className="allocation-input" key={c.id}>
              <div className="allocation-name">
                <CompanyMark company={c} />
                <div>
                  <strong>{c.name}</strong>
                  <small>Original {c.allocation}%</small>
                </div>
              </div>
              <label>
                <span className="sr-only">{c.name} allocation</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value={Number.isFinite(weights[i]) ? weights[i] : ""}
                  onChange={(e) =>
                    change(
                      i,
                      e.target.value === "" ? NaN : Number(e.target.value),
                    )
                  }
                />
                <span>%</span>
              </label>
            </div>
          ))}
          <div className={`allocation-total ${valid ? "valid" : "invalid"}`}>
            <strong>Total allocation</strong>
            <span>
              {Number.isFinite(total)
                ? `${Number(total.toFixed(2))}%`
                : "Enter all weights"}{" "}
              {valid ? <CheckCircle size={18} /> : <WarningCircle size={18} />}
            </span>
          </div>
          <p className="form-help" role="status">
            {valid
              ? "Ready to compare. Allocations add up to 100%."
              : "Enter values from 0 to 100. All allocations must total 100%."}
          </p>
          <div className="editor-actions">
            <button
              className="secondary"
              onClick={() => {
                if (companiesList.length === 5) {
                  setWeights([...alternative]);
                } else {
                  // Tilt to greener companies
                  const clean = companiesList.map((c) => (c.score !== null && c.score >= 7.0 ? 30 : 10));
                  const s = clean.reduce((a, b) => a + b, 0);
                  setWeights(clean.map((w) => Math.round((w / s) * 100)));
                }
                setCompared(false);
                setAnalysisResult(null);
              }}
            >
              <Sparkle size={16} />
              Load example
            </button>
            <button
              className="primary"
              disabled={!valid || analyzing}
              onClick={handleCompare}
            >
              {analyzing ? "Analyzing..." : "Compare allocation"} <ArrowRight size={16} />
            </button>
          </div>
        </section>
        <section className="panel comparison-panel">
          <div className="section-top">
            <div>
              <h2>
                {compared ? "Your comparison" : "Make room for possibility"}
              </h2>
              <p>
                {compared
                  ? "Original and draft, side by side."
                  : "Start with small changes. See the difference."}
              </p>
            </div>
          </div>
          {compared ? (
            <>
              <div className="compare-legend">
                <span>
                  <i />
                  Original
                </span>
                <span>
                  <i />
                  Your draft
                </span>
              </div>
              <div className="comparison-bars">
                {companiesList.map((c, i) => (
                  <div key={c.id}>
                    <div className="bar-title">
                      <strong>{c.name}</strong>
                      <span>
                        {(weights[i] ?? 0) - c.allocation > 0 ? "+" : ""}
                        {Number(((weights[i] ?? 0) - c.allocation).toFixed(2))} pp
                      </span>
                    </div>
                    <div className="compare-track">
                      <i style={{ width: `${c.allocation}%` }} />
                      <span>{c.allocation}%</span>
                    </div>
                    <div className="compare-track draft">
                      <i style={{ width: `${weights[i] ?? 0}%` }} />
                      <span>{weights[i] ?? 0}%</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="coverage-compare">
                <span>Weight with company analysis</span>
                <strong>
                  {coverage(companiesList.map((c) => c.allocation), companiesList)}% <ArrowRight size={18} />{" "}
                  {coverage(weights, companiesList)}%
                </strong>
              </div>
              <p className="muted small">
                Coverage measures verified emissions data availability.
              </p>
              {analysisResult && (
                <div className="esg-scorecard">
                  <div className="esg-scorecard-head">
                    <h4>Live ESG Impact & Alignment</h4>
                    <Badge tone="mint">Quant Analysis</Badge>
                  </div>
                  <div className="esg-scorecard-grid">
                    <div className="esg-scorecard-card">
                      <span>Portfolio Greenness</span>
                      <strong>{analysisResult.portfolio_greenness !== null ? analysisResult.portfolio_greenness : "—"}</strong>
                      <small className="positive">Target: 0.0 (Net Zero)</small>
                    </div>
                    <div className="esg-scorecard-card">
                      <span>Carbon Intensity</span>
                      <strong>{analysisResult.weighted_pillars.carbon !== null ? `${analysisResult.weighted_pillars.carbon}/10` : "—"}</strong>
                      <small className="neutral">Audited emissions rank</small>
                    </div>
                    <div className="esg-scorecard-card">
                      <span>Greenwash Exposure</span>
                      <strong>{analysisResult.greenwash_flagged_allocation ?? 0}%</strong>
                      <small className={analysisResult.greenwash_flagged_allocation === 0 ? "positive" : "neutral"}>
                        {analysisResult.greenwash_flagged_allocation === 0 ? "Zero flagged capital" : "Flagged talk-walk gap"}
                      </small>
                    </div>
                    <div className="esg-scorecard-card">
                      <span>Verified Coverage</span>
                      <strong>{analysisResult.coverage_pct}%</strong>
                      <small className="positive">Audited company data</small>
                    </div>
                  </div>
                  <div className="rebalance-actions">
                    <button className="secondary" type="button" onClick={exportRebalancedCsv}>
                      <DownloadSimple size={16} /> Export Rebalanced CSV
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="comparison-placeholder">
              <AllocationRing companiesList={companiesList} large />
              <h3>Your portfolio. Your perspective.</h3>
              <p>
                Use the example or edit the percentages, then compare your
                allocation.
              </p>
            </div>
          )}
        </section>
      </div>
      <div className="scope-note">
        <Info size={21} />
        <div>
          <strong>Allocation sandbox</strong>
          <p>
            This demo compares holdings only. Environmental impact, expected
            returns and regulatory shock simulations require the team’s backend
            model. No investment recommendation is generated.
          </p>
        </div>
      </div>
    </div>
  );
}

function Method() {
  return (
    <div className="method-page enter">
      <div className="page-heading">
        <div className="eyebrow">UNDERSTAND WHAT YOU SEE</div>
        <h1>A score with context.</h1>
        <p>
          Environmental information should make your portfolio easier to
          understand.
        </p>
      </div>
      <div className="method-intro">
        <Leaf size={35} weight="duotone" />
        <div>
          <h2>Environment is our starting point.</h2>
          <p>
            This prototype focuses on the E in ESG. It does not represent a
            complete environmental, social and governance rating.
          </p>
        </div>
      </div>
      <div className="method-grid">
        {[
          {
            n: "01",
            title: "Company performance",
            key: "E_score · 0–10",
            text: "How a company performs environmentally. Higher scores indicate greener performance within the selected method.",
          },
          {
            n: "02",
            title: "Industry importance",
            key: "E_weight · 0–100",
            text: "How much environmental performance matters to an industry. This is separate from the percentage you invest in a company.",
          },
          {
            n: "03",
            title: "Greenness",
            key: "g = −(10 − E_score) × E_weight / 100",
            text: "Combines performance with industry importance. Closer to zero means greener under this formula.",
          },
        ].map((m) => (
          <section className="panel method-card" key={m.n}>
            <span className="method-number">{m.n}</span>
            <h2>{m.title}</h2>
            <code>{m.key}</code>
            <p>{m.text}</p>
          </section>
        ))}
      </div>
      <section className="panel method-details">
        <h2>From data to understanding</h2>
        {[
          {
            title: "Carbon, actions and commitments",
            text: "The team’s method report separates carbon intensity, realised actions (Walk) and stated commitments (Talk). A Talk − Walk gap is a signal to investigate, not a finding of misconduct. The sample component values here are illustrative and do not compute the displayed E_score.",
          },
          {
            title: "What does 88% coverage mean?",
            text: "Four companies with available E_score values represent 88% of the original portfolio. The remaining 12% has no company analysis. Availability does not guarantee that every metric or source is complete.",
          },
          {
            title: "What happens when data is missing?",
            text: "A missing score stays unavailable. It is never treated as zero, as a clean company, or as proof that there is no environmental exposure.",
          },
          {
            title: "What is still being researched?",
            text: "The team’s proposed link between greenness and expected returns is a research hypothesis. Forecasts, optimisation, scenario shocks and market coverage still need validated models and a confirmed backend contract.",
          },
        ].map((m) => (
          <details key={m.title}>
            <summary>{m.title}</summary>
            <p>{m.text}</p>
          </details>
        ))}
      </section>
      <p className="source-note">
        Design basis: Main Idea.docx · escore_report.md · UI specification v0.1.
        All displayed companies and values are fictional.
      </p>
    </div>
  );
}

function BlueOverview({
  portfolio = companies,
  onSelect,
  onExplore,
  onMethod,
  query,
  onQuery,
}: {
  portfolio?: Company[];
  onSelect: (c: Company) => void;
  onExplore: () => void;
  onMethod: () => void;
  query: string;
  onQuery: (q: string) => void;
}) {
  const coveredCount = portfolio.filter((c) => c.score !== null).length;
  const covPct = coverage(portfolio.map((c) => c.allocation), portfolio);
  const sectors = Array.from(new Set(portfolio.map((c) => c.sector)));
  const markets = Array.from(new Set(portfolio.map((c) => c.region)));
  const greenwashCandidate = portfolio.find((c) => c.greenwasher) || portfolio.find((c) => (c.gap ?? 0) > 0) || portfolio[0];
  const missingCandidate = portfolio.find((c) => c.score === null);
  const missingWeight = portfolio.filter((c) => c.score === null).reduce((sum, c) => sum + c.allocation, 0);

  return (
    <div className="enter">
      <div className="page-heading heading-with-action">
        <div>
          <div className="eyebrow">YOUR PORTFOLIO, IN PERSPECTIVE</div>
          <h1>See beyond the numbers.</h1>
          <p className="brand-slogan">we make your wallet and the streets green</p>
        </div>
        <button className="primary" onClick={onExplore}>
          <SlidersHorizontal size={18} />
          Explore changes
        </button>
      </div>
      <section className="stat-strip">
        <div>
          <span>
            Companies in your portfolio <ChartDonut size={17} />
          </span>
          <strong>
            {portfolio.length.toString().padStart(2, "0")}
            <small>across {sectors.length} sectors</small>
          </strong>
        </div>
        <div>
          <span>
            Weight with company analysis <Info size={16} />
          </span>
          <strong>
            {covPct}<em>%</em>
            <small className="green-text">{coveredCount} of {portfolio.length} companies</small>
          </strong>
        </div>
        <div>
          <span>
            Markets in this sample <Compass size={17} />
          </span>
          <strong>
            {markets.length.toString().padStart(2, "0")}
            <small>{markets.slice(0, 3).join(" · ")}</small>
          </strong>
        </div>
      </section>
      <div className="analysis-grid">
        <section className="panel chart-panel">
          <div className="section-top">
            <div>
              <h2>Your environmental profile</h2>
              <p>Company performance, with industry context.</p>
            </div>
            <Badge tone="blue">FY 2025 · Live Analysis</Badge>
          </div>
          <ProfileChart onSelect={onSelect} companiesList={portfolio} />
        </section>
        <aside className="insight-panel">
          <div className="insight-top">
            <span className="soft-icon">
              <Sparkle size={21} />
            </span>
            <span>Worth a closer look</span>
          </div>
          <h2>
            Good questions. <br />
            Clearer decisions.
          </h2>
          <p>Look past a single score to understand what drives it.</p>
          {greenwashCandidate && (
            <button
              className="insight-item"
              onClick={() => onSelect(greenwashCandidate)}
            >
              <span className="insight-number amber-text">01</span>
              <div>
                <strong>A gap worth exploring</strong>
                <p>
                  {greenwashCandidate.name}’s commitments {greenwashCandidate.greenwasher ? "significantly exceed" : "differ from"} documented actions.
                </p>
              </div>
              <ArrowUpRight size={17} />
            </button>
          )}
          {missingCandidate ? (
            <button
              className="insight-item"
              onClick={() => onSelect(missingCandidate)}
            >
              <span className="insight-number">02</span>
              <div>
                <strong>A piece of the picture is missing</strong>
                <p>{missingWeight}% of your portfolio has no company analysis.</p>
              </div>
              <ArrowUpRight size={17} />
            </button>
          ) : (
            <div className="insight-item">
              <span className="insight-number mint-text">02</span>
              <div>
                <strong>Comprehensive coverage</strong>
                <p>100% of your portfolio weight has verified company analysis.</p>
              </div>
            </div>
          )}
          <button className="text-button insight-link" onClick={onMethod}>
            How to read these signals <ArrowRight size={16} />
          </button>
        </aside>
      </div>
      <HoldingTable query={query} onQuery={onQuery} onSelect={onSelect} companiesList={portfolio} />
      <div className="footnote">
        <Info size={15} />
        <span>
          Quantitative emissions & gap analysis powered by consolidated ESGx engine.
        </span>
      </div>
    </div>
  );
}

function GreenOverview({
  portfolio = companies,
  onSelect,
  onExplore,
  onMethod,
  query,
  onQuery,
}: {
  portfolio?: Company[];
  onSelect: (c: Company) => void;
  onExplore: () => void;
  onMethod: () => void;
  query: string;
  onQuery: (q: string) => void;
}) {
  const covPct = coverage(portfolio.map((c) => c.allocation), portfolio);
  const markets = Array.from(new Set(portfolio.map((c) => c.region)));

  return (
    <div className="enter">
      <section className="green-hero">
        <div className="green-hero-copy">
          <div className="eyebrow">
            <span />A MORE CONSIDERED WAY TO INVEST
          </div>
          <h1>
            A clearer view of <br />
            what you own.
          </h1>
          <p className="brand-slogan">we make your wallet and the streets green</p>
          <button className="primary" onClick={onExplore}>
            Explore your portfolio <ArrowUpRight size={19} />
          </button>
          <div className="hero-mini">
            <span>
              <CheckCircle size={16} />
              Company-level insights
            </span>
            <span>
              <CheckCircle size={16} />
              Evidence in context
            </span>
          </div>
        </div>
        <div className="hero-orbit">
          <span className="orbit-label top">
            <i />
            Your portfolio, connected
          </span>
          <div className="orbit-circle">
            <AllocationRing large companiesList={portfolio} />
          </div>
          <div className="orbit-card">
            <span className="orbit-icon">
              <Leaf weight="duotone" size={24} />
            </span>
            <div>
              <strong>
                {covPct}% <small>of portfolio weight</small>
              </strong>
              <span>has company analysis</span>
            </div>
          </div>
          <span className="orbit-label bottom">
            {portfolio.length} companies · {markets.length} markets · One perspective
          </span>
        </div>
      </section>
      <div className="green-stat-line">
        <div>
          <strong>{portfolio.length.toString().padStart(2, "0")}</strong>
          <span>
            Companies
            <br />
            in your portfolio
          </span>
        </div>
        <div>
          <strong>
            {covPct}<span>%</span>
          </strong>
          <span>
            Weight with
            <br />
            company analysis
          </span>
        </div>
        <div>
          <strong>{markets.length.toString().padStart(2, "0")}</strong>
          <span>
            Markets in
            <br />
            this portfolio
          </span>
        </div>
        <button className="text-button" onClick={onMethod}>
          Understand the methodology <ArrowRight size={18} />
        </button>
      </div>
      <div className="green-section-title">
        <div>
          <span className="eyebrow">START WITH THE COMPANIES</span>
          <h2>Every holding has a story.</h2>
        </div>
        <button className="text-button" onClick={onExplore}>
          Explore a different balance <ArrowUpRight size={18} />
        </button>
      </div>
      <div className="company-cards">
        {portfolio.slice(0, 3).map((c, i) => (
          <button
            className={`company-story story-${i}`}
            key={c.id}
            onClick={() => onSelect(c)}
          >
            <div className="story-top">
              <CompanyMark company={c} />
              <ArrowUpRight size={22} />
            </div>
            <span className="story-sector">
              {c.sector} · {c.region}
            </span>
            <h3>{c.name}</h3>
            <div className="story-score">
              <Score value={c.score} />
              <span>
                Environmental
                <br />
                score
              </span>
            </div>
            <div className="story-bottom">
              <span>{c.allocation}% of your portfolio</span>
              <span>
                View story <ArrowRight size={15} />
              </span>
            </div>
          </button>
        ))}
      </div>
      <HoldingTable query={query} onQuery={onQuery} onSelect={onSelect} companiesList={portfolio} />
      <section className="green-learning">
        <span className="learning-icon">
          <Leaf size={37} weight="duotone" />
        </span>
        <div>
          <h2>There’s more to green than a number.</h2>
          <p>
            Discover the difference between a company’s commitments and its
            actions.
          </p>
        </div>
        <button className="secondary" onClick={onMethod}>
          Make sense of the score <ArrowRight size={16} />
        </button>
      </section>
    </div>
  );
}

function PortfolioUploadModal({
  onClose,
  onUploadSuccess,
}: {
  onClose: () => void;
  onUploadSuccess: (companies: Company[]) => void;
}) {
  const [csvText, setCsvText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDownloadSample = async () => {
    try {
      const sample = await fetchSampleCsv();
      downloadCsvFile("sample_holdings.csv", sample);
    } catch {
      downloadCsvFile(
        "sample_holdings.csv",
        "ticker,allocation\n0002.HK,28\n2330.TW,22\n0066.HK,20\n0857.HK,18\n0992.HK,12\n"
      );
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      setCsvText(text);
      setError(null);
    };
    reader.readAsText(file);
  };

  const handleSubmit = async () => {
    if (!csvText.trim()) {
      setError("Please paste CSV data or choose a file.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await uploadPortfolioCsv(csvText);
      if (result.success && result.companies && result.companies.length > 0) {
        onUploadSuccess(result.companies);
        onClose();
      } else {
        setError(result.error || "Failed to parse portfolio CSV");
      }
    } catch (err: any) {
      setError(err?.message || "Failed to upload and analyze portfolio");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="Import Portfolio Holdings (CSV)" onClose={onClose} wide>
      <div className="upload-modal-body">
        <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)" }}>
          Upload your portfolio holdings with ticker symbols and percentage allocations.
          The engine will match holdings to the quantitative universe and compute live greenness, talk-walk gap, and carbon metrics.
        </p>

        <div
          className="upload-dropzone"
          onClick={() => fileInputRef.current?.click()}
        >
          <UploadSimple size={32} style={{ marginBottom: "8px", color: "var(--primary)" }} />
          <div>
            <strong>Choose a CSV file</strong> or drag & drop here
          </div>
          <small style={{ color: "var(--muted)", display: "block", marginTop: "4px" }}>
            Accepts format: <code>ticker,allocation</code> (e.g. <code>0002.HK, 28%</code>)
          </small>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            style={{ display: "none" }}
            onChange={handleFileChange}
          />
        </div>

        <div>
          <label style={{ display: "block", fontSize: "12px", fontWeight: 600, marginBottom: "6px" }}>
            Or paste CSV content directly:
          </label>
          <textarea
            className="upload-textarea"
            rows={5}
            placeholder={`ticker,allocation\n0002.HK,28\n2330.TW,22\n0066.HK,20\n0857.HK,18\n0992.HK,12`}
            value={csvText}
            onChange={(e) => {
              setCsvText(e.target.value);
              setError(null);
            }}
          />
        </div>

        {error && (
          <div className="upload-error">
            <WarningCircle size={16} style={{ verticalAlign: "text-bottom", marginRight: "4px" }} />
            {error}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "8px" }}>
          <button
            type="button"
            className="text-button"
            onClick={handleDownloadSample}
          >
            <DownloadSimple size={16} /> Download Sample CSV
          </button>
          <div style={{ display: "flex", gap: "10px" }}>
            <button type="button" className="secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button
              type="button"
              className="primary"
              onClick={handleSubmit}
              disabled={loading || !csvText.trim()}
            >
              {loading ? "Analyzing..." : "Import & Analyze Portfolio"}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  );
}

function StateView({
  state,
  onReset,
}: {
  state: DemoState;
  onReset: () => void;
}) {
  return (
    <div className="state-view" role="status">
      {state === "loading" ? (
        <>
          <div className="skeleton-block" />
          <h2>Loading the sample portfolio…</h2>
          <p>Preparing the local demonstration data.</p>
        </>
      ) : state === "error" ? (
        <>
          <WarningCircle size={44} />
          <h2>We couldn’t load the analysis.</h2>
          <p>Your original holdings are safe. Try loading the sample again.</p>
          <button className="primary" onClick={onReset}>
            Try again <ArrowRight size={17} />
          </button>
        </>
      ) : (
        <>
          <ChartDonut size={44} />
          <h2>Your portfolio starts here.</h2>
          <p>Load a fictional portfolio to explore the experience.</p>
          <button className="primary" onClick={onReset}>
            Load sample portfolio <ArrowRight size={17} />
          </button>
        </>
      )}
    </div>
  );
}

export default function App() {
  const [version, setVersion] = useState<"blue" | "green">(() =>
    new URLSearchParams(location.search).get("v") === "green"
      ? "green"
      : "blue",
  );
  const [view, setView] = useState<View>("portfolio");
  const [selected, setSelected] = useState<Company | null>(null);
  const [query, setQuery] = useState("");
  const [demoState, setDemoState] = useState<DemoState>("partial");
  const [notice, setNotice] = useState("");
  const [portfolio, setPortfolio] = useState<Company[]>(companies);
  const [isLive, setIsLive] = useState(false);
  const [market, setMarket] = useState<"hk" | "tw">("hk");
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function loadEngineData() {
      try {
        const health = await fetchHealth();
        if (health && (health.status === "healthy" || health.status === "ok")) {
          setIsLive(true);
          const liveCompanies = await fetchCompanies(market);
          if (mounted && liveCompanies && liveCompanies.length > 0) {
            setPortfolio(liveCompanies);
          }
        }
      } catch (err) {
        console.warn("FastAPI engine not reachable, using static demonstration data.", err);
      }
    }
    loadEngineData();
    return () => {
      mounted = false;
    };
  }, [market]);

  const handleUploadSuccess = (uploadedCompanies: Company[]) => {
    setPortfolio(uploadedCompanies);
    const covered = uploadedCompanies.filter((c) => c.score !== null).length;
    setNotice(`Loaded ${uploadedCompanies.length} holdings (${covered} covered by ESG universe)`);
  };

  useEffect(() => {
    document.documentElement.dataset.theme = version;
    const url = new URL(location.href);
    url.searchParams.set("v", version);
    history.replaceState({}, "", url);
  }, [version]);

  useEffect(() => {
    if (demoState === "loading") {
      const id = window.setTimeout(() => setDemoState("partial"), 900);
      return () => clearTimeout(id);
    }
  }, [demoState]);

  useEffect(() => {
    if (notice) {
      const id = window.setTimeout(() => setNotice(""), 3500);
      return () => clearTimeout(id);
    }
  }, [notice]);

  const navigate = (next: View) => {
    setView(next);
    window.scrollTo({ top: 0, behavior: "instant" });
  };

  const exportData = () => {
    const blob = new Blob(
      [
        JSON.stringify(
          {
            isDemo: !isLive,
            notice: isLive
              ? "Live ESG Quantitative Engine Portfolio Export"
              : "Fictional UI data. Not investment analysis.",
            period: "FY 2025",
            companies: portfolio,
            capabilities,
          },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "green-street-portfolio.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setNotice("Portfolio downloaded.");
  };

  const overviewProps = {
    portfolio,
    onSelect: setSelected,
    onExplore: () => navigate("explore"),
    onMethod: () => navigate("method"),
    query,
    onQuery: setQuery,
  };

  return (
    <div className={`app ${version}`}>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="concept-bar">
        <span>
          <span className="concept-brand">GREEN STREET</span>
          <span className="concept-divider" />
          UI CONCEPTS
        </span>
        <div
          className="version-switch"
          role="group"
          aria-label="Choose design version"
        >
          <button
            aria-pressed={version === "blue"}
            onClick={() => setVersion("blue")}
          >
            <i className="blue-dot" />
            01 · Clarity blue
          </button>
          <button
            aria-pressed={version === "green"}
            onClick={() => setVersion("green")}
          >
            <i className="green-dot" />
            02 · Sage green
          </button>
        </div>
        <div
          className="version-switch"
          role="group"
          aria-label="Choose market"
          title="Market shown when the live engine answers (fixtures stay Hong Kong)"
        >
          <button
            aria-pressed={market === "hk"}
            onClick={() => setMarket("hk")}
          >
            Hong Kong
          </button>
          <button
            aria-pressed={market === "tw"}
            onClick={() => setMarket("tw")}
          >
            Taiwan
          </button>
        </div>
        <span className="concept-note">
          {isLive ? `Live Quantitative Engine · ${market === "hk" ? "HK/China" : "Taiwan"} Universe` : "Fictional data · Interactive prototype"}
        </span>
      </div>
      {version === "blue" ? (
        <aside className="sidebar">
          <Logo version={version} />
          <span className="nav-caption">WORKSPACE</span>
          <nav aria-label="Main navigation">
            {navItems.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                className={view === id ? "active" : ""}
                aria-current={view === id ? "page" : undefined}
                onClick={() => navigate(id)}
              >
                <Icon size={20} />
                {label}
                {id === view && <span className="active-indicator" />}
              </button>
            ))}
          </nav>
          <div className="sidebar-learn">
            <span className="soft-icon">
              <Leaf size={22} />
            </span>
            <h3>Invest with perspective.</h3>
            <p>A little understanding makes a meaningful difference.</p>
            <button onClick={() => navigate("method")}>
              Find your starting point <ArrowRight size={16} />
            </button>
          </div>
          <div className="sidebar-profile">
            <span className="avatar">JD</span>
            <div>
              <strong>Jamie’s workspace</strong>
              <small>Personal portfolio · {isLive ? "Engine live" : "Demo"}</small>
            </div>
          </div>
        </aside>
      ) : (
        <header className="green-nav">
          <Logo version={version} />
          <nav aria-label="Main navigation">
            {navItems.map(({ id, label }) => (
              <button
                key={id}
                className={view === id ? "active" : ""}
                aria-current={view === id ? "page" : undefined}
                onClick={() => navigate(id)}
              >
                {label}
              </button>
            ))}
          </nav>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Badge tone={isLive ? "mint" : "neutral"}>
              <span className={`status-dot ${isLive ? "live" : ""}`} />
              {isLive ? "Engine Connected" : "Demo Portfolio"}
            </Badge>
            <button
              className="secondary"
              style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "11px", padding: "6px 12px" }}
              onClick={() => setUploadModalOpen(true)}
            >
              <UploadSimple size={15} />
              Import CSV
            </button>
            <span className="avatar">JD</span>
          </div>
        </header>
      )}
      <div className="workspace">
        {version === "blue" && (
          <header className="workspace-top">
            <div className="breadcrumb">
              Workspace <span>/</span>{" "}
              <strong>{navItems.find((n) => n.id === view)?.label}</strong>
            </div>
            <div className="workspace-actions">
              <Badge tone={isLive ? "mint" : "neutral"}>
                <span className={`status-dot ${isLive ? "live" : ""}`} />
                {isLive ? "Engine Connected" : "Demo Portfolio"}
              </Badge>
              <button
                className="secondary"
                style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "11px", padding: "6px 12px" }}
                onClick={() => setUploadModalOpen(true)}
              >
                <UploadSimple size={15} />
                Import CSV
              </button>
              <button
                className="icon-button"
                aria-label="Download portfolio data"
                title="Download portfolio data"
                onClick={exportData}
              >
                <DownloadSimple size={20} />
              </button>
              <span className="avatar small-avatar">JD</span>
            </div>
          </header>
        )}
        <main id="main" tabIndex={-1}>
          {view === "portfolio" ? (
            demoState === "partial" ? (
              version === "blue" ? (
                <BlueOverview {...overviewProps} />
              ) : (
                <GreenOverview {...overviewProps} />
              )
            ) : (
              <StateView
                state={demoState}
                onReset={() => setDemoState("loading")}
              />
            )
          ) : view === "explore" ? (
            <Explore companiesList={portfolio} onNotice={setNotice} />
          ) : (
            <Method />
          )}
          <footer className="demo-footer">
            <span>
              <Leaf size={15} />
              Built for a more informed perspective.
            </span>
            <label>
              Demo state
              <select
                value={demoState}
                onChange={(e) => {
                  setDemoState(e.target.value as DemoState);
                  navigate("portfolio");
                }}
              >
                <option value="partial">Partial data</option>
                <option value="loading">Loading</option>
                <option value="empty">Empty portfolio</option>
                <option value="error">Service error</option>
              </select>
            </label>
            <button className="text-button" onClick={exportData}>
              Export sample <DownloadSimple size={15} />
            </button>
            <span className="demo-disclaimer">
              {isLive ? "Quantitative engine connected · HK Universe" : "Fictional data · No live trading"}
            </span>
          </footer>
        </main>
      </div>
      {selected && (
        <CompanyDetail
          company={selected}
          onClose={() => setSelected(null)}
          onExplore={() => {
            setSelected(null);
            navigate("explore");
          }}
        />
      )}
      {uploadModalOpen && (
        <PortfolioUploadModal
          onClose={() => setUploadModalOpen(false)}
          onUploadSuccess={handleUploadSuccess}
        />
      )}
      {notice && (
        <div className="toast" role="status">
          <Check size={18} />
          {notice}
        </div>
      )}
    </div>
  );
}
