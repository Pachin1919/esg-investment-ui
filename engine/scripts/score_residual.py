"""Excess talk (residual greenwashing measure) from the deterministic talk and walk tables.

Reads outputs/det_greenwashing_hk.csv and det_walk_hk.csv (run score_deterministic.py first),
regresses claim intensity on emissions intensity, its trend and report length with industry × year
effects, and keeps the residual. Then asks whether excess talk predicts next year's emissions.

  .venv/bin/python scripts/score_residual.py   # Hong Kong; needs at least 30 firm-years

Outputs: outputs/det_residual_hk.csv, det_residual_fit_hk.csv, det_residual_validation_hk.csv
"""

from __future__ import annotations

import argparse

import pandas as pd

from esgx.config import OUTPUT_DIR
from esgx.measures.residual import LEVEL_AND_TREND, LEVEL_ONLY, excess_talk
from esgx.measures.validation import predictive_regression

KEEP = ["firm_id", "year", "sector", "claim_per_1000", "talk_expected", "excess_talk", "excess_talk_z", "excess_talker",
        "greenwasher", "talk", "walk", "gap", "intensity", "d_log_intensity", "n_words"]


def next_year_outcomes(walk: pd.DataFrame) -> pd.DataFrame:
    """firm × year: change in log intensity and in log emissions from t to t+1."""
    nxt = walk[["firm_id", "year", "d_log_intensity", "d_log_level"]].assign(year=lambda x: x["year"] - 1)
    return nxt.rename(columns={"d_log_intensity": "d_log_intensity_next", "d_log_level": "d_log_level_next"})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", choices=["hk"], default="hk", help="Hong Kong only: Taiwan has no talk table yet")
    args = ap.parse_args()
    sfx = f"_{args.universe}"
    gw = pd.read_csv(OUTPUT_DIR / f"det_greenwashing{sfx}.csv")
    walk = pd.read_csv(OUTPUT_DIR / f"det_walk{sfx}.csv")
    df = gw.merge(walk[["firm_id", "year", "d_log_intensity", "d_log_level"]], on=["firm_id", "year"], how="left")

    fits = []
    for name, regs in (("level", LEVEL_ONLY), ("level_trend", LEVEL_AND_TREND)):
        try:
            res, fit = excess_talk(df, regressors=regs)
        except ValueError as e:
            print(f"{name}: skipped ({e})")
            continue
        fits.append(fit.assign(spec=name).reset_index())
        print(f"\n[{name}]\n{fit.round(3).to_string()}")
    if not fits:
        return
    pd.concat(fits, ignore_index=True).to_csv(OUTPUT_DIR / f"det_residual_fit{sfx}.csv", index=False)
    res[KEEP].sort_values(["year", "excess_talk"], ascending=[True, False]).to_csv(OUTPUT_DIR / f"det_residual{sfx}.csv", index=False)

    both = int((res["excess_talker"] & res["greenwasher"]).sum())
    print(f"\nexcess talkers: {int(res['excess_talker'].sum())} of {len(res)} firm-years; double-sort greenwashers: "
          f"{int(res['greenwasher'].sum())}; flagged by both: {both}")
    print(f"rank correlation excess_talk vs gap: {res['excess_talk'].corr(res['gap'], method='spearman'):.2f}, "
          f"vs intensity: {res['excess_talk'].corr(res['intensity'], method='spearman'):.2f}")
    last = res[res["year"] == res["year"].max()].nlargest(10, "excess_talk")
    print(f"\ntop excess talk, {int(res['year'].max())}:\n{last[['firm_id', 'sector', 'claim_per_1000', 'talk_expected', 'excess_talk', 'walk', 'greenwasher']].round(2).to_string(index=False)}")

    oc = next_year_outcomes(walk)
    rows = []
    for outcome in ("d_log_intensity_next", "d_log_level_next"):
        try:
            v = predictive_regression(res, oc, outcome=outcome, pillars=("excess_talk", "walk"), controls=())
            rows.append(v.assign(outcome=outcome).reset_index())
        except ValueError as e:
            print(f"validation {outcome}: skipped ({e})")
    if rows:
        val = pd.concat(rows, ignore_index=True)
        val.to_csv(OUTPUT_DIR / f"det_residual_validation{sfx}.csv", index=False)
        print(f"\nnext-year emissions on excess talk and walk (industry × year effects, firm-clustered):\n{val.round(3).to_string(index=False)}")


if __name__ == "__main__":
    main()
