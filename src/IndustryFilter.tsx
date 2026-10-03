import { useEffect, useState } from "react";
import { fetchFilterOptions } from "./api";
import type { SectorOption } from "./api";

/** Sector → industry checklist. Reports the included industries, or null when nothing is filtered out. */
export function IndustryFilter({
  market,
  onChange,
}: {
  market: "hk" | "tw";
  onChange: (included: string[] | null) => void;
}) {
  const [sectors, setSectors] = useState<SectorOption[]>([]);
  const [excluded, setExcluded] = useState<Set<string>>(new Set());

  useEffect(() => {
    let mounted = true;
    fetchFilterOptions(market).then((s) => {
      if (!mounted) return;
      setSectors(s);
      setExcluded(new Set());
      onChange(null);
    });
    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [market]);

  const all = sectors.flatMap((s) => s.industries.map((i) => i.industry));
  const update = (next: Set<string>) => {
    setExcluded(next);
    onChange(next.size === 0 ? null : all.filter((i) => !next.has(i)));
  };
  const toggle = (industries: string[], include: boolean) => {
    const next = new Set(excluded);
    industries.forEach((i) => (include ? next.delete(i) : next.add(i)));
    update(next);
  };

  if (sectors.length === 0) return null;
  const firms = sectors.reduce(
    (sum, s) => sum + s.industries.filter((i) => !excluded.has(i.industry)).reduce((a, i) => a + i.n, 0),
    0,
  );
  return (
    <div className="industry-filter">
      <div className="preference-head">
        <strong>Industries</strong>
        <em>
          {all.length - excluded.size} of {all.length} · {firms} companies
        </em>
      </div>
      <div className="industry-filter-actions">
        <button type="button" className="text-button" onClick={() => update(new Set())}>
          Select all
        </button>
        <button type="button" className="text-button" onClick={() => update(new Set(all))}>
          Clear
        </button>
      </div>
      {sectors.map((s) => {
        const names = s.industries.map((i) => i.industry);
        const on = names.filter((i) => !excluded.has(i)).length;
        return (
          <details key={s.sector}>
            <summary>
              <input
                type="checkbox"
                aria-label={`Include ${s.sector}`}
                checked={on === names.length}
                ref={(el) => {
                  if (el) el.indeterminate = on > 0 && on < names.length;
                }}
                onClick={(e) => e.stopPropagation()}
                onChange={(e) => toggle(names, e.target.checked)}
              />
              <span>{s.sector}</span>
              <small>
                {on}/{names.length}
              </small>
            </summary>
            {s.industries.map((i) => (
              <label key={i.industry}>
                <input
                  type="checkbox"
                  checked={!excluded.has(i.industry)}
                  onChange={(e) => toggle([i.industry], e.target.checked)}
                />
                <span>{i.industry}</span>
                <small>{i.n}</small>
              </label>
            ))}
          </details>
        );
      })}
      <small>Applied exactly as ticked. Only the selected industries are bought or rebalanced; holdings outside them are left untouched.</small>
    </div>
  );
}
