"""Current vs recommended positions: capital and share counts per firm.

`recommend` works in weights; an investor trades shares. Share counts are capital / last
close, rounded down to whole shares (board lots are not modeled). Firms without a price
keep capital figures and get null share counts — never a guessed price.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_positions(trades: pd.DataFrame, target_capital: float, close: pd.Series | None = None) -> pd.DataFrame:
    """Adds capital_current/capital_target and, where `close` (firm_id -> price) has the firm,
    price, shares_current, shares_target and shares_delta."""
    out = trades.copy()
    out["capital_current"] = out["w_current"] * target_capital
    out["capital_target"] = out["w_target"] * target_capital
    price = out["firm_id"].map(close) if close is not None else pd.Series(np.nan, index=out.index)
    price = price.where(price > 0)
    out["price"] = price
    out["shares_current"] = np.floor(out["capital_current"] / price)
    out["shares_target"] = np.floor(out["capital_target"] / price)
    out["shares_delta"] = out["shares_target"] - out["shares_current"]
    return out
