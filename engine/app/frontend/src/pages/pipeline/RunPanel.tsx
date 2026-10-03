import { Play, Save, Upload } from 'lucide-react';
import clsx from 'clsx';
import type { Estimate, PipelineSpec, RunDetail, RunMode, SavedConfig } from '@/core/api';
import { Card } from '@/shared/ui';

export function RunPanel({
  tickers,
  setTickers,
  tickerList,
  mode,
  setMode,
  estimate,
  onRun,
  running,
  saveName,
  setSaveName,
  onSave,
  msg,
  configs,
  onLoad,
}: {
  tickers: string;
  setTickers: (v: string) => void;
  tickerList: string[];
  mode: RunMode;
  setMode: (m: RunMode) => void;
  estimate: Estimate | null;
  onRun: () => void;
  running: boolean;
  saveName: string;
  setSaveName: (v: string) => void;
  onSave: () => void;
  msg: string | null;
  configs: SavedConfig[];
  onLoad: (s: PipelineSpec) => void;
}) {
  return (
    <Card
      title="Run"
      subtitle="Each run writes to outputs/pipeline_runs/<id>/; main outputs change only if Aggregate has publish on"
    >
      <label className="block text-xs text-ink2">
        Tickers
        <input
          value={tickers}
          onChange={(e) => setTickers(e.target.value)}
          placeholder="XOM NEE AAPL"
          className="mt-1 w-full rounded-md border border-line bg-surface px-2 py-1.5 text-sm text-ink"
        />
      </label>
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        {(['dry_run', 'cache_only', 'live'] as RunMode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={clsx(
              'rounded-md border px-2.5 py-1',
              mode === m ? 'border-accent bg-accent/10 text-ink' : 'border-line text-ink2',
            )}
          >
            {m === 'dry_run'
              ? 'Dry run · free'
              : m === 'cache_only'
                ? 'Cache only · free'
                : 'Live · costs money'}
          </button>
        ))}
      </div>
      {estimate && (
        <div className="mt-3 rounded-md bg-page p-3 text-xs text-ink2">
          <div className="flex justify-between">
            <span>Sections to score</span>
            <span className="tabular text-ink">{estimate.sections}</span>
          </div>
          <div className="flex justify-between">
            <span>Firm-years to review</span>
            <span className="tabular text-ink">{estimate.firm_years}</span>
          </div>
          <div className="mt-1 flex justify-between border-t border-grid pt-1">
            <span>Live cost estimate</span>
            <span className="tabular text-ink">
              {mode === 'live' ? `${estimate.total_usd.toFixed(2)} USD` : '0 USD'}
            </span>
          </div>
        </div>
      )}
      <div className="mt-3 flex gap-2">
        <button
          onClick={onRun}
          disabled={!tickerList.length || running}
          className="flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          <Play className="h-4 w-4" /> Run pipeline
        </button>
        <input
          value={saveName}
          onChange={(e) => setSaveName(e.target.value)}
          placeholder="config name"
          className="w-32 rounded-md border border-line bg-surface px-2 py-1 text-sm text-ink"
        />
        <button
          onClick={onSave}
          className="flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-sm"
        >
          <Save className="h-4 w-4" /> Save
        </button>
      </div>
      {msg && <p className="mt-2 text-xs text-ink2">{msg}</p>}
      {configs.length > 0 && (
        <div className="mt-3 text-xs text-ink2">
          <div className="mb-1 font-medium text-ink">Saved configurations</div>
          <ul className="space-y-1">
            {configs.map((c) => (
              <li key={c.file} className="flex items-center gap-2">
                <span className="font-mono">{c.file}</span>
                {c.spec && (
                  <button
                    onClick={() => onLoad(c.spec!)}
                    className="flex items-center gap-1 text-accent"
                  >
                    <Upload className="h-3 w-3" /> load
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

export function RunStatus({ run, stages }: { run: RunDetail; stages: PipelineSpec['stages'] }) {
  return (
    <Card
      title={`Run ${run.id}`}
      subtitle={`${run.mode} · ${run.tickers.join(', ')} · ${run.status}`}
    >
      <ol className="space-y-1 text-xs">
        {stages.map((s) => {
          const st = run.stages[s.id];
          return (
            <li key={s.id} className="flex items-center gap-2">
              <span
                className={clsx(
                  'inline-block h-2 w-2 rounded-full',
                  st?.status === 'done'
                    ? 'bg-[color:var(--status-good)]'
                    : st?.status === 'running'
                      ? 'bg-accent'
                      : st?.status === 'skipped'
                        ? 'bg-grid'
                        : 'bg-line',
                )}
              />
              <span className="w-40 truncate">{s.name}</span>
              <span className="text-ink2">
                {st?.status}
                {st?.seconds !== undefined ? ` · ${st.seconds}s` : ''}
              </span>
              <span className="ml-auto text-muted">
                {Object.entries(st ?? {})
                  .filter(([k]) => !['status', 'seconds', 'agent'].includes(k))
                  .map(([k, v]) => `${k} ${String(v)}`)
                  .join(' · ')}
              </span>
            </li>
          );
        })}
      </ol>
      {run.error && <p className="mt-2 text-xs text-[color:var(--status-critical)]">{run.error}</p>}
      <pre className="mt-3 max-h-56 overflow-auto rounded-md bg-page p-2 text-[11px] leading-relaxed text-ink2">
        {run.log.map((l) => `${l.t.slice(11, 19)} [${l.stage}] ${l.msg}`).join('\n')}
      </pre>
    </Card>
  );
}
