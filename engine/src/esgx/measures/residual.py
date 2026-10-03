"""Excess talk: the part of a firm's green talk that its hard data does not explain.

Greenwashing is talk *given* walk (Giannetti et al. 2023; Liang, Sun & Teo 2022; Chen 2025). The
double sort and the percentile gap in `greenwash.py` compare ranks; this module makes the direct
comparison. Pooled OLS on the raw quantities, with industry × year effects:

    log(1 + talk_it) = b1·log(1 + intensity_it) + b2·Δlog intensity_it + b3·log(words_it) + a_industry×year + e_it

* `talk` is claim words per 1,000 words (deterministic, `talk_dict`), `intensity` the emissions
  intensity behind walk, `Δlog intensity` its change from the previous year, `words` the document
  length (longer reports dilute word shares).
* `excess_talk` = e_it, in log points: 0.3 means about 35 % more green claims than firms with the
  same emissions level, trend, report length, industry and year.
* One slope for the whole sample rather than one per industry-year: groups hold 14-26 firms, too
  few for a slope each (`gap._resid_within` does the per-group version on the 0-10 scores).

The residual alone is "talks more than its numbers justify". Whether that is greenwashing is an
empirical question answered by the validation in `validation.predictive_regression`: excess talk
that is followed by falling emissions is credible signalling, excess talk that is not is cheap talk.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from esgx.measures.standardize import standardize_within

LEVEL_ONLY = ("log_intensity", "log_words")
LEVEL_AND_TREND = ("log_intensity", "d_log_intensity", "log_words")


def excess_talk(
    df: pd.DataFrame,
    regressors: tuple[str, ...] = LEVEL_AND_TREND,
    talk: str = "claim_per_1000",
    industry_col: str = "sector",
    top_q: float = 0.8,
    min_obs: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (firm-year table, fit table).

    `df` needs firm_id, year, `industry_col`, `talk`, intensity, n_words and, for the trend
    specification, d_log_intensity. Rows missing a regressor are dropped (reported in the fit).
    Firm-year columns added: talk_expected (per 1,000 words), excess_talk (log points),
    excess_talk_z (z within industry × year), excess_talker (top `top_q` of excess_talk in the year).
    Fit table: coef, t, p per regressor (firm-clustered), with n, r2 and r2_fe_only as columns.
    """
    d = df.copy()
    d["log_talk"] = np.log1p(d[talk])
    d["log_intensity"] = np.log1p(d["intensity"])
    d["log_words"] = np.log(d["n_words"].where(d["n_words"] > 0))
    d = d.dropna(subset=["log_talk", *regressors, industry_col, "year"]).reset_index(drop=True)
    if len(d) < min_obs:
        raise ValueError(f"only {len(d)} firm-years with talk and {list(regressors)}; need {min_obs}")
    fe = pd.get_dummies(d[industry_col].astype(str) + "|" + d["year"].astype(str), drop_first=True, dtype=float)
    groups = pd.factorize(d["firm_id"])[0]
    X = sm.add_constant(pd.concat([d[list(regressors)].astype(float), fe], axis=1))
    fit = sm.OLS(d["log_talk"], X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    fe_only = sm.OLS(d["log_talk"], sm.add_constant(fe)).fit()

    d["talk_expected"] = np.expm1(fit.fittedvalues)
    d["excess_talk"] = fit.resid
    d = standardize_within(d, ["excess_talk"], by=["year", industry_col], method="z")
    d["excess_talker"] = (d.groupby("year")["excess_talk"].rank(pct=True, method="average") >= top_q).astype(int)
    table = pd.DataFrame(
        [{"var": v, "coef": float(fit.params[v]), "t": float(fit.tvalues[v]), "p": float(fit.pvalues[v]),
          "n": int(fit.nobs), "firms": int(d["firm_id"].nunique()), "r2": float(fit.rsquared), "r2_fe_only": float(fe_only.rsquared)}
         for v in regressors]
    ).set_index("var")
    return d.drop(columns=["log_talk", "log_words"]), table
