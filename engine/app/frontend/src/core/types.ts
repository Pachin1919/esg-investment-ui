// Response types of the FastAPI service in src/esgx/api.

export interface DatasetInfo {
  available: boolean;
  rows: number | null;
  updated: string | null;
  path: string;
}
export interface Health {
  status: string;
  datasets: Record<string, DatasetInfo>;
}
export interface Firm {
  firm_id: string;
  name: string;
  sector: string | null;
  industry: string | null;
  country: string | null;
  has_talkwalk: boolean;
  has_emissions: boolean;
  has_greenness: boolean;
}
export interface TalkWalkYear {
  firm_id: string;
  year: number;
  talk: number;
  walk: number;
  gap: number;
  n_docs: number;
  [subscore: string]: number | string | null;
}
export interface TalkWalkDocument {
  firm_id: string;
  form: string;
  filing_date: string;
  period: string | null;
  accession: string;
  section: string;
  skipped: boolean;
  climate_relevance: number | null;
  talk: number | null;
  walk: number | null;
  gap: number | null;
  n_commitments: number | null;
  n_quantified: number | null;
  summary: string | null;
  env_keyword_share: number | null;
  env_sentiment: number | null;
  forward_looking_share: number | null;
  realised_share: number | null;
  climate_similarity: number | null;
  glossiness?: number | null;
  climate_share?: number | null;
  gated_sentiment?: number | null;
  [k: string]: number | string | boolean | null | undefined;
}
export interface EmissionRow {
  firm_id: string;
  year: number;
  scope1: number | null;
  scope2: number | null;
  scope3: number | null;
  source: string;
  matched: boolean;
  revenue?: number | null;
  intensity?: number | null;
}
export interface GreennessRow {
  firm_id: string;
  name?: string | null;
  sector?: string | null;
  year?: number;
  provider?: string;
  e_score: number;
  e_weight: number;
  g: number;
  g_across: number;
  g_within: number;
}
export interface GreennessResponse {
  years: number[];
  providers: string[];
  year: number | null;
  provider: string | null;
  firms: GreennessRow[];
  sectors: { sector: string; g: number; g_across: number; n: number }[];
}
export interface GmbMonth {
  month: string;
  gmb: number | null;
  gmb_ew: number | null;
  gmb_within: number | null;
  gmb_reg: number | null;
  n: number;
  cum_gmb?: number;
  cum_gmb_ew?: number;
  cum_gmb_within?: number;
}
export interface GmbResponse {
  months: GmbMonth[];
  summary: Record<string, { mean_bps: number; t_stat: number | null; n_months: number }>;
}
export interface FirmProfile extends Firm {
  emissions: EmissionRow[];
  greenness: GreennessRow[];
  talkwalk: TalkWalkYear[];
  documents: TalkWalkDocument[];
}
