"""Long-only green tilt: the deployable product built on the greenness characteristic.

    w_i ∝ base_w_i * exp(lam * z_i),   z = cross-sectional z-score of g (higher = greener)

lam = 0 reproduces the base index; higher lam tilts greener. Underweighting brown vs
the index is economically a benchmark-relative short, so the tilt keeps the long-short
trade's economics without HK short-selling frictions (designated lists, borrow cost,
uptick rule). The GMB factor itself stays the long-short measurement instrument.

`g` is one value per firm (e.g. latest-year greenness from `measures.greenness`);
reduce firm x year tables before calling.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _zscore(g: pd.Series) -> pd.Series:
    z = (g - g.mean()) / g.std(ddof=0)
    return z.fillna(0.0)


def green_tilt(
    base_w: pd.Series,
    g: pd.Series,
    lam: float,
    w_max: float = 0.10,
    min_names: int = 30,
    keep_unscored: bool = True,
) -> pd.Series:
    """Tilted weights indexed by firm_id, summing to 1. Firms without g keep multiplier 1
    (z = 0) when `keep_unscored`, else are dropped. Weights are capped at w_max with the
    excess redistributed to uncapped names."""
    w = base_w.dropna().astype(float)
    w = w[w > 0]
    if len(w) < min_names:
        raise ValueError(f"base portfolio has {len(w)} names (< min_names={min_names})")
    if w_max * len(w) < 1.0:
        raise ValueError(f"w_max={w_max} infeasible with {len(w)} names (need w_max >= {1 / len(w):.3f})")
    w = w / w.sum()
    g = g.reindex(w.index)
    if g.notna().sum() < min_names:
        raise ValueError(f"only {int(g.notna().sum())} names have greenness (< min_names={min_names})")
    if not keep_unscored:
        w = w[g.notna()]
        w = w / w.sum()
        g = g.reindex(w.index)
    w = w * np.exp(lam * _zscore(g))
    w = w / w.sum()
    for _ in range(len(w)):  # cap and redistribute until no weight exceeds w_max
        over = w > w_max
        if not over.any():
            break
        excess = float((w[over] - w_max).sum())
        w.loc[over] = w_max
        if w.loc[~over].sum() <= 0:
            break
        w.loc[~over] += excess * w.loc[~over] / w.loc[~over].sum()
    return w / w.sum()


def tilt_ladder(
    base_w: pd.Series,
    g: pd.Series,
    lams: tuple[float, ...] = (0.0, 0.25, 0.5, 1.0),
    **kwargs,
) -> pd.DataFrame:
    """One row per lam: holdings-weighted g, effective number of names (1/HHI), max weight
    and one-way turnover vs the base index. The greenness-vs-deviation exhibit; per-lam
    weights come from `green_tilt`."""
    rows = []
    base = base_w / base_w.sum()
    for lam in lams:
        w = green_tilt(base_w, g, lam, **kwargs)
        gf = g.reindex(w.index)
        g_avg = float((w * gf).sum() / w[gf.notna()].sum()) if gf.notna().any() else np.nan
        both = pd.concat([w, base.reindex(w.index)], axis=1).fillna(0.0)
        rows.append({
            "lam": lam,
            "g_avg": g_avg,
            "eff_names": float(1.0 / (w**2).sum()),
            "w_max": float(w.max()),
            "turnover": float(0.5 * (both.iloc[:, 0] - both.iloc[:, 1]).abs().sum()),
        })
    return pd.DataFrame(rows)
