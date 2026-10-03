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
  sector_allocation: Record<string, number>;
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

export async function fetchCompanies(): Promise<Company[] | null> {
  try {
    const res = await fetch("/api/companies");
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
