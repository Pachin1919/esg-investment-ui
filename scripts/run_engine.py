"""
ESG Exposure Engine – MVP runner.

How to use
----------
1. Edit PARAMETERS below.
2. Run:  python main.py            (or `python -i main.py` to explore `result` afterwards)
3. Everything is returned as an `EngineResult`, printed to the terminal, and saved to outputs/.

Pipeline
--------
Step 1  Phase 0        US only. Free data -> carbon intensity -> Method A greenness (g),
                       green-minus-brown factor, carbon-premium regression.
Step 2  Deterministic  No LLM. walk  = scope-1 intensity percentile within industry-year
                                       (hard data only, matched firms only)
                                talk  = green-claim word intensity in filings, risk context removed
                                flags = greenwasher (top-quintile talk AND bottom-tercile walk)
                                gap   = talk - walk, diagnostics, predictive validation (Chen 2025)
Step 3  LLM (optional) The paid agent pipeline (talk/walk rubric read by Claude). Off by default.
Step 4  Scoring        Final per-firm scores by provider:
                         carbon_proxy : Method A, every matched firm
                         esgx_custom  : Method A blended with the greenwashing gap, firms that have both
Step 5  Print + save
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add engine directories to Python path
_REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (_REPO_ROOT / "engine", _REPO_ROOT / "engine" / "greenwash"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from dataclasses import dataclass, field

import pandas as pd
from tqdm import tqdm

from esgx.config import OUTPUT_DIR, PROCESSED_DIR, RAW_DIR

# ---- Phase 0 -----------------------------------------------------------------------
from esgx.report.phase0_measure import build_measurement
from esgx.report.phase0_gmb import build_gmb
from esgx.report.phase0_premium import build_carbon_premium

# ---- Deterministic talk / walk / greenwashing ---------------------------------------
from esgx.ingest.universe import load_universe
from esgx.ingest.universe_hk import load_universe_hk
from esgx.measures.carbon import carbon_intensity
from esgx.measures.walk_hard import walk_score
from esgx.measures.talk_dict import collect_us_counts, firm_year_intensity, report_counts, talk_score
from esgx.measures.greenwash import diagnostics, greenwashing_table
from esgx.measures.validation import emissions_outcomes, predictive_regression

# ---- Optional LLM engine --------------------------------------------------------------
from esgx.agents.pipeline import Orchestrator, default_pipeline, estimate_cost

# ---- Scoring ---------------------------------------------------------------------------
from esgx.measures.custom_score import ScoreSpec, combine_pillars
from esgx.measures.greenness import greenness_table, scores_from_carbon_intensity


# ==================================================================================
# PARAMETERS – edit these, then run the file
# ==================================================================================

# --- Universe -----------------------------------------------------------------------
# "us" : S&P 500. Emissions from EPA GHGRP (scope 1), filings from SEC EDGAR.
# "hk" : Hang Seng. Needs `scripts/ingest_hk.py` run first (reports + LLM-extracted scope 1+2).
#        Phase 0 and the final blend are US-only, so for "hk" only the deterministic block runs.
UNIVERSE = "hk"

# --- Which steps run ------------------------------------------------------------------
RUN_PHASE0 = True            # Step 1. US only. Required before step 2 (it produces the emissions data).
RUN_DETERMINISTIC = True     # Step 2. Free. Needs EDGAR downloads on the first run (cached afterwards).
RUN_LLM_TALKWALK = False     # Step 3. Paid in MODE = "live". Off by default.
RUN_SCORING = True           # Step 4. Final carbon_proxy / esgx_custom tables.

# --- Phase 0 --------------------------------------------------------------------------
REFRESH_DATA = False         # True = re-download everything (about 15 min).

# --- Which firms get a talk score -----------------------------------------------------
# Talk needs one full filing download per firm-year, so it is limited to this selection.
# The deterministic validation needs >= 20 scored firm-years, so a handful of tickers
# is not enough: use whole sectors. Only firms with matched emissions are fetched.
TICKERS = ["XOM", "NEE", "DUK"]
SECTORS = ["Energy", "Utilities", "Materials"]     # [] = tickers only
FILINGS = ("10-K",)          # add "8-K" to include press releases (voluntary communication)
FILINGS_START = "2021-01-01" # earliest filing date
MAX_8K = 20                  # per firm, only used if "8-K" is in FILINGS

# --- Optional LLM engine --------------------------------------------------------------
# "dry_run"    free keyword heuristic, plumbing test ONLY, never a finding
# "cache_only" free, reuses earlier LLM answers, skips anything not cached
# "live"       calls the Anthropic API (~0.08 USD per document section)
MODE = "dry_run"
MAX_COST_USD = 20.0

# --- Scoring --------------------------------------------------------------------------
# Which talk/walk engine feeds the final blend: "deterministic" or "llm".
TALKWALK_SOURCE = "deterministic"

# Pillars are 0-10. A negative weight means "higher is worse" (flipped before averaging).
# These are informed guesses, not calibrated. IMPORTANT: with the deterministic engine,
# `walk` is a re-ranking of the same scope-1 intensity the `carbon` pillar already uses
# (same order among matched firms), so it is NOT blended; that would count carbon twice.
WEIGHTS_DETERMINISTIC = {"carbon": 0.5, "gap": -0.1}
WEIGHTS_LLM = {"carbon": 0.5, "walk": 0.4, "gap": -0.1}

# --- Output ---------------------------------------------------------------------------
TOP_N = 10
SAVE_CSV = True


# ==================================================================================
# RESULT CONTAINER
# ==================================================================================

@dataclass
class EngineResult:
    """Everything one run produces. A field is None if its step was skipped."""
    # Step 1 – Phase 0 (US)
    firms: pd.DataFrame | None = None
    emissions: pd.DataFrame | None = None
    fundamentals: pd.DataFrame | None = None
    intensity: pd.DataFrame | None = None
    greenness_proxy: pd.DataFrame | None = None
    gmb: pd.DataFrame | None = None
    carbon_premium: pd.DataFrame | None = None
    phase0_report: str = ""
    # Step 2 – deterministic talk / walk / greenwashing
    walk: pd.DataFrame | None = None
    talk: pd.DataFrame | None = None
    greenwashing: pd.DataFrame | None = None
    diagnostics: pd.DataFrame | None = None
    validation: pd.DataFrame | None = None
    # Step 3 – LLM engine (optional)
    llm_talkwalk: pd.DataFrame | None = None
    llm_mode: str | None = None
    llm_log: list[str] = field(default_factory=list)
    # Step 4 – final scores, both providers stacked (filter on `provider`)
    scores: pd.DataFrame | None = None
    warnings: list[str] = field(default_factory=list)


# ==================================================================================
# STEP 1 – Phase 0: data, Method A greenness, GMB factor, carbon premium (US) / HK Ingest
# ==================================================================================

def run_phase0_us(result: EngineResult) -> None:
    report: list[str] = ["# Phase 0 report\n"]
    data = build_measurement(report, refresh=REFRESH_DATA)
    gmb = build_gmb(report, data.exposure, data.factors)
    premium = build_carbon_premium(report, data.prices, data.inten, data.firms)
    
    result.firms, result.emissions, result.fundamentals = data.firms, data.emissions, data.fund
    result.intensity, result.greenness_proxy = data.inten, data.green
    result.gmb, result.carbon_premium = gmb, premium
    result.phase0_report = "\n".join(report)
    result.warnings.append(
        "Method A treats firms without an EPA facility as cleanest in their sector. "
        "XOM scope 1 is inflated by GHGRP Subpart MM."
    )

def run_phase0_hk(result: EngineResult) -> None:
    import json
    import subprocess
    import sys
    from esgx.ingest.fundamentals_yf import load_fundamentals_yf
    from esgx.ingest.hkexnews import load_documents_hk
    
    print("Fetching HK universe & Yahoo Finance fundamentals...")
    firms = load_universe_hk(refresh=REFRESH_DATA)
    result.firms = firms
    
    fund = load_fundamentals_yf(firms, refresh=REFRESH_DATA, cache_name="fundamentals_yf_hk")
    result.fundamentals = fund
    
    docs_path = PROCESSED_DIR / "documents_hk.parquet"
    if REFRESH_DATA or not docs_path.exists():
        print("Fetching HKEX PDFs (this may take a few minutes for the first run)...")
        rows = []
        for r in tqdm(firms.itertuples(), total=len(firms)):
            if pd.isna(r.hkex_sid): continue
            rows.append(load_documents_hk(r.firm_id, int(r.stock_code), int(r.hkex_sid), start=FILINGS_START))
        docs = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
        docs.to_parquet(docs_path, index=False)
    else:
        docs = pd.read_parquet(docs_path)

    emissions_path = PROCESSED_DIR / "emissions_hk.parquet"
    if REFRESH_DATA or not emissions_path.exists():
        print("Extracting metrics via offline NLP pipeline (Deterministic & Free)...")
        pref = docs.assign(_t=docs["doc_type"].map({"esg_report": 1, "annual_report": 0}))
        pref = pref.sort_values(["firm_id", "fiscal_year", "_t", "filing_date"], ascending=[True, True, False, False])
        target_docs = pref.drop_duplicates(["firm_id", "fiscal_year"])
        
        extracted_rows = []
        run_dir = OUTPUT_DIR / "hk_extract_runs"
        run_dir.mkdir(exist_ok=True)
        
        for d in tqdm(target_docs.itertuples(), total=len(target_docs)):
            if pd.isna(d.path): continue
            out_folder = run_dir / d.firm_id / str(d.fiscal_year)
            out_folder.mkdir(parents=True, exist_ok=True)
            
            try:
                env = os.environ.copy()
                env["PYTHONPATH"] = f"{_REPO_ROOT / 'engine'}:{_REPO_ROOT / 'engine' / 'greenwash'}"
                subprocess.run(
                    [sys.executable, "-m", "greenwash", "extract", 
                     str(d.path), "--company", d.firm_id, "--out", str(out_folder)],
                    check=True, capture_output=True, env=env
                )
                cand_file = out_folder / "candidates.json"
                if cand_file.exists():
                    data = json.loads(cand_file.read_text())
                    for rec in data.get("records", []):
                        if rec.get("kind") == "observation":
                            fields = rec.get("fields", {})
                            metric = fields.get("metric")
                            if metric in ("scope1", "scope2"):
                                extracted_rows.append({
                                    "firm_id": d.firm_id,
                                    "year": fields.get("year", int(d.fiscal_year)),
                                    "metric": metric,
                                    "value": fields.get("value")
                                })
            except Exception as e:
                result.warnings.append(f"Offline extraction failed for {d.firm_id} FY{d.fiscal_year}: {e}")
        
        if extracted_rows:
            raw_em = pd.DataFrame(extracted_rows).dropna(subset=["value"])
            if not raw_em.empty:
                em = raw_em.groupby(["firm_id", "year", "metric"])["value"].first().unstack(fill_value=pd.NA).reset_index()
                for col in ["scope1", "scope2"]:
                    if col not in em.columns: em[col] = pd.NA
            else:
                em = pd.DataFrame(columns=["firm_id", "year", "scope1", "scope2"])
        else:
            em = pd.DataFrame(columns=["firm_id", "year", "scope1", "scope2"])
            
        em.to_parquet(emissions_path, index=False)
    
    result.emissions = pd.read_parquet(emissions_path)



# ==================================================================================
# STEP 2 – Deterministic talk / walk / greenwashing (no LLM)
# ==================================================================================

def load_universe_inputs(result: EngineResult) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    if UNIVERSE == "hk":
        for p in (PROCESSED_DIR / "emissions_hk.parquet", RAW_DIR / "fundamentals_yf_hk.parquet", PROCESSED_DIR / "documents_hk.parquet"):
            if not p.exists():
                raise RuntimeError(f"Missing {p.name}: run scripts/ingest_hk.py first.")
        em = pd.read_parquet(PROCESSED_DIR / "emissions_hk.parquet")
        em["scope12"] = em["scope1"].fillna(0) + em["scope2"].fillna(0)
        return load_universe_hk(), em, pd.read_parquet(RAW_DIR / "fundamentals_yf_hk.parquet"), "scope12"

    if result.emissions is None:
        raise RuntimeError("US walk needs emissions: set RUN_PHASE0 = True (or run it once before).")
    return result.firms, result.emissions, result.fundamentals, "scope1"

def run_deterministic(result: EngineResult) -> None:
    firms, emissions, fundamentals, scope = load_universe_inputs(result)

    carbon = result.intensity if UNIVERSE == "us" else carbon_intensity(emissions, fundamentals, scope=scope)
    result.walk = walk_score(carbon, firms)

    if UNIVERSE == "hk":
        counts = report_counts(pd.read_parquet(PROCESSED_DIR / "documents_hk.parquet"))
    else:
        counts = collect_us_counts(firms, set(result.walk["firm_id"]), TICKERS, SECTORS, FILINGS, FILINGS_START, MAX_8K)
    result.talk = talk_score(firm_year_intensity(counts), firms)

    result.greenwashing = greenwashing_table(result.talk, result.walk)
    result.diagnostics = diagnostics(result.greenwashing)

    try:
        em = emissions.assign(scope1=emissions["scope12"]) if UNIVERSE == "hk" else emissions
        outcomes = emissions_outcomes(em, fundamentals)
        result.validation = predictive_regression(result.greenwashing, outcomes, pillars=("talk",))
    except ValueError as e:
        result.warnings.append(f"Validation skipped: {e}")

    result.warnings.append("Check diagnostics: corr(talk, walk) near -1 means talk is re-measuring emissions.")


# ==================================================================================
# STEP 3 – Optional LLM engine (paid)
# ==================================================================================

def run_llm_talkwalk(result: EngineResult) -> None:
    if not (PROCESSED_DIR / "emissions.parquet").exists():
        raise RuntimeError("Run Phase 0 first: the LLM cross-checks claims against emissions.parquet.")
    if MODE == "live" and not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("MODE = 'live' needs ANTHROPIC_API_KEY.")

    spec = default_pipeline()
    if MODE == "live":
        est = estimate_cost(spec, n_sections=len(TICKERS) * 16, n_firm_years=len(TICKERS) * 4)["total_usd"]
        print(f"Estimated LLM cost: {est:.2f} USD")
        if est > MAX_COST_USD:
            raise RuntimeError(f"Estimate {est:.2f} USD exceeds MAX_COST_USD = {MAX_COST_USD}.")

    run = Orchestrator().start(spec, [t.upper() for t in TICKERS], MODE, blocking=True)
    result.llm_log = [f"[{e.get('stage')}] {e.get('msg')}" for e in run.log]
    if run.status != "done":
        raise RuntimeError(f"LLM pipeline failed: {run.error}")
    result.llm_talkwalk = pd.DataFrame(run.results.get("firm_years", []))
    result.llm_mode = MODE
    if MODE == "dry_run":
        result.warnings.append("LLM engine ran in dry_run mode: heuristic numbers, NOT a result.")


# ==================================================================================
# STEP 4 – Final scores
# ==================================================================================

def build_pillars(result: EngineResult, base: pd.DataFrame) -> tuple[pd.DataFrame | None, dict[str, float]]:
    carbon = base.rename(columns={"e_score": "carbon"})[["firm_id", "year", "carbon"]]

    if TALKWALK_SOURCE == "deterministic":
        gw = result.greenwashing
        if gw is None or gw.empty:
            return None, {}
        gap = gw[["firm_id", "year", "gap"]].assign(gap=lambda d: d["gap"].clip(lower=0))
        return carbon.merge(gap, on=["firm_id", "year"], how="inner"), WEIGHTS_DETERMINISTIC

    tw = result.llm_talkwalk
    if tw is None or tw.empty:
        return None, {}
    if result.llm_mode == "dry_run":
        result.warnings.append("esgx_custom skipped: LLM talk/walk came from dry_run.")
        return None, {}
    llm = tw[["firm_id", "year", "walk", "gap"]].assign(gap=lambda d: d["gap"].clip(lower=0))
    return carbon.merge(llm, on=["firm_id", "year"], how="inner"), WEIGHTS_LLM

def run_scoring(result: EngineResult) -> None:
    if result.intensity is None or result.firms is None:
        raise RuntimeError("Scoring is US-only and needs Phase 0 in this run (RUN_PHASE0 = True).")

    base = scores_from_carbon_intensity(result.intensity, result.firms)
    tables = [greenness_table(base, result.firms)]

    pillars, weights = build_pillars(result, base)
    if pillars is not None and len(pillars):
        custom = combine_pillars(pillars, base[["firm_id", "year", "e_weight"]], ScoreSpec(weights=weights))
        tables.append(greenness_table(custom, result.firms))
        result.warnings.append(f"esgx_custom: {len(pillars)} firm-years, weights {weights}, unvalidated.")

    result.scores = pd.concat(tables, ignore_index=True)


# ==================================================================================
# STEP 5 – Terminal output and saving
# ==================================================================================

def print_summary(result: EngineResult) -> None:
    line = "=" * 84

    if result.greenness_proxy is not None:
        g = result.greenness_proxy
        year = g["year"].max()
        latest = g[g["year"] == year].merge(result.firms[["firm_id", "name", "sector"]], on="firm_id")
        print(f"{line}\nMETHOD A – carbon-proxy greenness {year}  (g: 0 = green, more negative = browner)")
        print(latest.nsmallest(TOP_N, "g")[["firm_id", "name", "sector", "e_score", "e_weight", "g"]]
              .round(2).to_string(index=False))

    if result.gmb is not None and len(result.gmb):
        print(f"\n{line}\nGMB factor: {len(result.gmb)} months (details: outputs/phase0_report.md)")

    if result.greenwashing is not None:
        gw = result.greenwashing
        print(f"\n{line}\nDETERMINISTIC TALK / WALK  ({UNIVERSE}; {len(gw)} firm-years, {gw['firm_id'].nunique()} firms)")
        flagged = gw[gw["greenwasher"] == 1]
        print(f"\nGreenwashers (top-quintile talk, bottom-tercile walk): {len(flagged)}")
        if len(flagged):
            print(flagged.head(TOP_N)[["firm_id", "year", "sector", "talk", "walk", "gap"]].round(2).to_string(index=False))
        print("\nHighest gap (talk - walk):")
        print(gw.nlargest(TOP_N, "gap")[["firm_id", "year", "talk", "walk", "gap", "claim_per_1000"]].round(2).to_string(index=False))
        print("\nDiagnostics (corr_talk_walk near -1 = text re-measures emissions):")
        print(result.diagnostics.round(2).to_string())
        if result.validation is not None:
            print("\nPredictive validation, next-year change in log scope 1 (talk coef should be ~0):")
            print(result.validation.round(3).to_string())

    if result.llm_talkwalk is not None and len(result.llm_talkwalk):
        print(f"\n{line}\nLLM TALK / WALK (mode: {result.llm_mode})")
        print(result.llm_talkwalk[["firm_id", "year", "talk", "walk", "gap", "n_docs"]].round(2).to_string(index=False))

    if result.scores is not None:
        print(f"\n{line}\nFINAL SCORES by provider (latest year)")
        for provider, part in result.scores.groupby("provider"):
            part = part[part["year"] == part["year"].max()]
            print(f"\n{provider}  ({len(part)} firms)")
            print(part.nsmallest(TOP_N, "g")[["firm_id", "e_score", "e_weight", "g", "g_within"]].round(2).to_string(index=False))

    if result.warnings:
        print(f"\n{line}\nWARNINGS")
        for w in result.warnings:
            print(" -", w)

def save_outputs(result: EngineResult) -> None:
    sfx = "_hk" if UNIVERSE == "hk" else ""
    if result.phase0_report:
        (OUTPUT_DIR / "phase0_report.md").write_text(result.phase0_report)
    for name, df in (("det_walk", result.walk), ("det_talk", result.talk), ("det_greenwashing", result.greenwashing),
                     ("det_diagnostics", result.diagnostics), ("det_validation", result.validation),
                     ("main_scores", result.scores)):
        if df is not None:
            df.to_csv(OUTPUT_DIR / f"{name}{sfx}.csv")

# ==================================================================================
# MAIN
# ==================================================================================

def main() -> EngineResult:
    result = EngineResult()
    
    # Pre-checks
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if RUN_PHASE0:
        if UNIVERSE == "us":
            print("Step 1  Phase 0 (US) ...")
            run_phase0_us(result)
        elif UNIVERSE == "hk":
            print("Step 1  Phase 0 (HK) ...")
            run_phase0_hk(result)

    if RUN_DETERMINISTIC:
        print(f"Step 2  Deterministic talk/walk ({UNIVERSE}) ...")
        run_deterministic(result)

    if RUN_LLM_TALKWALK:
        print(f"Step 3  LLM talk/walk for {TICKERS} in {MODE} mode ...")
        run_llm_talkwalk(result)

    if RUN_SCORING and UNIVERSE == "us":
        print("Step 4  Scoring ...")
        run_scoring(result)

    print_summary(result)
    if SAVE_CSV:
        save_outputs(result)
    return result

if __name__ == "__main__":
    result = main()
