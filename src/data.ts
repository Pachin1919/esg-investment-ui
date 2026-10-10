// The company view model served by GET /api/companies.
export type Company = {
  id: string;
  name: string;
  ticker: string;
  sector: string;
  region: string;
  listing_market?: string;
  listing_currency?: string;
  domicile?: string;
  model_proxy?: string;
  assessment_status?: string;
  allocation: number;
  score: number | null;
  materiality: number;
  carbon: number | null;
  walk: number | null;
  talk: number | null;
  gap?: number | null;
  greenwasher?: boolean | null;
  greenhusher?: boolean | null;
  color: string;
  initials: string;
  note: string;
};
