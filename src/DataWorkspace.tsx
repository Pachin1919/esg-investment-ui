import { useEffect, useRef, useState } from "react";
import { ArrowCounterClockwise, Database, DownloadSimple, FileArrowUp, MagnifyingGlass, WarningCircle } from "@phosphor-icons/react";
import { dataLabel, dateRange, fetchDataSources, fetchDataStatus, fetchTalkWalk, readDataset } from "./dataset";
import type { DataSources, DataStatus, Market, TalkWalkData, TalkWalkFirm } from "./dataset";
import type { Universe } from "./live";
import { download } from "./portfolio";
import { Button } from "./ui";
import styles from "./DataWorkspace.module.css";

export function DataStatusBar({ status, error, market, onMarketChange, onSources }: {
  status: DataStatus | null; error: string; market: Market; onMarketChange: (market: Market) => void; onSources: () => void;
}) {
  return <div className={styles.statusBar}>
    <div role="status"><WarningCircle size={18} weight="fill" /><span><strong>{dataLabel(status)}</strong><small>{error || (status?.mode === "demo" ? "Illustrative values for exploring the workspace" : "Coverage periods vary by measure")}</small></span></div>
    <label>Listing market<select aria-label="Listing market" value={market} onChange={e => onMarketChange(e.target.value as Market)}><option value="all">All · Hong Kong &amp; Taiwan</option><option value="hk">Hong Kong</option><option value="tw">Taiwan</option></select></label>
    <button type="button" onClick={onSources}>Data sources</button>
  </div>;
}

export function DataSourcesPage({ datasetId, status, onDatasetChange }: { datasetId: string; status: DataStatus | null; onDatasetChange: (id: string) => void }) {
  const [sources, setSources] = useState<DataSources | null>(null), [error, setError] = useState(""), [busy, setBusy] = useState(false);
  const [sourceStatus, setSourceStatus] = useState<DataStatus | null>(null);
  const coverageStatus = sourceStatus ?? status;
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    let active = true; setSources(null); setSourceStatus(null); setError("");
    Promise.all([fetchDataSources(), fetchDataStatus("all")]).then(([data, coverage]) => { if (active) { setSources(data); setSourceStatus(coverage); } }).catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [datasetId]);
  async function schema() {
    try { const data = await readDataset<unknown>("/api/data/schema"); download("green-street-dataset-schema.json", JSON.stringify(data, null, 2), "application/json"); }
    catch (err) { setError((err as Error).message); }
  }
  async function mount(file?: File) {
    if (!file) return;
    setError(""); setBusy(true);
    try {
      if (!file.name.toLowerCase().endsWith(".json")) throw new Error("Choose a standard JSON dataset file.");
      if (file.size > 32 * 1024 * 1024) throw new Error("The dataset must be smaller than 32 MiB.");
      let payload: unknown;
      try { payload = JSON.parse(await file.text()); } catch { throw new Error("This file is not valid JSON. Download the schema to check the required format."); }
      const mounted = await readDataset<{ dataset_id: string }>("/api/data/mount", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      onDatasetChange(mounted.dataset_id);
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); if (input.current) input.current.value = ""; }
  }
  return <div className={`workspace-page ${styles.page}`}>
    <div className="workspace-heading"><div><span className="workspace-eyebrow">DATA WORKSPACE</span><h1>Data sources</h1><p>Review the active dataset and bring in a dated dataset.</p></div></div>
    <section className="workspace-panel">
      <div className="panel-heading"><div><h2>Active dataset</h2><p>{datasetId === "builtin" ? "Built-in dataset" : "Mounted JSON dataset"} · {dataLabel(coverageStatus)}</p></div><Database size={24} /></div>
      <div className={styles.coverage}>{(["hk", "tw"] as const).map(market => {
        const coverage = coverageStatus?.markets[market];
        return <article key={market}><strong>{market === "hk" ? "Hong Kong" : "Taiwan"}</strong><span>{coverage?.company_count ?? 0} companies · {coverage?.status === "missing" || !coverage ? "Insufficient data" : "Database coverage"}</span><small>{dateRange(coverage?.status === "missing" ? undefined : coverage?.data_dates)}</small></article>;
      })}</div>
      {coverageStatus?.limitations?.length ? <ul className={styles.limitations}>{coverageStatus.limitations.map(text => <li key={text}>{text}</li>)}</ul> : null}
      <p className={styles.note}>The listing-market selector limits companies and recommendation candidates. Domicile and the financial model’s market proxy are separate attributes.</p>
      {datasetId !== "builtin" && <Button kind="secondary" onClick={() => onDatasetChange("builtin")}><ArrowCounterClockwise size={18} />Use built-in dataset</Button>}
    </section>
    <section className="workspace-panel">
      <div className="panel-heading"><div><h2>Import a JSON dataset</h2><p>Use metadata and supported tables from the standard schema. Validation happens before activation.</p></div></div>
      <div className={styles.sourceActions}><Button onClick={() => input.current?.click()} disabled={busy}><FileArrowUp size={18} />{busy ? "Validating dataset…" : "Upload JSON dataset"}</Button><Button kind="secondary" onClick={() => void schema()}><DownloadSimple size={18} />Download schema</Button></div>
      <input ref={input} className="sr-only" type="file" aria-label="JSON dataset" accept=".json,application/json" onChange={e => void mount(e.target.files?.[0])} />
      <p className={styles.note}>The active selection is saved in this browser. Existing holdings stay in your portfolio; holdings outside the new universe can remain frozen. Mounted datasets are stored by this backend and may need to be uploaded again after a restart.</p>
      {error && <p className="form-error" role="alert">{error}</p>}
    </section>
    <section className="workspace-panel">
      <div className="panel-heading"><div><h2>Source coverage</h2><p>Rows and dates reflect the active dataset’s available tables.</p></div></div>
      {sources ? <div className="table-scroll"><table className="analysis-table"><thead><tr><th>Table / source</th><th>Market</th><th>Measure</th><th>Rows</th><th>Date range</th><th>Availability</th></tr></thead><tbody>{sources.sources.map(source => <tr key={source.key}><td><strong>{source.key}</strong><small className={styles.sourcePath}>{source.source}</small></td><td>{source.market === "hk" ? "Hong Kong" : source.market === "tw" ? "Taiwan" : source.market}</td><td>{source.kind}</td><td>{source.rows.toLocaleString()}</td><td>{dateRange(source.data_dates)}</td><td>{source.available ? "Available" : "Insufficient data"}</td></tr>)}</tbody></table></div> : <p className={styles.note}>{error ? "Source coverage is unavailable. Use the built-in dataset or retry the upload." : "Loading source coverage…"}</p>}
    </section>
    <section className="workspace-panel"><div className="panel-heading"><div><h2>Supported data routes</h2><p>Choose an import format that the adapter supports.</p></div></div><div className={styles.routes}><article><strong>Internal CSV / Parquet</strong><p>The backend reads configured local source tables. These are internal readers; this screen does not upload arbitrary CSV or Parquet tables.</p></article><article><strong>External SQL / API</strong><p>Export your source to the standard JSON dataset, then upload it above. Native database and API connections are not implemented.</p></article></div></section>
  </div>;
}

function showValue(value: unknown): string {
  if (value == null || value === "" || (typeof value === "number" && !Number.isFinite(value))) return "Insufficient data";
  if (typeof value === "number") return value.toFixed(2);
  if (typeof value === "boolean") return value ? "Signal detected" : "No signal detected";
  if (typeof value === "object") return Object.entries(value as Record<string, unknown>).map(([key, val]) => `${friendlyKey(key)}: ${showValue(val)}`).join(" · ");
  return String(value);
}
function friendlyKey(key: string) { return key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()); }
function assessment(row?: TalkWalkFirm) {
  if (!row || row.talk == null || row.walk == null || row.gap == null || row.assessment_status === "insufficient_data") return "Insufficient data";
  if (row.greenwasher === true) return "Greenwash signal detected";
  if (row.greenhusher === true) return "Quiet-action signal detected";
  if (row.greenwasher == null || row.greenhusher == null) return "Assessment available · signal classification not provided";
  return "No signal detected";
}
function ScoreSummary({ row, scale, signal }: { row?: TalkWalkFirm; scale: string; signal?: string }) {
  return <><div className={styles.scores}>{(["talk", "walk", "gap"] as const).map(key => <div key={key}><span>{key === "gap" ? "Talk–walk gap" : friendlyKey(key)}</span><strong>{showValue(row?.[key])}</strong>{key !== "gap" && row?.[key] != null && <meter aria-label={`${friendlyKey(key)} score`} min={0} max={10} value={row[key]} />}</div>)}</div><p className={styles.note}>{scale}{row?.year != null ? ` · ${row.year}` : ""}{signal ? ` · ${signal}` : ""}</p></>;
}
export function TalkWalkPage({ universe, market, datasetId }: { universe: Universe | null; market: Market; datasetId: string }) {
  const [query, setQuery] = useState(""), [selected, setSelected] = useState("");
  const [chooserOpen, setChooserOpen] = useState(true);
  const [selectedYear, setSelectedYear] = useState("");
  const [data, setData] = useState<TalkWalkData | null>(null), [error, setError] = useState(""), [loading, setLoading] = useState(false);
  const words = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  const matches = [...(universe?.values() ?? [])].filter(c => words.every(w => `${c.name} ${c.ticker} ${c.sector}`.toLowerCase().includes(w)));
  const company = universe?.get(selected);
  useEffect(() => { setSelected(""); setChooserOpen(true); setQuery(""); setData(null); setError(""); }, [market, datasetId]);
  useEffect(() => {
    if (!selected) { setData(null); setError(""); setLoading(false); return; }
    let active = true; setData(null); setError(""); setLoading(true);
    fetchTalkWalk(market, selected).then(result => { if (active) setData(result); }).catch(err => { if (active) setError(err.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [selected, market, datasetId]);
  const semanticYears = data?.semantic_llm.firms.slice().sort((a, b) => (b.year ?? 0) - (a.year ?? 0)) ?? [];
  const semantic = semanticYears.find(row => String(row.year) === selectedYear) ?? semanticYears[0];
  const dictionary = data?.dictionary.firms.slice().sort((a, b) => (b.year ?? 0) - (a.year ?? 0))[0];
  const documents = semantic?.documents ?? [];
  return <div className={`workspace-page ${styles.page}`}>
    <div className="workspace-heading"><div><span className="workspace-eyebrow">ENVIRONMENTAL EVIDENCE</span><h1>Talk &amp; Walk</h1><p>Compare stated environmental ambition with documented action.</p></div></div>
    <section className="workspace-panel"><div className="panel-heading"><div><h2>{selected ? company?.name ?? selected : "Select a company"}</h2><p>{selected ? `${selected} · Company selected` : `${universe?.size ?? 0} companies in the selected listing market.`}</p></div>{selected && <Button kind="secondary" onClick={() => setChooserOpen(open => !open)}>{chooserOpen ? "Close company selection" : "Change company"}</Button>}</div>
      <div hidden={!!selected && !chooserOpen}>
      <div className="company-keyword-input"><MagnifyingGlass size={19} /><input value={query} aria-label="Search Talk & Walk companies" placeholder="Search company, ticker or sector" onChange={e => setQuery(e.target.value)} /></div>
      <div className={styles.companyChoices}>{matches.slice(0, 6).map(c => <button type="button" key={c.ticker} aria-pressed={selected === c.ticker} onClick={() => { setSelected(c.ticker); setChooserOpen(false); setSelectedYear(""); }}><strong>{c.name}</strong><small>{c.ticker} · {c.sector}</small></button>)}</div>
      {matches.length > 6 && <p className={styles.note}>Showing 6 of {matches.length} matches. Search to find your company.</p>}
      {!matches.length && <p className={styles.note} role="status">{universe ? "No matching companies in this market." : "Loading companies…"}</p>}
      </div>
    </section>
    {!selected && <section className="workspace-panel"><p className={styles.note}>Select a company to review its available LLM dimensions, supporting documents and separate dictionary scores.</p></section>}
    {selected && <><section className="workspace-panel"><div className="panel-heading"><div><h2>{company?.name ?? selected}</h2><p>{selected} · {company?.listing_market === "hk" || selected.endsWith(".HK") ? "Hong Kong listing" : "Taiwan listing"}{company?.domicile ? ` · Domicile: ${company.domicile}` : ""}{company?.model_proxy ? ` · Model proxy: ${company.model_proxy}` : ""}</p></div></div>
      <div className={styles.semanticHeading}><h3 className={styles.subheading}>LLM semantic assessment</h3>{semanticYears.length > 1 && <label>Period<select aria-label="LLM assessment period" value={String(semantic?.year)} onChange={e => setSelectedYear(e.target.value)}>{semanticYears.map(row => <option key={row.year} value={row.year}>{row.year}</option>)}</select></label>}</div><p className={styles.note}>Stored assessments from the active dataset’s filings. Selecting a company reads existing evidence; it does not run a real-time LLM.</p>
      {loading ? <p role="status">Loading company evidence…</p> : error ? <p className="form-error" role="alert">{error}</p> : <><ScoreSummary row={semantic} scale={data?.semantic_llm.scale ?? "0–10 semantic rubric"} signal={assessment(semantic)} />
        {semantic?.dimensions && Object.keys(semantic.dimensions).length > 0 && <details className={styles.dimensionDetails}><summary>View {Object.keys(semantic.dimensions).length} LLM dimensions</summary><div className={styles.dimensions}>{Object.entries(semantic.dimensions).map(([dimension, value]) => <article key={dimension}><span>{friendlyKey(dimension)}</span><strong>{showValue(value)}</strong></article>)}</div></details>}
        {!semantic && <p className={styles.note}>Insufficient data · No stored LLM assessment is available for this company in the selected dataset.</p>}
        <p className={styles.note}>A missing assessment is not a negative result. “No signal detected” describes the available evidence and does not certify a company as safe.</p></>}
    </section>
    <section className="workspace-panel"><div className="panel-heading"><div><h2>Document evidence</h2><p>{documents.length} documents in the displayed LLM assessment.</p></div></div>
      {documents.length ? documents.map((document, index) => <details className={styles.document} key={`${document.source_url}-${index}`}><summary><strong>{document.period || "Period unavailable"}</strong> · Filed {document.filing_date || "date unavailable"}{document.model ? ` · ${document.model}` : ""}</summary>{document.summary && <p>{document.summary}</p>}{document.source_url && /^https?:\/\//i.test(document.source_url) && <a href={document.source_url} target="_blank" rel="noreferrer">Open source document ↗</a>}
        <div className={styles.evidence}><div><h3>Talk evidence</h3>{document.evidence_talk?.length ? <ul>{document.evidence_talk.map((item, i) => <li key={i}>{showValue(item)}</li>)}</ul> : <p>Insufficient data</p>}</div><div><h3>Walk evidence</h3>{document.evidence_walk?.length ? <ul>{document.evidence_walk.map((item, i) => <li key={i}>{showValue(item)}</li>)}</ul> : <p>Insufficient data</p>}</div></div>
        {document.dimensions && Object.keys(document.dimensions).length > 0 && <details><summary>Document dimensions</summary><dl className={styles.documentDimensions}>{Object.entries(document.dimensions).map(([key, value]) => <div key={key}><dt>{friendlyKey(key)}</dt><dd>{showValue(value)}</dd></div>)}</dl></details>}
      </details>) : <p className={styles.note}>{loading ? "Loading documents…" : "Insufficient data · No supporting LLM documents are available in this dataset."}</p>}
    </section>
    <section className="workspace-panel"><div className="panel-heading"><div><h2>Dictionary assessment</h2><p>Keyword and sector-relative scores, shown separately from the LLM rubric.</p></div></div><ScoreSummary row={dictionary} scale={data?.dictionary.scale ?? "0–10 within-sector percentile"} signal={assessment(dictionary)} />{!dictionary && <p className={styles.note}>Insufficient data · No dictionary assessment is available for this company.</p>}</section>
    {data?.limitations?.length ? <section className="workspace-panel"><h2>Coverage notes</h2><ul className={styles.limitations}>{data.limitations.map(note => <li key={note}>{note}</li>)}</ul></section> : null}</>}
  </div>;
}
