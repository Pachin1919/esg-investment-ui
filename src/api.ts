import type { Company } from "./data";

export type HealthStatus = {
  status: string;
  engine: string;
  version: string;
  capabilities: {
    liveData: boolean;
    portfolioScore: boolean;
    recalculation: boolean;
    returnForecast: boolean;
    csvUpload?: boolean;
  };
};

export type PortfolioAnalysis = {
  total_allocation: number;
  coverage_pct: number;
  portfolio_greenness: number | null;
  portfolio_e_score: number | null;
  weighted_pillars: {
    carbon: number | null;
    walk: number | null;
    talk: number | null;
  };
  greenwash_flagged_allocation?: number;
  sector_allocation: Record<string, number>;
};

export type UploadCsvResult = {
  success: boolean;
  companies?: Company[];
  total_allocation?: number;
  count?: number;
  unmatched_tickers?: string[];
  coverage_pct?: number;
  error?: string;
};

export async function fetchHealth(): Promise<HealthStatus | null> {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchCompanies(market: "hk" | "tw" | "all" = "all"): Promise<Company[] | null> {
  try {
    const res = await fetch(`/api/companies?market=${market}`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function analyzePortfolioApi(
  allocations: Record<string, number>
): Promise<PortfolioAnalysis | null> {
  try {
    const res = await fetch("/api/portfolio/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ allocations }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function uploadPortfolioCsv(csv_text: string): Promise<UploadCsvResult> {
  try {
    const res = await fetch("/api/portfolio/upload-csv", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ csv_text }),
    });
    if (!res.ok) {
      let msg = "Failed to parse CSV";
      try {
        const err = await res.json();
        if (err.detail) msg = err.detail;
      } catch {}
      return { success: false, error: msg };
    }
    const data = await res.json();
    return {
      success: true,
      companies: data.companies,
      total_allocation: data.total_allocation,
      count: data.count,
      unmatched_tickers: data.unmatched_tickers,
      coverage_pct: data.coverage_pct,
    };
  } catch (e: any) {
    return { success: false, error: e?.message || "Network error uploading CSV" };
  }
}

export async function fetchSampleCsv(): Promise<string> {
  try {
    const res = await fetch("/api/portfolio/sample-csv");
    if (res.ok) return await res.text();
  } catch {}
  return "ticker,allocation\n0002.HK,28\n0066.HK,20\n2330.TW,24\n0857.HK,16\n0992.HK,12\n";
}

export function downloadCsvFile(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export type PortfolioStats = {
  ann_ret: number | null;
  ann_vol: number | null;
  g_avg: number | null;
  exposures: Record<string, number>;
  n_positions: number;
  top_weight: number;
  effective_n: number;
};

export type Trade = {
  firm_id: string;
  w_current: number;
  w_target: number;
  dw: number;
  capital_delta: number;
  side: string;
  capital_current: number;
  capital_target: number;
  price: number | null;
  shares_current: number | null;
  shares_target: number | null;
  shares_delta: number | null;
};

export type Recommendation = {
  params: { vol_target_ann: number | null; g_target_pctl: number | null; n_candidates: number };
  total_capital: number;
  new_capital: number;
  turnover: number;
  before: PortfolioStats;
  after: PortfolioStats;
  trades: Trade[];
  unmodeled: { firm_id: string; capital: number; weight: number }[];
};

export async function recommendPortfolio(body: {
  holdings: Record<string, number>;
  risk_score: number;
  green_score: number;
  max_new_capital: number;
  market: "hk" | "tw";
  filters?: { include_industries: string[] };
}): Promise<Recommendation | { error: string }> {
  try {
    const res = await fetch("/api/portfolio/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      return { error: typeof err?.detail === "string" ? err.detail : "The engine could not produce a recommendation." };
    }
    return await res.json();
  } catch {
    return { error: "The engine is not reachable." };
  }
}

export type SectorOption = { sector: string; n: number; industries: { industry: string; n: number }[] };

export async function fetchFilterOptions(market: "hk" | "tw"): Promise<SectorOption[]> {
  try {
    const res = await fetch(`/api/portfolio/filters?market=${market}`);
    if (!res.ok) return [];
    return (await res.json()).sectors ?? [];
  } catch {
    return [];
  }
}
