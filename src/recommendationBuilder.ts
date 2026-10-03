import { displayTicker, recommendStocks, sharePrice, totalValue } from "./portfolio";
import type { Candidate, Portfolio } from "./portfolio";

export const industries = [
  { id:"renewables",label:"Renewable energy",description:"Solar, wind & clean power",color:"#438666" },
  { id:"technology",label:"Technology",description:"Systems, circuits & energy storage",color:"#597fba" },
  { id:"utilities",label:"Utilities",description:"Water & essential services",color:"#429797" },
  { id:"infrastructure",label:"Infrastructure",description:"Efficient buildings & networks",color:"#8a79b2" },
  { id:"materials",label:"Materials & recycling",description:"Circular economy & industrial materials",color:"#b38c45" },
  { id:"mobility",label:"Transport & mobility",description:"Electric mobility & logistics",color:"#b47567" },
];
export type RecommendationPlan = { industries:string[]; tolerancePercent:number; selectedIds:string[] };
export function recommendationBudget(p:Portfolio,tolerancePercent:number,maximum:number) {
  return Math.floor(Math.min(totalValue(p)*(1+tolerancePercent/100),maximum)*100+.000001)/100;
}
// Keep the full default selection affordable: reserve at least one whole share per company.
export function industryRecommendations(p:Portfolio,risk:number,green:number,maximum:number,focus:string[],tolerancePercent:number) {
  const budget=recommendationBudget(p,tolerancePercent,maximum);
  let available=Math.round(budget*100);
  return recommendStocks(risk,green,budget,p.baseCurrency).filter(c=>{
    if(!focus.includes(c.industryId))return false;
    const price=Math.round(sharePrice(c,p.baseCurrency)!*100);
    if(price>available)return false;
    available-=price;return true;
  });
}
export function allocateRecommendedPortfolio(p:Portfolio,companies:Candidate[],budget:number):Portfolio|null {
  if(!companies.length||!Number.isFinite(budget)||budget<=0)return null;
  const prices=companies.map(c=>Math.round(sharePrice(c,p.baseCurrency)!*100));
  const minimum=prices.reduce((sum,price)=>sum+price,0),cents=Math.floor(budget*100+.000001);
  if(prices.some(price=>!Number.isSafeInteger(price)||price<=0)||minimum>cents)return null;
  const perCompany=(cents-minimum)/companies.length;
  const holdings=companies.map((c,i)=>{
    const units=1+Math.floor(perCompany/prices[i]);
    const original=p.holdings.find(h=>displayTicker(h.ticker)===displayTicker(c.ticker)&&h.exchange===c.exchange);
    return {...c,id:original?.id??c.id,currency:p.baseCurrency,unitPrice:prices[i]/100,units,value:units*prices[i]/100};
  });
  return {...p,name:"Recommended portfolio",holdings};
}
export function resolveRecommendation(p:Portfolio,risk:number,green:number,maximum:number,plan:RecommendationPlan|null) {
  if(!plan)return {companies:[],portfolio:null,budget:0};
  const companies=industryRecommendations(p,risk,green,maximum,plan.industries,plan.tolerancePercent);
  const budget=recommendationBudget(p,plan.tolerancePercent,maximum);
  return {companies,budget,portfolio:allocateRecommendedPortfolio(p,companies.filter(c=>plan.selectedIds.includes(c.id)),budget)};
}
