import { displayTicker, greenExplanation, metrics, money, percent, score, totalValue, unitMoney } from "./portfolio";
import type { Portfolio } from "./portfolio";

export type ExportFormat = "pdf" | "json";
export type ExportKind = "current" | "recommended" | "comparison";
export type InvestmentPreferences = { riskLevel:number;greenPreference:number;maxInvestment:number };
function portfolioSnapshot(p:Portfolio) {
  const m=metrics(p),total=totalValue(p);
  return {reportingCurrency:p.baseCurrency,valuationDate:p.asOf,totalValue:total,expectedReturn:m.expectedReturn.value,greenScore:m.greenScore.value,
    holdings:p.holdings.map(h=>({ticker:displayTicker(h.ticker),company:h.name,exchange:h.exchange,assetClass:h.assetClass,currency:h.currency,
      unitPrice:h.unitPrice??null,units:h.units??null,totalPrice:h.value,currentValue:h.value,weight:total>0?h.value/total:0,
      expectedReturn:h.expectedReturn,eScore:h.eScore,greenExplanation:greenExplanation(h)}))};
}
export async function createPortfolioExport(kind:ExportKind,format:ExportFormat,baseline:Portfolio,recommended:Portfolio,preferences:InvestmentPreferences) {
  const oldPortfolio=portfolioSnapshot(baseline),newPortfolio=portfolioSnapshot(recommended);
  const currency=baseline.baseCurrency,before=metrics(baseline),after=metrics(recommended);
  const rows: (string|number|null)[][]=[
    ["Portfolio value",oldPortfolio.totalValue,newPortfolio.totalValue,newPortfolio.totalValue-oldPortfolio.totalValue],
    ["Expected return · annual",before.expectedReturn.value,after.expectedReturn.value,before.expectedReturn.value===null||after.expectedReturn.value===null?null:after.expectedReturn.value-before.expectedReturn.value],
    ["Portfolio green score",before.greenScore.value,after.greenScore.value,before.greenScore.value===null||after.greenScore.value===null?null:after.greenScore.value-before.greenScore.value],
    ["Portfolio volatility",null,null,null],
    ["E-score coverage",before.greenScore.coverage,after.greenScore.coverage,after.greenScore.coverage-before.greenScore.coverage],
  ];
  const holdingChanges=[...new Set([...baseline.holdings,...recommended.holdings].map(h=>h.id))].map(id=>{
    const old=baseline.holdings.find(h=>h.id===id),next=recommended.holdings.find(h=>h.id===id),h=next??old!;
    return {ticker:displayTicker(h.ticker),company:h.name,unitPrice:h.unitPrice??null,oldUnits:old?.units??(old?null:0),newUnits:next?.units??(next?null:0),
      oldValue:old?.value??0,newValue:next?.value??0,valueChange:(next?.value??0)-(old?.value??0),eScore:h.eScore,
      oldWeight:old?old.value/oldPortfolio.totalValue:0,newWeight:next?next.value/newPortfolio.totalValue:0};
  });
  const comparison={metrics:rows.map(([metric,oldValue,newValue,change])=>({metric,oldValue,newValue,change})),holdings:holdingChanges};
  const payload=kind==="current"?{preferences,currentPortfolio:newPortfolio}:kind==="recommended"?{preferences,recommendedPortfolio:newPortfolio}:{preferences,oldPortfolio,newPortfolio,comparison};
  const title=kind==="current"?"Current portfolio":kind==="recommended"?"Recommended portfolio":"Old vs. new portfolio comparison";
  const name=`green-street-${kind==="current"?"current-portfolio":kind==="recommended"?"recommended-portfolio":"portfolio-comparison"}.${format}`;
  if(format==="json")return {name,content:JSON.stringify(payload,null,2),mimeType:"application/json"};
  const [{jsPDF},{autoTable}]=await Promise.all([import("jspdf"),import("jspdf-autotable")]);
  const doc=new jsPDF({orientation:"landscape",unit:"mm",format:"a4"});
  const width=doc.internal.pageSize.getWidth(),height=doc.internal.pageSize.getHeight(),margin=16;
  let y=0;
  function header(title:string) {
    doc.setFillColor(20,60,49);doc.rect(0,0,width,34,"F");
    doc.setTextColor(255,255,255);doc.setFont("helvetica","bold");doc.setFontSize(23);doc.text("Green Street",margin,16);
    doc.setFont("helvetica","normal");doc.setFontSize(9);doc.setTextColor(183,216,198);doc.text("ENVIRONMENTAL INVESTMENT INSIGHTS",margin,25);
    doc.setTextColor(255,255,255);doc.setFontSize(11);doc.text(title,width-margin,16,{align:"right"});
    doc.setTextColor(197,220,207);doc.setFontSize(9);doc.text(`Valuation: ${baseline.asOf}  |  Reporting currency: ${currency}`,width-margin,25,{align:"right"});
    y=45;
  }
  function summary() {
    const cards=[[kind==="current"?"CURRENT PORTFOLIO VALUE":"NEW PORTFOLIO VALUE",money(newPortfolio.totalValue,currency)],["ANNUAL EXPECTED RETURN",percent(newPortfolio.expectedReturn)],["PORTFOLIO GREEN SCORE",score(newPortfolio.greenScore)]];
    const cardWidth=(width-margin*2-12)/3;
    cards.forEach(([label,value],i)=>{
      const x=margin+i*(cardWidth+6);
      doc.setFillColor(241,247,244);doc.setDrawColor(218,232,224);doc.roundedRect(x,y,cardWidth,26,3,3,"FD");
      doc.setTextColor(90,118,103);doc.setFontSize(8);doc.setFont("helvetica","normal");doc.text(label,x+6,y+8);
      doc.setTextColor(24,64,49);doc.setFont("helvetica","bold");doc.setFontSize(17);doc.text(value,x+6,y+19);
    });
    y+=36;
    doc.setFont("helvetica","normal");doc.setFontSize(9);doc.setTextColor(88,107,119);
    doc.text(`Risk level ${preferences.riskLevel}   |   Green preference ${preferences.greenPreference}   |   Maximum investment ${money(preferences.maxInvestment,currency)}`,margin,y);
    y+=11;
  }
  function table(title:string,head:string[],body:string[][]) {
    if(y>height-45){doc.addPage();header(title);}
    doc.setFont("helvetica","bold");doc.setFontSize(12);doc.setTextColor(28,60,48);doc.text(title,margin,y);
    autoTable(doc,{startY:y+5,head:[head],body,margin:{left:margin,right:margin,top:44,bottom:18},
      theme:"striped",styles:{font:"helvetica",fontSize:8.5,cellPadding:3.5,lineColor:[226,234,229],lineWidth:.15,textColor:[53,73,64],overflow:"linebreak"},
      headStyles:{fillColor:[42,91,71],textColor:[255,255,255],fontStyle:"bold"},
      alternateRowStyles:{fillColor:[245,249,246]},
      didDrawPage:data=>{if(data.pageNumber>1){const savedY=y;header(title);y=savedY;}},
    });
    y=(doc as unknown as {lastAutoTable:{finalY:number}}).lastAutoTable.finalY+14;
  }
  function holdingsTable(title:string,p:ReturnType<typeof portfolioSnapshot>) {
    table(title,["Company","Ticker","Unit price ("+currency+")","Units","Total value ("+currency+")","Weight","Annual return","E-score"],
      p.holdings.map(h=>[h.company,h.ticker,h.unitPrice===null?"Unavailable":unitMoney(h.unitPrice,currency),h.units===null?"Unavailable":String(h.units),
        money(h.totalPrice,currency),percent(h.weight,1),percent(h.expectedReturn),score(h.eScore)]));
  }
  header(title);summary();
  if(kind==="comparison") {
    const fmt=(label:string,value:string|number|null)=>value===null?"Unavailable":typeof value==="number"?(label==="Portfolio value"?money(value,currency):label.includes("return")||label.includes("coverage")?percent(value,3):score(value)):value;
    const delta=(label:string,value:string|number|null)=>{
      if(value===null)return "Unavailable";
      if(typeof value!=="number"||label==="Portfolio value")return fmt(label,value);
      const percentage=label.includes("return")||label.includes("coverage");
      const rounded=Number((value*(percentage?100:1)).toFixed(percentage?3:2));
      return `${rounded>=0?"+":""}${rounded.toFixed(percentage?3:2)} ${percentage?"pp":"points"}`;
    };
    table("Portfolio performance",["Metric","Old portfolio","New portfolio","Change"],rows.map(([label,oldValue,newValue,change])=>[String(label),fmt(String(label),oldValue),fmt(String(label),newValue),delta(String(label),change)]));
    table("Company-by-company comparison",["Company","Ticker","Unit price","Old units","New units","Old total","New total","E-score"],
      holdingChanges.map(h=>[h.company,h.ticker,h.unitPrice===null?"Unavailable":unitMoney(h.unitPrice,currency),h.oldUnits===null?"Unavailable":String(h.oldUnits),h.newUnits===null?"Unavailable":String(h.newUnits),money(h.oldValue,currency),money(h.newValue,currency),score(h.eScore)]));
    doc.addPage();header("Old portfolio holdings");holdingsTable("Old portfolio",oldPortfolio);
    doc.addPage();header("New portfolio holdings");holdingsTable("Recommended portfolio",newPortfolio);
  } else holdingsTable(kind==="current"?"Current holdings":"Recommended holdings",newPortfolio);
  table("Environmental score explanations",["Company","E-score","Explanation"],newPortfolio.holdings.map(h=>[h.company,score(h.eScore),h.greenExplanation]));
  const pages=doc.getNumberOfPages();
  for(let page=1;page<=pages;page++){
    doc.setPage(page);doc.setDrawColor(216,229,219);doc.line(margin,height-12,width-margin,height-12);
    doc.setFont("helvetica","normal");doc.setFontSize(8);doc.setTextColor(102,124,112);
    doc.text("Green Street | Portfolio analysis",margin,height-7);doc.text(`Page ${page} of ${pages}`,width-margin,height-7,{align:"right"});
  }
  doc.setProperties({title:`Green Street | ${title}`,author:"Green Street"});
  return {name,content:doc.output("arraybuffer"),mimeType:"application/pdf"};
}
