# Data snapshot for the app

A snapshot of the tables the API reads, committed so that a fresh clone runs without
access to the data bucket. Taken 2026-10-04 from the pipeline's outputs.

`engine/data/` and `engine/outputs/` are the engine's default paths, so no `.env` data
settings are needed. Both stay git-ignored: these files were added with `git add -f`, and
anything else the pipeline writes there is still left out of the repo.

| Path | Content |
|---|---|
| `data/raw/universe_*.parquet` | Company universe: name, sector, industry, domicile (HSI, HSCI, TWSE) |
| `data/raw/prices_monthly_{hk,tw}.parquet` | Monthly returns and market cap (yfinance) |
| `data/raw/last_close_hk.parquet` | Latest close per HK ticker, for share counts (2026-10-02) |
| `data/raw/last_close_tw.parquet` | Latest close for the three largest Taiwan names per sector (105, covers the balanced pool), for share counts (2026-10-02); `scripts/ingest_last_close.py` |
| `data/raw/factors_monthly_*.parquet` | FF5 + momentum factor returns per region |
| `data/raw/fx_monthly.parquet` | Month-end FX rates for pooling markets in HKD |
| `data/raw/fundamentals_*.parquet`, `data/processed/emissions_tw.parquet` | Revenue and emissions inputs |
| `outputs/det_greenness_*.csv`, `det_greenwashing_*.csv` | E-score, E-weight, greenness, talk/walk, flags |
| `outputs/gmb_monthly_*.csv`, `emissions_hk.csv`, `talkwalk_*_hk.csv` | Green factor, extracted emissions, LLM talk/walk |

To refresh: re-run the pipeline (or sync from the bucket), copy the same files here and
commit them with `git add -f`. The full raw data (reports, about 9 GB) stays in the bucket
and is not needed to run the app.
