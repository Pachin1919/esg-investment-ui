# Data workspace

The application uses a dated local dataset by default. The latest date in the header is the most recent observation **inside the selected dataset**, not its download time or proof of live market coverage. Each source table exposes its own coverage period.

## Data routes

- `GET /api/data/status?market=all|hk|tw`: mode, observation dates and market coverage.
- `GET /api/data/sources`: source tables and actual connector capabilities.
- `GET /api/data/schema`: versioned import contract, units, currencies, required tables and limits.
- `POST /api/data/mount`: validate a `{metadata, tables}` JSON bundle and return an immutable dataset ID.
- `GET /api/data/fx`: available dated conversion rates and source attribution.
- `GET /api/talk-walk?market=hk&firm_id=0002.HK`: stored semantic assessments, source evidence and separate dictionary scores.

Send `X-Dataset-Id` with company, evidence, filter and recommendation requests. Omit it or use `builtin` for the original local dataset. Imported datasets live in isolated temporary directories, expire at server restart and never replace original files. Unknown IDs return an explicit error.

Institutional APIs and SQL databases can export the standard JSON contract. There is no native database connection or credential storage in this version. Import is limited to 32 MiB, 500,000 rows and 16 distinct datasets per server session. The validator checks units, currencies, dates, unique keys, numeric values, market membership and required tables. A valid import does not guarantee enough usable history for every requested model; those failures remain explicit.

## Model conventions

- Capital, allocation values and share prices: HKD.
- Factor regressions, excess return and volatility: USD. HKD/TWD monthly stock returns are converted using dated FX before meeting French USD factors and the USD risk-free rate.
- No FX interpolation across missing months. Incomplete current months are excluded. The response reports model periods separately from quote dates and valuation FX months.
- Annual observations use supplied `available_date` from the following month; without one, the explicit assumption is July of the following year. This corrects the former 18-month lag.
- Hong Kong listings use Asia Pacific ex Japan factors; Taiwan listings use Emerging factors. Listing venue, company domicile and factor proxy are separate fields.
- Missing greenwashing assessments remain null and display **Insufficient data**. A valid zero carbon measure is retained.

Talk & Walk reads saved evidence; opening the page does not make a new LLM request. Semantic rubric values and dictionary percentiles remain separate. Details and documents are collapsed by default.

## Validation

`npm run build` compiles the UI. `npm run test:ui` runs deterministic browser regressions (install Chromium using `npx playwright install chromium`; on a local installed Chrome, set `PW_CHANNEL=chrome`).

Run `python -m pytest engine/tests tests --ignore=tests/browser` with the engine installed or its source and pipeline directories on `PYTHONPATH`. Tests include a validated dataset import followed by an actual recommendation computation, with independent checks of currency conversion and observation timing.

GitHub Actions runs the build, browser tests and Python tests. No live APIs, private credentials or LLM calls are required by these checks.

Local validation on 2026-10-10: 170 Python tests, 7 browser tests and the production build passed. Actual UI dataset import and restoration were verified. In the audit Windows environment, application control blocks the optional `qdldl` dependency used during CVXPY import. The existing SciPy fallback remains available and optional-backend initialization is now safe under concurrent requests. Two simultaneous full pooled recommendations at risk 3 / green 4 exceeded the local HTTP time limits; large-pool latency is an open performance limitation, not a passed acceptance check. The optimizer objective was not simplified to make the demonstration faster.
