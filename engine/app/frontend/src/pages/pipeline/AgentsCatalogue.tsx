import { usePipelineAgents } from '@/core/queries';
import { Card } from '@/shared/ui';
import { color } from '@/shared/charts';

const COST: Record<string, string> = {
  free: 'var(--status-good)',
  network: 'var(--series-1)',
  paid: 'var(--status-critical)',
};

export function AgentsCatalogue() {
  const q = usePipelineAgents();
  if (!q.data) return null;
  return (
    <Card
      title="Agents and their tools"
      subtitle="Defined in pipeline/agents/<id>/agent.py; tools in pipeline/tools/. An agent can only call the tools listed here."
    >
      <ul className="grid gap-3 md:grid-cols-2">
        {q.data.map((a) => (
          <li key={a.id} className="rounded-md border border-line p-3 text-xs">
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="font-medium text-ink">{a.role}</span>
              <span className="font-mono text-muted">{a.folder}</span>
              <span
                className="rounded px-1.5 text-[11px] text-white"
                style={{ background: a.llm ? color.s2 : color.s1 }}
              >
                {a.llm ? `LLM · ${a.default_model}` : 'code'}
              </span>
            </div>
            <p className="mt-1 text-ink2">{a.description}</p>
            <div className="mt-2 text-muted">
              reads {a.inputs.join(', ')} → writes {a.outputs.join(', ')}
            </div>
            <ul className="mt-2 flex flex-wrap gap-1">
              {a.tools.map((t) => (
                <li
                  key={t.name}
                  title={`${t.description} (${t.kind}, ${t.cost})`}
                  className="flex items-center gap-1 rounded border border-line px-1.5 py-0.5 font-mono text-[11px] text-ink2"
                >
                  <span
                    className="inline-block h-1.5 w-1.5 rounded-full"
                    style={{ background: COST[t.cost] }}
                  />
                  {t.name}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-[11px] text-muted">
        Dot colour = tool cost: green free, blue network download, red paid model call.
      </p>
    </Card>
  );
}
