"""Hard-data tool: the self-reported scope 1+2 and revenue figures a firm's text is checked against."""

from __future__ import annotations

from esgx.measures import hard_data as _hd
from pipeline.tools.base import tool


@tool(kind="compute", cost="free")
def firm_hard_data(firm_id: str, year: int, universe: str = "hk") -> dict:
    """Scope 1+2 trend (last 4 years), revenue and assurance flags for one firm-year (see hard_data.PROVENANCE)."""
    return _hd.hard_data_for(firm_id, year, market=universe)
