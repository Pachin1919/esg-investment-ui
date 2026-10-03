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
import { useGmb } from '@/core/queries';
import { fmt } from '@/core/format';
import { Card, Empty, ErrorBox, Loading, StatTile } from '@/shared/ui';
import { axisProps, ChartTooltip, color, Legend } from '@/shared/charts';

const SERIES = [
  { key: 'cum_gmb', raw: 'gmb', name: 'GMB value-weighted', swatch: color.s1 },
  { key: 'cum_gmb_ew', raw: 'gmb_ew', name: 'GMB equal-weighted', swatch: color.s2 },
  { key: 'cum_gmb_within', raw: 'gmb_within', name: 'GMB within-industry', swatch: color.s3 },
];

export function GmbPage() {
  const q = useGmb();
  if (q.isError) return <ErrorBox error={q.error} />;
  if (q.isLoading || !q.data) return <Loading />;
  const { months, summary } = q.data;
  if (!months.length)
    return (
      <Empty>
        No GMB series yet. Run <code>scripts/phase0_replicate.py</code>.
      </Empty>
    );
  const yearTicks = months.filter((m) => m.month.endsWith('-01')).map((m) => m.month);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Green-minus-brown factor</h1>
        <p className="mt-1 max-w-3xl text-sm text-ink2">
          Monthly return of green minus brown portfolios sorted on g (Pástor, Stambaugh & Taylor
          2022). Value- and equal-weighted, plus the within-industry component. PST find the return
          sits almost entirely in the across-industry part.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {SERIES.map((s) => (
          <StatTile
            key={s.key}
            label={s.name}
            value={fmt.bps(summary[s.raw]?.mean_bps)}
            hint={
              summary[s.raw]
                ? `per month, t = ${fmt.num(summary[s.raw].t_stat, 2)}, ${summary[s.raw].n_months} months`
                : 'not available'
            }
          />
        ))}
      </div>
      <Card title="Cumulative return" subtitle="Compounded from the first month of the sample">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={months} margin={{ top: 8, right: 24, bottom: 4, left: -8 }}>
            <CartesianGrid stroke={color.grid} vertical={false} />
            <XAxis
              dataKey="month"
              ticks={yearTicks}
              tickFormatter={(m: string) => m.slice(0, 4)}
              {...axisProps}
            />
            <YAxis tickFormatter={(v: number) => `${(v * 100).toFixed(0)} %`} {...axisProps} />
            <Tooltip
              cursor={{ stroke: color.axis }}
              content={({ active, label, payload }) => (
                <ChartTooltip
                  active={active}
                  label={String(label)}
                  rows={(payload ?? []).map((p) => ({
                    name: String(p.name),
                    value: fmt.pct(p.value as number),
                    swatch: String(p.stroke),
                  }))}
                />
              )}
            />
            {SERIES.map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.name}
                stroke={s.swatch}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
        <Legend items={SERIES.map((s) => ({ name: s.name, swatch: s.swatch }))} />
      </Card>
      <Card title="Monthly GMB, value-weighted" subtitle="Blue above zero, red below">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={months}
            margin={{ top: 8, right: 24, bottom: 4, left: -8 }}
            barCategoryGap="20%"
          >
            <CartesianGrid stroke={color.grid} vertical={false} />
            <XAxis
              dataKey="month"
              ticks={yearTicks}
              tickFormatter={(m: string) => m.slice(0, 4)}
              {...axisProps}
            />
            <YAxis tickFormatter={(v: number) => `${(v * 100).toFixed(0)} %`} {...axisProps} />
            <Tooltip
              cursor={{ fill: 'var(--grid)', opacity: 0.4 }}
              content={({ active, label, payload }) => (
                <ChartTooltip
                  active={active}
                  label={String(label)}
                  rows={[{ name: 'GMB', value: fmt.pct(payload?.[0]?.value as number, 2) }]}
                />
              )}
            />
            <Bar dataKey="gmb">
              {months.map((m) => (
                <Cell key={m.month} fill={(m.gmb ?? 0) >= 0 ? color.pos : color.neg} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}
