import clsx from 'clsx';

export function WeightEditor({
  title,
  fields,
  weights,
  onChange,
  swatch,
}: {
  title: string;
  fields: string[];
  weights: Record<string, number>;
  onChange: (w: Record<string, number>) => void;
  swatch: string;
}) {
  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  return (
    <div className="rounded-md bg-page p-3">
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-medium">{title}</span>
        <span
          className={clsx(
            'text-[11px]',
            Math.abs(total - 1) > 0.01 ? 'text-[color:var(--status-critical)]' : 'text-muted',
          )}
        >
          sum {total.toFixed(2)}
        </span>
      </div>
      {fields.map((f) => (
        <label key={f} className="mt-1 flex items-center gap-2 text-xs">
          <span className="w-40 truncate text-ink2">{f.replace(/_/g, ' ')}</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={weights[f] ?? 0}
            onChange={(e) => onChange({ ...weights, [f]: Number(e.target.value) })}
            className="flex-1"
            style={{ accentColor: swatch }}
          />
          <span className="w-8 tabular text-right text-ink2">{(weights[f] ?? 0).toFixed(2)}</span>
        </label>
      ))}
      <p className="mt-1 text-[11px] text-muted">
        Weights are used as given (no renormalisation) so a sum other than 1 changes the scale.
      </p>
    </div>
  );
}
