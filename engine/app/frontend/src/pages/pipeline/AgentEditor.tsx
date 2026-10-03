import clsx from 'clsx';
import type { AgentSpec } from '@/core/api';
import { Select } from '@/shared/ui';

const MODELS = ['kimi-k3', 'kimi-k2.6', 'claude-opus-5', 'claude-sonnet-5', 'claude-haiku-4-5-20251001'];
const EFFORTS = ['low', 'medium', 'high'];
const input = 'rounded-md border border-line bg-surface px-2 py-1 text-sm text-ink';

export function AgentEditor({
  agent,
  onChange,
}: {
  agent: AgentSpec;
  onChange: (a: AgentSpec) => void;
}) {
  return (
    <div className="mt-3 rounded-md bg-page p-3">
      <div className="grid gap-3 md:grid-cols-3">
        <label className="text-xs text-ink2">
          Agent name
          <input
            value={agent.name}
            onChange={(e) => onChange({ ...agent, name: e.target.value })}
            className={clsx('mt-1 w-full', input)}
          />
        </label>
        <Select
          label="Model"
          value={agent.model}
          onChange={(v) => onChange({ ...agent, model: v })}
          options={(MODELS.includes(agent.model) ? MODELS : [agent.model, ...MODELS]).map((m) => ({
            value: m,
            label: m,
          }))}
        />
        <Select
          label="Effort"
          value={agent.effort}
          onChange={(v) => onChange({ ...agent, effort: v })}
          options={EFFORTS.map((m) => ({ value: m, label: m }))}
        />
      </div>
      <label className="mt-2 block text-xs text-ink2">
        Role prompt (appended to the versioned base prompt; creates a prompt variant with its own
        cache)
        <textarea
          value={agent.role_prompt}
          onChange={(e) => onChange({ ...agent, role_prompt: e.target.value })}
          rows={3}
          className="mt-1 w-full rounded-md border border-line bg-surface px-2 py-1 font-mono text-xs text-ink"
        />
      </label>
    </div>
  );
}
