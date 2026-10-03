// The company view model served by GET /api/companies.
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
