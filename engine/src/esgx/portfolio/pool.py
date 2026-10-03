"""Balanced cross-market pool: how many names a second market adds to the home market.

Pooling all of Taiwan (~1,900 priced names) with the ~85 priced Hong Kong names lets the
larger market dominate the candidate set and makes a request take most of a minute. The
balanced pool gives the added market as many names as the home market has, chosen as the
largest of every sector first, then the second largest of every sector, and so on — so
every sector is represented before any sector gets a second name. A product rule, not a
replication of a paper; size is the latest market cap in `prices`.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

MIN_MONTHS = 24  # same history requirement as `exposures.exposure_snapshot`


def eligible(prices: pd.DataFrame) -> pd.Index:
    """firm_ids with enough return history to get factor betas."""
    n = prices.dropna(subset=["ret"]).groupby("firm_id").size()
    return n[n >= MIN_MONTHS].index


def largest_per_sector(prices: pd.DataFrame, sectors: pd.Series, n: int, keep: Iterable[str] = ()) -> list[str]:
    """`n` eligible firm_ids, round-robin over sectors by latest market cap (firms without a
    sector share one "Unknown" bucket). `keep` — current holdings — are added on top when
    they are priced but not selected, so a holding is never dropped from the risk model."""
    cap = prices.sort_values("month").dropna(subset=["mktcap"]).groupby("firm_id")["mktcap"].last()
    cap = cap[cap.index.isin(eligible(prices))]
    df = pd.DataFrame({"sector": sectors.reindex(cap.index).fillna("Unknown"), "mktcap": cap})
    df["rank"] = df.groupby("sector")["mktcap"].rank(ascending=False, method="first")
    picked = df.sort_values(["rank", "mktcap"], ascending=[True, False]).head(n).index.tolist()
    priced = set(prices["firm_id"])
    return picked + [f for f in keep if f in priced and f not in picked]
