import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { TalkWalkYear } from '@/core/api';
import { fmt } from '@/core/format';
import { Card } from '@/shared/ui';
import { axisProps, ChartTooltip, color, Legend } from '@/shared/charts';

const dot = { r: 4, strokeWidth: 2, fill: 'var(--surface-1)' };

export function PillarLines({ years }: { years: TalkWalkYear[] }) {
  return (
    <Card
      title="Talk and walk by year"
      subtitle="Firm-year pillars, 10-K weighted 2×, other filings 1×"
      className="lg:col-span-2"
    >
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={years} margin={{ top: 8, right: 24, bottom: 4, left: -16 }}>
          <CartesianGrid stroke={color.grid} vertical={false} />
          <XAxis dataKey="year" padding={{ left: 16, right: 16 }} {...axisProps} />
          <YAxis domain={[0, 10]} ticks={[0, 2.5, 5, 7.5, 10]} {...axisProps} />
          <Tooltip
            cursor={{ stroke: color.axis }}
            content={({ active, label, payload }) => (
              <ChartTooltip
                active={active}
                label={String(label)}
                rows={(payload ?? []).map((p) => ({
                  name: String(p.name),
                  value: fmt.num(p.value as number),
                  swatch: String(p.stroke),
                }))}
              />
            )}
          />
          <Line
            type="monotone"
            dataKey="talk"
            name="Talk"
            stroke={color.s1}
            strokeWidth={2}
            dot={dot}
          />
          <Line
            type="monotone"
            dataKey="walk"
            name="Walk"
            stroke={color.s2}
            strokeWidth={2}
            dot={dot}
          />
        </LineChart>
      </ResponsiveContainer>
      <Legend
        items={[
          { name: 'Talk', swatch: color.s1 },
          { name: 'Walk', swatch: color.s2 },
        ]}
      />
    </Card>
  );
}

export function GapBars({ years }: { years: TalkWalkYear[] }) {
  return (
    <Card title="Gap (talk − walk)" subtitle="Positive = words exceed actions">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={years}
          margin={{ top: 8, right: 8, bottom: 4, left: -16 }}
          barCategoryGap="30%"
        >
          <CartesianGrid stroke={color.grid} vertical={false} />
          <XAxis dataKey="year" {...axisProps} />
          <YAxis domain={[-10, 10]} {...axisProps} />
          <Tooltip
            cursor={{ fill: 'var(--grid)', opacity: 0.4 }}
            content={({ active, label, payload }) => (
              <ChartTooltip
                active={active}
                label={String(label)}
                rows={(payload ?? []).map((p) => ({
                  name: 'Gap',
                  value: fmt.num(p.value as number),
                }))}
              />
            )}
          />
          <Bar dataKey="gap" radius={[4, 4, 0, 0]}>
            {years.map((y) => (
              <Cell key={y.year} fill={y.gap >= 0 ? color.neg : color.pos} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function SubscoreBars({
  title,
  row,
  prefix,
  keys,
  fill,
}: {
  title: string;
  row: TalkWalkYear;
  prefix: string;
  keys: string[];
  fill: string;
}) {
  const data = keys.map((k) => ({
    name: k.replace(/_/g, ' '),
    value: Number(row[`${prefix}${k}`] ?? 0),
  }));
  return (
    <Card title={title} subtitle="0 = absent, 10 = exceptional">
      <ResponsiveContainer width="100%" height={30 * data.length + 30}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 40, bottom: 4, left: 8 }}
          barCategoryGap="28%"
        >
          <CartesianGrid stroke={color.grid} horizontal={false} />
          <XAxis type="number" domain={[0, 10]} ticks={[0, 5, 10]} {...axisProps} />
          <YAxis type="category" dataKey="name" width={150} {...axisProps} />
          <Tooltip
            cursor={{ fill: 'var(--grid)', opacity: 0.4 }}
            content={({ active, label, payload }) => (
              <ChartTooltip
                active={active}
                label={String(label)}
                rows={(payload ?? []).map((p) => ({
                  name: 'score',
                  value: fmt.num(p.value as number),
                }))}
              />
            )}
          />
          <Bar
            dataKey="value"
            fill={fill}
            radius={[0, 4, 4, 0]}
            label={{
              position: 'right',
              fill: color.ink2,
              fontSize: 11,
              formatter: (v: number) => v.toFixed(1),
            }}
          />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
