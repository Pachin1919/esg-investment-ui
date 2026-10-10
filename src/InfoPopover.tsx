import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { Info } from "@phosphor-icons/react";
import { displayTicker, greenExplanation, score } from "./portfolio";
import type { Holding } from "./portfolio";

export const metricExplanations: Record<string,string> = {
  "Portfolio value":"The sum of the current market values of all holdings, expressed in the reporting currency. Share value is unit price multiplied by the number of shares.",
  "Expected return · annual":"Model-implied annual excess return on a USD basis from the factor model (market, size, value, profitability, investment, momentum and, when estimated, green). Excess means above the model's risk-free rate. Monetary holdings and trade capital are reported in HKD; this is not an HKD total-return forecast or a guarantee.",
  "Portfolio green score":"E-score is a company's emission-intensity rank within its sector, from 0 to 10; higher is greener. The portfolio score is the value-weighted average over the holdings that have a score; E-score coverage shows how much of the portfolio that is.",
  "Portfolio volatility":"Annual volatility on a USD basis from the factor risk model. Your risk level sets the target; holdings without return history are not included. HKD reporting capital does not change the model's return or risk currency.",
  "E-score coverage":"The percentage of current portfolio value represented by holdings with an available environmental score. Missing company scores stay unavailable.",
  "Greenness · g":"Greenness combines the E-score with how much the environment matters for the company's industry. Zero is the greenest possible value; more negative is browner.",
  "Positions":"The number of holdings the risk model covers.",
  "Largest position":"The weight of the single largest holding.",
  "Effective positions":"How many equally weighted holdings would give the same concentration. Lower means more concentrated.",
};

export function InfoPopover({ label, children, content }: { label:string; children:ReactNode; content:ReactNode }) {
  const id=useId();
  const trigger=useRef<HTMLButtonElement>(null);
  const [position,setPosition]=useState<{left:number;top:number;width:number}|null>(null);
  const open=()=>{
    const rect=trigger.current!.getBoundingClientRect();
    const width=Math.min(330,window.innerWidth-32);
    setPosition({left:Math.max(16,Math.min(rect.left,window.innerWidth-width-16)),top:Math.max(16,Math.min(rect.bottom+10,window.innerHeight-250)),width});
  };
  useEffect(()=>{
    if(!position)return;
    const reposition=()=>{
      const rect=trigger.current?.getBoundingClientRect();
      if(!rect||rect.bottom<0||rect.top>window.innerHeight){setPosition(null);return;}
      open();
    };
    window.addEventListener("scroll",reposition,true);window.addEventListener("resize",reposition);
    return ()=>{window.removeEventListener("scroll",reposition,true);window.removeEventListener("resize",reposition);};
  },[position]);
  return <><button ref={trigger} type="button" className="info-trigger" aria-label={`About ${label}`} aria-describedby={position?id:undefined}
    onMouseEnter={open} onMouseLeave={()=>{if(document.activeElement!==trigger.current)setPosition(null);}}
    onFocus={open} onBlur={()=>setPosition(null)} onClick={open} onKeyDown={e=>{if(e.key==="Escape")setPosition(null);}}>
    {children}<Info size={14}/></button>
    {position&&createPortal(<div id={id} role="tooltip" className="info-popover" style={position}>{content}</div>,document.body)}</>;
}
export function CompanyInfo({ company }: { company:Holding }) {
  return <InfoPopover label={company.name} content={<><strong>{company.name}</strong><span className="popover-symbol">{displayTicker(company.ticker)} · {company.exchange}</span><div className="popover-score"><span>Environmental score</span><b>{score(company.eScore)}</b></div><p>{greenExplanation(company)}</p></>}>{company.name}</InfoPopover>;
}
