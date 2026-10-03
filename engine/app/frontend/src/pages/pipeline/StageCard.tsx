import { Bot, Cpu } from 'lucide-react';
import clsx from 'clsx';
import type { StageSpec } from '@/core/api';
import { color } from '@/shared/charts';
import { AgentEditor } from './AgentEditor';
import { StageParams } from './StageParams';

export function StageCard({
  stage,
  index,
  onChange,
}: {
  stage: StageSpec;
  index: number;
  onChange: (p: Partial<StageSpec>) => void;
}) {
  const agent = stage.agent;
  const setParam = (k: string, v: unknown) => onChange({ params: { ...stage.params, [k]: v } });
  return (
    <section
      className={clsx(
        'rounded-lg border border-line bg-surface p-4',
        !stage.enabled && 'opacity-60',
      )}
    >
      <header className="flex items-start gap-3">
        <div
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white"
          style={{ background: agent ? color.s2 : color.s1 }}
        >
          {agent ? <Bot className="h-4 w-4" /> : <Cpu className="h-4 w-4" />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted">{index + 1}</span>
            <input
              value={stage.name}
              onChange={(e) => onChange({ name: e.target.value })}
              className="min-w-0 flex-1 bg-transparent text-sm font-medium outline-none"
            />
            <span className="rounded border border-line px-1.5 text-[11px] text-ink2">
              {stage.kind}
            </span>
            <label className="flex items-center gap-1 text-xs text-ink2">
              <input
                type="checkbox"
                checked={stage.enabled}
                onChange={(e) => onChange({ enabled: e.target.checked })}
              />{' '}
              enabled
            </label>
          </div>
          <p className="mt-1 text-xs text-ink2">{stage.description}</p>
        </div>
      </header>
      {agent && <AgentEditor agent={agent} onChange={(a) => onChange({ agent: a })} />}
      <StageParams stage={stage} setParam={setParam} />
    </section>
  );
}
