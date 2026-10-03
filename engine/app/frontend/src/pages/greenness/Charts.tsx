import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { GreennessResponse } from '@/core/api';
import { fmt } from '@/core/format';
import { Card } from '@/shared/ui';
import { axisProps, ChartTooltip, color } from '@/shared/charts';

export function SectorBars({ sectors }: { sectors: GreennessResponse['sectors'] }) {
  const gMin = Math.min(...sectors.map((s) => s.g));
  const seq = (g: number) =>
    color.seq[Math.min(3, Math.floor((gMin >= 0 ? 0 : Math.min(1, Math.max(0, g / gMin))) * 4))];
  return (
    <Card
      title="Average g by sector"
      subtitle="PST Table 1 analogue: the across-industry component of greenness"
    >
      <ResponsiveContainer width="100%" height={26 * sectors.length + 30}>
        <BarChart
          data={sectors}
          layout="vertical"
          margin={{ top: 4, right: 48, bottom: 4, left: 8 }}
          barCategoryGap="25%"
        >
          <CartesianGrid stroke={color.grid} horizontal={false} />
          <XAxis type="number" domain={[Math.floor(gMin), 0]} {...axisProps} />
          <YAxis type="category" dataKey="sector" width={150} {...axisProps} />
          <Tooltip
            cursor={{ fill: 'var(--grid)', opacity: 0.4 }}
            content={({ active, label, payload }) => {
              const s = payload?.[0]?.payload as { n: number } | undefined;
              return (
                <ChartTooltip
                  active={active}
                  label={String(label)}
                  rows={[
                    { name: 'mean g', value: fmt.num(payload?.[0]?.value as number) },
                    { name: 'firms', value: String(s?.n ?? '') },
                  ]}
                />
              );
            }}
          />
          <Bar
            dataKey="g"
            radius={[4, 0, 0, 4]}
            label={{
              position: 'right',
              fill: color.ink2,
              fontSize: 11,
              formatter: (v: number) => v.toFixed(2),
            }}
          >
            {sectors.map((s) => (
              <Cell key={s.sector} fill={seq(s.g)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function histogram(values: number[], bins: number) {
  if (!values.length) return [];
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const w = (hi - lo) / bins || 1;
  const out = Array.from({ length: bins }, (_, i) => ({
    x0: lo + i * w,
    x1: lo + (i + 1) * w,
    n: 0,
  }));
  values.forEach((v) => {
    out[Math.min(bins - 1, Math.floor((v - lo) / w))].n += 1;
  });
  return out;
}

export function Histogram({ values, subtitle }: { values: number[]; subtitle: string }) {
  const hist = histogram(values, 20);
  return (
    <Card title="Distribution of g" subtitle={subtitle}>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart
          data={hist}
          margin={{ top: 8, right: 8, bottom: 4, left: -16 }}
          barCategoryGap="10%"
        >
          <CartesianGrid stroke={color.grid} vertical={false} />
          <XAxis dataKey="x0" tickFormatter={(v: number) => v.toFixed(1)} {...axisProps} />
          <YAxis {...axisProps} />
          <Tooltip
            cursor={{ fill: 'var(--grid)', opacity: 0.4 }}
            content={({ active, payload }) => {
              const b = payload?.[0]?.payload as { x0: number; x1: number; n: number } | undefined;
              return (
                <ChartTooltip
                  active={active && !!b}
                  label={b ? `g in [${b.x0.toFixed(2)}, ${b.x1.toFixed(2)})` : ''}
                  rows={[{ name: 'firms', value: String(b?.n ?? '') }]}
                />
              );
            }}
          />
          <Bar dataKey="n" fill={color.s1} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
