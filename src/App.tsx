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
  WarningCircle,
  X,
} from "@phosphor-icons/react";
import {
  alternative,
  baseline,
  capabilities,
  companies,
  coverage,
} from "./data";
import type { Company } from "./data";

type View = "portfolio" | "explore" | "method";
type DemoState = "partial" | "loading" | "empty" | "error";
const navItems = [
  { id: "portfolio" as View, label: "My portfolio", icon: SquaresFour },
  { id: "explore" as View, label: "Explore changes", icon: ArrowsLeftRight },
  { id: "method" as View, label: "Our methodology", icon: Compass },
];

function Logo({ version }: { version: string }) {
  return (
    <a className="brand" href={"?v=" + version} aria-label="Verdant home">
      <span className="brand-symbol">
        <Leaf size={24} weight="fill" />
      </span>
      verdant<span className="brand-period">.</span>
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
  weights = baseline,
  large = false,
}: {
  weights?: number[];
  large?: boolean;
}) {
  let accumulated = 0;
  const stops = companies
    .map((c, i) => {
      const from = accumulated;
      accumulated += weights[i];
      return `${c.color} ${from}% ${accumulated}%`;
    })
    .join(",");
  return (
    <div
      className={`allocation-ring ${large ? "large" : ""}`}
      style={{ background: `conic-gradient(from -90deg, ${stops})` }}
      role="img"
      aria-label={`Portfolio allocation: ${companies.map((c, i) => `${c.name} ${weights[i]}%`).join(", ")}`}
    >
      <div className="ring-center">
        <Leaf size={24} />
        <strong>{companies.length}</strong>
        <span>companies</span>
      </div>
    </div>
  );
}

function ProfileChart({ onSelect }: { onSelect: (c: Company) => void }) {
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
          {companies
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
        {companies
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
        {companies
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
}: {
  query: string;
  onQuery: (q: string) => void;
  onSelect: (c: Company) => void;
}) {
  const [sort, setSort] = useState<"allocation" | "score">("allocation");
  const filtered = companies
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
            Your holdings <span className="count">05</span>
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
                        : c.id === "river"
                          ? "amber"
                          : "mint"
                    }
                  >
                    {c.score === null
                      ? "Missing data"
                      : c.id === "river"
                        ? "Review suggested"
                        : "Sample available"}
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
          {filtered.length} of {companies.length} fictional companies
        </span>
        <span>Illustrative reporting period · FY 2025</span>
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

function Explore() {
  const [weights, setWeights] = useState<number[]>([...baseline]);
  const [compared, setCompared] = useState(false);
  const total = weights.reduce((a, b) => a + b, 0);
  const valid =
    weights.every((w) => Number.isFinite(w) && w >= 0 && w <= 100) &&
    Math.abs(total - 100) < 0.001;
  const change = (index: number, value: number) => {
    setWeights((old) => old.map((w, i) => (i === index ? value : w)));
    setCompared(false);
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
                setWeights([...baseline]);
                setCompared(false);
              }}
            >
              Reset
            </button>
          </div>
          {companies.map((c, i) => (
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
                setWeights([...alternative]);
                setCompared(false);
              }}
            >
              <Sparkle size={16} />
              Load example
            </button>
            <button
              className="primary"
              disabled={!valid}
              onClick={() => setCompared(true)}
            >
              Compare allocation <ArrowRight size={16} />
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
                {companies.map((c, i) => (
                  <div key={c.id}>
                    <div className="bar-title">
                      <strong>{c.name}</strong>
                      <span>
                        {weights[i] - c.allocation > 0 ? "+" : ""}
                        {Number((weights[i] - c.allocation).toFixed(2))} pp
                      </span>
                    </div>
                    <div className="compare-track">
                      <i style={{ width: `${c.allocation}%` }} />
                      <span>{c.allocation}%</span>
                    </div>
                    <div className="compare-track draft">
                      <i style={{ width: `${weights[i]}%` }} />
                      <span>{weights[i]}%</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="coverage-compare">
                <span>Weight with company analysis</span>
                <strong>
                  {coverage(baseline)}% <ArrowRight size={18} />{" "}
                  {coverage(weights)}%
                </strong>
              </div>
              <p className="muted small">
                Coverage measures data availability, not environmental quality.
              </p>
            </>
          ) : (
            <div className="comparison-placeholder">
              <AllocationRing large />
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
  onSelect,
  onExplore,
  onMethod,
  query,
  onQuery,
}: {
  onSelect: (c: Company) => void;
  onExplore: () => void;
  onMethod: () => void;
  query: string;
  onQuery: (q: string) => void;
}) {
  return (
    <div className="enter">
      <div className="page-heading heading-with-action">
        <div>
          <div className="eyebrow">YOUR PORTFOLIO, IN PERSPECTIVE</div>
          <h1>See beyond the numbers.</h1>
          <p>Understand the environmental story behind your investments.</p>
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
            05<small>across 5 sectors</small>
          </strong>
        </div>
        <div>
          <span>
            Weight with company analysis <Info size={16} />
          </span>
          <strong>
            88<em>%</em>
            <small className="green-text">4 of 5 companies</small>
          </strong>
        </div>
        <div>
          <span>
            Markets in this sample <Compass size={17} />
          </span>
          <strong>
            03<small>China · Hong Kong · Taiwan</small>
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
            <Badge tone="blue">FY 2025 · Sample</Badge>
          </div>
          <ProfileChart onSelect={onSelect} />
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
          <button
            className="insight-item"
            onClick={() => onSelect(companies[3])}
          >
            <span className="insight-number amber-text">01</span>
            <div>
              <strong>A gap worth exploring</strong>
              <p>Riverstone’s commitments exceed its documented actions.</p>
            </div>
            <ArrowUpRight size={17} />
          </button>
          <button
            className="insight-item"
            onClick={() => onSelect(companies[4])}
          >
            <span className="insight-number">02</span>
            <div>
              <strong>A piece of the picture is missing</strong>
              <p>12% of your portfolio has no company analysis.</p>
            </div>
            <ArrowUpRight size={17} />
          </button>
          <button className="text-button insight-link" onClick={onMethod}>
            How to read these signals <ArrowRight size={16} />
          </button>
        </aside>
      </div>
      <HoldingTable query={query} onQuery={onQuery} onSelect={onSelect} />
      <div className="footnote">
        <Info size={15} />
        <span>
          Environmental insights, not a full ESG rating. Fictional data for
          demonstration.
        </span>
      </div>
    </div>
  );
}

function GreenOverview({
  onSelect,
  onExplore,
  onMethod,
  query,
  onQuery,
}: {
  onSelect: (c: Company) => void;
  onExplore: () => void;
  onMethod: () => void;
  query: string;
  onQuery: (q: string) => void;
}) {
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
          <p>
            Connect your investments to their environmental story. Start with
            understanding.
          </p>
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
            <AllocationRing large />
          </div>
          <div className="orbit-card">
            <span className="orbit-icon">
              <Leaf weight="duotone" size={24} />
            </span>
            <div>
              <strong>
                88% <small>of portfolio weight</small>
              </strong>
              <span>has company analysis</span>
            </div>
          </div>
          <span className="orbit-label bottom">
            5 companies · 3 markets · One perspective
          </span>
        </div>
      </section>
      <div className="green-stat-line">
        <div>
          <strong>05</strong>
          <span>
            Companies
            <br />
            in your portfolio
          </span>
        </div>
        <div>
          <strong>
            88<span>%</span>
          </strong>
          <span>
            Weight with
            <br />
            company analysis
          </span>
        </div>
        <div>
          <strong>03</strong>
          <span>
            Markets in
            <br />
            this fictional sample
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
        {companies.slice(0, 3).map((c, i) => (
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
      <HoldingTable query={query} onQuery={onQuery} onSelect={onSelect} />
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
            isDemo: true,
            notice: "Fictional UI data. Not investment analysis.",
            period: "FY 2025",
            companies,
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
    a.download = "verdant-demo-portfolio.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setNotice("Sample portfolio downloaded.");
  };
  const overviewProps = {
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
          <span className="concept-brand">VERDANT</span>
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
        <span className="concept-note">
          Fictional data · Interactive prototype
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
              <small>Personal portfolio · Demo</small>
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
          <span className="avatar">JD</span>
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
              <Badge tone="mint">
                <span className="status-dot" />
                Demo portfolio
              </Badge>
              <button
                className="icon-button"
                aria-label="Download sample portfolio"
                title="Download sample portfolio"
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
            <Explore />
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
              Fictional data · No live trading
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
      {notice && (
        <div className="toast" role="status">
          <Check size={18} />
          {notice}
        </div>
      )}
    </div>
  );
}
