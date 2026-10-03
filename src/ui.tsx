import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import { Leaf, SquaresFour, X } from "@phosphor-icons/react";

export const riskColors = ["#287b53", "#326bbb", "#a97808", "#be621e", "#b13c46"];

export function Button({ children, onClick, disabled, kind = "primary" }: { children: ReactNode; onClick?: () => void; disabled?: boolean; kind?: "primary" | "secondary" | "ghost" }) {
  return <button type="button" className={`button ${kind}`} onClick={onClick} disabled={disabled}>{children}</button>;
}
export function Dialog({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    const dialog = ref.current!; dialog.showModal();
    const overflow = document.body.style.overflow; document.body.style.overflow = "hidden";
    return () => { dialog.close(); document.body.style.overflow = overflow; opener?.focus(); };
  }, []);
  return <dialog ref={ref} className="flow-dialog" onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) onClose(); }} aria-labelledby="flow-title"><div className="setup-modal"><div className="setup-top"><h2 id="flow-title">{title}</h2><button className="close-button" onClick={onClose} aria-label="Close dialog"><X /></button></div>{children}</div></dialog>;
}
export function RiskBadge({ value }: { value: number }) {
  return <span className="risk-badge" style={{ "--risk-color": riskColors[value - 1] } as React.CSSProperties}><i />Risk level {value}</span>;
}
export function HighlightBadge({ variant, children }: { variant: "assets" | "green" | "budget"; children: ReactNode }) {
  return <span className={`highlight-badge highlight-${variant}`}>{variant === "green" ? <Leaf size={15} /> : <SquaresFour size={14} />}<span>{children}</span></span>;
}
