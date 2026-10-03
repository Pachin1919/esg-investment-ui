"""Within-group standardisation of firm-level measures.

Talk and walk live on different scales and have different industry levels (utilities both talk
and emit a lot), so every comparison across pillars is made on standardised values within
industry and year (Giannetti et al. 2023 normalise text measures per year; Pástor, Stambaugh &
Taylor 2022 demean greenness within industry). Two methods:

* ``z``   : (x - mean) / std within the group; groups with std == 0 get 0.
* ``pct`` : percentile rank in [0, 1] within the group (robust to outliers).
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

Method = str  # "z" | "pct"


def standardize_within(
    df: pd.DataFrame,
    cols: Sequence[str],
    by: Sequence[str] = ("year", "sector"),
    method: Method = "z",
    suffix: str | None = None,
) -> pd.DataFrame:
    """Add ``<col>_<suffix>`` columns standardised within ``by`` groups (suffix defaults to method).
    Rows whose group has fewer than two valid observations get NaN."""
    if method not in ("z", "pct"):
        raise ValueError(f"method must be 'z' or 'pct', got {method!r}")
    out = df.copy()
    sfx = suffix or method
    g = out.groupby(list(by), dropna=False)
    for c in cols:
        n = g[c].transform("count")
        if method == "z":
            mu, sd = g[c].transform("mean"), g[c].transform("std")
            val = ((out[c] - mu) / sd).where(sd > 0, 0.0)
        else:
            val = g[c].rank(pct=True, method="average")
        out[f"{c}_{sfx}"] = val.where(n >= 2)
    return out


def attach_sector(firm_year: pd.DataFrame, firms: pd.DataFrame, industry_col: str = "sector") -> pd.DataFrame:
    """Merge the industry column from ``firms`` onto a firm × year table (left join on firm_id)."""
    if industry_col in firm_year.columns:
        return firm_year
    return firm_year.merge(firms[["firm_id", industry_col]].drop_duplicates("firm_id"), on="firm_id", how="left")
