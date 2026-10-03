"""Phase 0 – build the exposure table and replicate two course results on free data.

1. Greenness g (PST 2022 structure) from a carbon-intensity proxy, with across/within split.
2. Green-minus-brown factor (sorted and regression-based), cumulative plot,
   alphas on FF5+MOM, and the HML/UMD "explained by GMB" check.
3. Carbon premium via lagged Fama-MacBeth (BK 2021 / Crosignani et al. 2025 spec),
   with the robustness matrix from Lecture 3.

The sections live in `esgx.report.phase0_*`; this script only sequences them and writes the report.
Run:  .venv/bin/python scripts/phase0_replicate.py [--refresh]
"""

from __future__ import annotations

import argparse

from esgx.config import OUTPUT_DIR
from esgx.report.phase0_gmb import build_gmb
from esgx.report.phase0_measure import build_measurement
from esgx.report.phase0_premium import build_carbon_premium


def main(refresh: bool = False) -> None:
    report: list[str] = ["# Phase 0 replication report\n"]
    data = build_measurement(report, refresh=refresh)
    build_gmb(report, data.exposure, data.factors)
    build_carbon_premium(report, data.prices, data.inten, data.firms)
    (OUTPUT_DIR / "phase0_report.md").write_text("\n".join(report))
    print("\n".join(report))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-download all raw data")
    main(refresh=ap.parse_args().refresh)
