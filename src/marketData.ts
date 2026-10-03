// Indicative static rates, used only to restate an imported CSV in the reporting currency.
// The engine itself converts with its own month-end FX series when markets are pooled.
const usdPerCurrency: Record<string, number> = { USD:1,HKD:1/7.8,TWD:1/31.2,CNY:1/7.1,SEK:1/10.5,EUR:1.1,GBP:1.3,JPY:1/150,SGD:1/1.35 };
export function exchangeRate(from: string, to: string) {
  if (from === to) return 1;
  if (!usdPerCurrency[from] || !usdPerCurrency[to]) throw new Error(`Automatic conversion is unavailable for ${from} / ${to}. Choose a supported reporting currency.`);
  return usdPerCurrency[from] / usdPerCurrency[to];
}
