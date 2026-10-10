"""Portfolio recommendation route: holdings + 1-5 risk/green scores -> trade list.

Unlike the read-only dataset routes, this one computes on request: it builds the factor
model (betas, moments) from the cached price/factor tables, GMB from the greenness table
when coverage allows (>= 30 scored names and >= 24 factor months), and solves the
turnover-penalized green mean-variance problem. A few seconds per call at HSI scale.

`market="all"` pools Hong Kong and Taiwan into one optimization (`portfolio.inputs`):
returns restated in USD to match the regional French factors and US risk-free rate,
one block factor model, greenness standardized within market. Holdings and share prices
are stated in HKD for both single-market and pooled requests. The model's expected
returns are USD excess returns, and its volatility target is USD based. By default the pool is balanced
(`portfolio.pool`): Taiwan adds as many names as Hong Kong has, the largest of every sector
first, plus any Taiwan holdings; `pool="full"` uses every priced Taiwan name.
"""

from __future__ import annotations

from typing import Annotated, Literal

import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from esgx.api.store import DataStore, records
from esgx.ingest.fx import BASE_CURRENCY
from esgx.factors.timeseries import FF5_MOM
from esgx.portfolio.inputs import MIN_GMB_MONTHS, ModelInputs, combine_inputs, market_inputs, to_base_currency
from esgx.portfolio.pool import eligible, largest_per_sector
from esgx.portfolio.positions import add_positions
from esgx.portfolio.recommend import recommend
from esgx.portfolio.screen import PreferenceFilter, filter_options, screen_filter, screen_universe
from esgx.schema import to_month

router = APIRouter(prefix="/api")

MARKET_REGION = {"hk": "asia_pacific_ex_japan", "tw": "emerging", "us": "us"}
ALL_MARKETS = ("hk", "tw")  # pooled by market="all"
LISTING_CURRENCY = {"hk": "HKD", "tw": "TWD", "us": "USD"}


def _store() -> DataStore:
    return DataStore()


Store = Annotated[DataStore, Depends(_store)]


class RecommendRequest(BaseModel):
    holdings: dict[str, float]
    capital_currency: Literal["HKD"] = "HKD"
    risk_score: int = Field(3, ge=1, le=5)
    green_score: int = Field(3, ge=1, le=5)
    max_new_capital: float = Field(0.0, ge=0.0)
    vol_target: float | None = Field(None, gt=0.0, le=1.0)
    g_target: float | None = Field(None, gt=0.0, lt=1.0)
    preferences: str | None = None
    filters: PreferenceFilter | None = None  # deterministic screen; wins over `preferences`, keeps holdings outside it
    kappa: float = Field(0.02, ge=0.0)
    w_max: float = Field(0.15, gt=0.0, le=1.0)
    market: Literal["hk", "tw", "us", "all"] = "hk"
    pool: Literal["balanced", "full"] = "balanced"  # market="all" only, see `portfolio.pool`


def _pool_prices(store: DataStore, market: str, balanced: bool, keep=()) -> pd.DataFrame:
    """Monthly prices of a market as it enters the pool: all of the home market (the first
    of ALL_MARKETS); for an added market in the balanced pool, as many names as the home
    market has eligible, the largest per sector, plus `keep`."""
    prices = store.prices(market)
    home = ALL_MARKETS[0]
    if not balanced or market == home or prices.empty:
        return prices
    sectors = store.firms().set_index("firm_id")["sector"]
    ids = largest_per_sector(prices, sectors, len(eligible(store.prices(home))), keep)
    return prices[prices["firm_id"].isin(ids)]


def _fx_rates(store: DataStore, pair: str) -> pd.DataFrame:
    fx = store.fx(pair)
    if fx.empty:
        raise HTTPException(503, f"dated FX rates {pair} not available; required for currency-consistent model/pricing")
    try:
        fx = fx.assign(month=to_month(fx["month"]), rate=pd.to_numeric(fx["rate"], errors="raise")).sort_values("month")
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(503, f"invalid dated FX rates {pair}: {e}") from e
    if fx["month"].duplicated().any() or not np.isfinite(fx["rate"]).all() or (fx["rate"] <= 0).any():
        raise HTTPException(503, f"FX rates {pair} must contain unique months and finite positive rates")
    return fx[["month", "rate"]]


def _usd_rates(store: DataStore, market: str) -> pd.DataFrame:
    """USD per listing-currency unit; exact dated cross rate, never a fixed peg."""
    usd_hkd = _fx_rates(store, "USDHKD")
    if market == "hk":
        return usd_hkd.assign(rate=1 / usd_hkd["rate"])
    if market == "tw":
        twd_hkd = _fx_rates(store, "TWDHKD")
        cross = twd_hkd.merge(usd_hkd, on="month", suffixes=("_twdhkd", "_usdhkd"))
        return cross.assign(rate=cross["rate_twdhkd"] / cross["rate_usdhkd"])[["month", "rate"]]
    return pd.DataFrame()  # US prices are already in the factors' USD currency


def _inputs(store: DataStore, market: str, prices: pd.DataFrame | None = None,
            at: pd.Period | None = None) -> tuple[ModelInputs, pd.Series]:
    """Model inputs and latest market cap in USD for one market.
    `prices` overrides the market's full price table (the balanced pool passes a subset)."""
    prices = store.prices(market) if prices is None else prices
    factors = store.factors(MARKET_REGION.get(market, market))
    if prices.empty or factors.empty:
        raise HTTPException(503, f"monthly prices/factors for market {market!r} not available yet")
    green = store.greenness(market)
    if green.empty or "g" not in green:
        raise HTTPException(503, f"greenness table not available yet for market {market!r}")
    cutoff = min(at or pd.Timestamp.today().to_period("M") - 1, pd.Timestamp.today().to_period("M") - 1)
    prices = prices.assign(month=to_month(prices["month"]))
    factors = factors.assign(month=to_month(factors["month"]))
    prices, factors = prices[prices["month"] <= cutoff], factors[factors["month"] <= cutoff]
    try:
        if market != "us":
            prices = to_base_currency(prices, _usd_rates(store, market))
        inp = market_inputs(prices, factors, green)
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(503, f"invalid model data for market {market!r}: {e}") from e
    if inp.betas.empty:
        raise HTTPException(503, f"not enough return history to estimate factor betas for market {market!r}")
    mktcap = prices.assign(month=to_month(prices["month"])).sort_values("month").groupby("firm_id")["mktcap"].last()
    return inp, mktcap


def _last_close(store: DataStore, markets) -> pd.Series:
    """Latest close in HKD. Foreign closes use completed FX months at or before their
    own price date; absent dates/rates leave share counts null rather than guessed."""
    out = []
    timing = {}
    for m in markets:
        close = store.last_close(m)
        path = store._paths().get(f"last_close_{m}")
        frame = store.table(path).copy() if path else pd.DataFrame()
        dates = pd.to_datetime(frame["date"], errors="coerce") if "date" in frame else pd.Series(dtype="datetime64[ns]")
        timing[m] = {"price_date": str(dates.max().date()) if dates.notna().any() else None,
                     "fx_month": None}
        if m != "hk" and not close.empty:
            fx = _fx_rates(store, "TWDHKD" if m == "tw" else "USDHKD")
            converted = {}
            used = []
            for row, date in zip(frame.to_dict("records"), dates):
                if pd.isna(date):
                    continue
                month = date.to_period("M")
                # A monthly FX quote is known only once its entire month has completed.
                latest_known = month if date.date() >= month.end_time.date() else month - 1
                latest_known = min(latest_known, pd.Timestamp.today().to_period("M") - 1)
                rates = fx[fx["month"] == latest_known]
                if not rates.empty:
                    converted[row["firm_id"]] = row["close"] * rates["rate"].iloc[-1]
                    used.append(rates["month"].iloc[-1])
            close = pd.Series(converted, dtype=float)
            timing[m]["fx_month"] = str(max(used)) if used else None
        out.append(close.where(np.isfinite(close)))
    result = pd.concat(out) if out else pd.Series(dtype=float)
    result.attrs["timing"] = timing
    return result


def _model_period(inp: ModelInputs) -> dict:
    complete = inp.factors.dropna(subset=inp.cols)
    return {"start": str(complete["month"].min()), "end": str(complete["month"].max()), "n_months": len(complete)}


def _model_cutoff(store: DataStore, markets) -> pd.Period:
    """Last complete month shared by prices, factors and consecutive FX rates in all markets."""
    common = None
    for market in markets:
        prices, factors = store.prices(market), store.factors(MARKET_REGION[market])
        if prices.empty or factors.empty:
            raise HTTPException(503, f"monthly prices/factors for market {market!r} not available yet")
        try:
            valid = set(to_month(prices.loc[prices["ret"].notna(), "month"]))
            valid &= set(to_month(factors.dropna(subset=list(FF5_MOM) + ["rf"])["month"]))
            if market != "us":
                fx = _usd_rates(store, market)
                consecutive = fx["month"].astype("int64").diff().eq(1)
                valid &= set(fx.loc[consecutive, "month"])
        except (ValueError, TypeError, KeyError) as e:
            raise HTTPException(503, f"invalid model data for market {market!r}: {e}") from e
        common = valid if common is None else common & valid
    last_complete = pd.Timestamp.today().to_period("M") - 1
    common = {m for m in common if m <= last_complete}
    if len(common) < MIN_GMB_MONTHS:
        raise HTTPException(503, "not enough common completed price/factor/FX months to estimate the model (need 24)")
    return max(common)


@router.get("/portfolio/filters")
def portfolio_filters(store: Store, market: str = "hk", pool: Literal["balanced", "full"] = "balanced") -> dict:
    """Sector -> industry values (with firm counts) of the firms the optimizer can trade in a
    market ("all" pools Hong Kong and Taiwan, by default the balanced pool): the choices for
    `RecommendRequest.filters`."""
    frames = [_pool_prices(store, m, market == "all" and pool == "balanced")
              for m in (ALL_MARKETS if market == "all" else (market,))]
    if any(f.empty for f in frames):
        raise HTTPException(503, f"monthly prices for market {market!r} not available yet")
    prices = pd.concat(frames)
    firms = store.firms()
    priced = firms[firms["firm_id"].isin(prices["firm_id"].unique())]
    return {"market": market, "n_firms": int(priced["firm_id"].nunique()), "sectors": filter_options(priced)}


@router.post("/portfolio/recommend")
def recommend_portfolio(req: RecommendRequest, store: Store) -> dict:
    pooled = req.market == "all"
    parts, caps = {}, []
    markets = ALL_MARKETS if pooled else (req.market,)
    cutoff = _model_cutoff(store, markets)
    for m in markets:
        prices = _pool_prices(store, m, pooled and req.pool == "balanced", keep=req.holdings)
        parts[m], cap = _inputs(store, m, prices=prices, at=cutoff)
        caps.append(cap)
    inp = combine_inputs(parts) if pooled else parts[req.market]
    if len(inp.factors.dropna(subset=inp.cols)) < MIN_GMB_MONTHS:
        raise HTTPException(503, "not enough common model months to estimate factor covariance (need 24)")
    betas, g, mktcap = inp.betas, inp.g, pd.concat(caps)
    f_mean, f_cov = inp.moments()
    market_of = {f: m for m, part in reversed(parts.items()) for f in part.betas.index}
    screen, universe = None, None
    has_text = bool(req.preferences and req.preferences.strip())
    if req.filters is not None or has_text:
        firms = store.firms()
        universe, screen = (screen_filter(req.filters, firms, mktcap) if req.filters is not None
                            else screen_universe(req.preferences, firms, mktcap))
        if not universe:
            raise HTTPException(400, "the preference filter leaves no candidate assets; "
                                     f"interpretation: {screen['spec']}")
    try:
        out = recommend(req.holdings, betas, g, f_mean, f_cov, betas["idio_var"],
                        risk_score=req.risk_score, green_score=req.green_score,
                        kappa=req.kappa, max_new_capital=req.max_new_capital,
                        vol_target=req.vol_target, g_target=req.g_target,
                        w_max=req.w_max, universe=universe,
                        keep_outside=req.filters is not None)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    close = _last_close(store, parts)
    return {
        "dataset_id": getattr(store, "dataset_id", "builtin"),
        "params": out["params"],
        "total_capital": out["total_capital"],
        "new_capital": out["new_capital"],
        "target_capital": out["target_capital"],
        "turnover": out["turnover"],
        "before": out["before"],
        "after": out["after"],
        "trades": records(add_positions(out["trades"], out["target_capital"], close)
                          .assign(market=lambda t: t["firm_id"].map(market_of), price_currency="HKD")),
        "unmodeled": out["unmodeled"],
        "screen": screen,
        "coverage": {"n_modeled": len(betas), "n_scored": int(g.notna().sum()), "gmb_months": inp.gmb_months},
        "market": req.market,
        "base_currency": BASE_CURRENCY,
        "capital_currency": "HKD",
        "pricing_currency": "HKD",
        "model_currency": "USD",
        "return_basis": "excess",
        "model_period": _model_period(inp),
        "pricing_timing": close.attrs["timing"],
        "annual_availability": "available_date + following month; otherwise fiscal December + 7 months (assumption)",
        "pool": req.pool if pooled else None,
        "markets": {m: {"n_modeled": len(p.betas), "n_scored": int(p.g.notna().sum()), "gmb_months": p.gmb_months,
                        "listing_market": m, "listing_currency": LISTING_CURRENCY[m],
                        "factor_region": MARKET_REGION[m], "factor_currency": "USD",
                        "factor_region_is_proxy": m != "us", "model_period": _model_period(p)}
                    for m, p in parts.items()},
    }
