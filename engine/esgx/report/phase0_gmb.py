"""Phase 0, layer C: green-minus-brown factor, cumulative plot, alphas, HML/UMD check."""

from __future__ import annotations

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from esgx.config import OUTPUT_DIR
from esgx.factors.gmb import cumulative, gmb_regression, gmb_sorted
from esgx.factors.timeseries import FF5_MOM, alpha_regression
from esgx.report.md import md_table


def build_gmb(report: list[str], exposure: pd.DataFrame, factors: pd.DataFrame) -> pd.DataFrame:
    """GMB series (VW, EW, regression, within), summary, sub-periods, plot, alphas, HML/UMD; returns the monthly table."""
    # ---------- layer C: GMB ----------
    panel = exposure.dropna(subset=["g"])
    gmb_vw = gmb_sorted(panel, weight="vw")
    gmb_ew = gmb_sorted(panel, weight="ew")
    gmb_reg = gmb_regression(panel, factors)
    gmb_within = gmb_sorted(panel, g_col="g_within", weight="vw").rename(columns={"gmb": "gmb_within"})
    gmb = (
        gmb_vw[["month", "green", "brown", "gmb", "n"]]
        .merge(gmb_ew[["month", "gmb"]].rename(columns={"gmb": "gmb_ew"}), on="month")
        .merge(gmb_reg[["month", "gmb_reg"]], on="month", how="left")
        .merge(gmb_within[["month", "gmb_within"]], on="month", how="left")
    )
    gmb.assign(month=gmb["month"].astype(str)).to_csv(OUTPUT_DIR / "gmb_monthly.csv", index=False)
    
    summ = pd.DataFrame(
        {
            "mean_bps": gmb[["gmb", "gmb_ew", "gmb_reg", "gmb_within"]].mean() * 1e4,
            "t_stat": gmb[["gmb", "gmb_ew", "gmb_reg", "gmb_within"]].apply(lambda s: s.mean() / s.std() * np.sqrt(s.notna().sum())),
            "n_months": gmb[["gmb", "gmb_ew", "gmb_reg", "gmb_within"]].notna().sum(),
        }
    )
    report.append(f"## Green-minus-brown factor, {gmb['month'].min()} – {gmb['month'].max()}\n")
    report.append("PST 2022 reference: GMB averaged 65 bps/month (t=3.23) on MSCI data, 2012–2020; industry-adjusted GMB ~4x smaller and insignificant.\n")
    report.append(md_table(summ, "{:.2f}") + "\n")
    
    # sub-periods: PST sample (to 2020) vs the post-2021 energy rally (Lecture 4: realized != expected)
    sub = []
    for name, lo, hi in [("2012-06 to 2020-12 (PST window)", "2012-06", "2020-12"), ("2021-01 to end", "2021-01", "2099-12")]:
        w = gmb[(gmb["month"] >= pd.Period(lo, "M")) & (gmb["month"] <= pd.Period(hi, "M"))]
        for col in ["gmb", "gmb_ew", "gmb_within"]:
            s_ = w[col].dropna()
            sub.append({"period": name, "series": col, "mean_bps": s_.mean() * 1e4, "t_stat": s_.mean() / s_.std() * np.sqrt(len(s_)), "n": len(s_)})
    report.append("Sub-periods:\n\n" + md_table(pd.DataFrame(sub).set_index("period"), "{:.2f}") + "\n")
    
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = gmb["month"].dt.to_timestamp()
    ax.plot(x, cumulative(gmb["gmb"]), label="GMB (VW, carbon-proxy g)")
    ax.plot(x, cumulative(gmb["gmb_within"]), label="GMB within-industry", alpha=0.8)
    ax.plot(x, cumulative(gmb["gmb_ew"]), label="GMB (EW)", alpha=0.6)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("cumulative return")
    ax.set_title("Green-minus-brown, S&P 500, greenness from EPA GHGRP intensity")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "gmb_cumulative.png", dpi=130)
    
    rows = {}
    for name, ycol in [("GMB vw", "gmb"), ("GMB ew", "gmb_ew"), ("GMB regression", "gmb_reg"), ("GMB within", "gmb_within")]:
        rows[name] = alpha_regression(gmb[["month", ycol]], factors, ycol, FF5_MOM)
    alphas = pd.DataFrame(rows).T
    alphas["alpha_bps"] = alphas["alpha"] * 1e4
    report.append("### Alphas on FF5 + MOM (Newey–West t)\n\n" + md_table(alphas[["alpha_bps", "t_alpha", "r2", "n", "b_mkt_rf", "b_hml", "b_mom"]], "{:.2f}") + "\n")
    
    # HML / UMD explained by GMB? (PST Table 6 analogue)
    fm = factors.merge(gmb[["month", "gmb"]], on="month", how="inner").dropna(subset=["gmb"])
    
    def _ts_alpha(ycol: str, xcols: list[str]) -> pd.Series:
        import statsmodels.api as sm
    
        fit = sm.OLS(fm[ycol].astype(float), sm.add_constant(fm[xcols].astype(float))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
        return pd.Series({"alpha_bps": fit.params["const"] * 1e4, "t_alpha": fit.tvalues["const"], "r2": fit.rsquared})
    
    hu = pd.DataFrame(
        {
            "HML | mkt": _ts_alpha("hml", ["mkt_rf"]),
            "HML | mkt+GMB": _ts_alpha("hml", ["mkt_rf", "gmb"]),
            "UMD | mkt": _ts_alpha("mom", ["mkt_rf"]),
            "UMD | mkt+GMB": _ts_alpha("mom", ["mkt_rf", "gmb"]),
        }
    ).T
    report.append("### Do value and momentum alphas shrink once GMB is added? (PST: HML -71 bps, UMD +66 bps, both vanish)\n\n" + md_table(hu, "{:.2f}") + "\n")
    return gmb
