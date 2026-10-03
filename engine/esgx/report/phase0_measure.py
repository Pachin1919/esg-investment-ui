"""Phase 0, layer A: ingest free data, build carbon intensity, greenness and the exposure panel."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from esgx.config import PROCESSED_DIR
from esgx.ingest.factors import load_factors
from esgx.ingest.ghgrp import load_ghgrp_parent_emissions, match_to_universe
from esgx.ingest.prices import load_prices
from esgx.ingest.sec_facts import load_fundamentals
from esgx.ingest.universe import load_universe
from esgx.measures.carbon import align_annual_to_months, carbon_intensity
from esgx.measures.greenness import greenness_table, scores_from_carbon_intensity
from esgx.report.md import md_table
from esgx.schema import validate


@dataclass
class Phase0Data:
    firms: pd.DataFrame
    factors: pd.DataFrame
    prices: pd.DataFrame
    fund: pd.DataFrame
    emissions: pd.DataFrame
    inten: pd.DataFrame
    green: pd.DataFrame
    exposure: pd.DataFrame


def build_measurement(report: list[str], refresh: bool = False) -> Phase0Data:
    """Ingest, coverage tables, greenness and exposure; appends report sections in place."""
    # ---------- ingest ----------
    firms = load_universe(refresh=refresh)
    factors = load_factors(refresh=refresh)
    prices = load_prices(firms["firm_id"].tolist(), refresh=refresh)
    fund = load_fundamentals(firms, refresh=refresh)
    parent = load_ghgrp_parent_emissions(refresh=refresh)
    emissions = match_to_universe(parent, firms)
    
    cov = emissions.groupby("year")["matched"].mean()
    n_matched = emissions[emissions["matched"]]["firm_id"].nunique()
    report.append(f"Universe: {len(firms)} firms (current S&P 500). GHGRP-matched firms (any year): {n_matched}.\n")
    report.append("GHGRP match rate by year:\n\n" + md_table(cov.to_frame("share_matched"), "{:.2f}") + "\n")
    
    matched_by_sector = (
        emissions[emissions["matched"]].drop_duplicates("firm_id").merge(firms, on="firm_id")
        .groupby("sector").size().rename("matched").to_frame()
        .join(firms.groupby("sector").size().rename("total"))
    )
    matched_by_sector["share"] = matched_by_sector["matched"] / matched_by_sector["total"]
    report.append("Matched firms by sector:\n\n" + md_table(matched_by_sector.fillna(0), "{:.2f}") + "\n")
    
    # ---------- layer A: carbon + greenness ----------
    inten = carbon_intensity(emissions, fund)
    scores = scores_from_carbon_intensity(inten, firms)
    green = greenness_table(scores, firms)
    validate(scores, "esg_scores")
    
    months = pd.period_range(prices["month"].min(), prices["month"].max(), freq="M")
    g_m = align_annual_to_months(green[["firm_id", "year", "g", "g_across", "g_within"]], months)
    i_m = align_annual_to_months(inten[["firm_id", "year", "intensity", "log_level", "matched"]], months)
    exposure = (
        prices.merge(g_m.drop(columns="year"), on=["firm_id", "month"], how="left")
        .merge(i_m.drop(columns="year"), on=["firm_id", "month"], how="left")
        .rename(columns={"intensity": "carbon_intensity"})
    )
    validate(exposure, "exposure")
    exposure.assign(month=exposure["month"].astype(str)).to_parquet(PROCESSED_DIR / "exposure.parquet", index=False)
    green.to_parquet(PROCESSED_DIR / "greenness_annual.parquet", index=False)
    emissions.to_parquet(PROCESSED_DIR / "emissions.parquet", index=False)
    
    latest = green[green["year"] == green["year"].max()].merge(firms[["firm_id", "name", "sector"]], on="firm_id")
    report.append(f"## Greenness (carbon proxy), year {green['year'].max()}\n")
    report.append("Brownest 10:\n\n" + md_table(latest.nsmallest(10, "g").set_index("firm_id")[["name", "sector", "e_score", "e_weight", "g"]], "{:.2f}") + "\n")
    report.append("Sector average g (PST Table 1 analogue):\n\n" + md_table(latest.groupby("sector")["g"].mean().sort_values().to_frame(), "{:.2f}") + "\n")
    return Phase0Data(firms, factors, prices, fund, emissions, inten, green, exposure)
