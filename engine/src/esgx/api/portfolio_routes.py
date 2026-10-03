"""Portfolio recommendation route: holdings + 1-5 risk/green scores -> trade list.

Unlike the read-only dataset routes, this one computes on request: it builds the factor
model (betas, moments) from the cached price/factor tables, GMB from the greenness table
when coverage allows (>= 30 scored names and >= 24 factor months), and solves the
turnover-penalized green mean-variance problem. A few seconds per call at HSI scale.

`market="all"` pools Hong Kong and Taiwan into one optimization (`portfolio.inputs`):
returns restated in HKD, one block factor model, greenness standardized within market.
Holdings must then be stated in one currency.
"""

from __future__ import annotations

from typing import Annotated, Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from esgx.api.store import DataStore, records
from esgx.ingest.fx import BASE_CURRENCY, pair_for
from esgx.portfolio.inputs import ModelInputs, combine_inputs, market_inputs, to_base_currency
from esgx.portfolio.recommend import recommend
from esgx.portfolio.screen import screen_universe
from esgx.schema import to_month

router = APIRouter(prefix="/api")

MARKET_REGION = {"hk": "asia_pacific_ex_japan", "tw": "emerging", "us": "us"}
ALL_MARKETS = ("hk", "tw")  # pooled by market="all"


def _store() -> DataStore:
    return DataStore()


Store = Annotated[DataStore, Depends(_store)]


class RecommendRequest(BaseModel):
    holdings: dict[str, float]
    risk_score: int = Field(3, ge=1, le=5)
    green_score: int = Field(3, ge=1, le=5)
    max_new_capital: float = Field(0.0, ge=0.0)
    vol_target: float | None = Field(None, gt=0.0, le=1.0)
    g_target: float | None = Field(None, gt=0.0, lt=1.0)
    preferences: str | None = None
    kappa: float = Field(0.02, ge=0.0)
    w_max: float = Field(0.15, gt=0.0, le=1.0)
    market: Literal["hk", "tw", "us", "all"] = "hk"


def _inputs(store: DataStore, market: str, convert: bool) -> tuple[ModelInputs, pd.Series]:
    """Model inputs and latest market cap for one market; `convert` restates it in HKD."""
    prices, factors = store.prices(market), store.factors(MARKET_REGION.get(market, market))
    if prices.empty or factors.empty:
        raise HTTPException(503, f"monthly prices/factors for market {market!r} not available yet")
    green = store.greenness(market)
    if green.empty or "g" not in green:
        raise HTTPException(503, f"greenness table not available yet for market {market!r}")
    if convert and (pair := pair_for(market)):
        fx = store.fx(pair)
        if fx.empty:
            raise HTTPException(503, f"FX rates {pair} not available yet (scripts/ingest_fx.py): market='all' "
                                     f"needs them to restate {market!r} returns in {BASE_CURRENCY}")
        prices = to_base_currency(prices, fx)
    inp = market_inputs(prices, factors, green)
    if inp.betas.empty:
        raise HTTPException(503, f"not enough return history to estimate factor betas for market {market!r}")
    mktcap = prices.assign(month=to_month(prices["month"])).sort_values("month").groupby("firm_id")["mktcap"].last()
    return inp, mktcap


@router.post("/portfolio/recommend")
def recommend_portfolio(req: RecommendRequest, store: Store) -> dict:
    pooled = req.market == "all"
    parts, caps = {}, []
    for m in ALL_MARKETS if pooled else (req.market,):
        parts[m], cap = _inputs(store, m, convert=pooled)
        caps.append(cap)
    inp = combine_inputs(parts) if pooled else parts[req.market]
    betas, g, mktcap = inp.betas, inp.g, pd.concat(caps)
    f_mean, f_cov = inp.moments()
    market_of = {f: m for m, part in reversed(parts.items()) for f in part.betas.index}
    screen, universe = None, None
    if req.preferences and req.preferences.strip():
        firms = store.firms()
        universe, screen = screen_universe(req.preferences, firms, mktcap)
        if not universe:
            raise HTTPException(400, "the preference filter leaves no candidate assets; "
                                     f"interpretation: {screen['spec']}")
    try:
        out = recommend(req.holdings, betas, g, f_mean, f_cov, betas["idio_var"],
                        risk_score=req.risk_score, green_score=req.green_score,
                        kappa=req.kappa, max_new_capital=req.max_new_capital,
                        vol_target=req.vol_target, g_target=req.g_target,
                        w_max=req.w_max, universe=universe)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {
        "params": out["params"],
        "total_capital": out["total_capital"],
        "new_capital": out["new_capital"],
        "target_capital": out["target_capital"],
        "turnover": out["turnover"],
        "before": out["before"],
        "after": out["after"],
        "trades": records(out["trades"].assign(market=out["trades"]["firm_id"].map(market_of))),
        "unmodeled": out["unmodeled"],
        "screen": screen,
        "coverage": {"n_modeled": len(betas), "n_scored": int(g.notna().sum()), "gmb_months": inp.gmb_months},
        "market": req.market,
        "base_currency": BASE_CURRENCY if pooled else None,
        "markets": {m: {"n_modeled": len(p.betas), "n_scored": int(p.g.notna().sum()), "gmb_months": p.gmb_months}
                    for m, p in parts.items()},
    }
