"""Combined talk score (deterministic word intensity + LLM rubric) and the three-variant flag table.

  .venv/bin/python scripts/score_combined.py --universe hk
  .venv/bin/python scripts/score_combined.py --universe hk --index hsci

Reads outputs/det_talk{sfx}.csv and det_walk{sfx}.csv (run score_deterministic.py first) and, when
present, outputs/talkwalk_firm_year{sfx}.csv (LLM rubric; optional — without it every firm-year
falls back to the dictionary score, flagged talk_source = "dict").

Writes outputs/combined_talk{sfx}.csv and outputs/combined_greenwashing{sfx}.csv.

Universe: Hong Kong and Taiwan only. The project never scores US assets — decided 2026-10-03,
see brain/scope/Scope – översikt.md.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from esgx.config import OUTPUT_DIR
from esgx.ingest.twse_esg import load_universe_tw
from esgx.ingest.universe_hk import load_universe_hk
from esgx.measures.talk_combined import combine_talk, greenwashing_variants


def _read(path: Path, required: bool = False) -> pd.DataFrame | None:
    if path.exists():
        return pd.read_csv(path)
    if required:
        raise SystemExit(f"missing {path} — run scripts/score_deterministic.py for this universe first")
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", choices=["hk", "tw"], default="hk", help="US assets are never scored (scope decision 2026-10-03)")
    ap.add_argument("--index", choices=["hsi", "hsci"], default="hsi", help="Hong Kong universe: Hang Seng Index or Composite proxy")
    args = ap.parse_args()
    sfx = f"_{args.universe}"

    talk_det = _read(OUTPUT_DIR / f"det_talk{sfx}.csv", required=True)
    walk = _read(OUTPUT_DIR / f"det_walk{sfx}.csv", required=True)
    talk_llm = _read(OUTPUT_DIR / f"talkwalk_firm_year{sfx}.csv")
    firms = load_universe_hk(index=args.index) if args.universe == "hk" else load_universe_tw()

    combined = combine_talk(talk_det, talk_llm, firms)
    combined.to_csv(OUTPUT_DIR / f"combined_talk{sfx}.csv", index=False)
    gw = greenwashing_variants(combined, walk)
    gw.to_csv(OUTPUT_DIR / f"combined_greenwashing{sfx}.csv", index=False)

    print(f"talk: {len(combined)} firm-years -> outputs/combined_talk{sfx}.csv")
    print(combined["talk_source"].value_counts().rename("firm-years").to_string())
    if talk_llm is None:
        print(f"no outputs/talkwalk_firm_year{sfx}.csv — dictionary fallback everywhere; run the LLM rubric to enrich")
    print(f"\ngreenwashing: {len(gw)} firm-years -> outputs/combined_greenwashing{sfx}.csv")
    for v in ("dict", "llm", "combined"):
        print(f"  greenwasher_{v}: {int(gw[f'greenwasher_{v}'].sum())} flagged of {gw[f'greenwasher_{v}'].notna().sum()} scored")


if __name__ == "__main__":
    main()
