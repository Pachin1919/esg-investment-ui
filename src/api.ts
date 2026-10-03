// Typed client for the ESG Exposure Engine FastAPI backend (repo: ESG-Investing-Strategy).
// Set VITE_API_BASE to the backend origin (see .env.example). When unset, this page's
// features show a configuration hint instead of failing.
export type Market = "hk" | "tw";

export type Firm = {
  firm_id: string;
  name: string;
  sector: string;
  industry: string;
  country: string;
  has_talkwalk: boolean;
  has_emissions: boolean;
  has_greenness: boolean;
};

export type GreennessRow = {
  firm_id: string;
  name: string;
  sector: string;
  e_score: number;
  e_weight: number;
  g: number;
  g_across: number;
  g_within: number;
};

export type GreennessResponse = {
  years: number[];
  providers: string[];
  year: number | null;
  provider: string | null;
  firms: GreennessRow[];
  sectors: { sector: string; g: number; g_across: number; n: number }[];
};

export type Health = {
  status: string;
  datasets: Record<string, { available: boolean; rows: number | null; updated: string | null }>;
};

export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || "";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  firms: () => get<Firm[]>("/api/firms"),
  greenness: (market: Market) => get<GreennessResponse>(`/api/greenness?market=${market}`),
  health: () => get<Health>("/api/health"),
};
