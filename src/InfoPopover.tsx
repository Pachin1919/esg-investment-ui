import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { Info } from "@phosphor-icons/react";
import { displayTicker, greenExplanation, score } from "./portfolio";
import type { Holding } from "./portfolio";

export const metricExplanations: Record<string,string> = {
  "Portfolio value":"The sum of the current market values of all holdings, expressed in the reporting currency. Share value is unit price multiplied by the number of shares.",
  "Expected return · annual":"Expected return is expressed as an annual percentage. Portfolio return combines the available company returns using current-value weights. Evaluate it alongside environmental performance and portfolio risk.",
  "Portfolio green score":"E-score describes a company's environmental performance. A higher score indicates stronger environmental performance. The portfolio score combines company E-scores using current-value weights.",
  "Portfolio volatility":"Volatility describes how much portfolio returns can fluctuate. A higher value indicates larger fluctuations. A value is shown only when the required portfolio risk data is available.",
  "E-score coverage":"The percentage of current portfolio value represented by holdings with an available environmental score. Missing company scores stay unavailable.",
};

export function InfoPopover({ label, children, content }: { label:string; children:ReactNode; content:ReactNode }) {
  const id=useId();
  const trigger=useRef<HTMLButtonElement>(null);
  const closeTimer=useRef<number|null>(null);
  const [position,setPosition]=useState<{left:number;top:number;width:number}|null>(null);
  const cancelClose=()=>{
    if(closeTimer.current!==null){window.clearTimeout(closeTimer.current);closeTimer.current=null;}
  };
  const closeSoon=()=>{
    cancelClose();
    closeTimer.current=window.setTimeout(()=>{setPosition(null);closeTimer.current=null;},140);
  };
  const open=()=>{
    cancelClose();
    const rect=trigger.current!.getBoundingClientRect();
    const width=Math.min(330,window.innerWidth-32);
    setPosition({left:Math.max(16,Math.min(rect.left,window.innerWidth-width-16)),top:Math.max(16,Math.min(rect.bottom+10,window.innerHeight-250)),width});
  };
  useEffect(()=>()=>cancelClose(),[]);
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
    onMouseEnter={open} onMouseLeave={closeSoon} onMouseDown={e=>e.preventDefault()}
    onFocus={open} onBlur={closeSoon} onKeyDown={e=>{if(e.key==="Escape")setPosition(null);}}>
    {children}<Info size={14}/></button>
    {position&&createPortal(<div id={id} role="tooltip" className="info-popover" style={position} onMouseEnter={cancelClose} onMouseLeave={closeSoon}>{content}</div>,document.body)}</>;
}
export function CompanyInfo({ company }: { company:Holding }) {
  return <InfoPopover label={company.name} content={<><strong>{company.name}</strong><span className="popover-symbol">{displayTicker(company.ticker)} · {company.exchange}</span><div className="popover-score"><span>Environmental score</span><b>{score(company.eScore)}</b></div><p>{greenExplanation(company)}</p></>}>{company.name}</InfoPopover>;
}
