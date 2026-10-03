// A front-end view model, not a proposed backend contract. All companies and values are fictional.
export type Company = {
  id: string;
  name: string;
  ticker: string;
  sector: string;
  region: string;
  allocation: number;
  score: number | null;
  materiality: number;
  carbon: number | null;
  walk: number | null;
  talk: number | null;
  gap?: number | null;
  greenwasher?: boolean;
  greenhusher?: boolean;
  color: string;
  initials: string;
  note: string;
};
export const companies: Company[] = [
  {
    id: "aurora",
    name: "Aurora Renewables",
    ticker: "DEMO-AR",
    sector: "Utilities",
    region: "Hong Kong",
    allocation: 28,
    score: 8.2,
    materiality: 45,
    carbon: 8.6,
    walk: 7.8,
    talk: 8.1,
    color: "#629dcc",
    initials: "AR",
    note: "Realised reductions and investment disclosures are available in this fictional sample.",
  },
  {
    id: "formosa",
    name: "Formosa Circuits",
    ticker: "DEMO-FC",
    sector: "Technology",
    region: "Taiwan",
    allocation: 24,
    score: 6.7,
    materiality: 30,
    carbon: 6.3,
    walk: 7.1,
    talk: 8.2,
    color: "#93c9bf",
    initials: "FC",
    note: "Ambitions outpace the actions described in this fictional sample. Review the underlying evidence.",
  },
  {
    id: "harbour",
    name: "Harbour Mobility",
    ticker: "DEMO-HM",
    sector: "Industrials",
    region: "Hong Kong",
    allocation: 20,
    score: 7.4,
    materiality: 40,
    carbon: 7.2,
    walk: 7.6,
    talk: 7.8,
    color: "#a5b8dc",
    initials: "HM",
    note: "Operational improvements are described in the sample. Independent verification is not supplied.",
  },
  {
    id: "river",
    name: "Riverstone Materials",
    ticker: "DEMO-RM",
    sector: "Materials",
    region: "Mainland China",
    allocation: 16,
    score: 4.3,
    materiality: 50,
    carbon: 4.1,
    walk: 4.6,
    talk: 7.5,
    color: "#d7bd89",
    initials: "RM",
    note: "A larger gap between stated ambitions and documented actions is an invitation to investigate, not proof of misconduct.",
  },
  {
    id: "canopy",
    name: "Canopy Consumer",
    ticker: "DEMO-CC",
    sector: "Consumer goods",
    region: "Taiwan",
    allocation: 12,
    score: null,
    materiality: 20,
    carbon: null,
    walk: null,
    talk: null,
    color: "#cbd4db",
    initials: "CC",
    note: "No company analysis has been provided. Missing information is not a zero score.",
  },
];
export const baseline = companies.map((c) => c.allocation);
export const alternative = [34, 22, 24, 8, 12];
export const capabilities = {
  liveData: false,
  portfolioScore: false,
  returnForecast: false,
  recalculation: false,
};
export function coverage(weights: number[], list: Company[] = companies) {
  const total = weights.reduce((a, b) => a + b, 0);
  return total
    ? Math.round(
        (list.reduce(
          (sum, c, i) => sum + (c.score !== null ? (weights[i] ?? 0) : 0),
          0,
        ) /
          total) *
          100,
      )
    : 0;
}
