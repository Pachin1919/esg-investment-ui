import clsx from 'clsx';
import type { StageSpec } from '@/core/api';
import { color } from '@/shared/charts';
import { WeightEditor } from './WeightEditor';

const ALL_SECTIONS = ['business', 'risk_factors', 'mdna', 'full_climate', 'press_release'];
const TALK_FIELDS = [
  'ambition',
  'specificity',
  'forward_looking_share',
  'hedging',
  'promotional_tone',
];
const WALK_FIELDS = [
  'realised_reductions',
  'capital_deployed',
  'verification',
  'governance',
  'hard_data_consistency',
  'implementation_share',
];
const input = 'rounded-md border border-line bg-surface px-2 py-1 text-sm text-ink';

/** Per-kind parameter editors. Deterministic stages expose their knobs here; agent settings live in AgentEditor. */
export function StageParams({
  stage,
  setParam,
}: {
  stage: StageSpec;
  setParam: (k: string, v: unknown) => void;
}) {
  const p = stage.params;
  switch (stage.kind) {
    case 'collect_documents': {
      const cur = (p.sections as string[] | undefined) ?? [];
      return (
        <div className="mt-3 flex flex-wrap gap-3 text-xs text-ink2">
          Sections
          {ALL_SECTIONS.map((sec) => (
            <label key={sec} className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={cur.includes(sec)}
                onChange={(e) =>
                  setParam(
                    'sections',
                    e.target.checked ? [...cur, sec] : cur.filter((x) => x !== sec),
                  )
                }
              />
              <span className="font-mono">{sec}</span>
            </label>
          ))}
        </div>
      );
    }
    case 'preprocess':
      return (
        <div className="mt-3 flex flex-wrap gap-4 text-xs text-ink2">
          <label className="flex items-center gap-2">
            Max characters per section
            <input
              type="number"
              step={5000}
              value={Number(p.max_chars ?? 60000)}
              onChange={(e) => setParam('max_chars', Number(e.target.value))}
              className={clsx('w-24', input)}
            />
          </label>
          <label className="flex items-center gap-2">
            Skip sections shorter than
            <input
              type="number"
              step={100}
              value={Number(p.min_chars ?? 300)}
              onChange={(e) => setParam('min_chars', Number(e.target.value))}
              className={clsx('w-24', input)}
            />
          </label>
        </div>
      );
    case 'score_talkwalk':
      return (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <WeightEditor
            title="Talk pillar weights"
            fields={TALK_FIELDS}
            weights={(p.talk_weights as Record<string, number>) ?? {}}
            onChange={(w) => setParam('talk_weights', w)}
            swatch={color.s1}
          />
          <WeightEditor
            title="Walk pillar weights"
            fields={WALK_FIELDS}
            weights={(p.walk_weights as Record<string, number>) ?? {}}
            onChange={(w) => setParam('walk_weights', w)}
            swatch={color.s2}
          />
        </div>
      );
    case 'aggregate':
      return (
        <div className="mt-3 flex flex-wrap gap-4 text-xs text-ink2">
          <label className="flex items-center gap-2">
            10-K weight (others 1)
            <input
              type="number"
              step={0.5}
              min={0}
              value={Number(((p.form_weights as Record<string, number>) ?? {})['10-K'] ?? 2)}
              onChange={(e) => setParam('form_weights', { '10-K': Number(e.target.value) })}
              className={clsx('w-20', input)}
            />
          </label>
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={!!p.publish}
              onChange={(e) => setParam('publish', e.target.checked)}
            />{' '}
            publish to outputs/talkwalk_*.csv (overwrites the dashboard's data)
          </label>
        </div>
      );
    default:
      return null;
  }
}
