import { useEffect, useRef, useState } from "react";
import { CaretDown, DownloadSimple } from "@phosphor-icons/react";

/** One export button for the comparison tables; each entry downloads one table as CSV. */
export default function ExportTablesMenu({ disabled, items }: { disabled: boolean; items: { label: string; detail?: string; onExport: () => void }[] }) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null), trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    const dismiss = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    const escape = (e: KeyboardEvent) => { if (e.key === "Escape") { setOpen(false); trigger.current?.focus(); } };
    document.addEventListener("mousedown", dismiss); document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("mousedown", dismiss); document.removeEventListener("keydown", escape); };
  }, [open]);
  return <div ref={root} className="table-export">
    <button ref={trigger} type="button" className="table-export-trigger" aria-haspopup="menu" aria-expanded={open} disabled={disabled} onClick={() => setOpen(o => !o)}><DownloadSimple size={17} />Export tables<CaretDown size={14} /></button>
    {open && <div className="table-export-menu" role="menu">{items.map(item => <button key={item.label} type="button" role="menuitem" onClick={() => { item.onExport(); setOpen(false); }}>{item.label}<small>CSV</small></button>)}</div>}
  </div>;
}
