import type { ReactNode } from 'react';
import clsx from 'clsx';

export function Card({
  title,
  subtitle,
  children,
  className,
  right,
}: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
  right?: ReactNode;
}) {
  return (
    <section className={clsx('rounded-lg border border-line bg-surface p-4', className)}>
      {(title || right) && (
        <header className="mb-3 flex items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-sm font-semibold">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-ink2">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      {children}
    </section>
  );
}

export function StatTile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <div className="text-xs text-ink2">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-line p-6 text-center text-sm text-ink2">
      {children}
    </div>
  );
}

export function Loading() {
  return <div className="p-6 text-sm text-muted">Loading…</div>;
}

export function ErrorBox({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="rounded-md border border-[color:var(--status-critical)]/40 p-4 text-sm">
      <div className="font-medium">Could not reach the API</div>
      <div className="mt-1 text-ink2">
        {msg}. Is the backend running? Try <code>make api</code>.
      </div>
    </div>
  );
}

export function Select<T extends string | number>({
  value,
  onChange,
  options,
  label,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
  label?: string;
}) {
  return (
    <label className="flex items-center gap-2 text-xs text-ink2">
      {label}
      <select
        value={String(value)}
        onChange={(e) => {
          const raw = e.target.value;
          const match = options.find((o) => String(o.value) === raw);
          if (match) onChange(match.value);
        }}
        className="rounded-md border border-line bg-surface px-2 py-1 text-sm text-ink"
      >
        {options.map((o) => (
          <option key={String(o.value)} value={String(o.value)}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function Table<T extends object>({
  rows,
  columns,
  rowKey,
  onRowClick,
}: {
  rows: T[];
  columns: {
    key: string;
    label: string;
    render: (r: T) => ReactNode;
    align?: 'left' | 'right';
    width?: string;
  }[];
  rowKey: (r: T) => string;
  onRowClick?: (r: T) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-xs text-ink2">
            {columns.map((c) => (
              <th
                key={c.key}
                style={{ width: c.width }}
                className={clsx(
                  'py-2 pr-3 font-medium',
                  c.align === 'right' ? 'text-right' : 'text-left',
                )}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={rowKey(r)}
              onClick={onRowClick ? () => onRowClick(r) : undefined}
              className={clsx(
                'border-b border-grid last:border-0',
                onRowClick && 'cursor-pointer hover:bg-accent/5',
              )}
            >
              {columns.map((c) => (
                <td
                  key={c.key}
                  className={clsx(
                    'py-1.5 pr-3 align-top',
                    c.align === 'right' && 'text-right tabular',
                  )}
                >
                  {c.render(r)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
