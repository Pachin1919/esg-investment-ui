// Replace this local provider with the market-data API when it is available.
export type MarketCompany = {
  id: string; ticker: string; name: string; exchange: string; currency: string;
  price: number; riskLevel: number; eScore: number; expectedReturn: number; color: string;
  keywords: string; greenExplanation: string;
};
export const marketCompanies: MarketCompany[] = [
  { id:"demo-verdant-solar",ticker:"VS",name:"Verdant Solar",exchange:"XHKG",currency:"HKD",price:120,riskLevel:3,eScore:8.8,expectedReturn:.075,color:"#5487bb",keywords:"solar renewable energy utilities",greenExplanation:"An 8.8 E-score reflects a strong renewable-energy focus, efficient resource use and a clear transition plan." },
  { id:"demo-seabreeze",ticker:"SS",name:"Seabreeze Systems",exchange:"XTAI",currency:"TWD",price:400,riskLevel:2,eScore:8.5,expectedReturn:.07,color:"#65a593",keywords:"technology systems efficiency software",greenExplanation:"An 8.5 E-score reflects energy-efficient systems and lower operational emissions, with room to improve supply-chain reporting." },
  { id:"clearwater",ticker:"CW",name:"Clearwater Utilities",exchange:"XHKG",currency:"HKD",price:40,riskLevel:1,eScore:8.7,expectedReturn:.045,color:"#4a9a99",keywords:"water infrastructure utilities conservation",greenExplanation:"An 8.7 E-score reflects water conservation, strong resource efficiency and consistent environmental reporting." },
  { id:"evergreen",ticker:"EG",name:"Evergreen Infrastructure",exchange:"XHKG",currency:"HKD",price:80,riskLevel:1,eScore:8.1,expectedReturn:.05,color:"#5a846c",keywords:"infrastructure clean energy transport",greenExplanation:"An 8.1 E-score reflects investment in efficient infrastructure and a documented plan to reduce emissions." },
  { id:"circular",ticker:"CM",name:"Circular Materials",exchange:"XHKG",currency:"HKD",price:55,riskLevel:2,eScore:7.8,expectedReturn:.065,color:"#a68d52",keywords:"recycling circular economy materials",greenExplanation:"A 7.8 E-score reflects recycled inputs and waste reduction; energy use remains an area for improvement." },
  { id:"efficient",ticker:"EF",name:"Efficient Freight",exchange:"XHKG",currency:"HKD",price:65,riskLevel:3,eScore:7.1,expectedReturn:.082,color:"#9482b8",keywords:"transport freight logistics electric",greenExplanation:"A 7.1 E-score reflects fleet-efficiency gains, while fossil-fuel dependence continues to affect environmental performance." },
  { id:"nova",ticker:"NB",name:"Nova Battery",exchange:"XHKG",currency:"HKD",price:180,riskLevel:4,eScore:9.1,expectedReturn:.105,color:"#7f9cc7",keywords:"battery storage renewable energy technology",greenExplanation:"A 9.1 E-score reflects clean-energy storage and responsible sourcing; battery recycling is an ongoing priority." },
  { id:"horizon",ticker:"HW",name:"Horizon Wind",exchange:"XHKG",currency:"HKD",price:210,riskLevel:5,eScore:9.4,expectedReturn:.12,color:"#4f8e72",keywords:"wind renewable energy utilities",greenExplanation:"A 9.4 E-score reflects renewable generation and low operating emissions, alongside attention to land and biodiversity impacts." },
  { id:"aurora",ticker:"AR",name:"Aurora Renewables",exchange:"XHKG",currency:"HKD",price:100,riskLevel:2,eScore:8.2,expectedReturn:.08,color:"#5487bb",keywords:"renewable energy solar",greenExplanation:"An 8.2 E-score reflects a renewable-energy portfolio, lower operating emissions and measurable efficiency improvements." },
  { id:"formosa",ticker:"FC",name:"Formosa Circuits",exchange:"XTAI",currency:"TWD",price:320,riskLevel:3,eScore:5.7,expectedReturn:.06,color:"#65a593",keywords:"circuits semiconductor technology",greenExplanation:"A 5.7 E-score reflects some efficiency improvements; manufacturing energy use and water intensity limit the overall score." },
  { id:"harbour",ticker:"HM",name:"Harbour Mobility",exchange:"XHKG",currency:"HKD",price:100,riskLevel:3,eScore:7.4,expectedReturn:.07,color:"#8d9dca",keywords:"mobility electric transport",greenExplanation:"A 7.4 E-score reflects cleaner mobility and improved fleet efficiency, with further progress needed on lifecycle emissions." },
  { id:"riverstone",ticker:"RM",name:"Riverstone Materials",exchange:"XSHG",currency:"CNY",price:100,riskLevel:4,eScore:5.4,expectedReturn:.07,color:"#bb8f45",keywords:"materials industrial construction",greenExplanation:"A 5.4 E-score reflects a resource-intensive production process. Emissions reduction and cleaner energy remain key priorities." },
];
const usdPerCurrency: Record<string, number> = { USD:1,HKD:1/7.8,TWD:1/31.2,CNY:1/7.1,SEK:1/10.5,EUR:1.1,GBP:1.3,JPY:1/150,SGD:1/1.35 };
export function exchangeRate(from: string, to: string) {
  if (from === to) return 1;
  if (!usdPerCurrency[from] || !usdPerCurrency[to]) throw new Error(`Automatic conversion is unavailable for ${from} / ${to}. Choose a supported reporting currency.`);
  return usdPerCurrency[from] / usdPerCurrency[to];
}
export function companyQuote(ticker: string, name?: string) {
  const symbol = ticker.replace(/^DEMO-/i,"").toUpperCase();
  return marketCompanies.find(c => c.ticker === symbol || (name && c.name.toLowerCase() === name.toLowerCase()));
}
