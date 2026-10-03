# Proposed v1 UI contract and mock files

These are proposed frontend defaults, not an approved backend API. No live endpoint, delivery date, forecasting model, or risk calibration has been confirmed. The UI now uses the current-portfolio and recommendation fixtures in explicitly labeled demo mode. Imported holdings do not receive fixture forecasts or scores.

The latest screenshot Q&A confirms both preferences use levels 1–5, with no descriptive risk-category names required. Current holding value is confirmed as the import valuation basis. Simulation can add new money or rebalance existing holdings, optionally with additional money. The UI implements both as local value/weight previews; analytical results for imported portfolios still require the backend.

All securities, expected returns, scores and FX rates in this folder are fictional. The fixtures illustrate UI behavior and must be labeled as demo data. They do not validate recommendation ranking or suitability for any risk level.

## Decisions and confirmation status

| Item | Draft choice | Status |
| --- | --- | --- |
| Risk preference | Level 1–5; 5 means higher risk tolerance | Confirmed by latest Q&A; quantitative model mapping pending |
| Green preference | Level 1–5; 5 means stronger preference for green firms | Confirmed by latest Q&A; recommendation mapping pending |
| Import valuation | Current holding value, not original purchase cost | Confirmed by latest Q&A |
| Supported import currencies | HKD, CNY, TWD; one currency per holding | Proposed initial set |
| Reporting currency | HKD | Proposed default |
| Simulation funding | New money or specified reductions of existing holdings, optionally with added money | Both modes confirmed by latest Q&A; local previews implemented |
| Expected return | Next 12 months, nominal total return in the reporting currency, including dividends and excluding fees/taxes | Entire return convention requires backend confirmation |
| Company green score | E-score, 0–10, higher means more environmentally friendly | Direction confirmed; equivalence and range proposed |
| Portfolio green score | Current-value-weighted mean of company E-scores | Mock aggregation only; actual backend method not confirmed |
| Portfolio volatility | Unavailable in these draft v1 fixtures | Actual first-version availability not confirmed |

### Preference labels

| Value | Risk preference | Green preference |
| --- | --- | --- |
| 1 | Level 1 · green | Level 1 |
| 2 | Level 2 · blue | Level 2 |
| 3 | Level 3 · yellow | Level 3 |
| 4 | Level 4 · orange | Level 4 |
| 5 | Level 5 · red | Level 5 |

These are preference categories, not measured volatility bands. Risk calibration and recommendation eligibility must come from the backend. A green preference of 5 does not require 100% green holdings or guarantee a particular outcome. Preference levels and E-scores use different scales.

## Portfolio import

Use [portfolio-import.sample.csv](portfolio-import.sample.csv), encoded as UTF-8. All example holdings share the valuation date 2026-10-03.

| Column | Required | Meaning |
| --- | --- | --- |
| `stock_code` | Yes | Exchange-qualified identifier; preserve it as text, including leading zeros |
| `exchange` | Yes | Proposed identifiers: XHKG (Hong Kong), XTAI (Taiwan), XSHG (Shanghai), XSHE (Shenzhen) |
| `company_name` | No | Display label; the backend should resolve identity from exchange and stock code |
| `current_holding_value` | Yes | Current total market value of the position in its stated currency; not share price or cost basis |
| `currency` | Yes | HKD, CNY or TWD; never guess from a currency symbol |
| `as_of_date` | Yes | Valuation date in YYYY-MM-DD format; use a common date for the comparison |

The sample DEMO-* stock codes deliberately do not identify real tradable securities. A live service would need a fixture mode to accept them. The browser importer also supports ticker/name broker exports and normalized headers such as Total Market Value (SEK); it uses that header currency, not the underlying security currency, to avoid double conversion. Funds and cash are retained for valuation, with analysis unavailable.

The imported amount means current holding value. If a platform only exports original invested capital, request quantity and a valuation price or a current-value export before computing current portfolio weights. Do not silently interpret cost basis as market value.

FX conversion is performed against the chosen reporting currency before weighting. The illustrative rates in the JSON files are 1 HKD = 1 HKD, 1 TWD = 0.25 HKD, and 1 CNY = 1.10 HKD. These are arbitrary mock rates, not current quotes. A real response should identify its FX source and valuation date.

The four sample rows convert to HKD 28,000 + 24,000 + 20,000 + 22,000 = HKD 94,000. Weight = converted holding value / total converted holding value.

The browser preview accepts positive-value equities, funds and cash. It preserves every row rather than silently dropping holdings; it does not resolve security identities or merge duplicate rows across accounts. Mixed valuation dates and invalid amounts are rejected. A live backend must define identifier resolution, duplicate handling, supported currencies, cash analysis, short positions and leveraged products before providing analytical results.

## Response examples

- [current-portfolio.json](current-portfolio.json): current holdings, preferences and aggregate metrics.
- [stock-recommendations.json](stock-recommendations.json): two illustrative candidates linked to the current portfolio and preferences.
- [company-details.json](company-details.json): details of the first candidate, Verdant Solar.
- [simulated-portfolio.json](simulated-portfolio.json): an immutable baseline, a new-money simulation and metric changes.

The simulation adds HKD 10,000 to Verdant Solar. The portfolio value becomes HKD 104,000; existing position values stay unchanged and all weights are recomputed. No real orders or payments occur. The example assumes the full amount is invested without fees, taxes or board-lot constraints.

The mock portfolio expected return is the value-weighted mean of fixed fictional company forecasts. These forecasts are assumed to share the same 12-month horizon and HKD reporting basis, with FX effects already reflected in the fictional values. This is not an estimated factor model. The mock green score is also a weighted mean; it replaces none of the backend's pending model definitions.

All metrics use the same valuation date and model version when compared. Changes in preferences, prices, FX, forecast horizon or model version require recalculating the baseline and simulation together.

### Units and formatting

- `weight`, `expectedReturn` and `greenDataCoverage` use fractions: 0.08 displays as 8%.
- Return deltas also use fractions: a delta of 0.005 displays as +0.5 percentage points, not +0.5% relative growth.
- `eScore` and `greenScore` use points on the proposed 0–10 scale.
- Preference fields use integers on the confirmed 1–5 scale; model mapping remains pending.
- Monetary amounts carry a currency; `fxRateToBase` is reporting-currency units per one holding-currency unit.
- Use sufficient internal precision and round only for display; displayed weights may not sum to exactly 100% due to rounding.

Higher E-score means more environmentally friendly. Higher expected return or higher preference values should not receive an automatic universal "better" label. Keep return, environmental performance and risk separate.

### Missing data

Each metric has a `status`, `value` and `unit`. `available` metrics have numeric values. `partial` and `unavailable` metrics have `value: null`; never convert missing values to zero. A `reasonCode` explains the state.

For a partially scored portfolio, show the full-portfolio score as unavailable/partial and show data coverage separately. If a covered-assets-only mean is provided, use a separate field and label its limited denominator explicitly. Missing FX or holding values also prevent treating the portfolio valuation as complete.

Example missing company metric:

```json
{
  "status": "unavailable",
  "value": null,
  "unit": "score_0_to_10",
  "reasonCode": "MISSING_ENVIRONMENTAL_DATA"
}
```

Volatility in the fixtures is explicitly unavailable. Do not fill it with a weighted mean of company volatilities or assume zero correlations without an agreed model. Do not imply quantitative risk matching from an unavailable risk estimate.

## Proposed API routes

These route names are placeholders for discussion, not callable endpoints:

| Method | Route | Intended operation |
| --- | --- | --- |
| POST | `/api/v1/portfolios/import` | Upload CSV plus reporting currency and preferences; validate rows and create a baseline |
| GET | `/api/v1/portfolios/{id}` | Return the current portfolio analysis |
| POST | `/api/v1/portfolios/{id}/recommendations` | Generate candidates using the current preferences |
| GET | `/api/v1/companies/{id}` | Return company details on a specified valuation date, horizon and reporting-currency basis |
| POST | `/api/v1/portfolios/{id}/simulations` | Return a new simulated portfolio without mutating the baseline |

Example simulation request:

```json
{
  "stockId": "demo-verdant-solar",
  "amount": 10000,
  "currency": "HKD",
  "fundingMode": "new_money",
  "preferences": { "riskLevel": 3, "greenPreference": 4 }
}
```

Proposed HTTP semantics: 400 for malformed payloads, 422 for validation failures, 404 for unresolved resources, and 503 for temporarily unavailable analysis. A queued calculation can use 202 only after a job/polling contract is agreed. Exact error codes, authentication, processing times and delivery date remain unconfirmed.

Example validation error:

```json
{
  "schemaVersion": "draft-0.1",
  "error": {
    "code": "INVALID_IMPORT",
    "message": "Correct the highlighted portfolio rows.",
    "retryable": false,
    "fields": [
      {
        "row": 2,
        "field": "current_holding_value",
        "code": "VALUE_MUST_BE_POSITIVE"
      }
    ]
  }
}
```

During loading or failure, preserve the imported portfolio and simulation draft. Clear or mark old results as stale when inputs change; only compare results for matching inputs and model conventions.
