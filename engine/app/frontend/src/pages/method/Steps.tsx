import type { MethodSnapshot, StageSpec } from '@/core/api';
import { Card } from '@/shared/ui';
import { color } from '@/shared/charts';
import { Weights } from './Weights';

const LIT: Record<string, string> = {
  collect_documents: 'Chen (2025); Giannetti et al. (2023) use annual and sustainability reports',
  collect_hard_data:
    'Bolton & Kacperczyk (2021); Crosignani, Osambela & Pritsker (2025): 18-month publication lag',
  preprocess:
    'Engle et al. (2020) climate vocabulary; Gourier & Mathurin (2025) low relevance threshold',
  score_talkwalk:
    'Chen (2025) implementation rule; Liang, Sun & Teo (2022) talk given walk; Gourier & Mathurin (2025) prompt discipline',
  dictionary_measures:
    'Giannetti et al. (2023) keyword share + LM sentiment window; Engle et al. (2020) cosine similarity',
  review:
    'Cao, Jiang, Wang & Yang (2024): man + machine, the LLM as an analyst that is checked, not trusted',
  aggregate:
    'Giannetti et al. (2023) and Liang, Sun & Teo (2022) normalise per industry-year before sorting',
};

export function Steps({ stages, d }: { stages: StageSpec[]; d: MethodSnapshot }) {
  return (
    <Card
      title="The talk / walk pipeline, step by step"
      subtitle="Each step is either deterministic code or an LLM agent with its own prompt. You can re-wire it on the Pipeline page."
    >
      <ol className="space-y-3">
        {stages.map((s, i) => (
          <li key={s.id} className="flex gap-4 rounded-md border border-line p-3">
            <div
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold text-white"
              style={{ background: s.agent ? color.s2 : color.s1 }}
            >
              {i + 1}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="font-medium">{s.name}</span>
                <span className="rounded border border-line px-1.5 text-[11px] text-ink2">
                  {s.agent
                    ? `agent · ${s.agent.model} · effort ${s.agent.effort}`
                    : 'deterministic'}
                </span>
              </div>
              <p className="mt-1 text-sm text-ink2">{s.description}</p>
              {s.kind === 'score_talkwalk' && (
                <div className="mt-2 grid gap-3 md:grid-cols-2">
                  <Weights
                    title="Talk = weighted mean of"
                    weights={d.talk_weights}
                    fields={d.talk_fields}
                    swatch={color.s1}
                    note="Specificity and hedging are scored but not in the pillar: they describe credibility, not the amount of talk."
                  />
                  <Weights
                    title="Walk = weighted mean of"
                    weights={d.walk_weights}
                    fields={d.walk_fields}
                    swatch={color.s2}
                    note="Implementation share applies Chen's rule: only content that changes environmental outcomes counts."
                  />
                </div>
              )}
              {s.kind === 'aggregate' && (
                <p className="mt-1 text-xs text-ink2">
                  Weight per section = climate relevance (floor 0.5) × form weight (
                  {Object.entries(d.form_weights)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(', ')}
                  , others 1). Gap = talk − walk.
                </p>
              )}
              {s.kind === 'collect_documents' && (
                <p className="mt-1 text-xs text-ink2">
                  10-K items:{' '}
                  {Object.entries(d.sections_10k)
                    .map(([k, v]) => `Item ${k.toUpperCase()} → ${v}`)
                    .join(', ')}
                  ; sections under {d.min_section_chars} characters are dropped as cross-reference
                  stubs.
                </p>
              )}
              <p className="mt-1 text-xs text-muted">Literature: {LIT[s.kind]}</p>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}
