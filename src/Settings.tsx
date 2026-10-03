import { useState } from "react";
import { CheckCircle, Leaf } from "@phosphor-icons/react";
import { riskColors } from "./ui";

export default function Settings({ risk: savedRisk, green: savedGreen, maxInvestment: savedMax, currency, onSave }: { risk: number; green: number; maxInvestment: number; currency: string; onSave: (risk: number, green: number, maxInvestment: number) => void }) {
  const [risk, setRisk] = useState(savedRisk), [green, setGreen] = useState(savedGreen);
  const [maximum, setMaximum] = useState(String(savedMax)), [error, setError] = useState("");
  return <div className="workspace-page settings-page">
    <div className="workspace-heading"><div><span className="workspace-eyebrow">SETTINGS</span><h1>Your investment preferences.</h1><p>Choose your risk tolerance, environmental priority and investment budget.</p></div></div>
    <form className="settings-form" onSubmit={e => {
      e.preventDefault();
      const value = Number(maximum);
      if (!Number.isFinite(value) || value <= 0) { setError("Enter a positive maximum investment amount."); return; }
      onSave(risk, green, value); setError("");
    }}>
      <fieldset className="workspace-panel preference-setting"><legend>Risk tolerance</legend><p>Level 1 is lower tolerance; level 5 is higher tolerance.</p><div className="five-options risk-options" role="group" aria-label="Risk tolerance">{[1, 2, 3, 4, 5].map(v => <button type="button" key={v} aria-pressed={risk === v} className={risk === v ? "selected" : ""} style={{ "--risk-color": riskColors[v - 1] } as React.CSSProperties} onClick={() => setRisk(v)}><span>{v}</span>Level {v}{risk === v && <CheckCircle size={16} />}</button>)}</div><div className="scale-endpoints"><span>Lower tolerance</span><span>Higher tolerance</span></div></fieldset>
      <fieldset className="workspace-panel preference-setting"><legend>Green preference</legend><p>Choose how much emphasis to put on environmental performance.</p><div className="five-options green-options" role="group" aria-label="Green preference">{[1, 2, 3, 4, 5].map(v => <button type="button" key={v} aria-pressed={green === v} className={green === v ? "selected" : ""} onClick={() => setGreen(v)}><span><Leaf size={18} weight={green === v ? "fill" : "regular"} /></span>Level {v}</button>)}</div><div className="scale-endpoints"><span>Less emphasis</span><span>More emphasis</span></div></fieldset>
      <fieldset className="workspace-panel budget-setting"><legend>Investment budget</legend><div className="budget-setting-content"><div><p>Set the maximum amount of new money you are comfortable adding in one recommendation.</p><p className="budget-help">Rebalancing your existing holdings does not count towards this limit.</p></div><label className="budget-label" htmlFor="max-investment">Maximum investment amount ({currency})<div className="budget-input"><span>{currency}</span><input id="max-investment" aria-label="Maximum investment amount" type="number" min="0.01" step="0.01" required value={maximum} onChange={e => { setMaximum(e.target.value); setError(""); }} /></div></label></div></fieldset>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="settings-actions"><button type="submit" className="button primary">Save settings <CheckCircle size={18} /></button></div>
    </form>
  </div>;
}
