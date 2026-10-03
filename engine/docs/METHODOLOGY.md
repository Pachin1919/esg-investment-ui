# Methodology: the papers behind the ESG Exposure Engine

Every number the product produces traces to published research. This document lists the
concepts we use, the paper each comes from, and exactly how it is implemented in the code.
Pointers use `path:line`-free references to modules; the authoritative source is always the
module docstring.

| Paper | Concept | Where in the product |
|---|---|---|
| Pástor, Stambaugh & Taylor (2022, JFE) | Greenness `g`, GMB factor, across/within decomposition | `measures/greenness.py`, `factors/gmb.py`, `portfolio/exposures.py` |
| Bolton & Kacperczyk (2021, JFE) | Carbon premium: emissions level *and* growth are priced | `factors/famamacbeth.py`, `measures/walk_hard.py` |
| Crosignani, Osambela & Pritsker (2025) | Emission *intensity* as the priced characteristic | `measures/walk_hard.py` |
| Fama & MacBeth (1973); Newey & West (1987) | Two-pass cross-sectional pricing; HAC standard errors | `factors/famamacbeth.py`, `factors/timeseries.py` |
| Fama & French (2015); Carhart (1997) | FF5 + momentum risk model | `ingest/factors.py`, `factors/timeseries.py`, `factors/build_local.py` |
| Jegadeesh & Titman (1993) | 12–2 momentum, skipping the most recent month | `factors/build_local.py` |
| Merton (1980) | Sample mean returns are unusable; factor-based `mu` | `portfolio/optimize.py` |
| Engle, Giglio, Kelly, Lee & Stroebel (2020, RFS) | Climate-news hedging; cosine similarity to climate vocabulary | `measures/text_measures.py`, `ingest/news_gdelt.py` |
| Loughran & McDonald (2011, JF) | Finance-specific sentiment dictionary | `measures/text_measures.py` |
| Giannetti et al. (2023) | Greenwashing = talk *given* walk; glossy-talk measure | `measures/residual.py`, `measures/standardize.py`, `measures/text_measures.py` |
| Gourier & Mathurin (2025) | LLM prompt discipline; salience; low-threshold segment inclusion | `pipeline/tools/llm_sources.py`, `portfolio/screen.py`, `measures/talkwalk.py` |
| Liang, Sun & Teo (2022); Chen (2022, 2025) | Words-vs-actions gap; talk/walk rubric dimensions | `measures/talkwalk.py`, `measures/greenwash.py` |
| Berg, Koelbel & Rigobon (2022, RFS) | ESG ratings diverge (56% measurement, 38% scope, 6% weight) | Motivation for the deterministic design, `brain/PLAN.md` |
| Bellon & Boualam | Tilting beats divestment | Long-only tilt as the default product, `portfolio/tilt.py` |

---

## 1. Measurement: talk, walk, greenness

### Greenness à la Pástor–Stambaugh–Taylor (2022, "Dissecting Green Returns", JFE)

**Paper.** PST construct a greenness measure `g = −(10 − E_score)·E_weight/100`, where
E_score (0–10) is the firm's environmental score and E_weight (0–100) is how material the
environmental pillar is for the firm's *industry* (at MSCI, an expert judgment: Exxon ≈ 48,
Best Buy ≈ 11). The weight stops a mediocre oil company and a mediocre retailer from looking
equally green. PST decompose `g` into an across-industry part (`g_across`, the industry mean)
and a within-industry part (`g_within`, the firm's deviation) — and find almost all of the
green outperformance sits in the across component.

**In the product.** `measures/greenness.py` implements the formula and the decomposition
(`greenness_table`). Because we have no MSCI license, both inputs are computed from data:
E_score **is the deterministic walk score** (percentile of emission intensity within
industry × year, `scores_from_walk`), so one objective number feeds the greenwashing flag,
greenness, the GMB factor and the return tests. E_weight is the industry's aggregate
emission intensity, percentile-ranked across industries per year and mapped to 5–50
(`industry_weight`). First Taiwan run: 1,960 companies, Cement 50 … Electronic Products
Distribution 6.

### Walk from hard data — Bolton & Kacperczyk (2021, JFE) and Crosignani, Osambela & Pritsker (2025)

**Papers.** Bolton–Kacperczyk show that both the *level* and the *growth* of carbon
emissions carry a return premium — so a walk measure must track level and trends.
Crosignani et al. show the priced characteristic is emission *intensity* (tCO2e / revenue),
and model it as a random walk — one-year changes are mostly noise.

**In the product.** `measures/walk_hard.py`: `walk` = percentile score of scope-1 intensity
within industry × year (0–10). The trend components (`intensity_trend`, `emission_trend`)
are computed and reported separately — per Crosignani they are noisy — but never blended
into the headline walk score, because no paper blends them. Firms without registry-matched
emissions get **no** walk score rather than a favourable one. Extra pillars (water, waste,
renewable share) follow the same percentile design in `measures/walk_pillars.py`.

### Greenwashing = talk *given* walk — Giannetti et al. (2023), Liang–Sun–Teo (2022), Chen (2025)

**Papers.** The literature defines greenwashing not as "talks green" but as *talk in excess
of what the firm's actions explain*: Giannetti et al. compare disclosure to lending
behaviour, Liang et al. compare PRI signatories' words to their holdings.

**In the product.** Two implementations. `measures/greenwash.py` + `measures/gap.py`:
double-sort / percentile gap on the 0–10 scores, standardized within industry × year
(`measures/standardize.py`, following Giannetti's per-year normalization and PST's
within-industry demeaning). `measures/residual.py`: the direct version — pooled OLS of
log talk on log intensity, Δlog intensity, log document length and industry × year fixed
effects; `excess_talk` is the residual. Whether excess talk is *cheap talk* is an empirical
question, answered by `validation.predictive_regression`: excess talk followed by falling
emissions is credible signalling; otherwise it is greenwashing.

### Climate vocabulary and glossy talk — Engle et al. (2020, RFS), Loughran–McDonald (2011, JF)

**Papers.** Engle, Giglio, Kelly, Lee & Stroebel hedge climate-change news using a climate
vocabulary and cosine similarity. Loughran–McDonald built the standard finance sentiment
dictionary (generic sentiment dictionaries misclassify financial text).

**In the product.** `measures/text_measures.py`: `climate_similarity` = cosine between a
document's term counts and the Engle et al. vocabulary; `glossiness` = a two-step measure
(cosine gate on the climate vocabulary, then LM sentiment around environment terms —
the Giannetti et al. glossy-talk design); the low-threshold segment-inclusion rule follows
Gourier & Mathurin (2025). GDELT news search (`ingest/news_gdelt.py`) uses an ESG query in
the same spirit for the news talk channel.

---

## 2. Factors and return tests

### The GMB factor — Pástor–Stambaugh–Taylor (2022)

**Paper.** PST build the green-minus-brown factor two ways: sorted portfolios (green tercile
minus brown tercile, value-weighted, monthly) and a cross-sectional regression of
market-adjusted excess returns on `g` (the return of a characteristic-mimicking portfolio).

**In the product.** `factors/gmb.py` implements both (`gmb_sorted`, `gmb_regression`).
Our regression version additionally accepts **cross-sectional controls** (size, momentum,
industry dummies): the monthly `g`-slope is then the return of the factor-mimicking
portfolio *neutral to those characteristics* — the risk-neutralized green premium, rather
than a sector bet. Market betas use a trailing 60-month window shifted to t−1 (no
look-ahead). PST's interpretation frames the reporting: realized green outperformance is
driven by climate-concern shocks, while the ex-ante expected premium on green assets is
*negative* — green assets are hedges, and investors accept lower expected returns for them.

### The carbon premium — Fama & MacBeth (1973), Newey & West (1987), Bolton & Kacperczyk (2021)

**Paper.** Fama–MacBeth: run a cross-sectional regression each period, then average the
slope time series; a slope is the return of a zero-cost characteristic-mimicking portfolio.
Newey–West: heteroskedasticity- and autocorrelation-consistent standard errors on that
average. Bolton–Kacperczyk apply it to emissions with the *lagged* specification
(year t−1 emissions, year t returns); contemporaneous monthly specs are biased toward zero.

**In the product.** `factors/famamacbeth.py` implements the two-pass estimator with NW
t-stats and enforces the lagged annual design (`annual_returns` compounds monthly prices).
`factors/timeseries.py` runs per-series alpha regressions on FF5+MOM(+GMB) with 6-lag NW
errors — used both for factor validation and for the portfolio's own `b_gmb`.

### The risk model — Fama & French (2015), Carhart (1997), Jegadeesh & Titman (1993), Merton (1980)

**Papers.** FF5 plus momentum is the standard empirical risk model. Momentum is the prior
12–2 month return (skipping the most recent month). Merton (1980): mean returns are
estimated far too noisily to use as optimizer inputs.

**In the product.** Ken French's published FF5+MOM series via `ingest/factors.py`
(US and **Asia Pacific ex Japan**, the file that covers Hong Kong). For markets Ken French
does not cover (Taiwan), `factors/build_local.py` constructs the local set with the same
recipes: value-weighted market minus the local risk-free, median-split SMB, 30/70 HML, and
12–2 tercile MOM. Expected returns and covariance for the optimizer are always factor-based
(`mu = B·mu_f`, `Σ = BFB′ + D` from the FF5+MOM+GMB betas) — never sample moments.

---

## 3. Portfolio construction

- **Green exposures**: per-asset time-series regressions of returns on FF5+MOM+GMB give
  `b_gmb` — the return sensitivity to the green factor (`portfolio/exposures.py`). A stock
  can be brown (negative `g`) yet have positive `b_gmb`; the tilt uses the characteristic,
  the risk model uses the exposure. Positive `b_gmb` = hedges climate-concern shocks (PST).
- **Tilt beats divestment** (Bellon–Boualam): the default product is a long-only tilt
  `w ∝ w_index·exp(λ·z(g))` (`portfolio/tilt.py`) — underweighting brown vs the benchmark
  is economically a benchmark-relative short, without short-selling frictions. The GMB
  factor itself remains the long-short measurement and hedging instrument.
- **Mean-variance with a green term** (`portfolio/optimize.py`): `max w′mu − γ/2·w′Σw +
  λ·w′z(g)`, long-only, capped, with an exact linear turnover penalty `κ·|w − w0|` so the
  user's current portfolio is the default and every recommended trade must earn its cost.

---

## 4. How the LLM is allowed to touch any of this — Gourier & Mathurin (2025)

**Paper.** Gourier & Mathurin's discipline for LLM text work: the model chooses only from
what is supplied; it must not infer, invent or speculate.

**In the product.** Every LLM task is scoped, structured and auditable:

- **Extraction** (scope 1/2 from HKEX PDFs, `ingest/emissions_hk.py`): page numbers +
  verbatim quotes required, cached per (document, model, extraction version).
- **Talk/walk rubric** (`measures/talkwalk.py`): fixed versioned rubric (0–10 sub-scores
  following Chen 2022, Giannetti 2023, Liang 2022, Gourier-Mathurin 2025), pydantic
  structured output, hard data passed in so the model checks claims against facts; cache
  key includes rubric version, model and prompt variant, so re-runs are free and
  comparable.
- **Screening agent** (`portfolio/screen.py`): free-text preferences are translated into a
  filter choosing only from the universe's *actual* sector/industry/country values; the
  output is sanitized and applied deterministically. The model proposes, the code disposes.
- **Provider neutrality** (`esgx.llm`): Kimi K3 primary, Claude as a second rater; the
  model id is part of every cache key so raters never mix.

The design rule: **AI where judgment is needed, math where it is not.** Downstream of a
score, everything — factors, exposures, optimization — is deterministic and reproducible.

---

## 5. Cross-cutting rigour

- **No look-ahead**: emissions become effective with an 18-month publication lag
  (`measures/carbon.align_annual_to_months`); all betas are shifted to t−1; B/M follows the
  same July-t+1 rule as the greenness panel.
- **Deterministic first**: deterministic talk/walk/greenwashing scores exist for the whole
  universe with no LLM at all; LLM measures layer on top, versioned and cached.
- **Validation as a first-class output**: Fama–MacBeth premium tables, with/without
  super-emitter robustness, and the predictive regression on excess talk are part of the
  pipeline, not an afterthought. See `brain/analys/` for the literature map (83 papers)
  behind these choices.

## References

- Pástor, Ľ., Stambaugh, R. F., & Taylor, L. A. (2022). Dissecting green returns. *Journal of Financial Economics*.
- Bolton, P., & Kacperczyk, M. (2021). Do investors care about carbon risk? *Journal of Financial Economics*.
- Crosignani, M., Osambela, E., & Pritsker, M. (2025). Working paper on emission intensity pricing.
- Fama, E. F., & MacBeth, J. D. (1973). Risk, return, and equilibrium: Empirical tests. *Journal of Political Economy*.
- Fama, E. F., & French, K. R. (2015). A five-factor asset pricing model. *Journal of Financial Economics*.
- Carhart, M. M. (1997). On persistence in mutual fund performance. *Journal of Finance*.
- Jegadeesh, N., & Titman, S. (1993). Returns to buying winners and selling losers. *Journal of Finance*.
- Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*.
- Merton, R. C. (1980). On estimating the expected return on the market. *Journal of Financial Economics*.
- Engle, R. F., Giglio, S., Kelly, B., Lee, H., & Stroebel, J. (2020). Hedging climate change news. *Review of Financial Studies*.
- Loughran, T., & McDonald, B. (2011). When is a liability not a liability? Textual analysis, dictionaries, and 10-Ks. *Journal of Finance*.
- Berg, F., Koelbel, J. F., & Rigobon, R. (2022). Aggregate confusion: The divergence of ESG ratings. *Review of Finance*.
- Giannetti, M., et al. (2023). Working paper on glossy talk vs lending behaviour.
- Gourier, G., & Mathurin, T. (2025). Working paper on LLM-based text classification for sustainable finance.
- Liang, H., Sun, L., & Teo, M. (2022). Working paper on PRI signatories' words vs holdings.
- Chen (2022, 2025). Talk/walk greenwashing measures (see `measures/talkwalk.py` docstring).
