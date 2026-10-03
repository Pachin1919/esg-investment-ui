import { useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, type Estimate, type PipelineSpec, type RunMode, type StageSpec } from '@/core/api';
import { usePipelineConfigs, usePipelineDefault, usePipelineRun } from '@/core/queries';
import { Card, ErrorBox, Loading, Select } from '@/shared/ui';
import { StageCard } from './StageCard';
import { RunPanel, RunStatus } from './RunPanel';
import { RunResults } from './RunResults';
import { AgentsCatalogue } from './AgentsCatalogue';

const input = 'rounded-md border border-line bg-surface px-2 py-1 text-sm text-ink';

export function PipelinePage() {
  const def = usePipelineDefault();
  const configs = usePipelineConfigs();
  const qc = useQueryClient();
  const [spec, setSpec] = useState<PipelineSpec | null>(null);
  const [tickers, setTickers] = useState('XOM');
  const [mode, setMode] = useState<RunMode>('cache_only');
  const [runId, setRunId] = useState<string | null>(null);
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [saveName, setSaveName] = useState('');
  const run = usePipelineRun(runId);

  useEffect(() => {
    if (def.data && !spec) setSpec(def.data);
  }, [def.data, spec]);
  const tickerList = useMemo(
    () =>
      tickers
        .split(/[\s,]+/)
        .map((t) => t.trim().toUpperCase())
        .filter(Boolean),
    [tickers],
  );
  useEffect(() => {
    if (!spec || !tickerList.length) return setEstimate(null);
    const t = setTimeout(
      () =>
        api
          .pipelineEstimate(spec, tickerList)
          .then(setEstimate)
          .catch(() => setEstimate(null)),
      300,
    );
    return () => clearTimeout(t);
  }, [spec, tickerList]);

  if (def.isError) return <ErrorBox error={def.error} />;
  if (!spec) return <Loading />;

  const update = (patch: Partial<PipelineSpec>) => setSpec({ ...spec, ...patch });
  const updateStage = (id: string, patch: Partial<StageSpec>) =>
    setSpec({ ...spec, stages: spec.stages.map((s) => (s.id === id ? { ...s, ...patch } : s)) });
  const start = async () => {
    setMsg(null);
    try {
      setRunId((await api.pipelineStart(spec, tickerList, mode, false)).id);
    } catch (e) {
      const text = e instanceof Error ? e.message : String(e);
      if (text.includes('confirm_cost') && window.confirm(`${text}\n\nRun anyway?`))
        setRunId((await api.pipelineStart(spec, tickerList, mode, true)).id);
      else setMsg(text);
    }
  };
  const save = async () => {
    if (!saveName.trim()) return setMsg('Give the configuration a name first.');
    try {
      const r = await api.pipelineSave(saveName.trim(), { ...spec, name: saveName.trim() });
      setMsg(
        `Saved configs/pipeline/${r.saved}. Run it with scripts/run_pipeline.py --config configs/pipeline/${r.saved}`,
      );
      qc.invalidateQueries({ queryKey: ['pipeline', 'configs'] });
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Pipeline designer</h1>
        <p className="mt-1 max-w-3xl text-sm text-ink2">
          The pipeline is a chain of stages. Blue stages are deterministic code; orange stages are
          owned by an AI agent with its own model, effort and role prompt. Re-wire the chain, change
          what each agent is told, then run it in dry-run (free heuristics), cache-only (free,
          cached LLM answers) or live mode.
        </p>
      </div>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="space-y-4">
          <Card title="Sources" subtitle="What is collected, for which filings and period">
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
              <Select
                label="Universe"
                value={spec.universe}
                onChange={(v) => update({ universe: v })}
                options={[
                  { value: 'us', label: 'S&P 500 (EDGAR)' },
                  { value: 'hk', label: 'Hang Seng (HKEX)' },
                ]}
              />
              <label className="flex items-center gap-2 text-xs text-ink2">
                Start
                <input
                  type="date"
                  value={spec.start}
                  onChange={(e) => update({ start: e.target.value })}
                  className={input}
                />
              </label>
              <label className="flex items-center gap-2 whitespace-nowrap text-xs text-ink2">
                Max 8-K per firm
                <input
                  type="number"
                  min={0}
                  max={40}
                  value={spec.max_8k}
                  onChange={(e) => update({ max_8k: Number(e.target.value) })}
                  className={`w-20 ${input}`}
                />
              </label>
              <div className="flex items-center gap-3 whitespace-nowrap text-xs text-ink2">
                Forms
                {['10-K', '10-Q', '8-K'].map((f) => (
                  <label key={f} className="flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={spec.forms.includes(f)}
                      onChange={(e) =>
                        update({
                          forms: e.target.checked
                            ? [...spec.forms, f]
                            : spec.forms.filter((x) => x !== f),
                        })
                      }
                    />
                    {f}
                  </label>
                ))}
              </div>
            </div>
          </Card>
          <div className="space-y-2">
            {spec.stages.map((s, i) => (
              <StageCard
                key={s.id}
                stage={s}
                index={i}
                onChange={(patch) => updateStage(s.id, patch)}
              />
            ))}
          </div>
        </div>
        <div className="space-y-4 xl:sticky xl:top-20 xl:self-start">
          <RunPanel
            tickers={tickers}
            setTickers={setTickers}
            tickerList={tickerList}
            mode={mode}
            setMode={setMode}
            estimate={estimate}
            onRun={start}
            running={run.data?.status === 'running'}
            saveName={saveName}
            setSaveName={setSaveName}
            onSave={save}
            msg={msg}
            configs={configs.data ?? []}
            onLoad={setSpec}
          />
          {run.data && <RunStatus run={run.data} stages={spec.stages} />}
        </div>
      </div>
      {run.data && <RunResults run={run.data} />}
      <AgentsCatalogue />
    </div>
  );
}
