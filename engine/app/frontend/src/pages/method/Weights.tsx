export function Weights({
  title,
  weights,
  fields,
  swatch,
  note,
}: {
  title: string;
  weights: Record<string, number>;
  fields: string[];
  swatch: string;
  note: string;
}) {
  return (
    <div className="rounded-md bg-page p-3">
      <div className="text-xs font-medium">{title}</div>
      <ul className="mt-1 space-y-1">
        {fields.map((f) => {
          const w = weights[f] ?? 0;
          return (
            <li key={f} className="flex items-center gap-2 text-xs">
              <span className="w-40 truncate text-ink2">{f.replace(/_/g, ' ')}</span>
              <span
                className="h-2 rounded-sm"
                style={{
                  width: `${Math.max(2, w * 160)}px`,
                  background: w ? swatch : 'var(--grid)',
                }}
              />
              <span className="tabular text-ink2">{w ? w.toFixed(2) : 'scored only'}</span>
            </li>
          );
        })}
      </ul>
      <p className="mt-2 text-[11px] text-muted">{note}</p>
    </div>
  );
}
