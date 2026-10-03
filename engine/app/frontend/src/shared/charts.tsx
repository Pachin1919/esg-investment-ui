// Shared chart chrome: palette roles as CSS variables, recessive axes, one tooltip style.
import type { ReactNode } from 'react';

export const color = {
  s1: 'var(--series-1)',
  s2: 'var(--series-2)',
  s3: 'var(--series-3)',
  seq: ['var(--seq-200)', 'var(--seq-350)', 'var(--seq-500)', 'var(--seq-650)'],
  neg: 'var(--div-neg)',
  pos: 'var(--div-pos)',
  grid: 'var(--grid)',
  axis: 'var(--axis)',
  ink2: 'var(--text-secondary)',
  muted: 'var(--text-muted)',
};

export const axisProps = {
  tick: { fill: color.muted, fontSize: 11 },
  axisLine: { stroke: color.axis },
  tickLine: false as const,
};

export function ChartTooltip({
  active,
  label,
  rows,
}: {
  active?: boolean;
  label?: ReactNode;
  rows: { name: string; value: string; swatch?: string }[];
}) {
  if (!active) return null;
  return (
    <div className="rounded-md border border-line bg-surface px-3 py-2 text-xs shadow-md">
      {label && <div className="mb-1 font-medium text-ink">{label}</div>}
      {rows.map((r) => (
        <div key={r.name} className="flex items-center gap-2">
          {r.swatch && (
            <span className="inline-block h-2 w-2 rounded-sm" style={{ background: r.swatch }} />
          )}
          <span className="text-ink2">{r.name}</span>
          <span className="ml-auto tabular text-ink">{r.value}</span>
        </div>
      ))}
    </div>
  );
}

export function Legend({ items }: { items: { name: string; swatch: string }[] }) {
  return (
    <div className="mt-2 flex flex-wrap gap-4 text-xs text-ink2">
      {items.map((i) => (
        <span key={i.name} className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-3 rounded-sm" style={{ background: i.swatch }} />
          {i.name}
        </span>
      ))}
    </div>
  );
}
