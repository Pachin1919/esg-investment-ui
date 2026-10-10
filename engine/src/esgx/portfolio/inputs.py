"""Risk-model inputs for `portfolio.recommend`, per market and pooled across markets.

One market: betas on its regional FF5+MOM factors (+ GMB when coverage allows), the latest
greenness per firm and the factor return frame the moments are taken from.

Several markets in one optimization (`combine_inputs`): each market keeps its own regional
factor set — local factor models describe regional returns better than a global one
(Fama & French 2012, "Size, value, and momentum in international stock returns", JFE) — and
the factor sets are stacked into one block model. A firm loads only on its own market's
factors (zero beta on the others), so the cross-market covariance comes entirely from the
joint factor covariance: Sigma = B F B' + D with F estimated over all stacked factors.
Returns are first restated in one base currency (`to_base_currency`), unhedged, so currency
risk is part of the volatility the investor targets (Solnik 1974). Greenness is standardized
within each market before pooling, so the green percentile target is not driven by level
differences between the markets' greenness tables or by the larger market's firm count.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import numpy as np

from esgx.factors.gmb import gmb_regression
from esgx.factors.timeseries import FF5_MOM
from esgx.measures.carbon import align_annual_to_months
from esgx.portfolio.exposures import exposure_snapshot
from esgx.portfolio.optimize import factor_moments
from esgx.schema import to_month

MIN_GMB_MONTHS = 24  # same threshold for using GMB in one market and for the pooled moments


@dataclass
class ModelInputs:
    betas: pd.DataFrame  # indexed by firm_id: b_<factor> columns + idio_var
    g: pd.Series  # latest greenness per firm (z-scored within market when pooled)
    factors: pd.DataFrame  # month + the factor return columns named in `cols`
    cols: list[str]
    gmb_months: int = 0

    def moments(self) -> tuple[pd.Series, pd.DataFrame]:
        return factor_moments(self.factors, self.cols)


def to_base_currency(prices: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    """Restate a market's monthly returns and market cap in the base currency.

    `fx`: month + rate (base currency per unit of the listing currency, month-end). The
    base-currency return compounds the local return with the currency return; months
    without an FX return are dropped rather than left in the listing currency."""
    fx = fx.assign(month=to_month(fx["month"])).sort_values("month")
    if fx["month"].duplicated().any():
        raise ValueError("FX must have exactly one rate per month")
    if not np.isfinite(fx["rate"]).all() or (fx["rate"] <= 0).any():
        raise ValueError("FX rates must be finite and strictly positive")
    fx["fx_ret"] = fx["rate"].pct_change(fill_method=None)
    # A missing calendar month cannot turn a multi-month change into a monthly return.
    consecutive = fx["month"].astype("int64").diff().eq(1)
    fx["fx_ret"] = fx["fx_ret"].where(consecutive)
    out = prices.assign(month=to_month(prices["month"])).merge(fx[["month", "rate", "fx_ret"]], on="month", how="left")
    out["ret"] = (1 + out["ret"]) * (1 + out["fx_ret"]) - 1
    out["mktcap"] = out["mktcap"] * out["rate"]
    if "close" in out:
        out["close"] = out["close"] * out["rate"]
    return out.dropna(subset=["ret"]).drop(columns=["rate", "fx_ret"]).reset_index(drop=True)


def market_inputs(prices: pd.DataFrame, factors: pd.DataFrame, green: pd.DataFrame) -> ModelInputs:
    """Betas, greenness and factor frame for one market. GMB enters the model when the
    greenness table supports it (>= 30 scored names and >= 24 factor months)."""
    prices, factors = prices.copy(), factors.copy()
    prices["month"], factors["month"] = to_month(prices["month"]), to_month(factors["month"])
    factors = factors.sort_values("month").dropna(subset=list(FF5_MOM) + ["rf"])
    if factors["month"].duplicated().any() or prices.duplicated(["firm_id", "month"]).any():
        raise ValueError("model inputs contain duplicate firm/month or factor/month rows")
    # Inputs are decimal simple returns. Reject invalid units; never infer percent units.
    if ((prices["ret"].dropna() < -1).any()
            or not np.isfinite(prices["ret"].dropna()).all()
            or not np.isfinite(factors[list(FF5_MOM) + ["rf"]]).all().all()
            or (factors[list(FF5_MOM) + ["rf"]].abs() > 1).any().any()):
        raise ValueError("model returns must be finite decimal returns (0.01 = 1%); check source units")
    common = sorted(set(prices["month"]) & set(factors["month"]))
    if not common:
        raise ValueError("no common price and factor months")
    prices = prices[prices["month"].isin(common)]
    factors = factors[factors["month"].isin(common)]
    green = green.drop_duplicates(["firm_id", "year"])
    annual_cols = ["firm_id", "year", "g"] + (["available_date"] if "available_date" in green else [])
    g_m = align_annual_to_months(green[annual_cols], pd.PeriodIndex(common, freq="M"))
    g = g_m[g_m["month"] == max(common)].set_index("firm_id")["g"]
    panel = prices.merge(g_m[["firm_id", "month", "g"]], on=["firm_id", "month"], how="left")
    gmb_df = gmb_regression(panel, factors, min_n=30)
    n_gmb = int(gmb_df["gmb_reg"].notna().sum()) if not gmb_df.empty else 0
    use_gmb = n_gmb >= MIN_GMB_MONTHS
    betas = exposure_snapshot(prices, factors, gmb_df if use_gmb else None, gmb_col="gmb_reg")
    if use_gmb:
        factors = factors.merge(gmb_df[["month", "gmb_reg"]].rename(columns={"gmb_reg": "gmb"}),
                                on="month", how="left")
    cols = list(FF5_MOM) + (["gmb"] if use_gmb else [])
    # Coverage and pooled z-scores describe the modeled universe, not every firm in
    # the annual source table (which may include firms with no usable price history).
    g = g.reindex(betas.index)
    return ModelInputs(betas, g, factors[["month"] + cols], cols, n_gmb if use_gmb else 0)


def _prefixed(inp: ModelInputs, market: str, cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    betas = inp.betas[[f"b_{c}" for c in cols] + ["idio_var"]].astype(float)
    betas = betas.rename(columns={f"b_{c}": f"b_{market}_{c}" for c in cols})
    fac = inp.factors[["month"] + cols].rename(columns={c: f"{market}_{c}" for c in cols})
    return betas, fac


def combine_inputs(parts: dict[str, ModelInputs]) -> ModelInputs:
    """Pool markets into one block factor model (see module docstring).

    Factor columns become `<market>_<factor>`, betas `b_<market>_<factor>` with zeros in the
    other markets' blocks. GMB factors are dropped from every market when the months on
    which all stacked factors are observed fall below MIN_GMB_MONTHS, so the joint
    covariance is never estimated on a handful of rows. A firm_id listed in several markets
    keeps its first market."""

    def stack(with_gmb: bool) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
        betas, fac, cols = [], None, []
        for market, inp in parts.items():
            keep = [c for c in inp.cols if with_gmb or c != "gmb"]
            b, f = _prefixed(inp, market, keep)
            betas.append(b)
            fac = f if fac is None else fac.merge(f, on="month", how="outer")
            cols += [f"{market}_{c}" for c in keep]
        b = pd.concat(betas)
        b = b[~b.index.duplicated(keep="first")]
        return b.fillna({f"b_{c}": 0.0 for c in cols}), fac.sort_values("month"), cols

    betas, fac, cols = stack(with_gmb=True)
    any_gmb = any("gmb" in inp.cols for inp in parts.values())
    joint = len(fac[cols].dropna())
    if any_gmb and joint < MIN_GMB_MONTHS:
        betas, fac, cols = stack(with_gmb=False)
        joint = 0
    zs = []
    for inp in parts.values():
        gm = inp.g.dropna().astype(float)
        sd = gm.std(ddof=0)
        zs.append((gm - gm.mean()) / sd if sd > 0 else gm * 0.0)
    g = pd.concat(zs)
    return ModelInputs(betas, g[~g.index.duplicated(keep="first")], fac, cols, joint if any_gmb else 0)
