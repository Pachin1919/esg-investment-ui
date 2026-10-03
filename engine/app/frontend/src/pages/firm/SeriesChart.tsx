import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { axisProps, ChartTooltip, color, Legend } from '@/shared/charts';

export function SeriesChart<T extends object>({
  data,
  x,
  series,
  format,
  tickFormat,
  domain,
}: {
  data: T[];
  x: keyof T & string;
  series: { key: string; name: string; swatch: string }[];
  format: (v: number) => string;
  tickFormat: (v: number) => string;
  domain?: [number, number];
}) {
  return (
    <>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 24, bottom: 4, left: 0 }}>
          <CartesianGrid stroke={color.grid} vertical={false} />
          <XAxis dataKey={x} padding={{ left: 16, right: 16 }} {...axisProps} />
          <YAxis domain={domain} tickFormatter={tickFormat} width={56} {...axisProps} />
          <Tooltip
            cursor={{ stroke: color.axis }}
            content={({ active, label, payload }) => (
              <ChartTooltip
                active={active}
                label={String(label)}
                rows={(payload ?? []).map((p) => ({
                  name: String(p.name),
                  value: format(p.value as number),
                  swatch: String(p.stroke),
                }))}
              />
            )}
          />
          {series.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name}
              stroke={s.swatch}
              strokeWidth={2}
              dot={{ r: 4, strokeWidth: 2, fill: 'var(--surface-1)' }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      {series.length > 1 && (
        <Legend items={series.map((s) => ({ name: s.name, swatch: s.swatch }))} />
      )}
    </>
  );
}
