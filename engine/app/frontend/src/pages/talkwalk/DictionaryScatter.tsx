import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { TalkWalkDocument } from '@/core/api';
import { fmt } from '@/core/format';
import { Card, Empty, Loading, Select } from '@/shared/ui';
import { axisProps, ChartTooltip, color } from '@/shared/charts';

export const DICT_AXES = [
  { value: 'glossiness', label: 'Glossiness (cosine gate → sentiment)' },
  { value: 'env_keyword_share', label: 'Environment keyword share' },
  { value: 'env_sentiment', label: 'Environment sentiment (LM window)' },
  { value: 'climate_similarity', label: 'Climate similarity (cosine)' },
  { value: 'forward_looking_share', label: 'Forward-looking share' },
] as const;
export type DictAxis = (typeof DICT_AXES)[number]['value'];

export function DictionaryScatter({
  docs,
  axis,
  setAxis,
  loading,
}: {
  docs: TalkWalkDocument[];
  axis: DictAxis;
  setAxis: (a: DictAxis) => void;
  loading: boolean;
}) {
  const hasAxis = docs.some((d) => d[axis] !== null && d[axis] !== undefined);
  return (
    <Card
      title="Dictionary measure vs LLM talk"
      subtitle="One point per document section. A cheap text measure should track the LLM talk score if the rubric captures 'talk'."
      right={
        <Select
          value={axis}
          onChange={setAxis}
          options={DICT_AXES.map((a) => ({ value: a.value, label: a.label }))}
        />
      }
    >
      {loading ? (
        <Loading />
      ) : !hasAxis ? (
        <Empty>
          The column <code>{axis}</code> is not in <code>talkwalk_documents.csv</code>. Re-run the
          scoring script with <code>--cache-only</code> to add the newer dictionary measures.
        </Empty>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <ScatterChart margin={{ top: 8, right: 16, bottom: 16, left: -8 }}>
            <CartesianGrid stroke={color.grid} />
            <XAxis
              type="number"
              dataKey={axis}
              name={axis}
              {...axisProps}
              label={{
                value: axis,
                position: 'insideBottom',
                offset: -8,
                fill: color.muted,
                fontSize: 11,
              }}
            />
            <YAxis
              type="number"
              dataKey="talk"
              domain={[0, 10]}
              {...axisProps}
              label={{
                value: 'LLM talk',
                angle: -90,
                position: 'insideLeft',
                fill: color.muted,
                fontSize: 11,
              }}
            />
            <Tooltip
              cursor={{ stroke: color.axis }}
              content={({ active, payload }) => {
                const d = payload?.[0]?.payload as TalkWalkDocument | undefined;
                return (
                  <ChartTooltip
                    active={active && !!d}
                    label={d ? `${d.form} · ${d.section} · ${d.period ?? d.filing_date}` : ''}
                    rows={
                      d
                        ? [
                            { name: 'LLM talk', value: fmt.num(d.talk) },
                            { name: 'LLM walk', value: fmt.num(d.walk) },
                            { name: axis, value: fmt.num(d[axis] as number, 3) },
                          ]
                        : []
                    }
                  />
                );
              }}
            />
            <Scatter data={docs} fill={color.s1} stroke="var(--surface-1)" strokeWidth={2} r={7} />
          </ScatterChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
