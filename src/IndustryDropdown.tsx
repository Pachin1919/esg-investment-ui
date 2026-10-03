import { useEffect, useRef, useState } from "react";
import { CaretDown } from "@phosphor-icons/react";
import type { SectorOption } from "./api";
import { sectorColor } from "./live";

/** Sector → industry checklist in a dropdown. `value` is the included industries, or null for all of them. */
export default function IndustryDropdown({ sectors, value, onChange }: { sectors: SectorOption[]; value: string[] | null; onChange: (included: string[] | null) => void }) {
  const [open, setOpen] = useState(false), [expanded, setExpanded] = useState<string | null>(null);
  const root = useRef<HTMLDivElement>(null), trigger = useRef<HTMLButtonElement>(null), allBox = useRef<HTMLInputElement>(null);
  const all = sectors.flatMap(s => s.industries.map(i => i.industry));
  const included = new Set(value ?? all);
  const names = sectors.map(s => s.sector);
  useEffect(() => { if (allBox.current) allBox.current.indeterminate = included.size > 0 && included.size < all.length; });
  useEffect(() => {
    if (!open) return;
    const dismiss = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    const escape = (e: KeyboardEvent) => { if (e.key === "Escape") { e.preventDefault(); setOpen(false); trigger.current?.focus(); } };
    document.addEventListener("mousedown", dismiss); document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("mousedown", dismiss); document.removeEventListener("keydown", escape); };
  }, [open]);
  const set = (industries: string[], on: boolean) => {
    const next = new Set(included);
    industries.forEach(i => (on ? next.add(i) : next.delete(i)));
    onChange(next.size === all.length ? null : all.filter(i => next.has(i)));
  };
  const picked = sectors.filter(s => s.industries.some(i => included.has(i.industry)));
  const label = included.size === all.length ? "All industries" : picked.length ? `${picked[0].sector}${picked.length > 1 ? ` +${picked.length - 1}` : ""}` : "Choose industries";
  return <fieldset className="industry-options"><legend>Industry focus</legend>
    <div ref={root} className="industry-dropdown">
      <button ref={trigger} type="button" className="industry-dropdown-trigger" aria-label="Choose industries" aria-expanded={open} aria-controls="industry-dropdown-options" onClick={() => setOpen(o => !o)}><span>{label}</span><CaretDown size={16} /></button>
      {open && <div id="industry-dropdown-options" className="industry-dropdown-options" role="group" aria-label="Investment industries">
        <label className="all-industries"><input ref={allBox} type="checkbox" aria-label="All industries" checked={included.size === all.length} onChange={e => onChange(e.target.checked ? null : [])} /><span>All industries</span></label>
        {sectors.map(s => {
          const own = s.industries.map(i => i.industry), on = own.filter(i => included.has(i)).length;
          return <div key={s.sector} className="industry-group">
            <label className={on ? "industry-option selected" : "industry-option"}>
              <input type="checkbox" aria-label={s.sector} checked={on === own.length} ref={el => { if (el) el.indeterminate = on > 0 && on < own.length; }} onChange={e => set(own, e.target.checked)} />
              <i style={{ background: sectorColor(s.sector, names) }} /><span><strong>{s.sector}</strong><small>{s.n} companies · {on} of {own.length} industries</small></span>
              <button type="button" className="industry-expand" aria-label={`Show industries in ${s.sector}`} aria-expanded={expanded === s.sector} onClick={e => { e.preventDefault(); setExpanded(x => (x === s.sector ? null : s.sector)); }}><CaretDown size={14} /></button>
            </label>
            {expanded === s.sector && <div className="industry-children">{s.industries.map(i => <label key={i.industry}><input type="checkbox" checked={included.has(i.industry)} onChange={e => set([i.industry], e.target.checked)} /><span>{i.industry}</span><small>{i.n}</small></label>)}</div>}
          </div>;
        })}
      </div>}
    </div>
    <p className="industry-selection-hint">{included.size} of {all.length} industries selected · Applied exactly as ticked.</p>
  </fieldset>;
}
