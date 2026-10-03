"""Portfolio recommendation route: holdings + 1-5 risk/green scores -> trade list.

Unlike the read-only dataset routes, this one computes on request: it builds the factor
model (betas, moments) from the cached price/factor tables, GMB from the greenness table
when coverage allows (>= 30 scored names and >= 24 factor months), and solves the
turnover-penalized green mean-variance problem. A few seconds per call at HSI scale.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from esgx.api.store import DataStore, records
from esgx.factors.gmb import gmb_regression
from esgx.factors.timeseries import FF5_MOM
from esgx.measures.carbon import align_annual_to_months
from esgx.portfolio.exposures import exposure_snapshot
from esgx.portfolio.optimize import factor_moments
from esgx.portfolio.recommend import recommend
from esgx.schema import to_month

router = APIRouter(prefix="/api")

MARKET_REGION = {"hk": "asia_pacific_ex_japan", "us": "us"}


def _store() -> DataStore:
    return DataStore()


Store = Annotated[DataStore, Depends(_store)]


class RecommendRequest(BaseModel):
    holdings: dict[str, float]
    risk_score: int = Field(3, ge=1, le=5)
    green_score: int = Field(3, ge=1, le=5)
    kappa: float = Field(0.02, ge=0.0)
    w_max: float = Field(0.15, gt=0.0, le=1.0)
    market: str = "hk"


@router.post("/portfolio/recommend")
def recommend_portfolio(req: RecommendRequest, store: Store) -> dict:
    prices, factors = store.prices(req.market), store.factors(MARKET_REGION.get(req.market, req.market))
    if prices.empty or factors.empty:
        raise HTTPException(503, f"monthly prices/factors for market {req.market!r} not available yet")
    prices, factors = prices.copy(), factors.copy()
    prices["month"], factors["month"] = to_month(prices["month"]), to_month(factors["month"])
    factors = factors.sort_values("month")
    green = store.greenness()
    if green.empty or "g" not in green:
        raise HTTPException(503, "greenness table not available yet")
    green = green.drop_duplicates(["firm_id", "year"])
    g = green.sort_values("year").groupby("firm_id").tail(1).set_index("firm_id")["g"]

    g_m = align_annual_to_months(green[["firm_id", "year", "g"]], prices["month"].unique())
    panel = prices.merge(g_m[["firm_id", "month", "g"]], on=["firm_id", "month"], how="left")
    gmb_df = gmb_regression(panel, factors, min_n=30)
    use_gmb = not gmb_df.empty and gmb_df["gmb_reg"].notna().sum() >= 24
    betas = exposure_snapshot(prices, factors, gmb_df if use_gmb else None, gmb_col="gmb_reg")
    if betas.empty:
        raise HTTPException(503, "not enough return history to estimate factor betas")
    fsrc = factors
    if use_gmb:
        fsrc = factors.merge(gmb_df[["month", "gmb_reg"]].rename(columns={"gmb_reg": "gmb"}),
                             on="month", how="left")
    f_mean, f_cov = factor_moments(fsrc, list(FF5_MOM) + (["gmb"] if use_gmb else []))
    try:
        out = recommend(req.holdings, betas, g, f_mean, f_cov, betas["idio_var"],
                        risk_score=req.risk_score, green_score=req.green_score,
                        kappa=req.kappa, w_max=req.w_max)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {
        "params": out["params"],
        "total_capital": out["total_capital"],
        "turnover": out["turnover"],
        "before": out["before"],
        "after": out["after"],
        "trades": records(out["trades"]),
        "unmodeled": out["unmodeled"],
        "coverage": {"n_modeled": len(betas), "n_scored": int(g.notna().sum()),
                     "gmb_months": int(gmb_df["gmb_reg"].notna().sum()) if use_gmb else 0},
    }
